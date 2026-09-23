"""mmxm-phase-sequence — $niper's market maker sell/buy model on 15m (guest; contested).

Sell model (buy model mirrored), all on 15m bars, one model per direction per NY
trading day. Everything below is declared before the first run:
  1. Premium array = the previous NY trading day's high (PDH; coverage >= 0.5).
  2. Smart money reversal: a 15m bar trades above PDH; the reaction must form: a 15m
     CLOSE below the most recent 2/2 swing low confirmed before the sweep bar, within
     16 bars (4h). H0 = highest high from the sweep bar to that MSS close.
  3. Leg 1 = H0 -> MSS bar. Its first bearish FVG (gap wholly formed after H0).
  4. FIRST ENTRY: first bar after the MSS whose high trades into that FVG (high >=
     gap low), high still < H0, with the gap low above the leg's equilibrium
     ((H0 + L1)/2, L1 = lowest low since H0 through that bar): "OTE FVG in premium".
     Within 32 bars of the MSS. Short at the next M1 open; stop H0; target PDL.
  5. Break of structure: a close below L1 (the low the retracement started from)
     within 32 bars of entry 1, with H0 never retaken. H1 = the retracement high
     (highest high from entry-1 bar to the BOS bar).
  6. SECOND ENTRY (the "silver bullet" second distribution leg): the first bearish FVG of
     leg H1 -> BOS, same premium rule vs (H1 + L2)/2, first bar after the BOS whose
     high trades into it with high < H1, within 32 bars. Stop H1; target PDL.
  Everything must stay inside the sweep's trading day. Target PDL must lie below the
  decision bar's close (else the objective is gone and the entry is dropped).
  Hold 480 M1 bars (8 trading hours).
Readings:
  a  trade_test on the SECOND-leg entries (the model's claimed best entry).
  b  gate_test on first+second entries, mask = second leg; claim second > first
     ("the second leg is the highest probability trade entry"), clustered by model.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl  # noqa: E402
from detectors.primitives import fair_value_gaps, swing_points  # noqa: E402

TF = "15min"
MSS_WAIT = 16
ENTRY_WAIT = 32
HOLD = "480min"


def _models(o, h, l, c, sw_lo_conf, fvg_bear_lo, fvg_bear_hi, fvg_bear, pdh, pdl, day_start, day_end,
            ct, mids, sgn):
    """Sell model on (o,h,l,c) as given. For the buy model the caller negates prices."""
    out = []
    n = len(c)
    for d0, d1 in zip(day_start, day_end):
        ref = pdh[d0]
        if not np.isfinite(ref):
            continue
        sweep = None
        for i in range(d0, d1):
            if h[i] > ref:
                sweep = i
                break
        if sweep is None:
            continue
        # most recent swing low confirmed at or before the sweep bar
        swl = sw_lo_conf[sweep]
        if not np.isfinite(swl):
            continue
        mss = None
        for k in range(sweep, min(d1, sweep + MSS_WAIT + 1)):
            if c[k] < swl:
                mss = k
                break
        if mss is None:
            continue
        h0pos = sweep + int(np.argmax(h[sweep:mss + 1]))
        H0 = h[h0pos]
        # first bearish FVG wholly after H0 through the MSS bar (stamped on 3rd bar)
        fv = None
        for i in range(h0pos + 2, mss + 1):
            if fvg_bear[i]:
                fv = i
                break
        if fv is None:
            continue
        glo = fvg_bear_lo[fv]
        e1 = None
        L1 = np.min(l[h0pos:mss + 1])
        for j in range(mss + 1, min(d1, mss + ENTRY_WAIT + 1)):
            if h[j] >= H0:
                break
            L1 = min(L1, l[j])
            if h[j] >= glo:
                if glo >= (H0 + L1) / 2.0:
                    e1 = j
                break
        if e1 is None:
            continue
        mid = mids[e1] if mids is not None else e1
        tgt = pdl[d0]
        if np.isfinite(tgt) and tgt < c[e1]:
            out.append((e1, H0, tgt, 1, mid))
        # break of structure below L1, then the second leg
        bos = None
        for k in range(e1 + 1, min(d1, e1 + ENTRY_WAIT + 1)):
            if h[k] >= H0:
                break
            if c[k] < L1:
                bos = k
                break
        if bos is None:
            continue
        h1pos = e1 + int(np.argmax(h[e1:bos + 1]))
        H1 = h[h1pos]
        fv2 = None
        for i in range(h1pos + 2, bos + 1):
            if fvg_bear[i]:
                fv2 = i
                break
        if fv2 is None:
            continue
        g2 = fvg_bear_lo[fv2]
        L2 = np.min(l[h1pos:bos + 1])
        e2 = None
        for j in range(bos + 1, min(d1, bos + ENTRY_WAIT + 1)):
            if h[j] >= H1:
                break
            L2 = min(L2, l[j])
            if h[j] >= g2:
                if g2 >= (H1 + L2) / 2.0:
                    e2 = j
                break
        if e2 is None:
            continue
        if np.isfinite(tgt) and tgt < c[e2]:
            out.append((e2, H1, tgt, 2, e1))
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF)
    b = b[b["n_m1"] > 0]
    ct = pd.DatetimeIndex(b["close_time"])
    ph = cl.prior_hilo(ct, "1D", m1=m1, min_coverage=0.5)
    # the prior day must be the day before this bar's trading day (not an older one
    # picked up because this bar's own day has not closed)
    td = cl.trading_day(b.index)
    tdv = td.to_numpy()
    starts = np.flatnonzero(np.r_[True, tdv[1:] != tdv[:-1]])
    ends = np.r_[starts[1:], len(b)]
    rows = []
    for sgn in (-1, 1):   # -1 = sell model at PDH, +1 = buy model at PDL (prices negated)
        f = 1.0 if sgn == -1 else -1.0
        o = f * b["open"].to_numpy()
        if sgn == -1:
            h, l = b["high"].to_numpy(), b["low"].to_numpy()
            pdh, pdl = ph["high"].to_numpy(), ph["low"].to_numpy()
        else:
            h, l = -b["low"].to_numpy(), -b["high"].to_numpy()
            pdh, pdl = -ph["low"].to_numpy(), -ph["high"].to_numpy()
        c = f * b["close"].to_numpy()
        tmp = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=b.index)
        sw = swing_points(tmp, 2, 2)
        # last swing-low price confirmed by each bar's close (confirmed_at = bar index of
        # the right-hand confirming bar; known at that bar's close)
        conf_pos = np.full(len(b), np.nan)
        is_l = sw["swing_low"].to_numpy()
        pos = np.flatnonzero(is_l)
        cpos = pos + 2
        keep = cpos < len(b)
        arr = np.full(len(b), np.nan)
        arr[cpos[keep]] = l[pos[keep]]
        sw_lo_conf = pd.Series(arr).ffill().to_numpy()
        fg = fair_value_gaps(tmp)
        fb = fg["bearish_fvg"].to_numpy()
        mods = _models(o, h, l, c, sw_lo_conf, fg["gap_low"].to_numpy(), fg["gap_high"].to_numpy(),
                       fb, pdh, pdl, starts, ends, ct, None, sgn)
        for (j, stop, tgt, leg, model_bar) in mods:
            rows.append({"decision_time": ct[j], "available_at": ct[j], "direction": sgn,
                         "stop_px": f * stop, "target_px": f * tgt, "leg": leg,
                         "model_id": f"{sgn}_{b.index[model_bar].value}"})
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "leg", "model_id"]
    if not rows:
        return pd.DataFrame(columns=cols + ["second_leg"])
    ev = pd.DataFrame(rows)[cols].sort_values(["decision_time", "direction"]).reset_index(drop=True)
    ev["second_leg"] = ev["leg"] == 2
    return ev


OP_RULES = [
    "15m bars, NY trading day (18:00 roll); premium/discount array = prior day high/low "
    "(coverage >= 0.5)",
    "SMR: first 15m trade through PDH; MSS = 15m close below the last 2/2 swing low "
    "confirmed before the sweep, within 16 bars; H0 = high from sweep to MSS",
    "entry 1: first return into the first bearish FVG of leg H0->MSS, FVG low above "
    "(H0+L1)/2, high < H0, within 32 bars; stop H0; target PDL",
    "BOS: close below L1 within 32 bars; H1 = retracement high; entry 2: first return "
    "into the first bearish FVG of leg H1->BOS, above (H1+L2)/2, high < H1, within 32 "
    "bars; stop H1; target PDL",
    "mirrored at PDL for the buy model; all steps inside the sweep's trading day; "
    "entries whose PDL/PDH objective is already behind price are dropped",
    "hold 480 M1 bars (hold_basis bars)"]
PARAMS = {"tf": TF, "array": "prior-day high/low", "min_coverage": 0.5, "swing": "2/2",
          "mss_wait_bars": MSS_WAIT, "entry_wait_bars": ENTRY_WAIT, "premium": "FVG low >= 0.5 of leg",
          "target": "previous daily low/high", "max_hold": HOLD, "hold_basis": "bars"}
SRC = {"tf": "corpus: CrUfTskOveo AM Trades builds the sell model on the 15-minute",
       "array": "corpus: UmLWRlXd_V8 'a push up into a premium array (previous daily high ...)'",
       "min_coverage": "declared-before-run: skip stub sessions (README trap 6)",
       "swing": "phase3: 2/2 fractal swing definition (conjunction_preregistration)",
       "mss_wait_bars": "declared-before-run: the reaction must form within 4h of the sweep",
       "entry_wait_bars": "declared-before-run: each step within 8h, and inside the trading day",
       "premium": "corpus: UmLWRlXd_V8 'I don't take a short unless price is above equilibrium'",
       "target": "corpus: UmLWRlXd_V8 execution targets 'previous daily low'",
       "max_hold": "declared-before-run: intraday model, 8 trading hours",
       "hold_basis": "declared-before-run: trading-time hold across the 17:00 halt (trap 7)"}

if __name__ == "__main__":
    ev = cl.cache_frame("mmxm_phase_seq_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev.leg.value_counts().to_dict(), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="12D")
    print("probe", probe["passed"], probe["events_compared"])
    ev2 = ev[ev.leg == 2].reset_index(drop=True)
    probe2 = cl.probe_lookahead(lambda m: (lambda e: e[e.leg == 2].reset_index(drop=True))(detect(m)),
                                ev2, lookback="12D")
    ra = cl.trade_test(ev2, max_hold=HOLD, hold_basis="bars", claim="+")
    print("a", {k: ra.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail", "exposure_bars")})
    rb = cl.gate_test(ev, "second_leg", mask_available_at="decision_time", max_hold=HOLD,
                      hold_basis="bars", cluster="model_id", claim="+")
    print("b", {k: rb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "verdict", "verdict_detail")})
    cl.write_result("mmxm-phase-sequence", "a", ra,
                    operationalization={"rules": OP_RULES + ["reading a: trade_test on second-leg entries only"],
                                        "params": PARAMS},
                    params_source=SRC, script=__file__, probe=probe2,
                    notes="$niper's sequence; the AM Trades 'SMR stab' early entry and the MMXM "
                          "Trader's SMT pairing are not included (no correlate used).")
    cl.write_result("mmxm-phase-sequence", "b", rb,
                    operationalization={"rules": OP_RULES + ["reading b: gate second-leg vs first-leg entries, clustered by model"],
                                        "params": PARAMS},
                    params_source=SRC, script=__file__, probe=probe,
                    notes="Comparative claim: second distribution leg beats the first post-MSS entry.")
