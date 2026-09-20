"""BTC perpetual funding + cross-exchange spot monitor (read-only, free APIs).

Research (2026-06) concluded none of the classic crypto arbs are EXECUTABLE by
this single-venue MT5 CFD bot, but the funding rate is an excellent crowd-
positioning / squeeze-risk SIGNAL, and a widening cross-exchange spot spread
flags liquidity stress. Both feed the BTC directional bias as confluence.

Funding sign convention: POSITIVE funding = longs pay shorts = crowded longs =
squeeze-DOWN risk (contrarian bearish). NEGATIVE = crowded shorts = squeeze-UP.

CLI:  python -m bot.funding
"""
import requests

_TIMEOUT = 12
_S = requests.Session()
_S.headers.update({"User-Agent": "ClaudeTradingBot/1.0"})

# ~0.03%/8h funding is "very crowded"; scale the score against that.
_FUNDING_FULL_SCALE = 0.0003


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def funding_rates():
    """Latest BTC perp funding from Binance + Bybit (per-8h decimal rate)."""
    out = {}
    try:
        r = _S.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                   params={"symbol": "BTCUSDT"}, timeout=_TIMEOUT)
        if r.ok:
            d = r.json()
            out["binance"] = {"rate": _f(d.get("lastFundingRate")),
                              "mark": _f(d.get("markPrice")),
                              "next_funding_ms": d.get("nextFundingTime")}
    except requests.RequestException as e:
        out["binance_error"] = str(e)
    try:
        r = _S.get("https://api.bybit.com/v5/market/tickers",
                   params={"category": "linear", "symbol": "BTCUSDT"},
                   timeout=_TIMEOUT)
        if r.ok:
            lst = r.json().get("result", {}).get("list", [])
            if lst:
                out["bybit"] = {"rate": _f(lst[0].get("fundingRate")),
                                "last": _f(lst[0].get("lastPrice"))}
    except requests.RequestException as e:
        out["bybit_error"] = str(e)
    return out


def cross_exchange_spread():
    """BTC spot best bid/ask across venues + the high-low spread."""
    venues = {}
    probes = [
        ("binance", "https://api.binance.com/api/v3/ticker/bookTicker",
         {"symbol": "BTCUSDT"}, lambda d: (_f(d["bidPrice"]), _f(d["askPrice"]))),
        ("coinbase", "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
         None, lambda d: (_f(d["bid"]), _f(d["ask"]))),
        ("kraken", "https://api.kraken.com/0/public/Ticker",
         {"pair": "XBTUSD"},
         lambda d: (lambda v: (_f(v["b"][0]), _f(v["a"][0])))(
             list(d["result"].values())[0])),
    ]
    for name, url, params, parse in probes:
        try:
            r = _S.get(url, params=params, timeout=_TIMEOUT)
            if r.ok:
                bid, ask = parse(r.json())
                if bid and ask:
                    venues[name] = {"bid": bid, "ask": ask,
                                    "mid": round((bid + ask) / 2, 2)}
        except (requests.RequestException, KeyError, IndexError, TypeError):
            continue
    mids = {k: v["mid"] for k, v in venues.items()}
    spread = None
    if len(mids) >= 2:
        hi_k = max(mids, key=mids.get)
        lo_k = min(mids, key=mids.get)
        d = mids[hi_k] - mids[lo_k]
        spread = {"high_venue": hi_k, "low_venue": lo_k,
                  "spread_usd": round(d, 2),
                  "spread_bps": round(d / mids[lo_k] * 1e4, 2)}
    return {"venues": venues, "spread": spread}


def positioning_score():
    """Combine funding into a -1..+1 squeeze score (+ = squeeze-down risk)."""
    fr = funding_rates()
    rates = [v["rate"] for v in (fr.get("binance"), fr.get("bybit"))
             if isinstance(v, dict) and v.get("rate") is not None]
    if not rates:
        return {"score": None, "label": "no funding data", "funding": fr}
    avg = sum(rates) / len(rates)
    score = max(-1.0, min(1.0, avg / _FUNDING_FULL_SCALE))
    if score > 0.5:
        label = "crowded LONGS — squeeze-down risk (contrarian bearish)"
    elif score < -0.5:
        label = "crowded SHORTS — squeeze-up risk (contrarian bullish)"
    elif abs(score) <= 0.2:
        label = "neutral positioning"
    else:
        label = "mild long lean" if score > 0 else "mild short lean"
    return {"score": round(score, 3), "avg_funding": round(avg, 8),
            "label": label, "funding": fr}


def snapshot():
    out = {"source": "funding", "as_of": _now()}
    try:
        out["positioning"] = positioning_score()
    except Exception as e:
        out["positioning_error"] = str(e)
    try:
        out["cross_exchange"] = cross_exchange_spread()
    except Exception as e:
        out["cross_exchange_error"] = str(e)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2))
