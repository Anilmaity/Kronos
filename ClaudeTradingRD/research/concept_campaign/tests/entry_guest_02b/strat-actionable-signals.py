"""strat-actionable-signals (guest: Alex's Options, TheSTRAT) -> trade_test.

Reading (declared before the run):
  * Candles typed vs the previous candle: 1 = inside (high<=prev high & low>=prev low),
    2u = high>prev high & low>=prev low, 2d = low<prev low & high<=prev high, 3 = both.
  * The five SPOKEN reversals (2-2, 1-2-2, 3-2-2, 2-1-2, 3-1-2) all reduce to one trigger:
    bearish = P is a 2u (any predecessor: plain 2-2, 1-2-2, 3-2-2) or P is a 1 whose
    predecessor is a 2u or 3 (2-1-2, 3-1-2); the next bar B trades below P's low.
    Bullish mirrored. Continuations (2-2 cont, 2-1-2 cont, 3-2) have no stated magnitude,
    so they are not in the book.
  * Entry: "on the trigger of the final 2 (the bar taking the prior candle's extreme)":
    decision at the close of the first M1 bar inside B whose low < P.low (short), provided
    B has not already taken P.high (then B is a 3, not a 2; a minute that takes both is
    skipped). Harness enters at the next M1 open.
  * Target (magnitude): the opposite extreme of the candle BEFORE P (for 3-2-2 the guest
    says "the bottom of that 3"; for a bearish 2-2 the low of the candle before the 2-up) —
    the same rule for all five. Rows with a non-positive target distance are dropped.
  * Stop (not stated by the guest): the other side of P, the trigger candle (P.high for a
    short) — the conventional STRAT stop. declared-before-run.
  * Timeframe continuity (execution: "filtered by timeframe continuity"): the trade must
    agree with the current trading day's candle — short only if the trigger level P.low is
    below the day's open (18:00 NY roll), long only if P.high is above it.
  * Timeframe: 1h (middle of the ltf list), forex grid. max_hold 10h.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "1h"
MAX_HOLD = "10h"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "ptype"]
    b = cl.build_bars(m1, TF)
    if len(b) < 4:
        return pd.DataFrame(columns=cols)
    H, L = b["high"].to_numpy(), b["low"].to_numpy()
    n = len(b)
    typ = np.full(n, "", dtype=object)
    ph, pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    up, dn = H > ph, L < pl
    typ[(~up) & (~dn)] = "1"
    typ[up & ~dn] = "2u"
    typ[dn & ~up] = "2d"
    typ[up & dn] = "3"
    typ[0] = ""
    # candidate P = row j-1 for bar B = row j; predecessor Q = row j-2
    P_t = np.concatenate([np.array([""], dtype=object), typ[:-1]])   # type of P (row j-1) for B row j
    Q_t = np.concatenate([np.array(["", ""], dtype=object), typ[:-2]])
    bear = (P_t == "2u") | ((P_t == "1") & np.isin(Q_t, ["2u", "3"]))
    bull = (P_t == "2d") | ((P_t == "1") & np.isin(Q_t, ["2d", "3"]))
    Ph, Pl = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    Qh, Ql = np.r_[np.nan, np.nan, H[:-2]], np.r_[np.nan, np.nan, L[:-2]]

    # map every M1 row to its 1h bar row
    mt = m1.index
    pos = np.searchsorted(b.index.values, mt.values, side="right") - 1
    ok = pos >= 0
    mh, ml = m1["high"].to_numpy(), m1["low"].to_numpy()
    g = pd.Series(pos)
    cmax = pd.Series(mh).groupby(g).cummax().to_numpy()
    cmin = pd.Series(ml).groupby(g).cummin().to_numpy()
    thr_hi, thr_lo = Ph[pos], Pl[pos]
    # short trigger minute: running low breaks P.low while running high has not broken P.high
    s_hit = ok & bear[pos] & (cmin < thr_lo) & ~(cmax > thr_hi)
    l_hit = ok & bull[pos] & (cmax > thr_hi) & ~(cmin < thr_lo)
    # first such minute per bar (running extremes make the condition monotone until the
    # other side breaks, so the first True is the trigger)
    rows = []
    for hit, d in ((s_hit, -1), (l_hit, 1)):
        idx = np.flatnonzero(hit)
        if not len(idx):
            continue
        first = pd.Series(idx).groupby(pos[idx]).min().to_numpy()
        # the trigger minute must be the first minute the extreme was taken
        j = pos[first]
        if d == -1:
            prev_ok = np.array([(i == 0) or (pos[i - 1] != pos[i]) or not (cmin[i - 1] < thr_lo[i])
                                for i in first])
        else:
            prev_ok = np.array([(i == 0) or (pos[i - 1] != pos[i]) or not (cmax[i - 1] > thr_hi[i])
                                for i in first])
        first, j = first[prev_ok], j[prev_ok]
        rows.append(pd.DataFrame({
            "m1_i": first, "j": j, "direction": d,
            "stop_px": np.where(d == -1, Ph[j], Pl[j]),
            "target_px": np.where(d == -1, Ql[j], Qh[j]),
            "trig": np.where(d == -1, Pl[j], Ph[j]),
            "ptype": np.array([f"{q}-{p}" for q, p in zip(Q_t[j], P_t[j])], dtype=object),
        }))
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.concat(rows, ignore_index=True)
    ev["decision_time"] = mt[ev["m1_i"].to_numpy()] + pd.Timedelta("1min")
    # timeframe continuity with the trading day's candle (open of the day's first M1)
    td = cl.trading_day(mt)
    day_open = pd.Series(m1["open"].to_numpy()).groupby(td.values).transform("first").to_numpy()
    dop = day_open[ev["m1_i"].to_numpy()]
    tfc = np.where(ev["direction"] == -1, ev["trig"] < dop, ev["trig"] > dop)
    tdist = (ev["trig"] - ev["target_px"]) * ev["direction"] * -1
    ev = ev[tfc & (tdist > 0)].copy()
    ev["available_at"] = ev["decision_time"]
    ev = ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("strat_rev_1h_tfcday", lambda: detect(cl.load_m1()))
    print(len(ev), ev["ptype"].value_counts().head(10).to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "1h bars (forex grid); STRAT types vs previous bar: 1 inside, 2u, 2d, 3 outside",
        "bearish reversal set: P=2u (2-2 / 1-2-2 / 3-2-2) or P=1 after a 2u or 3 (2-1-2 / 3-1-2); bullish mirrored",
        "trigger: first M1 inside the next bar B taking P's extreme, B not yet a 3; decide at that M1 close",
        "target = opposite extreme of the bar before P (STRAT magnitude); stop = other side of P",
        "timeframe continuity: trigger level on the trade side of the trading-day open (18:00 NY)",
        "continuations excluded (no stated magnitude); max_hold 10h"],
        "params": {"tf": TF, "stop": "other side of P", "target": "bar-before-P opposite extreme",
                   "tfc": "trading-day open", "max_hold": MAX_HOLD, "grid4h": "n/a (1h)"}}
    src = {"tf": "declared-before-run: 1h, middle of the concept's ltf list (1H..1m)",
           "stop": "declared-before-run: guest states no stop; conventional STRAT stop at the trigger bar's far side",
           "target": "corpus: 1XWyy6Q-_8Q 'you're gonna Target the bottom of the try' (3-2-2 -> bottom of the 3); same rule applied to all five reversals",
           "tfc": "declared-before-run: execution bias 'filtered by timeframe continuity', reduced to the day candle",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)",
           "grid4h": "declared-before-run: not used"}
    p = cl.write_result("strat-actionable-signals", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="Book pools the five spoken reversals; per-type counts in the script output. "
                              "Continuation signals untested (no magnitude stated).")
    print(p)
