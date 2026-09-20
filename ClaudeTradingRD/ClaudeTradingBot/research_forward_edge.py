"""FORWARD edge-test data collector (read-only, no orders).

The earlier edge tests were crippled by two things: a thin sample (~144 windows)
and CSV columns that logged Kalshi's LAST TRADE, not the executable book ask. This
logger fixes both. For each 15m BTC up/down window it records, ONCE at a fixed mark
(~180s before close), the REAL executable asks on both venues, then after the window
resolves it records each venue's ACTUAL settled direction. Over days this builds a
clean dataset to test the only not-yet-dead candidate -- Kalshi-only momentum -- on
prices you could actually trade and settlements that actually happened.

Row (journal/forward_edge_log.csv): window_end, mark_secs_left, spot, k_up_ask,
k_up_sz, k_dn_ask, k_dn_sz, p_up_ask, p_up_sz, p_dn_ask, p_dn_sz, k_settle, p_settle.

Run:  DRY_RUN=true .venv/Scripts/python.exe research_forward_edge.py
"""
import csv
import os
import time
from datetime import datetime, timezone

from bot import kalshi as K, polymarket as P

LOG = "journal/forward_edge_log.csv"
HEAD = ["window_end", "mark_secs_left", "spot", "k_up_ask", "k_up_sz", "k_dn_ask",
        "k_dn_sz", "p_up_ask", "p_up_sz", "p_dn_ask", "p_dn_sz", "k_settle", "p_settle"]
MARK_LO, MARK_HI = 120, 240   # capture once while in this seconds-left band
POLL = 11.0


def _spot():
    import requests
    try:
        return float(requests.get("https://api.binance.com/api/v3/ticker/price",
                                  params={"symbol": "BTCUSDT"}, timeout=6).json()["price"])
    except Exception:  # noqa: BLE001
        return None


def _done_windows():
    done = set()
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                done.add(r["window_end"])
    return done


def _append(row):
    new = not os.path.exists(LOG)
    os.makedirs("journal", exist_ok=True)
    with open(LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEAD)
        if new:
            w.writeheader()
        w.writerow(row)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _running_test():
    """Score the only-not-dead candidate on the REAL data collected so far:
    Kalshi-only momentum = buy the FAVORITE (higher-ask side) at its real ask,
    settle on Kalshi's ACTUAL direction. PnL/contract = (1-ask) if it won else -ask,
    minus the Kalshi taker fee. Reports running mean + the basis-break rate. A real
    edge needs the mean clearly > 0 over a few hundred windows."""
    rows = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    n = wins = breaks = 0
    net = 0.0
    for r in rows:
        ku, kd = _f(r.get("k_up_ask")), _f(r.get("k_dn_ask"))
        ks, ps = r.get("k_settle"), r.get("p_settle")
        if ku is None or kd is None or ks not in ("UP", "DOWN"):
            continue
        n += 1
        if ps in ("UP", "DOWN") and ks != ps:
            breaks += 1
        fav_ask = max(ku, kd)
        fav = "UP" if ku > kd else "DOWN"
        won = (fav == ks)
        fee = 0.07 * fav_ask * (1 - fav_ask)   # ~Kalshi taker fee per contract
        net += ((1 - fav_ask) if won else -fav_ask) - fee
        wins += 1 if won else 0
    if n == 0:
        return "forward test: no settled windows scored yet"
    return ("forward test n=%d | favorite win %.0f%% | mean net $%+.4f/contract "
            "| basis-break %.0f%% | (need ~300 windows for a confident verdict)"
            % (n, 100 * wins / n, net / n, 100 * breaks / n))


def main():
    done = _done_windows()
    pending = {}   # window_end -> captured-but-not-yet-settled row
    print(f"[forward] logging to {LOG} | {len(done)} windows already recorded")
    while True:
        try:
            p15 = P.updown_window_live("15m", 900) or {}
            k15 = K.updown_live() or {}
            we = p15.get("window_end")
            sl = p15.get("seconds_left")
            ticker = k15.get("ticker")
            # 1) capture at the mark, once per window
            if (we and we not in done and we not in pending and sl is not None
                    and MARK_LO <= sl <= MARK_HI and ticker):
                kua, kus = K.book_ask(ticker, "yes")
                kda, kds = K.book_ask(ticker, "no")
                pua, pus = P.book_ask(p15.get("up_token")) if p15.get("up_token") else (None, 0)
                pda, pds = P.book_ask(p15.get("down_token")) if p15.get("down_token") else (None, 0)
                pending[we] = {
                    "window_end": we, "mark_secs_left": sl, "spot": _spot(),
                    "k_up_ask": kua, "k_up_sz": kus, "k_dn_ask": kda, "k_dn_sz": kds,
                    "p_up_ask": pua, "p_up_sz": pus, "p_dn_ask": pda, "p_dn_sz": pds,
                    "_ticker": ticker, "_slug": p15.get("slug"),
                    "k_settle": "", "p_settle": "",
                }
                print(f"[forward] captured {we} @ {sl}s: "
                      f"k_up {kua}/{kda} p_up {pua}/{pda}")
            # 2) settle pending windows once both venues resolve
            now = datetime.now(timezone.utc).isoformat()
            for wk in list(pending):
                row = pending[wk]
                if now < wk:
                    continue   # window not closed yet
                ks = K.settled_direction(row["_ticker"])
                ps = P.settled_direction(row["_slug"]) if row.get("_slug") else None
                if ks and ps:
                    row["k_settle"], row["p_settle"] = ks, ps
                    _append({k: row[k] for k in HEAD})
                    done.add(wk)
                    del pending[wk]
                    brk = " *** BASIS BREAK (venues disagree)" if ks != ps else ""
                    print(f"[forward] settled {wk}: kalshi={ks} poly={ps}{brk} "
                          f"({len(done)} recorded)")
                    print("[forward] " + _running_test())
        except Exception as e:  # noqa: BLE001
            print(f"[forward] WARN {str(e)[:120]}")
        time.sleep(POLL)


if __name__ == "__main__":
    main()
