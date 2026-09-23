import numpy as np, pandas as pd
import indep as I
ev = pd.read_pickle("indep_events.pkl")
tn, O, H, L = I.tn, I.O, I.H, I.L
rng = np.random.default_rng(7)
ro, rn, prior_o, prior_n = [], [], [], []
for tt, lv, d in zip(pd.DatetimeIndex(ev.t).as_unit("ns").asi8, ev.lvl.values, ev.dir.values):
    p = np.searchsorted(tn, tt); nb = I.day_end[np.searchsorted(I.day_end, p, side="right")] - p
    q = min(p+nb, len(tn)); ro.append(H[p:q].max()-L[p:q].min()); prior_o.append(H[max(0,p-240):p].max()-L[max(0,p-240):p].min())
    loc = pd.Timestamp(tt, tz="UTC").tz_convert("America/New_York").tz_localize(None)
    for _ in range(50):
        kd = int(rng.integers(-30, 31))
        if kd == 0: continue
        try: cu = (loc+pd.Timedelta(days=kd)).tz_localize("America/New_York").tz_convert("UTC").value
        except Exception: continue
        p2 = np.searchsorted(tn, cu)
        if p2 < len(tn) and tn[p2] == cu:
            q2 = min(p2+nb, len(tn)); rn.append(H[p2:q2].max()-L[p2:q2].min()); prior_n.append(H[max(0,p2-240):p2].max()-L[max(0,p2-240):p2].min()); break
    else:
        rn.append(np.nan); prior_n.append(np.nan)
print("forward range obs/null median ratio", np.nanmedian(ro)/np.nanmedian(rn), "mean", np.nanmean(ro)/np.nanmean(rn))
print("prior-4h range obs/null median ratio", np.nanmedian(prior_o)/np.nanmedian(prior_n))
