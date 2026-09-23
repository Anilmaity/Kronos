"""strat-trigger-entry — trade_test.

Concept (9MUej4g9Jyg, "Strat Entries - Strat and ICT Part 2"): the ICT setup supplies the
location (liquidity swept, structure broken, a fair value gap to enter from) on the 15m; the
Strat supplies the TRIGGER on the 5m: once price is in the gap, enter when the current 5m
candle trades through the PREVIOUS 5m candle's extreme in the intended direction (2-2
reversal; the 2-1-2 and inside-bar triggers are the same break of the prior candle). Stop on
the trigger candle's extreme.

Setup (bullish; mirrored for bearish), 15m bars:
  1. sweep: a bar trades below the most recent confirmed 2/2 swing low (not swept before);
  2. structure broken: within 12 bars a bar CLOSES above the most recent confirmed swing high;
  3. a bullish FVG (low[k] > high[k-2]) formed in the leg from the sweep bar to that close
     (the latest one);
  4. after that close, price trades into the FVG (M1 low <= FVG top) within 3h, without
     trading below the leg's low first.
Trigger, 5m: from the tap on, the first M1 whose high exceeds the high of the last COMPLETED
5m bar (that bar must be the one containing the tap or a later one), before the 3h deadline
and before the leg low is traded. Decide at that M1's close; enter next M1 open.
Stop = the lower of the broken 5m bar's low and the trigger 5m bar's low so far; 2R;
max hold 50 min (10 entry-TF bars). One trade per FVG.

All parameters are declared here before the first run.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.primitives import swing_points

SETUP_TF = "15min"
SWING = 2
MSS_BARS = 12
TAP_WINDOW = pd.Timedelta(hours=3)
RR = 2.0
MAX_HOLD = "50min"
NS5 = np.int64(5 * 60 * 10**9)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "fvg_top",
            "fvg_bot", "leg_ext"]
    b = cl.build_bars(m1, SETUP_TF)
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    ohlc = b[["open", "high", "low", "close"]]
    sw = swing_points(ohlc, left=SWING, right=SWING)
    H, L, C = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    n = len(b)
    ct_ns = b["close_time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    is_sh, is_sl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    # b5 for the trigger
    b5 = cl.build_bars(m1, "5min")
    b5_ct = b5["close_time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    b5_st = b5.index.values.astype("datetime64[ns]").astype(np.int64)
    b5_h, b5_l = b5["high"].to_numpy(), b5["low"].to_numpy()
    mt = m1.index.values.astype("datetime64[ns]").astype(np.int64)
    MH, ML = m1["high"].to_numpy(), m1["low"].to_numpy()
    rows = []
    seen = set()
    for bull in (True, False):
        # running most-recent confirmed swing (value, pos) and whether swept
        last_sl = last_sh = np.nan
        sl_swept = sh_swept = True
        pend_l, pend_h = [], []            # swings awaiting confirmation (pos)
        for i in range(n):
            # swings at p are confirmed once bar p+SWING has closed, i.e. usable from bar p+SWING+1
            p = i - SWING - 1
            if p >= 0:
                if is_sl[p]:
                    last_sl, sl_swept = L[p], False
                if is_sh[p]:
                    last_sh, sh_swept = H[p], False
            if bull:
                if sl_swept or np.isnan(last_sl) or not (L[i] < last_sl):
                    continue
                sl_swept = True
                ref_sh = last_sh
            else:
                if sh_swept or np.isnan(last_sh) or not (H[i] > last_sh):
                    continue
                sh_swept = True
                ref_sh = last_sl
            if np.isnan(ref_sh):
                continue
            # structure break within MSS_BARS: close beyond the most recent confirmed opposite
            # swing (updated as new swings confirm)
            ref = ref_sh
            j_mss = -1
            for j in range(i + 1, min(n, i + 1 + MSS_BARS)):
                q = j - SWING - 1
                if q > i - SWING - 1 and q >= 0:
                    if bull and is_sh[q]:
                        ref = H[q]
                    if (not bull) and is_sl[q]:
                        ref = L[q]
                if (bull and C[j] > ref) or ((not bull) and C[j] < ref):
                    j_mss = j
                    break
            if j_mss < 0:
                continue
            leg_ext = L[i:j_mss + 1].min() if bull else H[i:j_mss + 1].max()
            fvg = None
            for k in range(j_mss, max(i + 1, 2) - 1, -1):
                if k - 2 < i:
                    break
                if bull and L[k] > H[k - 2]:
                    fvg = (L[k], H[k - 2], k)
                    break
                if (not bull) and H[k] < L[k - 2]:
                    fvg = (L[k - 2], H[k], k)      # (top, bottom)
                    break
            if fvg is None:
                continue
            key = (bull, fvg[2])
            if key in seen:
                continue
            seen.add(key)
            top, bot, _ = fvg
            t0 = ct_ns[j_mss]
            t1 = t0 + TAP_WINDOW.value
            a = np.searchsorted(mt, t0)
            z = np.searchsorted(mt, t1)
            tap = -1
            for m in range(a, z):
                if bull:
                    if ML[m] < leg_ext:
                        break
                    if ML[m] <= top:
                        tap = m
                        break
                else:
                    if MH[m] > leg_ext:
                        break
                    if MH[m] >= bot:
                        tap = m
                        break
            if tap < 0:
                continue
            tap_b5 = (mt[tap] // NS5) * NS5          # start of the 5m bar containing the tap
            trig = -1
            for m in range(tap, z):
                if (bull and ML[m] < leg_ext) or ((not bull) and MH[m] > leg_ext):
                    break
                cur = (mt[m] // NS5) * NS5
                q = np.searchsorted(b5_ct, cur, side="right") - 1   # last 5m bar closed by cur
                if q < 0 or b5_st[q] < tap_b5:
                    continue
                if bull and MH[m] > b5_h[q]:
                    lo_cur = ML[np.searchsorted(mt, cur):m + 1].min()
                    trig, stop = m, min(b5_l[q], lo_cur)
                    break
                if (not bull) and ML[m] < b5_l[q]:
                    hi_cur = MH[np.searchsorted(mt, cur):m + 1].max()
                    trig, stop = m, max(b5_h[q], hi_cur)
                    break
            if trig < 0:
                continue
            rows.append({"decision_time": mt[trig] + 60 * 10**9,
                         "direction": 1 if bull else -1, "stop_px": float(stop),
                         "fvg_top": float(top), "fvg_bot": float(bot),
                         "leg_ext": float(leg_ext)})
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True).dt.as_unit("ns")
    out["available_at"] = out["decision_time"]
    out["rr"] = RR
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("strat_trig_15m_5m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "15m setup: sweep of the most recent unswept confirmed 2/2 swing low; within 12 bars a "
        "close above the most recent confirmed swing high (structure broken); latest bullish "
        "FVG in the sweep..break leg (mirrored for shorts)",
        "within 3h of the break close: price trades into the FVG before trading beyond the leg "
        "extreme",
        "5m Strat trigger: first M1 from the tap on whose high breaks the last completed 5m "
        "bar's high (that bar at/after the tap's 5m bar) -> decide at that M1 close, enter "
        "next M1 open",
        "stop = min(broken 5m bar low, trigger 5m bar low so far); target 2R; 50 min hold; "
        "one trade per FVG"],
        "params": {"setup_tf": SETUP_TF, "trigger_tf": "5min", "swing": SWING,
                   "mss_bars": MSS_BARS, "tap_window": "3h", "rr": RR, "max_hold": MAX_HOLD}}
    src = {"setup_tf": "corpus: 9MUej4g9Jyg setup walked on 15m (concept htf 15m)",
           "trigger_tf": "corpus: 9MUej4g9Jyg 'focus on like a five minute three minute'",
           "swing": "phase3: locked 2/2 swing",
           "mss_bars": "declared-before-run: structure break within 12 15m bars (3h) of the sweep",
           "tap_window": "declared-before-run: FVG tap + trigger within 3h of the break",
           "rr": "method_spec: §5.3 2R floor",
           "max_hold": "phase3: 10 entry-TF bars (§1.13), entry TF 5m"}
    p = cl.write_result("strat-trigger-entry", None, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe,
                        notes="The three Strat triggers (2-2, 2-1-2, inside-bar break) all reduce "
                              "to the break of the previous 5m candle's extreme in the intended "
                              "direction, so one trigger rule covers them.")
    print(p)
