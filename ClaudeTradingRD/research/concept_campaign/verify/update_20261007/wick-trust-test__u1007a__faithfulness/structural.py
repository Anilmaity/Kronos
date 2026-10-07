import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import cl, np, pd, events, s

ev = events()
b = cl.gate_test(ev, "trusted", mask_available_at="decision_time", max_hold="10h", keep_trades=True)["_trades"]
yes = b[b.gate].copy(); no = b[~b.gate].copy()

def tt(name, frame):
    r = cl.trade_test(frame, max_hold="10h")
    print(name, s(r), {k: round(v["diff"], 3) for k, v in r["blocks"].items()}, "avgR_gross", round(r["avg_R_gross"], 4), flush=True)

base_y = ev[ev.trusted].reset_index(drop=True)[["decision_time", "available_at", "direction", "stop_px", "rr"]]
#tt("yes_as_traded", base_y)
# opposite direction, same entry, same stop distance
fl = pd.DataFrame({"decision_time": pd.DatetimeIndex(yes.decision_time), "available_at": pd.DatetimeIndex(yes.decision_time),
                   "direction": -yes.direction.values, "stop_dist": yes.risk.values, "rr": 2.0})
fl = fl.reset_index(drop=True)
tt("yes_flipped_direction", fl)
# shifted one LTF bar later (next 1h close), same stop level
sh = base_y.copy(); sh["decision_time"] = sh.decision_time + pd.Timedelta("1h"); sh["available_at"] = sh.decision_time
tt("yes_shifted_+1h", sh)
sh2 = base_y.copy(); sh2["decision_time"] = sh2.decision_time - pd.Timedelta("1h"); sh2["available_at"] = sh2.decision_time
tt("yes_shifted_-1h(one bar early, stop=final level: diagnostic only)", sh2)

# placement-matched control: each yes vs 'no' rows (stop also at the day's running extreme) with same direction,
# stop distance within +-15%, NY hour within +-1, |dt| <= 30 days. Raw net_R comparison (cost cancels).
ny = lambda x: cl.to_ny(pd.DatetimeIndex(x)).hour.to_numpy()
yh, nh = ny(yes.decision_time), ny(no.decision_time)
yt, nt = pd.DatetimeIndex(yes.decision_time).asi8, pd.DatetimeIndex(no.decision_time).asi8
nd, nr, nR = no.direction.to_numpy(), no.risk.to_numpy(), no.net_R.to_numpy()
order = np.argsort(nt); nt_s = nt[order]
D30 = 30 * 86400 * 10**9
m, keep = np.full(len(yes), np.nan), np.zeros(len(yes), bool)
for i, (t, d, r, h) in enumerate(zip(yt, yes.direction.to_numpy(), yes.risk.to_numpy(), yh)):
    lo, hi = np.searchsorted(nt_s, t - D30), np.searchsorted(nt_s, t + D30)
    idx = order[lo:hi]
    dh = np.abs(((nh[idx] - h + 12) % 24) - 12)
    sel = idx[(nd[idx] == d) & (np.abs(nr[idx] / r - 1) <= 0.15) & (dh <= 1) & (nt[idx] != t)]
    if len(sel) >= 3:
        m[i] = nR[sel].mean(); keep[i] = True
d = yes.net_R.to_numpy()[keep] - m[keep]
day = pd.DatetimeIndex(yes.decision_time).normalize().asi8[keep]
u, inv = np.unique(day, return_inverse=True)
rng = np.random.default_rng(20260825); sums = np.bincount(inv, d); cnt = np.bincount(inv)
bs = [sums[k].sum() / cnt[k].sum() for k in (rng.integers(0, len(u), len(u)) for _ in range(2000))]
yr = pd.DatetimeIndex(yes.decision_time).year.to_numpy()[keep]
print(f"placement-matched: matched {keep.sum()}/{len(yes)}  yes - matched_no = {d.mean():+.4f} "
      f"[{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}] (day-cluster bootstrap)")
print("  by half: H1", round(d[yr < 2021].mean(), 4), "H2", round(d[yr >= 2021].mean(), 4),
      " pre-2024", round(d[yr < 2024].mean(), 4), "2024+", round(d[yr >= 2024].mean(), 4))
