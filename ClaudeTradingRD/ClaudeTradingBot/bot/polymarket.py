"""Polymarket live odds (read-only, public Gamma API — no auth).

Pulls BTC price-threshold markets (an implied probability CDF for where BTC
lands) plus any geopolitical market that moves gold/BTC (the US-Iran peace
deal binary). Used as trade-confluence and surfaced on the dashboard.

CLI:  python -m bot.polymarket
"""
import json
import re
import requests

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
_TIMEOUT = 20
_S = requests.Session()
_S.headers.update({"User-Agent": "ClaudeTradingBot/1.0"})


def _get(path, **params):
    r = _S.get(f"{GAMMA}{path}", params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _clob_token_ids(market):
    """[yesTokenId, noTokenId] from a Gamma market, or None."""
    import json
    ct = market.get("clobTokenIds")
    if isinstance(ct, str):
        try:
            ct = json.loads(ct)
        except ValueError:
            return None
    return ct if isinstance(ct, list) and ct else None


def _clob_midpoint(token_id):
    """Live order-book midpoint (0..1) for a CLOB token; None on failure.

    This is the real-time price — the Gamma `outcomePrices` field is cached
    and can lag the book by minutes.
    """
    try:
        r = _S.get(f"{CLOB}/midpoint", params={"token_id": token_id}, timeout=10)
        if r.ok:
            return _f(r.json().get("mid"))
    except requests.RequestException:
        pass
    return None


def _clob_last_trade(token_id):
    try:
        r = _S.get(f"{CLOB}/last-trade-price",
                   params={"token_id": token_id}, timeout=10)
        if r.ok:
            return _f(r.json().get("price"))
    except requests.RequestException:
        pass
    return None


def _live_yes_price(market):
    """Real-time Yes price: CLOB midpoint, then last-trade, then Gamma cache.

    Returns (price, source). source in {'clob_mid','clob_last','gamma'}.
    """
    toks = _clob_token_ids(market)
    if toks:
        mid = _clob_midpoint(toks[0])
        if mid is not None:
            return mid, "clob_mid"
        last = _clob_last_trade(toks[0])
        if last is not None:
            return last, "clob_last"
    return _yes_price(market), "gamma"


def _f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _yes_price(market):
    """Yes-outcome price (0..1) from a Gamma market's parallel arrays."""
    import json
    outs = market.get("outcomes")
    prices = market.get("outcomePrices")
    if isinstance(outs, str):
        outs = json.loads(outs)
    if isinstance(prices, str):
        prices = json.loads(prices)
    if not outs or not prices:
        return None
    for o, p in zip(outs, prices):
        if str(o).strip().lower() == "yes":
            return _f(p)
    return _f(prices[0])


def search(query, limit=6):
    """Active events whose title matches `query` (Polymarket public-search)."""
    d = _get("/public-search", q=query, limit_per_type=limit,
             events_status="active")
    return d.get("events", []) if isinstance(d, dict) else []


def event_by_slug(slug):
    d = _get("/events", slug=slug)
    return (d[0] if isinstance(d, list) and d else d) or {}


def btc_threshold_cdf(slug=None):
    """Implied 'BTC above $X' probabilities → an empirical CDF.

    Returns {title, generated_from, levels:[{threshold, prob_above, volume}],
             implied_pivot}. implied_pivot = the $ level where prob_above
             crosses 50% (linear interp) = market-implied fair value.
    """
    if slug is None:
        # Pick the nearest-dated active "Bitcoin above ___ on <date>" event.
        evs = search("Bitcoin above", limit=10)
        cand = [e for e in evs if "above" in (e.get("title") or "").lower()]
        ev = cand[0] if cand else (evs[0] if evs else {})
    else:
        ev = event_by_slug(slug)
    levels = []
    sources = set()
    for m in ev.get("markets", []):
        q = m.get("question") or ""
        mt = re.search(r"\$([\d,]+)", q)
        if not mt:
            continue
        thr = _f(mt.group(1).replace(",", ""))
        yp, src = _live_yes_price(m)
        if thr is None or yp is None:
            continue
        sources.add(src)
        levels.append({"threshold": thr, "prob_above": round(yp, 4),
                       "live": src.startswith("clob"),
                       "volume": round(_f(m.get("volume"), 0.0), 0)})
    levels.sort(key=lambda x: x["threshold"])
    pivot = _interp_pivot(levels)
    return {"title": ev.get("title"), "slug": ev.get("slug"),
            "levels": levels, "implied_pivot": pivot,
            "price_source": "clob" if any(s.startswith("clob") for s in sources)
                            else "gamma",
            "as_of": _now()}


def _interp_pivot(levels):
    """$ level where prob_above passes through 0.5 (descending in threshold)."""
    for i in range(len(levels) - 1):
        a, b = levels[i], levels[i + 1]
        pa, pb = a["prob_above"], b["prob_above"]
        if (pa - 0.5) * (pb - 0.5) <= 0 and pa != pb:
            frac = (pa - 0.5) / (pa - pb)
            return round(a["threshold"] + frac * (b["threshold"] - a["threshold"]), 0)
    return None


def _parse_deadline(market):
    """datetime from a 'by <Month> <day>, <year>?' question; None if unparseable."""
    from datetime import datetime
    mt = re.search(r"by\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", market.get("question") or "")
    if not mt:
        return None
    try:
        return datetime.strptime(mt.group(1), "%B %d, %Y")
    except ValueError:
        return None


def iran_deal_prob():
    """US-Iran peace-deal binary (gold-down / BTC-up driver).

    These markets are a term structure ('permanent peace deal by <date>'), so
    a single market is misleading. Return the nearest-dated *live* market
    (0<prob<1) as the headline plus the full sorted term structure.
    """
    ev = None
    for e in search("Iran peace deal", limit=6) + search("Iran deal", limit=6):
        t = (e.get("title") or "").lower()
        if "iran" in t and ("deal" in t or "peace" in t or "ceasefire" in t):
            ev = e
            break
    if not ev:
        return None
    term = []
    for m in ev.get("markets", []):
        cached = _yes_price(m)
        # Only spend a live CLOB call on markets that are still uncertain;
        # markets already settled to 0/1 don't move.
        if cached is not None and 0.0 < cached < 1.0:
            yp, _ = _live_yes_price(m)
        else:
            yp = cached
        dl = _parse_deadline(m)
        if yp is None:
            continue
        term.append({"label": m.get("groupItemTitle") or (m.get("question") or "")[:24],
                     "deadline": dl.isoformat() if dl else None,
                     "_dt": dl, "prob_yes": round(yp, 4),
                     "volume": round(_f(m.get("volume"), 0.0), 0)})
    # sort by deadline; live = strictly uncertain
    term.sort(key=lambda x: (x["_dt"] is None, x["_dt"]))
    live = [t for t in term if 0.0 < t["prob_yes"] < 1.0]
    headline = live[0] if live else (term[0] if term else None)
    for t in term:
        t.pop("_dt", None)
    if not headline:
        return None
    return {"title": ev.get("title"), "slug": ev.get("slug"),
            "headline_label": headline["label"],
            "prob_yes": headline["prob_yes"],
            "as_of": _now(),
            "term_structure": [{k: t[k] for k in ("label", "prob_yes", "volume")}
                               for t in term]}


def btc_updown_5m(n_ahead=1):
    """Live 5-minute BTC Up/Down markets: the current window + `n_ahead` next.

    Polymarket runs rolling 5-min markets with slug `btc-updown-5m-<ts>`, where
    <ts> is the UTC unix timestamp of the window START (aligned to 300s). The
    'Up' outcome priced via live CLOB midpoint. Returns the active window first.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    base = (now_ts // 300) * 300
    windows = []
    for i in range(n_ahead + 1):
        ts = base + i * 300
        try:
            d = _get("/events", slug=f"btc-updown-5m-{ts}")
        except requests.RequestException:
            continue
        ev = d[0] if isinstance(d, list) and d else None
        if not ev or not ev.get("markets"):
            continue
        m = ev["markets"][0]
        toks = _clob_token_ids(m)
        up = None
        src = "gamma"
        if toks:
            up = _clob_midpoint(toks[0])
            src = "clob_mid" if up is not None else "gamma"
        if up is None:
            up = _yes_price(m)  # 'Up' is the first outcome
        end_iso = ev.get("endDate")
        secs_left = None
        if end_iso:
            try:
                end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                secs_left = max(0, int((end_dt - now).total_seconds()))
            except ValueError:
                pass
        windows.append({
            "label": ev.get("title"),
            "slug": ev.get("slug"),
            "window_start_ts": ts,
            "window_end": end_iso,
            "seconds_left": secs_left,
            "up_prob": round(up, 4) if up is not None else None,
            "down_prob": round(1 - up, 4) if up is not None else None,
            "live": src.startswith("clob"),
            "current": i == 0,
        })
    return {"windows": windows, "as_of": _now()}


# --- per-second live quotes for the rolling 5-min market -------------------
# Token IDs are stable for a window's 5-minute life, so resolve them once
# (Gamma) and then poll only the CLOB price (cheap) every second.
_TOKEN_CACHE = {}  # window_start_ts -> {yes, no, window_end, label, slug}


def _resolve_5m_window(ts):
    info = _TOKEN_CACHE.get(ts)
    if info:
        return info
    try:
        d = _get("/events", slug=f"btc-updown-5m-{ts}")
    except requests.RequestException:
        return None
    ev = d[0] if isinstance(d, list) and d else None
    if not ev or not ev.get("markets"):
        return None
    toks = _clob_token_ids(ev["markets"][0])
    if not toks:
        return None
    info = {"yes": toks[0], "no": toks[1] if len(toks) > 1 else None,
            "window_end": ev.get("endDate"), "label": ev.get("title"),
            "slug": ev.get("slug")}
    _TOKEN_CACHE[ts] = info
    for k in [k for k in _TOKEN_CACHE if k < ts - 3600]:
        del _TOKEN_CACHE[k]  # prune stale windows
    return info


def _clob_buy_price(token_id):
    """Best ask (what you PAY to buy this outcome), 0..1; None on failure."""
    try:
        r = _S.get(f"{CLOB}/price", params={"token_id": token_id, "side": "buy"},
                   timeout=8)
        if r.ok:
            return _f(r.json().get("price"))
    except requests.RequestException:
        pass
    return None


def _ask_from_book(data):
    """Best ask (price 0..1, size shares) from a Polymarket CLOB /book payload.
    `asks` is a list of {price, size}; best ask = LOWEST price. (None, 0) if empty."""
    asks = (data or {}).get("asks") or []
    if not asks:
        return None, 0
    best = min(asks, key=lambda a: float(a["price"]))
    return round(float(best["price"]), 4), int(float(best["size"]))


def book_ask(token_id):
    """Live best ask (price 0..1, size shares) for a CLOB token. (None, 0) on error."""
    try:
        r = _S.get(f"{CLOB}/book", params={"token_id": token_id}, timeout=8)
        if r.ok:
            return _ask_from_book(r.json())
    except Exception:  # noqa: BLE001  -- read-only path must never raise
        pass
    return None, 0


def settled_direction(slug):
    """'UP' / 'DOWN' once a btc-updown-15m window's price reflects its resolution,
    else None. Reads the market's `outcomePrices` aligned to `outcomes`
    (['Up','Down']); the outcome priced ~$1 is the winner. We key off the DECISIVE
    PRICE, not Polymarket's `closed`/`umaResolutionStatus` flags, because those lag
    minutes-to-hours behind the price snapping to the Chainlink outcome at window
    close. The caller settles only AFTER the window's end time, so a >=0.95 winner is
    the final result. Read-only; lets the paper lock settle on the REAL per-venue
    outcome (a basis break -> Poly resolves opposite to Kalshi -> both legs lose)."""
    try:
        d = _get("/events", slug=slug)
    except requests.RequestException:
        return None
    ev = d[0] if isinstance(d, list) and d else None
    if not ev or not ev.get("markets"):
        return None
    m = ev["markets"][0]
    outs, prices = m.get("outcomes"), m.get("outcomePrices")
    if isinstance(outs, str):
        try:
            outs = json.loads(outs)
        except (ValueError, TypeError):
            return None
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except (ValueError, TypeError):
            return None
    if not outs or not prices or len(outs) != len(prices):
        return None
    try:
        win = max(range(len(prices)), key=lambda i: float(prices[i]))
    except (ValueError, TypeError):
        return None
    if float(prices[win]) < 0.95:        # no clear winner -> treat as unresolved
        return None
    name = (outs[win] or "").lower()
    if "up" in name:
        return "UP"
    if "down" in name:
        return "DOWN"
    return None


_WINDOW_CACHE = {}  # (kind, ts) -> {yes, no, window_end, label, slug}


def _resolve_window(kind, ts):
    key = (kind, ts)
    info = _WINDOW_CACHE.get(key)
    if info:
        return info
    try:
        d = _get("/events", slug=f"btc-updown-{kind}-{ts}")
    except requests.RequestException:
        return None
    ev = d[0] if isinstance(d, list) and d else None
    if not ev or not ev.get("markets"):
        return None
    toks = _clob_token_ids(ev["markets"][0])
    if not toks:
        return None
    info = {"yes": toks[0], "no": toks[1] if len(toks) > 1 else None,
            "window_end": ev.get("endDate"), "label": ev.get("title"),
            "slug": ev.get("slug")}
    _WINDOW_CACHE[key] = info
    for k in [k for k in _WINDOW_CACHE if k[1] < ts - 7200]:
        del _WINDOW_CACHE[k]
    return info


def updown_window_live(kind="5m", secs=300):
    """Live Up/Down BUY costs for the current rolling window of any duration.

    kind/secs: '5m'/300, '15m'/900 — slug is btc-updown-<kind>-<ts> aligned to
    `secs`. Returns each side's ask (cost) like Polymarket's UI. ~2 CLOB calls.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ts = (int(now.timestamp()) // secs) * secs
    info = _resolve_window(kind, ts)
    if not info:
        return None
    up_cost = _clob_buy_price(info["yes"])
    down_cost = _clob_buy_price(info["no"]) if info["no"] else None
    if down_cost is None and up_cost is not None:
        down_cost = round(1 - up_cost, 4)
    secs_left = None
    if info["window_end"]:
        try:
            end = datetime.fromisoformat(info["window_end"].replace("Z", "+00:00"))
            secs_left = max(0, int((end - now).total_seconds()))
        except ValueError:
            pass
    return {"label": info["label"], "slug": info["slug"],
            "window_end": info["window_end"], "seconds_left": secs_left,
            "horizon": kind,
            # CLOB token IDs surfaced so the execution layer can place real
            # orders (additive — existing read-only callers ignore these).
            "up_token": info.get("yes"), "down_token": info.get("no"),
            "up_cost": round(up_cost, 4) if up_cost is not None else None,
            "down_cost": round(down_cost, 4) if down_cost is not None else None}


def updown_5m_live(n_ahead=0):
    """Per-second live quote for the current (and optionally next) 5-min window.

    Returns each side's BUY COST (the ask) + the mid, like Polymarket's UI.
    Lightweight: token IDs are cached, so each window costs 2-3 CLOB calls.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    base = (now_ts // 300) * 300
    wins = []
    for i in range(n_ahead + 1):
        ts = base + i * 300
        info = _resolve_5m_window(ts)
        if not info:
            continue
        up_cost = _clob_buy_price(info["yes"])
        down_cost = _clob_buy_price(info["no"]) if info["no"] else None
        up_mid = _clob_midpoint(info["yes"])
        if down_cost is None and up_cost is not None:
            down_cost = round(1 - up_cost, 4)
        secs = None
        if info["window_end"]:
            try:
                end = datetime.fromisoformat(info["window_end"].replace("Z", "+00:00"))
                secs = max(0, int((end - now).total_seconds()))
            except ValueError:
                pass
        wins.append({
            "label": info["label"], "slug": info["slug"],
            "window_start_ts": ts, "window_end": info["window_end"],
            "seconds_left": secs,
            "up_cost": round(up_cost, 4) if up_cost is not None else None,
            "down_cost": round(down_cost, 4) if down_cost is not None else None,
            "up_mid": round(up_mid, 4) if up_mid is not None else None,
            "current": i == 0,
        })
    return {"windows": wins, "as_of": _now()}


def snapshot():
    out = {"source": "polymarket"}
    try:
        out["btc_cdf"] = btc_threshold_cdf()
    except Exception as e:
        out["btc_cdf_error"] = str(e)
    try:
        out["updown_5m"] = btc_updown_5m()
    except Exception as e:
        out["updown_5m_error"] = str(e)
    try:
        out["iran_deal"] = iran_deal_prob()
    except Exception as e:
        out["iran_deal_error"] = str(e)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2))
