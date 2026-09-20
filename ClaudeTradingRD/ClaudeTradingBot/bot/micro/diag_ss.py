"""Diagnostic: raw forward-excursion asymmetry after an Asian-range sweep+reclaim.
If favorable >> adverse, an exit tuning can win; if symmetric, the family is dead.
Measured cost-free on TRAIN M1 mid bars. Run: python -m bot.micro.diag_ss
"""
import numpy as np
from bot.micro.engine import Bars, atr as atr_fn
from bot.micro.features import resample_bars, hours_mask
from bot.oanda_s5 import load

TF = 60
ASIA_A, ASIA_Z = 0, 7
HORIZON = 60


def session_range(b, hi, lo):
    n = b.n; day = b.day; hod = b.hod
    aH = np.full(n, np.nan); aL = np.full(n, np.nan)
    chg = np.concatenate(([0], np.where(np.diff(day) != 0)[0] + 1, [n]))
    for k in range(len(chg) - 1):
        s, e = int(chg[k]), int(chg[k + 1])
        m = (hod[s:e] >= ASIA_A) & (hod[s:e] < ASIA_Z)
        if m.any():
            aH[s:e] = hi[s:e][m].max(); aL[s:e] = lo[s:e][m].min()
    return aH, aL


def first_per_day(idx, day):
    if len(idx) == 0:
        return idx
    dd = day[idx]; keep = np.ones(len(idx), bool); keep[1:] = dd[1:] != dd[:-1]
    return idx[keep]


def excursion(b, hi, lo, idx, side):
    """For each signal, MFE (favorable) & MAE (adverse) in pts over HORIZON bars."""
    mfe = []; mae = []
    for i in idx:
        j0 = i + 1; j1 = min(i + 1 + HORIZON, b.n)
        if j1 <= j0:
            continue
        entry = b.mid[i]
        seg_hi = hi[j0:j1]; seg_lo = lo[j0:j1]
        if side < 0:   # short: favorable = down
            mfe.append(entry - seg_lo.min()); mae.append(seg_hi.max() - entry)
        else:          # long: favorable = up
            mfe.append(seg_hi.max() - entry); mae.append(entry - seg_lo.min())
    return np.array(mfe), np.array(mae)


def main():
    d = load("2024-01", "2025-07")
    b = Bars(resample_bars(d, TF))
    hi = (b.ah + b.bh) * 0.5; lo = (b.al + b.bl) * 0.5; c = b.mid
    A = atr_fn(b, 20); a = np.where(np.isfinite(A) & (A > 0), A, np.nan)
    aH, aL = session_range(b, hi, lo)
    rng = aH - aL
    sess = hours_mask(b, (7, 8, 9, 10, 11, 12, 13, 14))
    base = sess & np.isfinite(a) & (a >= 0.5) & np.isfinite(rng) & (rng >= 4) & (rng <= 45)

    for wick in (0.3, 0.6, 1.0):
        sweepH = base & (hi >= aH + 0.05 * a) & (hi <= aH + 1.6 * a) & (c <= aH) & ((hi - c) >= wick * a)
        sweepL = base & (lo <= aL - 0.05 * a) & (lo >= aL - 1.6 * a) & (c >= aL) & ((c - lo) >= wick * a)
        iH = first_per_day(np.where(sweepH)[0], b.day)
        iL = first_per_day(np.where(sweepL)[0], b.day)
        for tag, idx, side in (("SHORT(high-sweep)", iH, -1), ("LONG(low-sweep)", iL, 1)):
            mfe, mae = excursion(b, hi, lo, idx, side)
            if len(mfe) == 0:
                continue
            print(f"wick={wick} {tag:20s} n={len(mfe):4d} "
                  f"MFEmed={np.median(mfe):5.2f} MAEmed={np.median(mae):5.2f} "
                  f"MFEmean={mfe.mean():5.2f} MAEmean={mae.mean():5.2f} "
                  f"edge(mean MFE-MAE)={mfe.mean()-mae.mean():+5.2f}")
        print()


if __name__ == "__main__":
    main()
