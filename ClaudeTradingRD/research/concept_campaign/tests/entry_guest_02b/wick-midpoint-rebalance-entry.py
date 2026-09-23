"""wick-midpoint-rebalance-entry (guest: AP) -> trade_test.

Reading (declared before the run):
  * Execution on 15m (smallest of the concept's htf list 4H/1H/15m), forex grid.
  * "Extreme wick at a key level": the candle's wick on one side is >= 60% of its range
    (lower wick = min(open,close) - low) AND its extreme sweeps the prior 20 bars'
    extreme (low < min of the previous 20 lows) — the swept-low / key-level condition.
    Upper wick mirrored for shorts. A candle qualifying both ways is skipped.
  * Measure the wick from the body edge to the extreme; mid = its 50%.
  * After the wick candle W closes, within 4h: price must trade to the wick 50% (rebalance)
    without trading beyond W's extreme; then a buy stop above W's high (sell stop below
    W's low) triggers — decision at the close of the first M1 taking W's high, provided W's
    low has not been traded between rebalance and trigger (inclusive).
  * Stop: beyond the wick extreme (stated). Target: 2R (the stated targets — next
    unmitigated area / 0.41 / volume node — are not defined mechanically). max_hold 150min.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TF = "15min"
WICK_SHARE = 0.60
SWEEP_N = 20
WINDOW = pd.Timedelta("4h")
RR = 2.0
MAX_HOLD = "150min"


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    b = cl.build_bars(m1, TF)
    if len(b) < SWEEP_N + 2:
        return pd.DataFrame(columns=cols)
    o, h, l, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    rng = h - l
    lw = np.minimum(o, c) - l
    uw = h - np.maximum(o, c)
    prev_min = pd.Series(l).shift(1).rolling(SWEEP_N, min_periods=SWEEP_N).min().to_numpy()
    prev_max = pd.Series(h).shift(1).rolling(SWEEP_N, min_periods=SWEEP_N).max().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        bull = (rng > 0) & (lw >= WICK_SHARE * rng) & (l < prev_min)
        bear = (rng > 0) & (uw >= WICK_SHARE * rng) & (h > prev_max)
    both = bull & bear
    bull &= ~both
    bear &= ~both
    mt = m1.index.values
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    ct = b["close_time"].values
    out = []
    for i in np.flatnonzero(bull | bear):
        d = 1 if bull[i] else -1
        a = np.searchsorted(mt, ct[i], side="left")
        e = np.searchsorted(mt, ct[i] + WINDOW.to_timedelta64(), side="left")
        if a >= e:
            continue
        hh, ll = MH[a:e], ML[a:e]
        if d == 1:
            mid = (min(o[i], c[i]) + l[i]) / 2.0
            reb = ll <= mid
            bad = ll < l[i]
            trig = hh > h[i]
        else:
            mid = (max(o[i], c[i]) + h[i]) / 2.0
            reb = hh >= mid
            bad = hh > h[i]
            trig = ll < l[i]
        if not reb.any():
            continue
        r = int(np.argmax(reb))
        if bad[:r + 1].any():
            continue
        tr = np.flatnonzero(trig[r + 1:])
        if not len(tr):
            continue
        k = r + 1 + int(tr[0])
        if bad[r:k + 1].any():
            continue
        # the trigger must not have printed before the rebalance either (a stop above W's
        # high placed at W's close would have filled earlier -> that is not this entry)
        if trig[:r + 1].any():
            continue
        dt = pd.Timestamp(mt[a + k]).tz_localize("UTC") + pd.Timedelta("1min")
        out.append((dt, d, l[i] if d == 1 else h[i]))
    if not out:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(out, columns=["decision_time", "direction", "stop_px"])
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = RR
    return ev.sort_values("decision_time").reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame(f"wickmid_{TF}_{WICK_SHARE}_{SWEEP_N}_4h", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="5D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars; extreme wick = one-side wick >= 60% of range and the extreme takes the prior 20 bars' extreme",
        "wick 50% measured from the body edge to the extreme",
        "within 4h of the wick candle's close: price rebalances the wick 50% without trading beyond the wick extreme",
        "then stop-entry beyond the wick candle's opposite extreme (buy stop above its high for a lower wick); decide at that M1 close",
        "stop at the wick extreme; target 2R; max_hold 150min"],
        "params": {"tf": TF, "wick_share": WICK_SHARE, "sweep_n": SWEEP_N, "window": "4h",
                   "rr": RR, "max_hold": MAX_HOLD}}
    src = {"tf": "declared-before-run: 15m, the lowest htf in the concept's timeframe list",
           "wick_share": "declared-before-run: 'extreme wick' unquantified; >=60% of range (above threshold_fits' large-wick class)",
           "sweep_n": "declared-before-run: key-level proxy = the wick takes the prior 20 bars' extreme (concept: 'swept prior-session low')",
           "window": "declared-before-run: 16 execution bars for rebalance + trigger",
           "rr": "declared-before-run: stated targets not mechanical; 2R",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result("wick-midpoint-rebalance-entry", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe)
    print(p)
