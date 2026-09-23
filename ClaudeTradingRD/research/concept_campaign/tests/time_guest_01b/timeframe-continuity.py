"""timeframe-continuity (TheSTRAT, Alex's Options, guest).

Claim: take a trade only with full timeframe continuity - for day trading month, week and
day all coloured in the trade's direction (price above/below that timeframe's own open,
read LIVE) and none of them a 1 (inside bar: the in-progress candle has not yet traded
beyond the prior candle's high or low).

Test: gate_test on the phase-3 locked bare 1h CISD book (the 1H is in the concept's LTF
list). Gate = FTFC in the trade direction at the decision time, else complement.
Periods: day = trading day (18:00 NY open), week = Monday session-date week, month =
calendar month of the session date. All reads use M1 bars closed by the decision.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params


def _period_state(m1, keys, tpos):
    """For each event position tpos (index of last closed M1 bar): open, running hi/lo of
    the current period, and hi/lo of the immediately preceding period."""
    k = pd.Series(keys)
    code, uniq = pd.factorize(k, sort=True)
    hi = pd.Series(m1["high"].to_numpy()).groupby(code).cummax().to_numpy()
    lo = pd.Series(m1["low"].to_numpy()).groupby(code).cummin().to_numpy()
    op = pd.Series(m1["open"].to_numpy()).groupby(code).transform("first").to_numpy()
    ghi = pd.Series(m1["high"].to_numpy()).groupby(code).max().to_numpy()
    glo = pd.Series(m1["low"].to_numpy()).groupby(code).min().to_numpy()
    c = code[tpos]
    pc = c - 1
    ok = pc >= 0
    pc = np.clip(pc, 0, None)
    return op[tpos], hi[tpos], lo[tpos], np.where(ok, ghi[pc], np.nan), np.where(ok, glo[pc], np.nan)


def detect(m1):
    ev = cisd_book(m1, "1h")
    if ev.empty:
        ev["ftfc"] = pd.Series(dtype=bool)
        return ev
    t = pd.DatetimeIndex(ev["decision_time"])
    mclose = (m1.index + pd.Timedelta(minutes=1)).asi8
    tpos = np.searchsorted(mclose, t.asi8, side="right") - 1
    px = m1["close"].to_numpy()[tpos]
    sd = pd.DatetimeIndex(cl.session_date(m1.index))
    keys = {"D": sd.asi8,
            "W": (sd - pd.to_timedelta(sd.dayofweek, unit="D")).asi8,
            "M": (sd.year * 100 + sd.month).to_numpy()}
    d = ev["direction"].to_numpy()
    good = np.ones(len(ev), bool)
    for name, kk in keys.items():
        op, rh, rl, ph, pl = _period_state(m1, kk, tpos)
        colour = np.sign(px - op)
        not_one = (rh > ph) | (rl < pl)       # NaN prior -> False -> not in continuity
        good &= (colour == d) & not_one
    ev["ftfc"] = good
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame("tg01b_ftfc_1hcisd", lambda: detect(cl.load_m1()))
    print(len(ev), "events; ftfc share", ev["ftfc"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="75D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "ftfc", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "gate", "ties", "ctrl_overlap"):
        print(k, res.get(k))
    bp, bs = base_params("1h", "10h")
    op = {"rules": ["baseline: phase-3 bare 1h CISD (series_open, swing 2/2, max_wait 3), decide at confirming 1h close, enter next M1 open, stop protected swing, 2R, 10h",
                    "gate FTFC: at the decision, last closed M1 close is above (long) / below (short) the open of the current day (18:00 NY), week and calendar month",
                    "and none of day/week/month is a 1: each in-progress candle's running high > prior candle high or running low < prior candle low",
                    "complement = every other baseline trade"],
          "params": {**bp, "timeframes": "1M/1W/1D", "colour_ref": "live, last closed M1 vs period open",
                     "inside_rule": "running range not yet beyond prior period"}}
    src = {**bs,
           "timeframes": "corpus: 1XWyy6Q-_8Q - yaml detection rule 'month, week and day are all green' (day trading set)",
           "colour_ref": "corpus: yaml ambiguity 'it must be live for the method to work'",
           "inside_rule": "corpus: yaml 'none of them is a 1' / STRAT taxonomy (inside = within prior high/low)"}
    p = cl.write_result("timeframe-continuity", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="'Move the continuity read down a timeframe when volatility increases' not tested (no threshold given).")
    print(p)
