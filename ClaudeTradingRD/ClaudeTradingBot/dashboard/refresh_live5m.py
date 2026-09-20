"""Per-SECOND live feed for Polymarket's rolling 5-min BTC Up/Down market.

Writes dashboard/live5m.json roughly once per second with the current
window's live BUY COST for each side (Up / Down) + mid + seconds-left, so the
dashboard can tick the bet price every second like Polymarket. Token IDs are
cached per window, so each tick is only ~2-3 Polymarket CLOB calls — separate
from the heavier 15s bets feed and the 60s broker refresh.

Run:  ...\\.venv\\Scripts\\python.exe dashboard\\refresh_live5m.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from bot import polymarket, kalshi, arbitrage, pm_strategy, paper_pm  # noqa: E402

OUT_PATH = os.path.join(ROOT, "dashboard", "live5m.json")
LOG_PATH = os.path.join(ROOT, "journal", "arb15m_log.csv")
INTERVAL = 1.0  # seconds
_LOG_HEADER = ("ts,spot,poly5m_up,poly15m_up,kalshi15m_up,poly15m_down,"
               "kalshi15m_down,lock_cost,gross_edge,net_edge,window_end\n")


def _log_row(live, arb):
    """Append one per-second row for offline convergence/edge validation."""
    p5 = live.get("poly_5m") or {}
    p15 = live.get("poly_15m") or {}
    k15 = live.get("kalshi_15m") or {}
    row = [live.get("generated_at"), live.get("btc_spot"),
           p5.get("up_cost"), p15.get("up_cost"), k15.get("up_cost"),
           p15.get("down_cost"), k15.get("down_cost"),
           arb.get("lock_cost"), arb.get("gross_edge"), arb.get("net_edge_after_fees"),
           p15.get("window_end")]
    new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        if new:
            f.write(_LOG_HEADER)
        f.write(",".join("" if v is None else str(v) for v in row) + "\n")
_S = requests.Session()
_S.headers.update({"User-Agent": "ClaudeTradingBot/1.0"})


def _btc_spot():
    """Live BTC spot mid from Binance public ticker (fast, 1 call)."""
    try:
        r = _S.get("https://api.binance.com/api/v3/ticker/bookTicker",
                   params={"symbol": "BTCUSDT"}, timeout=6)
        if r.ok:
            d = r.json()
            bid, ask = float(d["bidPrice"]), float(d["askPrice"])
            return round((bid + ask) / 2, 2)
    except Exception:
        pass
    return None


# Short-TTL cache for book asks so the per-second feed doesn't refetch BOTH venues'
# order books (4 extra HTTP calls) every tick. A 15m book moves slowly, so ~5s
# staleness is harmless for both the display and the gate. Keyed by token /
# ticker+side; keys from rolled-over windows are pruned opportunistically.
_ASK_TTL = 5.0
_ASK_CACHE = {}  # key -> (ts, (price, size))


def _cached_ask(key, fetch):
    now = time.time()
    hit = _ASK_CACHE.get(key)
    if hit and now - hit[0] < _ASK_TTL:
        return hit[1]
    val = fetch() or (None, 0)
    _ASK_CACHE[key] = (now, val)
    for k in [k for k, (ts, _v) in _ASK_CACHE.items() if now - ts > 120]:
        del _ASK_CACHE[k]
    return val


_FWD_LOG = os.path.join(ROOT, "journal", "forward_edge_log.csv")


def _research_block():
    """Running read of the Kalshi-only momentum candidate from the forward log:
    buy the FAVORITE (higher-ask side) at its real ask, settle on Kalshi's actual
    direction; report n, favorite win-rate, mean net $/contract after fee, and the
    basis-break rate (venues disagreeing). None until any window has settled."""
    import csv
    if not os.path.exists(_FWD_LOG):
        return {"n": 0, "note": "forward collector started — no settled windows yet"}
    n = wins = breaks = 0
    net = 0.0
    try:
        with open(_FWD_LOG, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    ku = float(r.get("k_up_ask") or "nan")
                    kd = float(r.get("k_dn_ask") or "nan")
                except ValueError:
                    continue
                ks, ps = r.get("k_settle"), r.get("p_settle")
                if ks not in ("UP", "DOWN") or ku != ku or kd != kd:
                    continue
                n += 1
                if ps in ("UP", "DOWN") and ks != ps:
                    breaks += 1
                fav_ask = max(ku, kd)
                won = (("UP" if ku > kd else "DOWN") == ks)
                fee = 0.07 * fav_ask * (1 - fav_ask)
                net += ((1 - fav_ask) if won else -fav_ask) - fee
                wins += 1 if won else 0
    except Exception:  # noqa: BLE001
        return {"n": 0, "note": "forward log unreadable"}
    if n == 0:
        return {"n": 0, "note": "no settled windows scored yet"}
    return {"n": n, "fav_win_pct": round(100 * wins / n, 1),
            "mean_net_per_ct": round(net / n, 4),
            "basis_break_pct": round(100 * breaks / n, 1),
            "need": 300}


def write_once():
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return None
    live = {
        "poly_5m": _safe(lambda: polymarket.updown_window_live("5m", 300)),
        "poly_15m": _safe(lambda: polymarket.updown_window_live("15m", 900)),
        "kalshi_15m": _safe(kalshi.updown_live),
        "btc_spot": _btc_spot(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    arb = _safe(lambda: arbitrage.cross_venue_15m(
        live["poly_15m"], live["kalshi_15m"])) or {}
    live["arb15m"] = arb
    # Enrich the 15m legs with REAL book asks + sizes (price+depth) so the shared
    # gate sees what can actually fill — not the last-trade quote. Read-only.
    # Fetches go through _cached_ask (short TTL) so the per-second feed doesn't
    # refetch both venues' books every tick.
    def _enrich_poly(p15):
        if not p15:
            return
        for side, tok in (("up", p15.get("up_token")), ("down", p15.get("down_token"))):
            if tok:
                px, sz = _cached_ask(
                    ("poly", tok),
                    lambda tok=tok: _safe(lambda: polymarket.book_ask(tok)))
                p15[f"{side}_ask"], p15[f"{side}_ask_size"] = px, sz
    def _enrich_kalshi(k15):
        if not k15 or not k15.get("ticker"):
            return
        tk = k15["ticker"]
        for side in ("up", "down"):
            kside = "yes" if side == "up" else "no"
            px, sz = _cached_ask(
                ("kalshi", tk, kside),
                lambda kside=kside: _safe(lambda: kalshi.book_ask(tk, kside)))
            k15[f"{side}_ask"], k15[f"{side}_ask_size"] = px, sz
    _safe(lambda: _enrich_poly(live.get("poly_15m")))
    _safe(lambda: _enrich_kalshi(live.get("kalshi_15m")))
    try:
        _log_row(live, arb)
    except Exception:
        pass
    # Advance the dedicated PM paper account (auto-trades the lock when net>0).
    try:
        pm_strategy.step(live)
        acc = paper_pm.load()
        hist = acc["history"]
        live["pm"] = {
            "summary": paper_pm.account(acc),
            "open": acc["positions"],
            "history": list(reversed(hist[-25:])),  # most recent first
            # REAL-settlement outcome breakdown (paper now settles on each venue's
            # actual resolution, so basis breaks are real here):
            "breaks": sum(1 for h in hist if h.get("payout_per_unit") == 0.0),
            "windfalls": sum(1 for h in hist if h.get("payout_per_unit") == 2.0),
            "normals": sum(1 for h in hist if h.get("payout_per_unit") == 1.0),
        }
    except Exception as e:
        live["pm_error"] = str(e)
    # Forward edge-test read (the only not-yet-killed candidate, scored on REAL
    # executable asks + true settlements as they accumulate).
    live["research"] = _research_block()
    # Live execution account (read-only): real-money balances + recorded locks.
    try:
        from bot import live_strategy
        # 30s cache: balances/positions/orders barely move (esp. kill-switched), and
        # a per-tick refetch was the feed's dominant cost (each tick > the old 8s
        # cache, so it refetched BOTH venues every tick). The gate-watch reads the
        # per-tick quote/book data, not this panel, so 30s freshness is plenty.
        live["live"] = live_strategy.account_snapshot(30.0)
    except Exception as e:
        live["live_error"] = str(e)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(live, f)
    os.replace(tmp, OUT_PATH)


def main():
    once = "--once" in sys.argv
    while True:
        t0 = time.time()
        try:
            write_once()
        except Exception as e:
            print(f"[live5m] WARN {e}", file=sys.stderr, flush=True)
        if once:
            return
        # keep a steady ~1s cadence regardless of fetch latency
        time.sleep(max(0.2, INTERVAL - (time.time() - t0)))


if __name__ == "__main__":
    main()
