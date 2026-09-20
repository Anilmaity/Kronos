"""BTC edge-signal engine (READ-ONLY — flags, never auto-trades).

Synthesis of 2026-06 research (three parallel subagents). Conclusions baked in:
  * Classic crypto arb (cross-exchange / carry / triangular) is NOT executable
    by this single-venue MT5 CFD bot — see bot/funding.py for the monitor.
  * Polymarket<->Kalshi cross-venue arb is real but marginal: ~3.5% round-trip
    fees, oracle/settlement divergence, capital lockup, and one identity can't
    legally hold both venues. So it is surfaced as a basis-risk-gated WATCH.
  * The only short-horizon edge with a real mechanism is latency / stale-book
    mispricing in Polymarket's rolling 5-min BTC Up/Down market: compare the
    market's implied prob to a Bachelier fair value from live spot + realized
    vol + time-left, and flag when they diverge beyond costs.

ALL outputs are signals for paper validation (300+ trades before any real
size), not trade instructions. Settlement is via Chainlink (Polymarket) which
differs from the MT5 broker feed — treat "spot past strike" as approximate.

CLI:  python -m bot.arbitrage
"""
import math
import statistics

# --- thresholds (deliberately conservative; tighten only after paper proof) ---
EDGE_MIN_5M = 0.08         # model prob must beat executable price by >= 8c (paper)
MAX_SPREAD_5M = 0.06       # skip thin/wide 5-min books
MIN_SECONDS_LEFT = 20      # avoid the random last-10s resolution tail
PM_CROSS_MIN_EDGE = 0.045  # >=4.5c gross gap before fees on cross-venue PM
PM_FEE_FLOOR = 0.035       # ~3.5% round-trip taker fee drag near 50c


def _phi(x):
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def realized_dollar_vol(candles, per="sec"):
    """Std-dev of close-to-close $ moves from 1-min candles, scaled per sec/min.

    `candles` = list of MT5 M1 candles (dicts with 'c'). Returns $ sigma.
    """
    closes = [c["c"] for c in candles if c.get("complete", True)]
    if len(closes) < 5:
        return None
    diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    sigma_min = statistics.pstdev(diffs)
    if per == "min":
        return sigma_min
    return sigma_min / math.sqrt(60.0)  # per-second


def binary_fair_value(spot, strike, seconds_left, sigma_dollar_per_sec):
    """Bachelier (normal, driftless) fair P(spot_T >= strike) for a short horizon.

    P(up) = N( (spot - strike) / (sigma_$ * sqrt(seconds_left)) ).
    Returns None if inputs are unusable.
    """
    if not sigma_dollar_per_sec or seconds_left is None or seconds_left <= 0:
        return None
    denom = sigma_dollar_per_sec * math.sqrt(seconds_left)
    if denom <= 0:
        return None
    return _phi((spot - strike) / denom)


def updown_5m_signal(updown, spot, sigma_sec):
    """Compare Polymarket 5-min UP implied prob to Bachelier fair value.

    For these markets the strike is the spot at window open, so we don't know
    it exactly from the feed; we approximate by treating the *current* implied
    50% point as the strike anchor and instead score the DIVERGENCE between
    the market's UP prob and the model UP prob given how far spot has traveled
    this window. Practically: model = N(move / (sigma*sqrt(t_left))) where
    `move` is unknown without the open price, so we fall back to flagging when
    the market sits near 50/50 while spot momentum is strong, OR when an
    explicit strike is supplied. Returns a signal dict (may be 'no edge').
    """
    wins = (updown or {}).get("windows") or []
    cur = next((w for w in wins if w.get("current")), wins[0] if wins else None)
    if not cur or cur.get("up_prob") is None:
        return {"market": "btc-updown-5m", "status": "no data"}
    t_left = cur.get("seconds_left")
    mkt_up = cur["up_prob"]
    sig = {"market": "btc-updown-5m", "label": cur.get("label"),
           "seconds_left": t_left, "market_up_prob": mkt_up,
           "spot": spot}
    # Strike (window-open price) isn't in the feed; if a caller stores it we use
    # it, else we report the market prob + a momentum cross-check only.
    strike = cur.get("strike_open")
    if strike and spot and sigma_sec and t_left:
        fair = binary_fair_value(spot, strike, t_left, sigma_sec)
        sig["model_up_prob"] = round(fair, 4) if fair is not None else None
        if fair is not None:
            edge = fair - mkt_up           # +ve => model thinks UP underpriced
            sig["edge_up"] = round(edge, 4)
            tradable = (abs(edge) >= EDGE_MIN_5M and t_left > MIN_SECONDS_LEFT)
            sig["flag"] = ("BUY_UP" if edge >= EDGE_MIN_5M and tradable else
                           "BUY_DOWN" if -edge >= EDGE_MIN_5M and tradable else
                           "none")
            sig["status"] = "evaluated"
        return sig
    sig["status"] = "no strike anchor (need window-open price)"
    sig["note"] = ("model needs the window-open price as strike; the feed only "
                   "gives live UP odds. Strike capture added by the writer.")
    return sig


def cross_venue_pm(poly_cdf, kalshi_cdf):
    """Same-strike 'BTC above $X' divergence between Polymarket and Kalshi.

    Honest about basis risk: the two venues' BTC threshold markets usually
    settle at DIFFERENT times / price sources, so a price gap is a WATCH, not
    a locked arb. We match by exact strike and report net edge after the fee
    floor, always carrying basis_risk=True unless settlement is verified equal.
    """
    pl = {round(l["threshold"]): l["prob_above"]
          for l in (poly_cdf or {}).get("levels", [])}
    kl = {round(l["threshold"]): l["prob_above"]
          for l in (kalshi_cdf or {}).get("levels", [])}
    matches = []
    for strike in sorted(set(pl) & set(kl)):
        p, k = pl[strike], kl[strike]
        gap = abs(p - k)
        # YES on cheaper + NO on dearer locks (1 - |gap|)... the exploitable
        # gross edge on the matched strike is the probability divergence.
        net = gap - PM_FEE_FLOOR
        if gap >= PM_CROSS_MIN_EDGE:
            matches.append({
                "strike": strike, "poly_prob": round(p, 4),
                "kalshi_prob": round(k, 4), "gross_gap": round(gap, 4),
                "net_after_fees": round(net, 4),
                "buy_yes_on": "kalshi" if k < p else "polymarket",
                "basis_risk": True,  # settlement windows differ across venues
                "actionable": net > 0,
            })
    return {"matched_strikes": len(set(pl) & set(kl)),
            "divergences": matches,
            "note": ("Polymarket settles via Chainlink at the event date; "
                     "Kalshi daily settles intraday today — different windows, "
                     "so treat divergences as WATCH signals, not locked arb.")}


def _open_at(m1_candles, unix_ts):
    """Open price of the M1 candle starting at `unix_ts` (the 5-min window open).

    Polymarket's 5-min strike = spot at window open; the M1 candle on that
    boundary minute gives us a close proxy (Chainlink-vs-MT5 basis aside).
    """
    from datetime import datetime
    for c in m1_candles or []:
        try:
            ct = int(datetime.fromisoformat(
                c["time"].replace("Z", "+00:00")).timestamp())
        except (ValueError, KeyError):
            continue
        if ct == unix_ts:
            return c.get("o")
    return None


def cross_venue_15m(poly15m, kalshi15m, fee_floor=PM_FEE_FLOOR, margin=0.005):
    """Same-window cross-venue lock: Polymarket 15m vs Kalshi 15m Up/Down.

    Both resolve 'Up' vs the BTC price at the 15-min window open, so buying UP
    on the cheaper venue + DOWN on the dearer one collects $1 at settlement for
    a cost < $1. Returns the lock cost, gross/net edge after the fee floor, the
    legs to buy, and an explicit basis-risk flag (the venues use DIFFERENT
    settlement price sources — Polymarket=Chainlink, Kalshi=its index — so the
    'open reference' can differ by a few $, which can break the lock if BTC
    closes very near the open).
    """
    if not poly15m or not kalshi15m:
        return {"status": "missing a venue"}
    pu, pd = poly15m.get("up_cost"), poly15m.get("down_cost")
    ku, kd = kalshi15m.get("up_cost"), kalshi15m.get("down_cost")
    if None in (pu, pd, ku, kd):
        return {"status": "incomplete quotes"}
    same_window = (poly15m.get("window_end") or "") == (kalshi15m.get("settles") or "X")
    c1 = pu + kd   # UP Polymarket + DOWN Kalshi
    c2 = ku + pd   # UP Kalshi + DOWN Polymarket
    if c1 <= c2:
        best, legs = c1, "BUY UP Polymarket @ %.2f + DOWN Kalshi @ %.2f" % (pu, kd)
    else:
        best, legs = c2, "BUY UP Kalshi @ %.2f + DOWN Polymarket @ %.2f" % (ku, pd)
    gross = round(1.0 - best, 4)
    net = round(gross - fee_floor, 4)
    return {
        "status": "evaluated",
        "lock_cost": round(best, 4),
        "gross_edge": gross,
        "net_edge_after_fees": net,
        "legs": legs,
        "same_window": same_window,
        "settles": poly15m.get("window_end"),
        "basis_risk": True,
        "actionable": bool(net > margin and same_window),
        "note": ("Lock collects $1 at settlement. Net = gross - ~3.5% fees. "
                 "Basis risk: Polymarket(Chainlink) vs Kalshi(index) open "
                 "reference can differ — verify on paper before real size."),
    }


def build_signals(spot=None, sigma_sec=None, m1_candles=None,
                  updown=None, poly_cdf=None, kalshi_cdf=None):
    """Assemble all read-only edge signals from already-fetched inputs."""
    if sigma_sec is None and m1_candles:
        sigma_sec = realized_dollar_vol(m1_candles, per="sec")
    # Anchor the 5-min model: stamp each window's open price as its strike.
    for w in (updown or {}).get("windows", []):
        if w.get("strike_open") is None and m1_candles:
            w["strike_open"] = _open_at(m1_candles, w.get("window_start_ts"))
    out = {"sigma_dollar_per_sec": round(sigma_sec, 4) if sigma_sec else None,
           "spot": spot, "disclaimer":
           "READ-ONLY signals for paper validation. Not trade instructions."}
    try:
        out["updown_5m"] = updown_5m_signal(updown, spot, sigma_sec)
    except Exception as e:
        out["updown_5m_error"] = str(e)
    try:
        out["cross_venue_pm"] = cross_venue_pm(poly_cdf, kalshi_cdf)
    except Exception as e:
        out["cross_venue_pm_error"] = str(e)
    return out


def snapshot():
    """Self-contained: fetch live inputs and build signals (for the CLI)."""
    from bot import polymarket, kalshi, data_mt5
    spot = None
    m1 = []
    try:
        spot = data_mt5.current_price("BTCUSDT").get("mid")
        m1 = [c for c in data_mt5.candles("BTCUSDT", "M1", 60) if c["complete"]]
    except Exception:
        pass
    poly = polymarket.snapshot()
    kal = kalshi.snapshot(spot=spot)
    return build_signals(spot=spot, m1_candles=m1,
                         updown=poly.get("updown_5m"),
                         poly_cdf=poly.get("btc_cdf"),
                         kalshi_cdf=kal.get("btc_cdf"))


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2))
