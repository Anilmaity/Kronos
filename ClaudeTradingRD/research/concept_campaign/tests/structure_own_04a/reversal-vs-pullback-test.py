"""reversal-vs-pullback-test — gate_test, claim '-'.

Concept: mark short-term lows in an uptrend (highs in a downtrend); a break WITH
DISPLACEMENT is a reversal on that timeframe, no break is a pullback. Hierarchy: the
15-minute governs the 5-minute - a 5m reversal under an intact 15m uptrend is only a
retracement within the 15m trend (traded counter-trend to the 15m imbalance, and longs
are reloaded there).

Baseline book (stated): every 5m structural reversal traded in the reversal direction.
  * 5m swings = 2/2 fractals, usable from the confirming bar; 5m uptrend = last two
    confirmed swing highs rising AND last two confirmed swing lows rising (mirror);
  * break = first 5m close below the last confirmed swing low while in a 5m uptrend
    (mirror above the last swing high in a downtrend);
  * displacement = threshold_fits §2 magnitude gate on the N=4 window starting at the
    break bar: window range / pre-break 4-bar range >= 1.5 AND distance travelled beyond
    the broken level / pre-break range >= 0.65; decide at the 4th bar's close;
  * enter next M1 open in the reversal direction, stop = the extreme between the broken
    swing and the decision (the top the reversal came from), 2R, 50 min (10 bars).
Gate htf_intact: at the decision, the 15m structure (closed 15m bars only) is still in
the ORIGINAL trend - 15m uptrend (HH and HL on the last two confirmed 15m 2/2 swings) and
the last 15m close is still above the last confirmed 15m swing low (mirror).
claim '-': reversals under an intact 15m trend (really pullbacks) do WORSE than the rest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, complete_bars, empty, ns, to_ts, swing_points, OHLC,  # noqa: E402
                     PHASE3_SRC)

CID = "reversal-vs-pullback-test"
LTF, HTF = "5min", "15min"
N_WIN, R_MIN, D_MIN = 4, 1.5, 0.65
RR = 2.0
HOLD = "50min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "htf_intact"]


def structure(b: pd.DataFrame) -> dict:
    """Per bar j (state known at j's close): last/prev confirmed swing high & low values and
    the last confirmed swing low/high bar index."""
    sw = swing_points(b[OHLC], left=2, right=2)
    n = len(b)
    h = b["high"].to_numpy(float)
    l = b["low"].to_numpy(float)
    out = {}
    for kind, arr in (("h", h), ("l", l)):
        flag = sw["swing_high" if kind == "h" else "swing_low"].to_numpy(bool)
        pos = np.flatnonzero(flag)
        conf = pos + 2                                     # usable from bar i+2's close
        keep = conf < n
        pos, conf = pos[keep], conf[keep]
        last = np.full(n, np.nan)
        prev = np.full(n, np.nan)
        lidx = np.full(n, -1)
        if len(pos):
            last_s = pd.Series(np.nan, index=range(n))
            last_s.iloc[conf] = arr[pos]
            prev_vals = np.r_[np.nan, arr[pos][:-1]]
            prev_s = pd.Series(np.nan, index=range(n))
            prev_s.iloc[conf] = prev_vals
            idx_s = pd.Series(np.nan, index=range(n))
            idx_s.iloc[conf] = pos
            last = last_s.ffill().to_numpy()
            prev = prev_s.ffill().to_numpy()
            lidx = idx_s.ffill().fillna(-1).to_numpy(int)
        out[f"last_{kind}"], out[f"prev_{kind}"], out[f"idx_{kind}"] = last, prev, lidx
    out["up"] = (out["last_h"] > out["prev_h"]) & (out["last_l"] > out["prev_l"])
    out["dn"] = (out["last_h"] < out["prev_h"]) & (out["last_l"] < out["prev_l"])
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = complete_bars(cl.build_bars(m1, LTF), m1)
    hb = complete_bars(cl.build_bars(m1, HTF), m1)
    if len(b) < 40 or len(hb) < 20:
        return empty(COLS)
    h, l, c = (b[x].to_numpy(float) for x in ("high", "low", "close"))
    n = len(b)
    s = structure(b)
    ct = ns(b["close_time"])
    # data-hole guard: a bar whose final minute is missing cannot be known complete at its close
    whole = (ns(b["last_m1"]) + 60_000_000_000) == ct
    hs = structure(hb)
    hc = hb["close"].to_numpy(float)
    hct = ns(hb["close_time"])
    rows = []
    for d in (-1, 1):
        # d = reversal direction. -1: break DOWN of the last swing low in a 5m uptrend.
        lvl = s["last_l"] if d < 0 else s["last_h"]
        trend = s["up"] if d < 0 else s["dn"]
        prev_lvl = np.r_[np.nan, lvl[:-1]]
        prev_trend = np.r_[False, trend[:-1]]
        prev_c = np.r_[np.nan, c[:-1]]
        brk = prev_trend & np.isfinite(prev_lvl) & ((c < prev_lvl) if d < 0 else (c > prev_lvl)) & \
            ((prev_c >= prev_lvl) if d < 0 else (prev_c <= prev_lvl))
        sidx = s["idx_l"] if d < 0 else s["idx_h"]
        for j in np.flatnonzero(brk):
            e = j + N_WIN - 1
            if j < N_WIN or e >= n or not whole[e]:
                continue
            pre = h[j - N_WIN:j].max() - l[j - N_WIN:j].min()
            if pre <= 0:
                continue
            wr = h[j:e + 1].max() - l[j:e + 1].min()
            level = prev_lvl[j]
            dist = (level - l[j:e + 1].min()) if d < 0 else (h[j:e + 1].max() - level)
            if wr / pre < R_MIN or dist / pre < D_MIN:
                continue
            i_sw = sidx[j - 1]
            if i_sw < 0:
                continue
            stop = h[i_sw:e + 1].max() if d < 0 else l[i_sw:e + 1].min()
            if d * (c[e] - stop) <= 0:          # stop must sit beyond the entry, against the trade
                continue
            rows.append((ct[e], d, stop))
    if not rows:
        return empty(COLS)
    arr = np.array(rows, dtype=object)
    tdec = arr[:, 0].astype(np.int64)
    d = arr[:, 1].astype(int)
    # 15m state as of the decision: last 15m bar with close_time <= decision
    k = np.searchsorted(hct, tdec, side="right") - 1
    hwhole = (ns(hb["last_m1"]) + 60_000_000_000) == hct
    kk = np.clip(k, 0, None)
    k = np.where((k >= 0) & (hct[kk] == tdec) & ~hwhole[kk], k - 1, k)   # same data-hole guard
    kk = np.clip(k, 0, None)
    # original trend = opposite of the reversal direction
    intact = np.where(d < 0, hs["up"][kk] & (hc[kk] >= hs["last_l"][kk]),
                      hs["dn"][kk] & (hc[kk] <= hs["last_h"][kk]))
    intact &= k >= 0
    t = to_ts(tdec)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": arr[:, 2].astype(float), "rr": RR, "htf_intact": intact.astype(bool)})
    out = out.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return out.sort_values("decision_time").reset_index(drop=True)[COLS]


OP = {"rules": [
    "5m 2/2 swings (usable from the confirming bar); 5m uptrend = last two confirmed swing highs AND lows rising (mirror)",
    "break = first 5m close beyond the last confirmed swing low (uptrend) / high (downtrend)",
    "displacement = N=4 window from the break bar: window range / pre-break 4-bar range >= 1.5 AND distance beyond the "
    "broken level / pre-break range >= 0.65; decide at the 4th bar's close",
    "trade the reversal: enter next M1 open, stop = extreme from the broken swing's bar to the decision bar, 2R, 50 min",
    "gate htf_intact: closed 15m bars at the decision still in the original trend (HH & HL on the last two confirmed 15m "
    "2/2 swings, last 15m close not beyond the last confirmed 15m swing low/high)",
    "data-hole guard: the decision 5m bar must contain its final M1 minute; a 15m bar closing exactly at the decision "
    "with its final minute missing is not used (cannot be known complete at its close)",
    "claim '-': gated reversals (5m reversal under an intact 15m trend = pullback) do worse"],
    "params": {"ltf": LTF, "htf": HTF, "swing": "2/2", "disp_n": N_WIN, "disp_r": R_MIN, "disp_d": D_MIN,
               "rr": RR, "max_hold": HOLD}}
SRC = {"ltf": "corpus: FdRKBTz0Fps 'he reads trend on the 5-minute' (reversal-vs-pullback-test.yaml)",
       "htf": "corpus: FdRKBTz0Fps 'for most people i would recommend the 15-minute chart' - the 15m governs",
       "swing": PHASE3_SRC,
       "disp_n": "threshold_fits: §2 displacement magnitude N=4",
       "disp_r": "threshold_fits: §2 r=1.5",
       "disp_d": "threshold_fits: §2 d=0.65",
       "rr": PHASE3_SRC, "max_hold": PHASE3_SRC}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_5m15m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["htf_intact"].mean(), ev["direction"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "htf_intact", mask_available_at="decision_time", max_hold=HOLD, claim="-")
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    print(cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__, probe=probe,
                          notes=f"BUG FIX RE-RUN: the first run inverted the stop-side sanity check and emitted 0 events (UNTESTABLE n=0); fixed and re-run once (plus a data-hole guard added after the lookahead probe failed on a missing M1 minute, before any test ran). gate firing rate {ev['htf_intact'].mean():.3f}. The reload leg (long at the 15m "
                                "imbalance after a 1m/5m shift) is not tested here."))
