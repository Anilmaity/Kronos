"""Kalshi live odds (read-only, public trade API — no auth for market data).

Kalshi runs BTC threshold markets under series KXBTCD ("Bitcoin price on
<date>?", a Yes settles above the strike). In this environment the resting
ORDER BOOKS come back empty, but the /markets/trades feed is live and updates
every few seconds — so we derive the real-time implied 'prob BTC above $X'
CDF from each strike's most recent executed trade (yes_price_dollars).

CLI:  python -m bot.kalshi
"""
import re
import requests

API = "https://api.elections.kalshi.com/trade-api/v2"
_TIMEOUT = 20
_S = requests.Session()
_S.headers.update({"User-Agent": "ClaudeTradingBot/1.0"})


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get(path, **params):
    r = _S.get(f"{API}{path}", params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _markets(series_ticker, status="open", limit=200):
    return _get("/markets", series_ticker=series_ticker,
                status=status, limit=limit).get("markets", [])


def _strike(m):
    """Dollar threshold from floor_strike or the ticker tail (…-T64000.00)."""
    fs = m.get("floor_strike") or m.get("cap_strike")
    if isinstance(fs, (int, float)):
        return float(fs)
    mt = re.search(r"-T([\d.]+)$", m.get("ticker", ""))
    return float(mt.group(1)) if mt else None


def _last_trade(ticker):
    """Most recent executed trade for a market: (yes_prob 0..1, time) or (None, None)."""
    try:
        d = _get("/markets/trades", ticker=ticker, limit=1)
        ts = d.get("trades") or []
        if ts:
            yp = ts[0].get("yes_price_dollars")
            return (float(yp) if yp is not None else None,
                    ts[0].get("created_time"))
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None, None


def _ask_from_book(data, side):
    """Best executable ASK (price 0..1, size contracts) for BUYING `side`
    ('yes'/'no') from a Kalshi orderbook payload. To buy a side you cross the
    OPPOSITE side's best (highest) resting bid: ask = 1 - best_opposite_bid.

    The CURRENT API returns depth under `orderbook_fp` as {yes_dollars, no_dollars},
    each level [price_DOLLARS_str, size_str] (sizes may be fractional). The legacy
    `orderbook` field (cents) is now empty/None, so the old reader saw every BTC
    book as empty -> a false 'no book'. Prefer orderbook_fp; fall back to legacy
    cents. (None, 0) if that side has no resting bid. Size is FLOORED to whole
    contracts so we never claim more than rests."""
    data = data or {}
    opp = "no" if side == "yes" else "yes"
    fp = data.get("orderbook_fp") or {}
    levels = fp.get(f"{opp}_dollars")
    if levels:
        best = max(levels, key=lambda lvl: float(lvl[0]))
        return round(1.0 - float(best[0]), 4), int(float(best[1]))
    ob = data.get("orderbook") or {}
    levels = ob.get(opp) or []
    if not levels:
        return None, 0
    best = max(levels, key=lambda lvl: lvl[0])
    return round(1.0 - best[0] / 100.0, 4), int(best[1])


def book_ask(ticker, side):
    """Live best ask (price 0..1, size) for buying `side` on a Kalshi market.
    Read-only GET (safe in DRY_RUN / with kill switch on). (None, 0) on error."""
    side = side.lower()
    try:
        data = _get(f"/markets/{ticker}/orderbook")
        return _ask_from_book(data, side)
    except Exception:  # noqa: BLE001
        return None, 0


def settled_direction(ticker):
    """'UP' / 'DOWN' once a KXBTC15M market is FINALIZED on Kalshi's OWN index,
    else None (not yet resolved / unknown). For the up/down market, result 'yes' =
    UP (settled above the window-open reference), 'no' = DOWN. Read-only; used to
    settle the paper lock on the REAL per-venue outcome so it catches basis breaks
    (when this disagrees with Polymarket's Chainlink resolution, both legs lose)."""
    try:
        m = _get(f"/markets/{ticker}").get("market", {})
    except Exception:  # noqa: BLE001
        return None
    if m.get("status") != "finalized":
        return None
    return {"yes": "UP", "no": "DOWN"}.get(m.get("result"))


def btc_threshold_cdf(series_ticker="KXBTCD", spot=None, window=12, max_strikes=14):
    """Real-time 'prob BTC above $X' CDF from each strike's last trade.

    Pulls the open T-type strikes nearest `spot` (or nearest the median strike
    if spot is unknown), then queries each one's latest trade. Cheap: bounded
    to `max_strikes` trade calls per refresh.
    """
    mkts = [m for m in _markets(series_ticker) if "-T" in m.get("ticker", "")]
    strikes = [(m, _strike(m)) for m in mkts]
    strikes = [(m, s) for m, s in strikes if s is not None]
    if not strikes:
        return {"series": series_ticker, "levels": [], "implied_pivot": None}

    center = spot if spot else sorted(s for _, s in strikes)[len(strikes) // 2]
    near = sorted(strikes, key=lambda ms: abs(ms[1] - center))[:max_strikes]

    levels = []
    close_time = None
    for m, s in near:
        prob, ttime = _last_trade(m["ticker"])
        if prob is None:
            continue
        close_time = m.get("close_time") or close_time
        levels.append({"threshold": round(s, 0), "prob_above": round(prob, 4),
                       "ticker": m["ticker"], "trade_time": ttime})
    levels.sort(key=lambda x: x["threshold"])
    return {"series": series_ticker, "levels": levels,
            "implied_pivot": _interp_pivot(levels),
            "settles": close_time,
            "title": levels[0]["ticker"].rsplit("-", 1)[0] if levels else None,
            "as_of": _now()}


def _interp_pivot(levels):
    for i in range(len(levels) - 1):
        a, b = levels[i], levels[i + 1]
        pa, pb = a["prob_above"], b["prob_above"]
        if (pa - 0.5) * (pb - 0.5) <= 0 and pa != pb:
            frac = (pa - 0.5) / (pa - pb)
            return round(a["threshold"] + frac * (b["threshold"] - a["threshold"]), 0)
    return None


# Kalshi's native 15-min BTC Up/Down market (KXBTC15M): "BTC price up in next
# 15 mins?", YES = close >= the window-open target. Directly comparable to
# Polymarket's 5-min Up/Down. One market is open per window; cache its ticker.
_15M_CACHE = {"ts": 0.0, "ticker": None, "close": None, "target": None}


def _current_15m(series_ticker="KXBTC15M", max_age=20):
    import time
    from datetime import datetime, timezone
    now = time.time()
    if _15M_CACHE["ticker"] and now - _15M_CACHE["ts"] < max_age:
        return _15M_CACHE
    try:
        ms = _markets(series_ticker)
    except requests.RequestException:
        return _15M_CACHE if _15M_CACHE["ticker"] else None
    nowiso = datetime.now(timezone.utc).isoformat()
    cur = sorted([m for m in ms if m.get("close_time") and m["close_time"] > nowiso],
                 key=lambda m: m["close_time"])
    if not cur:
        return None
    m = cur[0]
    _15M_CACHE.update(ts=now, ticker=m["ticker"], close=m.get("close_time"),
                      target=m.get("floor_strike"))
    return _15M_CACHE


def updown_live(spot=None):
    """Kalshi 15-min BTC Up/Down (KXBTC15M) as an Up/Down cost pair.

    YES = price up vs the window-open target. Uses the last executed trade
    (order books are thin). `spot` is unused (kept for call-site symmetry).
    """
    info = _current_15m()
    if not info or not info.get("ticker"):
        return None
    up, ttime = _last_trade(info["ticker"])
    tgt = info.get("target")
    label = (f"up vs ${tgt:,.0f}" if isinstance(tgt, (int, float)) else "up/down")
    if up is None:
        return {"up_cost": None, "down_cost": None, "settles": info["close"],
                "label": label, "horizon": "15-min", "status": "no trades yet"}
    up = max(0.0, min(1.0, up))
    return {"up_cost": round(up, 4), "down_cost": round(1 - up, 4),
            "settles": info["close"], "label": label, "horizon": "15-min",
            # ticker surfaced so the execution layer can place real orders
            # (additive — existing read-only callers ignore it). NOTE: up/down
            # cost is the LAST TRADE, not a resting ask; fills are not guaranteed.
            "ticker": info.get("ticker"), "target": tgt,
            "trade_time": ttime}


def snapshot(spot=None):
    out = {"source": "kalshi"}
    try:
        out["updown"] = updown_live(spot)
    except Exception as e:
        out["updown_error"] = str(e)
    try:
        cdf = btc_threshold_cdf(spot=spot)
        out["btc_cdf"] = cdf
        out["quotes_available"] = bool(cdf.get("levels"))
        if not out["quotes_available"]:
            out["note"] = ("No recent Kalshi BTC trades and order books are "
                           "empty right now. Polymarket carries the live odds.")
    except Exception as e:
        out["btc_cdf_error"] = str(e)
        out["quotes_available"] = False
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2))
