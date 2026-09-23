"""mmxm-second-leg-entry — AM Trades: enter on the SECOND leg (failure swing), not the first.

Test: gate_test on a book of MMXM FVG-retrace entries (leg 1 AND leg 2 of the same
state machine). gate = leg 2. claim '+': leg-2 entries beat leg-1 entries
(control-adjusted R).

Bearish model on 15m (bullish = the same machine on negated prices):
  H0   = a confirmed 2/2 swing high (smart money reversal).
  MSS  = a 15m close below the most recent confirmed swing low that pivots before H0.
  leg1 = first 15m bar after the MSS that trades up into a bearish FVG formed after H0
         (high >= gap_low) without closing above the gap (close <= gap_high).
         -> leg-1 event, stop = H0.
  ITH  = the first 2/2 swing high pivoting at/after the leg-1 tap bar (below H0).
  BOS  = a close below the lowest low between the MSS bar and the ITH pivot.
  leg2 = first bar after the BOS that taps a bearish FVG formed after the ITH pivot
         (same tap rule). -> leg-2 event, stop = ITH (the defended stop).
  Any trade above the active stop reference (H0 before leg 2, ITH during leg 2)
  invalidates the model; a stage that waits > 96 bars (one day) expires.
Both legs: 2R target, 10 entry-TF bars (150 min) max hold.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "mmxm-second-leg-entry"
TF = "15min"
EXPIRE = 96
RR = 2.0
MAX_HOLD = "150min"


def swings(h, l, left=2, right=2):
    n = len(h)
    hs = pd.Series(h); ls = pd.Series(l)
    prev_h = hs.shift(1).rolling(left).max(); prev_l = ls.shift(1).rolling(left).min()
    next_h = hs[::-1].shift(1).rolling(right).max()[::-1]
    next_l = ls[::-1].shift(1).rolling(right).min()[::-1]
    is_h = ((hs > prev_h) & (hs >= next_h)).to_numpy()
    is_l = ((ls < prev_l) & (ls <= next_l)).to_numpy()
    return is_h, is_l


def bearish_models(o, h, l, c):
    """Return list of (bar_idx_of_tap, leg, stop_px) for the bearish machine."""
    n = len(h)
    is_h, is_l = swings(h, l)
    # FVG bearish at third bar k: h[k] < l[k-2]
    fvg_k = np.where(np.r_[False, False, h[2:] < l[:-2]])[0]
    fvg_lo = {k: h[k] for k in fvg_k}
    fvg_hi = {k: l[k - 2] for k in fvg_k}
    out = []
    state = 0
    last_sl_pivot = -1          # most recent CONFIRMED swing-low pivot index
    H0 = H0i = Lref = None
    t_stage = 0
    mss_i = tap1_i = ITH = ITHi = leg1_low = None
    fv_ptr = 0
    active = []                 # FVG third-bar indices collected for the current stage
    for i in range(n):
        # swings confirmed at bar i pivot at i-2
        p = i - 2
        new_sh = p >= 2 and is_h[p]
        if p >= 2 and is_l[p]:
            last_sl_pivot = p
        # FVGs formed at bar i (third bar = i) become known at i's close
        new_fvg = i in fvg_lo
        if state != 0 and i - t_stage > EXPIRE:
            state = 0
        if state == 0:
            if new_sh and last_sl_pivot >= 0 and last_sl_pivot < p:
                # swing low pivoting before H0, confirmed by now
                H0, H0i, Lref = h[p], p, l[last_sl_pivot]
                state, t_stage, active = 1, i, []
                # FVGs formed after H0 pivot and already known
                active = [k for k in fvg_k[(fvg_k > H0i) & (fvg_k <= i)]]
            continue
        if state == 1:                      # armed: waiting for MSS
            if new_fvg:
                active.append(i)
            if h[i] > H0:
                state = 0
                continue
            if c[i] < Lref:
                state, mss_i, t_stage = 2, i, i
            continue
        if state == 2:                      # leg 1: waiting for the FVG tap
            if h[i] > H0:
                state = 0; continue
            hit = False
            for k in active:
                if k < i and h[i] >= fvg_lo[k] and c[i] <= fvg_hi[k]:
                    hit = True; break
            if new_fvg:
                active.append(i)
            if hit:
                out.append((i, 1, H0))
                state, tap1_i, t_stage = 3, i, i
            continue
        if state == 3:                      # waiting for the ITH (swing high pivot >= tap1)
            if h[i] > H0:
                state = 0; continue
            if new_sh and p >= tap1_i:
                ITH, ITHi = h[p], p
                leg1_low = l[mss_i:ITHi + 1].min()
                state, t_stage, active = 4, i, [k for k in fvg_k[(fvg_k > ITHi) & (fvg_k <= i)]]
            continue
        if state == 4:                      # waiting for BOS below the leg-1 low
            if new_fvg and i > ITHi and i not in active:
                active.append(i)
            if h[i] > ITH:
                state = 0; continue
            if c[i] < leg1_low:
                state, t_stage = 5, i
            continue
        if state == 5:                      # leg 2: waiting for the FVG tap
            if h[i] > ITH:
                state = 0; continue
            hit = False
            for k in active:
                if k < i and h[i] >= fvg_lo[k] and c[i] <= fvg_hi[k]:
                    hit = True; break
            if new_fvg:
                active.append(i)
            if hit:
                out.append((i, 2, ITH))
                state = 0
            continue
    return out


def detect(m1):
    b = cl.build_bars(m1, TF)
    o, h, l, c = (b[x].to_numpy() for x in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    rows = []
    for sgn, (oo, hh, ll, cc) in ((-1, (o, h, l, c)), (1, (-o, -l, -h, -c))):
        for i, leg, stop in bearish_models(oo, hh, ll, cc):
            rows.append((ct[i], sgn, stop if sgn == -1 else -stop, leg))
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "leg2"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "leg"])
    df = df.sort_values(["decision_time", "direction"]).reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.decision_time, "available_at": df.decision_time,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "rr": RR, "leg2": (df.leg == 2).to_numpy()})


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{TF}_exp{EXPIRE}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.leg2.mean(), ev.direction.value_counts().to_dict())
    if "--dry" in sys.argv:
        print(ev.head(10)); raise SystemExit
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.gate_test(ev, "leg2", mask_available_at="decision_time", max_hold=MAX_HOLD, claim="+")
    for k in ("n", "n_gated", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "15m bars; swings = 2/2 fractal, confirmed 2 bars after the pivot",
        "bearish model: H0 swing high; MSS = close below the last confirmed swing low pivoting before H0",
        "leg 1 = first tap (high>=gap_low, close<=gap_high) of a bearish FVG formed after H0; stop H0",
        "ITH = first swing high pivoting at/after the leg-1 tap; BOS = close below min low MSS..ITH",
        "leg 2 = first tap of a bearish FVG formed after the ITH; stop = ITH (defended stop)",
        "trade above H0 (stages 1-3) or ITH (stages 4-5) invalidates; a stage older than 96 bars expires",
        "bullish = same machine on negated prices; decide at tap bar close, enter next M1 open",
        "gate = leg 2; complement = leg 1; both 2R target, 150 min max hold"],
        "params": {"tf": TF, "swing": "2/2", "rr": RR, "max_hold": MAX_HOLD, "expire_bars": EXPIRE}}
    src = {"tf": "corpus: CrUfTskOveo timeframes htf 1H/15m (concept yaml); 15m chosen as the model TF",
           "swing": "phase3: meta/conjunction_preregistration.md §1.8 left=2,right=2",
           "rr": "phase3: §1.12 primary 2R fixed (same for both legs so only the entry differs)",
           "max_hold": "phase3: §1.13 10 entry-TF periods",
           "expire_bars": "declared-before-run: a model stage waiting more than one trading day (96 x 15m) is dead; bounds probe warm-up"}
    notes = ("Leg-1 rows include models that never reach leg 2 (that membership is only known later, "
             "so it cannot be a row filter). Target is fixed 2R rather than the model completion "
             "(original consolidation), which the concept names but does not locate objectively.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, notes=notes, probe=probe)
    print(p)
