"""reversal-candle-quality — gate_test, two readings (contested).

Concept: quality tests applied to a DAILY candle-2 closure before trading away from it.
The YAML flags as unresolved whether the path test and the shape test are two views of
one rule or two independent filters, so each is a reading:
  (a) path test  — a bullish C2 must be open-LOW-high-close (the low printed before the
                   high inside the candle); open-high-low-close is an expansion candle and is
                   rejected. Mirror for bearish. Measured on the candle's own M1 bars.
  (b) shape test — "a reversal candle has a LARGE WICK and a SMALL BODY": the opposing run
                   (bullish C2: open - low; bearish: high - open) > |close - open|.

Baseline book (stated, the concept's own execution): every one-sided daily C2 closure
(method_spec §3.2 test: bullish = low < prior low and close > prior low; mirror bearish;
candles that are C2 on both sides are dropped — the concept demotes them to "low quality,
needs extra confirmation"). Decide at the C2 close, enter next M1 open ("ideal closure - the
next candle's continuation directly"), stop = the C2 extreme (the protected extreme it
created), target = the C2's opposite extreme (the "previous day high/low" once C3 opens),
hold one trading day (C3). claim '+': quality C2s beat the rest, control-adjusted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, complete_bars, empty, M1  # noqa: E402

CID = "reversal-candle-quality"
HOLD = "1380min"
MIN_M1 = 690
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "olhc", "shape_rev"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"].to_numpy() >= MIN_M1]
    if len(d) < 3:
        return empty(COLS)
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    pl, ph = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
    bull = (l < pl) & (c > pl)
    bear = (h > ph) & (c < ph)
    one = bull ^ bear
    m = M1(m1)
    st, en = ns(d["first_m1"]), ns(d["last_m1"])
    rows = []
    for i in np.flatnonzero(one):
        a = int(np.searchsorted(m.t, st[i], "left"))
        z = int(np.searchsorted(m.t, en[i], "right"))
        if z - a < 2:
            continue
        t_lo = a + int(np.argmin(m.l[a:z]))
        t_hi = a + int(np.argmax(m.h[a:z]))
        if bull[i]:
            olhc = t_lo < t_hi
            opp = o[i] - l[i]
            tgt, stp, dr = h[i], l[i], 1
        else:
            olhc = t_hi < t_lo
            opp = h[i] - o[i]
            tgt, stp, dr = l[i], h[i], -1
        if dr * (tgt - c[i]) <= 0 or dr * (c[i] - stp) <= 0:
            continue                         # closed on its extreme: no target / no stop room
        rows.append((d["close_time"].iloc[i], dr, stp, tgt, bool(olhc),
                     bool(opp > abs(c[i] - o[i]))))
    if not rows:
        return empty(COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px", "olhc", "shape_rev"])
    t = pd.DatetimeIndex(out["t"]).tz_convert("UTC")
    out.insert(0, "decision_time", t)
    out.insert(1, "available_at", t)
    return out[COLS].reset_index(drop=True)


OP_BASE = [
    "daily candles = NY trading day rolling 18:00 (cl 1D); stub days (< 690 M1 bars) removed before C1/C2 pairing",
    "C2 bullish: low < prior low and close > prior low; bearish mirror; two-sided C2s dropped",
    "decide at the C2 close, enter next M1 open; stop = C2 extreme; target = C2 opposite extreme; "
    "rows whose close equals an extreme dropped; hold one trading day (1380 trading minutes)"]
PARAMS = {"tf": "1D", "day_open": "18:00 NY", "min_m1": MIN_M1, "max_hold": HOLD,
          "hold_basis": "bars", "two_sided": "dropped"}
SRC = {"tf": "corpus: YAML definition 'a daily candle 2 closure'; timeframes htf [1D]",
       "day_open": "session_window_fit: NY DST day rolling at 18:00 (settled)",
       "min_m1": "declared-before-run: skip stub sessions (< half a trading day of M1) per README trap 6",
       "max_hold": "corpus: YAML execution 'the next candle's continuation' = one daily candle (C3)",
       "hold_basis": "declared-before-run: one trading day of M1 so Friday C2s are not cut by the weekend (README trap 7)",
       "two_sided": "corpus: YAML detection rule — a two-sided C2 is low quality and needs an hourly CISD + extra confirmation; excluded from the ideal-closure book",
       "stop_target": "corpus: YAML execution stop 'the protected extreme created by the closure', targets 'previous day low or high'"}

READINGS = {
    "a": ("olhc", "path test: bullish C2 must print its low before its high (open-low-high-close) on its own M1 bars; bearish mirror",
          "corpus: YAML detection rules 1-2 (open, low, high, close; reject open, high, low, close)"),
    "b": ("shape_rev", "shape test: opposing run (bullish open-low / bearish high-open) > |close-open| (large wick, small body)",
          "corpus: ecTRHQrbYzI 'A reversal candle has a large wick and a small body'; threshold_fits §1 crossover 1.0 (grade A)"),
}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_1D_c2", lambda: detect(cl.load_m1()))
    print(len(ev), ev["olhc"].mean(), ev["shape_rev"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    print("probe", probe["passed"])
    for rd, (col, rule, src) in READINGS.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD, hold_basis="bars")
        print(rd, {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                           "mde", "exposure_bars", "ties", "ctrl_overlap")})
        op = {"rules": OP_BASE + [f"gate {col}: {rule}"], "params": {**PARAMS, "gate": col}}
        p = cl.write_result(CID, rd, res, operationalization=op, params_source={**SRC, "gate": src},
                            script=__file__, probe=probe,
                            notes=f"gate firing rate {ev[col].mean():.3f} on {len(ev)} one-sided daily C2s")
        print(p)
