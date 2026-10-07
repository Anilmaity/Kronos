"""dealing-range — TTrades update 2026-10-07 (yb3Te7tiGRk "Understanding Dealing Ranges"), gate_test x2.

NEW claim only. Prior reading dealing-range.json (naive nearest-high/low at 15m, half split) is NULL
and untouched. The plain half split has also come back NULL on three other range definitions
(premium-discount-equilibrium a/b, premium-discount a/b, upper-half-positioning), so it is NOT re-run
as if new. What this video adds, and what is tested:

  * the range is MODEL-ANCHORED: from the C2 extreme being traded away from to the higher-timeframe
    swing "that made" it ("find the swing high that made this swing low", "this is not always going
    to be candle one");
  u1007a  the 25% floor: "As I get to 25% of the range or lower, that is where I'm not really looking
          for shorts" (mirror for longs) -> accepted = entry location p < 0.75, rejected = p >= 0.75;
  u1007b  nesting: "you use multiple dealing ranges and you sh[ort] the premium of both" -> among
          entries that sit inside BOTH a live daily-C2 range (outer: "this daily dealing range ... on
          this hourly chart") and the live 1h-C2 range (inner: "a new setup here, but on the hourly and
          5 minute"), gated = favourable half (EQ inclusive) of both.

Location p is measured from the invalidation end (C2 extreme) toward the target end (the swing that
made it): p = 0 at the C2 extreme, 1 at the target. Longs-in-discount and shorts-in-premium are both
p <= 0.5; "25% of the range or lower" for a short is p >= 0.75.

Base book (a: every row; b: only rows that also sit in a live same-direction daily C2 setup):
  HTF = 1h. C2 (method_spec §3.2): bullish low[k] < low[k-1] and close[k] > low[k-1]; bearish mirror.
  Outer range (bullish C2): lo = C2 low; hi = high of the swing that made it = walking back from bar
    k-1, the first bar i with high[i] > high[i-1], high[i] > high[i-2] (left side of the phase-3 2/2
    fractal) and high[i] >= every high in (i, k] (right side confirmed by the bars up to C2 itself,
    so known at C2's close and candle 1 is allowed). Wicks. Bearish mirror. Cap 120 bars, else none.
  Window: C3 and C4 = the two 1h candles after C2 (spec §3.4: from C5 onward a new phase is likely).
  Entry model: 5m rung-0 CISD (series_open, 2/2, max_wait 3) in the C2's direction, decided at its
    5m close inside the window; the most recent same-direction C2 owns it. Dropped if, between C2's
    close and the decision, price traded through the C2 extreme (void) or took the target end
    (spent) - both stated invalidations.
  Stop = CISD protected swing; target 2R; hold 10 x 5m = 50 min.
  Outer (daily) range for b: the same C2 / walk-back / C3+C4 / void / spent rules on 1D candles
    (NY 18:00 roll, sessions with <= 600 M1 are not candles).
"""
import sys

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

CID = "dealing-range"
RR = 2.0
MAX_HOLD = "50min"
CAP = 120          # walk-back cap, bars (both TFs)
FLOOR = 0.75       # u1007a: reject p >= 0.75 ("25% of the range or lower" for shorts)
HALF = 0.5         # u1007b: favourable half, EQ inclusive
MIN_M1 = 600      # daily stub-session guard
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "px", "p_1h", "p_1d",
        "setup", "setup_d", "gate_a", "gate_b"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def _empty():
    return pd.DataFrame({c: pd.Series(dtype="float64") for c in COLS})


def _maker(x, k, cap=CAP):
    """Index of the swing in x (x = high for 'swing high that made the low at k'; x = -low for
    the mirror) found walking back from k-1: x[i] > x[i-1], x[i] > x[i-2], x[i] >= max x(i..k]."""
    m = x[k]
    for i in range(k - 1, max(k - cap, 2) - 1, -1):
        if x[i] >= m and x[i] > x[i - 1] and x[i] > x[i - 2]:
            return i
        m = max(m, x[i])
    return -1


def _setups(b):
    """C2 setups on bars b (spec §3.2) with their swing-anchored dealing range.
    Returns {d: (close_ns, window_end_ns, near, far)} arrays sorted by close."""
    h, l, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = _ns(b["close_time"])
    n = len(b)
    out = {}
    for d in (1, -1):
        if d == 1:
            hit = np.r_[False, (l[1:] < l[:-1]) & (c[1:] > l[:-1])]
        else:
            hit = np.r_[False, (h[1:] > h[:-1]) & (c[1:] < h[:-1])]
        rows = []
        for k in np.flatnonzero(hit):
            i = _maker(h, k) if d == 1 else _maker(-l, k)
            if i < 0:
                continue
            near, far = (l[k], h[i]) if d == 1 else (h[k], l[i])
            if (far - near) * d <= 0:
                continue
            end = ct[k + 2] if k + 2 < n else np.iinfo(np.int64).max   # C3 + C4
            rows.append((ct[k], end, near, far))
        out[d] = (np.array([r[0] for r in rows], dtype=np.int64),      # keep ns exact (no float)
                  np.array([r[1] for r in rows], dtype=np.int64),
                  np.array([r[2] for r in rows], dtype=float),
                  np.array([r[3] for r in rows], dtype=float))
    return out


def _live(S, d, t, c, st5, h5, l5):
    """Latest same-direction setup closed before t whose C3+C4 window holds t and which is
    neither void (C2 extreme traded through) nor spent (far end taken) on 5m bars up to c.
    Returns (setup close ns, near, far) or None."""
    sc, se, nr, fr = S[d]
    j = np.searchsorted(sc, t, "left") - 1
    if j < 0 or t > se[j]:
        return None
    s0 = np.searchsorted(st5, sc[j], "left")
    if s0 > c:
        return None
    hi, lo = h5[s0:c + 1].max(), l5[s0:c + 1].min()
    if d == 1 and (lo < nr[j] or hi > fr[j]):
        return None
    if d == -1 and (hi > nr[j] or lo < fr[j]):
        return None
    return int(sc[j]), float(nr[j]), float(fr[j])


def detect_all(m1):
    # An in-progress last bar is harmless: every event reads only bars up to its own decision bar,
    # and a C2 on that bar opens its window after its close (> the data's end).
    b1 = cl.build_bars(m1, "1h")
    bd = cl.build_bars(m1, "1D")
    bd = bd[bd["n_m1"] > MIN_M1]                              # stub/holiday sessions are not candles
    b5 = cl.build_bars(m1, "5min")
    if len(b1) < 10 or len(b5) < 50:
        return _empty()
    S1, SD = _setups(b1), _setups(bd)
    h5, l5 = b5["high"].to_numpy(float), b5["low"].to_numpy(float)
    st5, ct5 = _ns(b5.index), _ns(b5["close_time"])
    ev = cisd_events(b5[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return _empty()
    cpos = b5.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    edir = np.where(ev["direction"] == "bullish", 1, -1)
    cc, ps = ev["confirm_close"].to_numpy(float), ev["protected_swing"].to_numpy(float)
    rows = []
    for r in range(len(ev)):
        d, c = int(edir[r]), cpos[r]
        t = ct5[c]
        s1 = _live(S1, d, t, c, st5, h5, l5)
        if s1 is None:
            continue
        sid, nr, fr = s1
        px = cc[r]
        p1 = (px - nr) / (fr - nr)
        sd = _live(SD, d, t, c, st5, h5, l5)
        pD, did = (np.nan, -1) if sd is None else ((px - sd[1]) / (sd[2] - sd[1]), sd[0])
        rows.append((t, d, ps[r], px, p1, pD, sid, did))
    if not rows:
        return _empty()
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "px", "p_1h", "p_1d", "setup", "setup_d"])
    dt = pd.to_datetime(out["t"].to_numpy(), utc=True)
    out.insert(0, "decision_time", dt)
    out.insert(1, "available_at", dt)
    out["rr"] = RR
    out["gate_a"] = out["p_1h"] < FLOOR
    out["gate_b"] = (out["p_1h"] <= HALF) & (out["p_1d"] <= HALF)   # rows with no daily setup dropped in b
    out = out.drop(columns="t").sort_values(["decision_time", "direction"], kind="stable")
    out = out.drop_duplicates(["decision_time", "direction"]).reset_index(drop=True)
    return out[COLS]


def detect_a(m1):                                        # reads no daily bars
    return detect_all(m1).drop(columns=["p_1d", "setup_d", "gate_b"])


def detect_b(m1):
    ev = detect_all(m1)
    return ev[ev["setup_d"] >= 0].reset_index(drop=True)


OP_COMMON = [
    "HTF 1h bars (UTC-aligned build_bars). C2 (method_spec §3.2): bullish low[k] < low[k-1] "
    "and close[k] > low[k-1]; bearish high[k] > high[k-1] and close[k] < high[k-1]; no POI/CISD gate on C2",
    "1h dealing range (bullish): near = C2 low (invalidation), far = the high of the swing that made it: walking "
    "back from k-1, first bar i with high[i] > high[i-1], high[i-2] and high[i] >= all highs in (i, k]; wicks; "
    "cap 120 bars else no setup. Bearish mirror",
    "window = C3 and C4: entries decided after C2's close and at or before the close of the 2nd 1h bar after C2",
    "entry model: 5m rung-0 CISD (series_open, 2/2, max_wait 3) in the C2 direction, decided at its 5m close; owned "
    "by the latest same-direction C2 closed before it; dropped if since C2's close price traded through the C2 "
    "extreme (void) or took the far end (spent)",
    "stop = CISD protected swing; target 2R; time exit 50 min; enter next M1 open",
    "location p = (entry close - near) / (far - near) for longs, mirrored for shorts: 0 at the C2 extreme, 1 at target",
    "p_1h = location in the 1h C2 range (reading a's range; reading b's inner range)",
    "outer range (b only): same C2 / walk-back / C3+C4 window / void / spent rules on 1D candles (18:00 NY roll, "
    "sessions with <= 600 M1 are not candles, so the previous REAL day is C1); p_1d = location in it",
    "cluster = the owning setup (a: 1h C2; b: daily C2), several 5m entries per setup",
]
PARAMS = {"min_m1": MIN_M1, "htf": "1h", "ltf": "5min", "c2": "spec §3.2 sweep + close back inside", "swing": "left 2 + dominance to the extreme",
          "extremes": "wicks", "cap_bars": CAP, "window": "C3+C4", "entry": "5m CISD series_open 2/2 max_wait 3",
          "stop": "protected swing", "rr": RR, "max_hold": MAX_HOLD, "grid4h": "n/a (1h/5m only)"}
SRC = {
    "min_m1": "declared-before-run: daily stub guard 600 M1 (fractal-model-c2 u1007 value); corpus rVRk4MLTJSs 'bank holiday Monday. It doesn't count'",
    "htf": "corpus: yb3Te7tiGRk 'we have a new setup here, but on the hourly and 5 minute'",
    "ltf": "corpus: yb3Te7tiGRk 'where would be the dealing range for the 5minut? From this high to this low'",
    "c2": "method_spec: §3.2 C2 test low[i] < low[i-1] AND close[i] > low[i-1]; corpus yb3Te7tiGRk 'we have a candle 2 closure'",
    "swing": "corpus: yb3Te7tiGRk 'find the swing high that made this swing low' + 'this is not always going to be candle one'; "
             "phase3: left=2 of the locked 2/2 fractal, right side = dominance up to the C2 bar (declared-before-run so C1 can qualify)",
    "extremes": "declared-before-run: wick vs body unstated (draft ambiguity); wicks as in every prior range reading",
    "cap_bars": "declared-before-run: walk-back cap 120 bars ('continue until we find that swing high' gives no limit)",
    "window": "method_spec: §3.4 'from C5 onward, treat a new phase of price as likely'; corpus yb3Te7tiGRk 'trade candle three'",
    "entry": "phase3: rung-0 CISD config (series_open, 2/2, max_wait 3); method_spec §3.5 model = HTF closure + LTF CISD",
    "stop": "corpus: yb3Te7tiGRk 'Put my stop on that protected high'",
    "rr": "corpus: yb3Te7tiGRk 'I can get 2R prior to this high being taken out'",
    "max_hold": "phase3: 10 entry-TF bars (§1.13) = 10 x 5m",
    "grid4h": "declared-before-run: no 4h bars are read",
}
READ = {
    "u1007a": dict(det=detect_a, gate="gate_a", key="dr_u1007a_c2_1h5m", cluster="setup", lookback="20D",
                   rule=f"gate (25% floor): accepted p < {FLOOR}; rejected p >= {FLOOR} (shorts at 25% of the range "
                        "or lower; longs at 75% or higher by mirror). claim +: accepted beats rejected",
                   xp={"floor": FLOOR},
                   xs={"floor": "corpus: yb3Te7tiGRk 'As I get to 25% of the range or lower' (not looking for shorts); "
                                "75% mirror for longs is the draft's stated inference"}),
    "u1007b": dict(det=detect_b, gate="gate_b", key="dr_u1007b_c2_1d1h5m", cluster="setup_d", lookback="200D",
                   rule=f"book b = base rows that also sit in a live same-direction daily C2 range; gate (nesting): "
                        f"p_1d <= {HALF} AND p_1h <= {HALF} (favourable half, EQ inclusive, of both). claim +",
                   xp={"half": HALF},
                   xs={"half": "corpus: yb3Te7tiGRk 'you use multiple dealing ranges and you shorten [short in] the premium of both' "
                               "+ 'It's okay if I'm entering right around that EQ point' (EQ inclusive)"}),
}


def run(rd):
    R = READ[rd]
    det = R["det"]
    ev = cl.cache_frame(R["key"], lambda: det(cl.load_m1()))
    g = ev[R["gate"]]
    print(rd, "events", len(ev), "clusters", ev[R["cluster"]].nunique(), "gate rate", round(float(g.mean()), 3),
          "p_1h quartiles", np.round(ev["p_1h"].quantile([.25, .5, .75]).to_numpy(), 3))
    probe = cl.probe_lookahead(det, ev, lookback=R["lookback"])  # > walk-back warm-up (1h 120 bars; 1D 117 days)
    print("probe", probe["passed"])
    res = cl.gate_test(ev, R["gate"], mask_available_at="decision_time", max_hold=MAX_HOLD, cluster=R["cluster"])
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "n_complement", "gate_firing_rate", "diff",
                                   "ci_lo", "ci_hi", "p", "mde", "exposure_bars", "ties", "ctrl_overlap",
                                   "dependence", "halves")})
    op = {"rules": OP_COMMON + [R["rule"]], "params": {**PARAMS, **R["xp"]}}
    notes = (f"TTrades yb3Te7tiGRk swing-anchored (C2-first) dealing range. {len(ev)} events on "
             f"{ev['setup'].nunique()} 1h C2 setups ({ev[R['cluster']].nunique()} clusters); gate firing rate {g.mean():.3f}. "
             "The plain half split is not re-run as new: NULL on 4 prior range definitions (dealing-range, "
             "premium-discount-equilibrium a/b, premium-discount a/b, upper-half-positioning). Prior reading dealing-range.json untouched. "
             "Pre-run correction (no outcome seen): nesting was first drafted as 1h-outer / 5m-CISD-inner; the 5m CISD close sits at "
             "the top of its own 5m range by construction (median p 0.96 on a 2-month slice) and the video's nesting is daily/hourly "
             "outer with hourly/5m inner, so b was re-mapped to daily-outer / 1h-inner before any test ran.")
    p = cl.write_result(CID, rd, res, operationalization=op, params_source={**SRC, **R["xs"]},
                        script=__file__, probe=probe, notes=notes)
    print(p)


if __name__ == "__main__":
    for rd in sys.argv[1:] or list(READ):
        run(rd)
