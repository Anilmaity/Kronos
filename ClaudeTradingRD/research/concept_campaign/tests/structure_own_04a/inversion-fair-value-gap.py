"""inversion-fair-value-gap — contested; two readings.

Inversion (both readings, the stricter full-close rule the corpus states): an FVG of
polarity P is inverted by the first later close beyond its FAR edge (a bearish gap
[h[i], l[i-2]] is inverted bullish by a close > l[i-2]; mirror). A close beyond the CE
only does not count. "Swiftly" is bounded at 12 bars after the gap forms (declared).
Several gaps inverted by the same close = one inversion (the close clears the series).

reading a - the TTrades gating claim (gate_test, claim '+').
  Baseline: every 5m inversion traded at the inverting close (entry next M1 open) in the
  inversion direction, stop at the swing point = the extreme from the gap's first candle
  to the inverting bar, 2R, 50 min (10 entry bars). This is the "bare pattern" he names
  as the common mistake.
  Gate c2_small_wick: the in-progress 1H candle (the 1H/5m pairing) has swept the
  previous 1H candle's low (bullish; high for bearish) AND supports expansion: price is
  beyond its open in the trade direction with opposing run <= |price - open| (small wick).
  (SMT-in-place-of-sweep is not implemented: no correlate on the harness.)

reading b - the canonical retest reading (trade_test).
  15m inversions; after the inverting close, the first M1 touch back to the inverted
  zone's near edge (bullish: the old bearish gap's top) within 16 bars (4h) is the
  entry (decide at that M1 close, fill next M1 open); stop = the swing point (as above);
  skipped if that minute also trades through the stop; 2R; 150 min.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, complete_bars, empty, ns, to_ts, M1, LiveCandle,  # noqa: E402
                     live_support, fvg_arrays, ONE_MIN, PHASE3_SRC)

CID = "inversion-fair-value-gap"
MAXW = 12
RR = 2.0
A_TF, A_HTF, A_HOLD = "5min", "1h", "50min"
B_TF, B_HOLD, B_RETEST = "15min", "150min", 16
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "rr", "c2_small_wick"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def inversions(b: pd.DataFrame) -> pd.DataFrame:
    """One row per inverting bar j (per direction): j, direction, zone (lo, hi) of the
    outermost gap cleared, swing extreme from the earliest cleared gap's first candle to j."""
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    n = len(c)
    bull, bear, glo, ghi = fvg_arrays(h, l)
    rows = []
    if n < MAXW + 4:
        return pd.DataFrame(columns=["j", "d", "zlo", "zhi", "i"])
    cpad = np.r_[c, np.full(MAXW, np.nan)]
    win = np.lib.stride_tricks.sliding_window_view(cpad[1:], MAXW)[:n]   # closes i+1..i+MAXW
    for pol, sel, far, d in ((bear, bear, ghi, 1), (bull, bull, glo, -1)):
        ii = np.flatnonzero(sel)
        if not len(ii):
            continue
        w = win[ii]
        hit = (w > far[ii][:, None]) if d > 0 else (w < far[ii][:, None])
        hit = np.where(np.isnan(w), False, hit)
        any_ = hit.any(axis=1)
        k = np.argmax(hit, axis=1)
        jj = ii + 1 + k
        for i_, j_ in zip(ii[any_], jj[any_]):
            rows.append((j_, d, glo[i_], ghi[i_], i_))
    if not rows:
        return pd.DataFrame(columns=["j", "d", "zlo", "zhi", "i"])
    df = pd.DataFrame(rows, columns=["j", "d", "zlo", "zhi", "i"])
    g = df.groupby(["j", "d"])
    out = g.agg(zlo=("zlo", "min"), zhi=("zhi", "max"), i=("i", "min")).reset_index()
    ext = []
    for j_, d_, i_ in zip(out["j"], out["d"], out["i"]):
        seg = slice(int(i_) - 2, int(j_) + 1)
        ext.append(l[seg].min() if d_ > 0 else h[seg].max())
    out["ext"] = ext
    return out.sort_values("j").reset_index(drop=True)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    b = complete_bars(cl.build_bars(m1, A_TF), m1)
    if len(b) < 30:
        return empty(COLS_A)
    inv = inversions(b)
    if inv.empty:
        return empty(COLS_A)
    ct = ns(b["close_time"])
    tdec = ct[inv["j"].to_numpy(int)]
    d = inv["d"].to_numpy(int)
    m = M1(m1)
    lc = LiveCandle(m1, m, A_HTF)
    st = lc.at(tdec)
    hb = cl.build_bars(m1, A_HTF)
    hl, hh = hb["low"].to_numpy(float), hb["high"].to_numpy(float)
    k = st["bucket"]
    prev_ok = st["ok"] & (k >= 1)
    kp = np.clip(k - 1, 0, None)
    swept = prev_ok & np.where(d > 0, st["lo"] < hl[kp], st["hi"] > hh[kp])
    gate = swept & live_support(st, d, "wick")
    t = to_ts(tdec)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": inv["ext"].to_numpy(float), "rr": RR, "c2_small_wick": gate})
    # an inverting close already beyond the stop cannot happen; keep sane rows only
    c_j = b["close"].to_numpy(float)[inv["j"].to_numpy(int)]
    ok = d * (c_j - out["stop_px"].to_numpy()) > 0
    return out[ok].reset_index(drop=True)[COLS_A]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    b = complete_bars(cl.build_bars(m1, B_TF), m1)
    if len(b) < 30:
        return empty(COLS_B)
    inv = inversions(b)
    if inv.empty:
        return empty(COLS_B)
    m = M1(m1)
    ct = ns(b["close_time"])
    nb = len(b)
    rows = []
    for j, d, zlo, zhi, ext in zip(inv["j"].to_numpy(int), inv["d"].to_numpy(int), inv["zlo"].to_numpy(float),
                                   inv["zhi"].to_numpy(float), inv["ext"].to_numpy(float)):
        s0 = ct[j]
        # window end = close of bar j+16; if that bar is not complete in this slice, the slice end
        s1 = ct[j + B_RETEST] if j + B_RETEST < nb else m.t[-1] + ONE_MIN
        i0 = int(np.searchsorted(m.t, s0, side="left"))
        i1 = int(np.searchsorted(m.t, s1, side="left"))
        if i1 <= i0:
            continue
        near = zhi if d > 0 else zlo
        seg = (m.l[i0:i1] <= near) if d > 0 else (m.h[i0:i1] >= near)
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        q = i0 + int(kk[0])
        if (d > 0 and m.l[q] <= ext) or (d < 0 and m.h[q] >= ext):
            continue
        rows.append((m.t[q] + ONE_MIN, d, ext))
    if not rows:
        return empty(COLS_B)
    a = np.array(rows, dtype=object)
    t = to_ts(a[:, 0].astype(np.int64))
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": a[:, 1].astype(int),
                        "stop_px": a[:, 2].astype(float), "rr": RR})
    out = out.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return out.sort_values("decision_time").reset_index(drop=True)[COLS_B]


COMMON = [
    "FVG = 3-bar wick gap stamped on the 3rd bar; inversion = first close beyond the gap's FAR edge within 12 bars "
    "(CE-only closes do not count); gaps cleared by the same close merge into one inversion (outermost zone)",
    "swing point = the extreme (low for a bullish inversion) from the earliest cleared gap's first candle to the inverting bar",
]
OP_A = {"rules": COMMON + [
    "baseline: every 5m inversion, decide at the inverting close, enter next M1 open in the inversion direction, "
    "stop = swing point, 2R, 50 min",
    "gate c2_small_wick: in-progress 1H candle (at a boundary: just completed) has traded below the previous 1H low "
    "(bullish; above its high for bearish) AND price beyond its open in the trade direction with opposing run <= |price-open|"],
    "params": {"tf": A_TF, "htf": A_HTF, "max_wait_inv": MAXW, "rr": RR, "max_hold": A_HOLD, "wick_body_cut": 1.0,
               "smt_substitute": "not implemented"}}
SRC_A = {"tf": "corpus: inversion-fair-value-gap.yaml ltf [15m, 5m, 3m]; method_spec §1.2 1H/5m pairing",
         "htf": "method_spec §1.2: 5m entry pairs with the 1-hour candle",
         "max_wait_inv": "declared-before-run: 'swiftly closed over' has no bar limit; 12 bars (= 1 hour on 5m)",
         "rr": "corpus: inversion-fair-value-gap.yaml execution targets '2R'",
         "max_hold": PHASE3_SRC,
         "wick_body_cut": "threshold_fits: small wick = opposing_run/body <= 1.0 (grade A)",
         "smt_substitute": "declared-before-run: no correlated series in concept_lab; sweep branch only"}
OP_B = {"rules": COMMON + [
    "15m inversions; entry = first M1 bar within 16 bars (4h) after the inverting close touching the inverted zone's near "
    "edge (bullish: old bearish gap's top); decide at that M1 close, enter next M1 open; skip if that minute also "
    "reaches the stop",
    "stop = swing point; target 2R; 150 min"],
    "params": {"tf": B_TF, "max_wait_inv": MAXW, "retest_bars": B_RETEST, "rr": RR, "max_hold": B_HOLD}}
SRC_B = {"tf": "corpus: inversion-fair-value-gap.yaml timeframes (15m ltf); method_spec §1.3 favourite entry TF",
         "max_wait_inv": "declared-before-run: 'swiftly closed over' has no bar limit; 12 bars",
         "retest_bars": "declared-before-run: the corpus gives no expiry ('the retest need not be immediate'); 16 bars = 4h",
         "rr": "corpus: inversion-fair-value-gap.yaml measurable 'hit rate of a fixed-2R trade taken on the first retest'",
         "max_hold": PHASE3_SRC}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame(f"{CID}_a_5m", lambda: detect_a(cl.load_m1()))
        print("a", len(ev), ev["c2_small_wick"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="15D")
        print("probe", probe["passed"])
        res = cl.gate_test(ev, "c2_small_wick", mask_available_at="decision_time", max_hold=A_HOLD)
        print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                       "mde", "exposure_bars", "ties", "ctrl_overlap")})
        print(cl.write_result(CID, "a", res, operationalization=OP_A, params_source=SRC_A, script=__file__,
                              probe=probe, notes=f"gate firing rate {ev['c2_small_wick'].mean():.3f}"))
    if "b" in which:
        ev = cl.cache_frame(f"{CID}_b_15m", lambda: detect_b(cl.load_m1()))
        print("b", len(ev))
        probe = cl.probe_lookahead(detect_b, ev, lookback="15D")
        print("probe", probe["passed"])
        res = cl.trade_test(ev, max_hold=B_HOLD)
        print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                       "mde", "exposure_bars", "ties", "ctrl_overlap")})
        print(cl.write_result(CID, "b", res, operationalization=OP_B, params_source=SRC_B, script=__file__,
                              probe=probe))
