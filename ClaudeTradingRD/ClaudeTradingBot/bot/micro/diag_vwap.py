"""Diagnostic: at a VWAP-extension signal, is reversion (toward VWAP) actually
larger than continuation (away)? Measure MFE-toward-VWAP vs MAE-away over next K
M1 bars on real OOS bars. Also report a rejection-confirmed subset."""
import numpy as np
from bot.oanda_s5 import load
from bot.micro.engine import Bars, atr
from bot.micro.features import resample_bars, hours_mask, ema

d = load("2025-08", "2026-06")
b = Bars(resample_bars(d, 60))
mid = b.mid; a = atr(b, 14)
sess = hours_mask(b, (7,8,9,10,11,12,13,14,15))

# session vwap (reuse strat logic, simplified)
import bot.micro.strat_m1_r1_3 as s
vwap, nsince = s._session_vwap(b, sess)
dev = mid - vwap
K = 2.0
ok = np.isfinite(vwap) & (a>0) & sess & (nsince>=10)
ext_up = ok & (dev >= K*a)   # extended up -> reversion = DOWN
ext_dn = ok & (dev <= -K*a)

Kf = 20  # forward bars
ah, al = (b.ah+b.bh)*0.5, (b.al+b.bl)*0.5  # mid hi/lo approx

def excursion(idx, revert_down):
    mfe=[]; mae=[]
    for i in idx:
        j0=i+1; j1=min(i+1+Kf, b.n)
        if j1<=j0: continue
        seg_hi = ah[j0:j1].max(); seg_lo = al[j0:j1].min()
        e = mid[i]
        if revert_down:  # short fade: favorable = down, adverse = up
            mfe.append(e - seg_lo); mae.append(seg_hi - e)
        else:
            mfe.append(seg_hi - e); mae.append(e - seg_lo)
    return np.array(mfe), np.array(mae)

iu = np.where(ext_up)[0]; il = np.where(ext_dn)[0]
mfe_u, mae_u = excursion(iu, True)
mfe_d, mae_d = excursion(il, False)
mfe = np.concatenate([mfe_u, mfe_d]); mae = np.concatenate([mae_u, mae_d])
print(f"ALL extensions n={len(mfe)}: MFE(revert) med={np.median(mfe):.2f} mean={mfe.mean():.2f} | "
      f"MAE(cont) med={np.median(mae):.2f} mean={mae.mean():.2f}  ratio_med={np.median(mfe)/np.median(mae):.2f}")

# rejection-confirmed: bar's own high pierced band but close came back inside band
band = K*a
rej_up = ext_up & ((b.ah*0.5+b.bh*0.5 - vwap) >= band) & (dev < band*0.9)  # closed back below band
# simpler: define pierce via prior bar extreme; use close vs band
# Use: this bar closed inside while max dev over last 2 bars exceeded band
dev_prev = np.concatenate([[np.nan], dev[:-1]])
rej_up = ok & (dev_prev >= band*0) & (np.maximum(dev, dev_prev) >= band) & (dev < band*0.7) & (dev>0)
rej_dn = ok & (np.minimum(dev, dev_prev) <= -band) & (dev > -band*0.7) & (dev<0)
ru=np.where(rej_up)[0]; rd=np.where(rej_dn)[0]
mfe_u,mae_u=excursion(ru,True); mfe_d,mae_d=excursion(rd,False)
mfe=np.concatenate([mfe_u,mfe_d]); mae=np.concatenate([mae_u,mae_d])
if len(mfe):
    print(f"REJECTION-confirmed n={len(mfe)}: MFE(revert) med={np.median(mfe):.2f} | "
          f"MAE(cont) med={np.median(mae):.2f}  ratio_med={np.median(mfe)/max(np.median(mae),1e-9):.2f}")
