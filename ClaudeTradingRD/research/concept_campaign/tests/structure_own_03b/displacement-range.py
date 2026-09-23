"""displacement-range (TTrades, CAuN4tvLInQ / Gu7FjYYcKhI) — trade_test.

Claim: after an aggressive move over structure, anchor a fib from the low that STARTED the
move (and broke the structure) to the high it reaches (trailed as it extends); buy only in
the discount of that leg (mirror for shorts); stop below the anchor low; target the high
the leg reached. If price never retraces into the discount, no trade. '+' = beats the
matched random entry at the same stop/target geometry.

Operationalisation (declared before the first run):
  * 15m bars (concept htf 1H/15m). Structure = latest confirmed unbroken 2/2 swing high
    (low); break = first 15m CLOSE beyond it at bar j.
  * aggressive = threshold_fits displacement: over N=4 candles from the break, window
    range / pre-break 4-candle range >= 1.5 AND distance beyond the broken level / pre
    range >= 0.65. The setup becomes live at the close of candle j+3.
  * anchor low A = the lowest low from the broken swing bar through the break bar j (the
    low that started the move that broke structure). High anchor H = running high since
    j, trailed on M1 (H uses M1 bars strictly before the one being tested).
  * entry: the first M1 bar after the setup is live whose low reaches EQ = (A + H) / 2;
    decide at that M1 bar's close, enter next M1 open. Requires that close to lie
    strictly between A and H.
  * setup expires 16 15m bars (4h) after going live, or when a newer same-direction setup
    goes live (a new displacement leg supersedes the old one). One trade per setup.
  * stop = A; target = H at the fill decision; time exit 8h.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402
from detectors.primitives import swing_points  # noqa: E402

N, R_MIN, D_MIN = 4, 1.5, 0.65
LIVE_BARS, MAX_HOLD = 16, "8h"
M1D = pd.Timedelta(minutes=1)


def setups(b: pd.DataFrame) -> pd.DataFrame:
    sw = swing_points(b[["high", "low"]], 2, 2)
    h, lo, c = (b[k].to_numpy(float) for k in ("high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"])
    ish, isl = sw["swing_high"].to_numpy(), sw["swing_low"].to_numpy()
    n = len(b)
    rows = []
    hi_i = lo_i = -1
    for j in range(n):
        i = j - 3                      # swing at i known at close of i+2 -> usable from i+3
        if i >= 0 and ish[i]:
            hi_i = i
        if i >= 0 and isl[i]:
            lo_i = i
        for d in (1, -1):
            si = hi_i if d == 1 else lo_i
            if si < 0:
                continue
            lvl = h[si] if d == 1 else lo[si]
            if not ((d == 1 and c[j] > lvl) or (d == -1 and c[j] < lvl)):
                continue
            if d == 1:
                hi_i = -1
            else:
                lo_i = -1
            if j - N < 0 or j + N - 1 >= n:
                continue
            pre = h[j - N:j].max() - lo[j - N:j].min()
            wh, wl = h[j:j + N].max(), lo[j:j + N].min()
            dist = (wh - lvl) if d == 1 else (lvl - wl)
            if not (pre > 0 and (wh - wl) / pre >= R_MIN and dist / pre >= D_MIN):
                continue
            anchor = lo[si:j + 1].min() if d == 1 else h[si:j + 1].max()
            rows.append({"live_at": ct[j + N - 1], "break_close": ct[j], "direction": d,
                         "anchor": float(anchor),
                         "expire_at": ct[min(j + N - 1 + LIVE_BARS, n - 1)]
                         if j + N - 1 + LIVE_BARS < n else pd.NaT})
    return pd.DataFrame(rows, columns=["live_at", "break_close", "direction", "anchor",
                                       "expire_at"])


def detect(m1):
    b = cl.build_bars(m1, "15min")
    S = setups(b).sort_values("live_at", kind="stable").reset_index(drop=True)
    tn = m1.index
    H, L, Cl = (m1[k].to_numpy(float) for k in ("high", "low", "close"))
    rows = []
    for d in (1, -1):
        s = S[S.direction == d].reset_index(drop=True)
        for r in range(len(s)):
            live = s.live_at[r]
            end = s.expire_at[r]
            if r + 1 < len(s):
                nxt = s.live_at[r + 1]
                end = nxt if (pd.isna(end) or nxt < end) else end
            if pd.isna(end):
                end = tn[-1] + M1D                       # scan to the end of the data
            i0 = tn.searchsorted(s.break_close[r] - pd.Timedelta(minutes=15))  # break bar start
            a = tn.searchsorted(live)                    # first M1 bar starting >= live
            e = tn.searchsorted(end - M1D, side="right")  # M1 bars that close <= end
            if a >= e:
                continue
            A = s.anchor[r]
            if d == 1:
                run = np.maximum.accumulate(H[i0:e])
                prev = np.concatenate([[-np.inf], run[:-1]])[a - i0:]   # max of bars BEFORE
                eq = (A + prev) / 2
                hit = np.flatnonzero(L[a:e] <= eq)
            else:
                run = np.minimum.accumulate(L[i0:e])
                prev = np.concatenate([[np.inf], run[:-1]])[a - i0:]
                eq = (A + prev) / 2
                hit = np.flatnonzero(H[a:e] >= eq)
            if not len(hit):
                continue
            m = a + hit[0]
            tgt = prev[hit[0]]
            if not (min(A, tgt) < Cl[m] < max(A, tgt)):
                continue
            t = tn[m] + M1D
            rows.append({"decision_time": t, "available_at": t, "direction": d,
                         "stop_px": float(A), "target_px": float(tgt),
                         "live_at": live})
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "live_at"]
    out = pd.DataFrame(rows, columns=cols)
    return (out.drop_duplicates(subset=["decision_time", "direction"])
            .sort_values("decision_time").reset_index(drop=True))


if __name__ == "__main__":
    ev = cl.cache_frame("disp_range_15m_eq_live16", lambda: detect(cl.load_m1()))
    print(len(ev), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    C.show(res)
    p = cl.write_result(
        "displacement-range", None, res,
        operationalization={"rules": [
            "15m bars: break = first 15m close beyond the latest confirmed unbroken 2/2 swing; aggressive = N=4 window range/pre-range >= 1.5 and distance beyond level/pre-range >= 0.65, live at the 4th window candle's close",
            "anchor = lowest low (highest high) from the broken swing bar through the break bar; far anchor = running extreme since the break, trailed on M1 (prior M1 bars only)",
            "entry: first M1 bar after live whose low (high) reaches the leg's 0.5; decide at that M1 close (must be between anchor and trailed extreme), enter next M1 open",
            "expire 16 15m bars after live or when a newer same-direction setup goes live; stop = anchor; target = trailed extreme at the fill; 8h time exit"],
            "params": {"tf": "15min", "swing": "2/2", "N": N, "r": R_MIN, "d": D_MIN,
                       "entry_level": 0.5, "live_bars": LIVE_BARS, "max_hold": MAX_HOLD}},
        params_source={
            "tf": "corpus: CAuN4tvLInQ concept timeframes htf 1H/15m, ltf 5m/1m (15m leg, M1 fill)",
            "swing": "phase3: swing_points left=2 right=2",
            "N": "threshold_fits: displacement N-window default N=4",
            "r": "threshold_fits: displacement win_range/pre_range default 1.5",
            "d": "threshold_fits: displacement dist/pre_range default 0.65",
            "entry_level": "corpus: CAuN4tvLInQ 'ideally you want to see a retracement into a discount before going along' (0.5 = discount boundary)",
            "live_bars": "declared-before-run: 16 15m bars (4h) for the retracement to arrive",
            "max_hold": "declared-before-run: 8h for the move back to the leg high"},
        script=__file__, probe=probe,
        notes="Entry at the 0.5 boundary of the displacement leg (no PD-array requirement); target the trailed leg extreme, stop the anchor, so the geometry is ~1:1.")
    print(p)
