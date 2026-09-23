"""False-EDGE measurement on pure-noise books under rules-2, five families.

    python rules2_false_edge.py <family> <book_from> <book_to> <out.csv>   (NB=2000)

rules2_false_edge.csv (530 books) was produced by an earlier revision that seeded
each book with Python's per-process string hash; this file seeds deterministically.
"""
import sys, os, time
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/review_statistics")
from common import *
fam = sys.argv[1]; b0 = int(sys.argv[2]); b1 = int(sys.argv[3]); out = sys.argv[4]
NB = int(os.environ.get("NB", 1000))
FAM_OFF = {"unclustered": 1, "setups120": 2, "dailybias": 3, "gate_setups": 4, "rate_daily": 5}
t_utc = pd.DatetimeIndex(pd.to_datetime(TN).tz_localize("UTC"))
g15 = np.flatnonzero((NY.minute.to_numpy() % 15) == 0)
def book(b):
    rng = np.random.default_rng(700000 + 1000 * FAM_OFF[fam] + b)
    if fam == "unclustered":            # exp10
        cand = np.flatnonzero((NY.minute.to_numpy() % 5) == 0)
        pos = np.sort(rng.choice(cand, 5000, replace=False))
        ev = events_from_pos(pos, rng.choice([-1, 1], len(pos)), 3.0, 2.0)
        return cl.trade_test(ev, max_hold="3h", n_boot=NB, blocks=False)
    if fam == "setups120":              # exp2
        ny_ok = np.flatnonzero((NYMIN >= 7*60) & (NYMIN < 9*60))
        starts = np.sort(rng.choice(ny_ok, 1200, replace=False))
        pos = np.unique((starts[:, None] + np.arange(120)[None, :]).ravel()); pos = pos[pos < len(TN)]
        sd = rng.choice([-1, 1], len(starts))
        dirs = sd[np.searchsorted(starts, pos, side="right") - 1]
        return cl.trade_test(events_from_pos(pos, dirs, 3.0, 2.0), max_hold="2h", n_boot=NB, blocks=False)
    if fam == "dailybias":              # exp3
        td = np.asarray(cl.trading_day(t_utc[g15]))
        days_u, di = np.unique(td, return_inverse=True)
        pick = rng.random(len(days_u)) < 0.6; ddir = rng.choice([-1, 1], len(days_u))
        sel = pick[di]
        return cl.trade_test(events_from_pos(g15[sel], ddir[di][sel], 4.0, 2.0), max_hold="4h", n_boot=NB, blocks=False)
    if fam == "gate_setups":            # exp7
        ny_ok = np.flatnonzero(NY.minute.to_numpy() == 0)
        K, L = 1500, 60
        starts = np.sort(rng.choice(ny_ok, K, replace=False))
        pos = (starts[:, None] + np.arange(L)[None, :]).ravel(); own = np.repeat(np.arange(K), L)
        keep = np.r_[True, np.diff(pos) > 0] & (pos < len(TN)); pos, own = pos[keep], own[keep]
        dirs = rng.choice([-1, 1], K)[own]; gate = (rng.random(K) < 0.4)[own]
        ev = events_from_pos(pos, dirs, 3.0, 2.0); ev["gate"] = gate
        return cl.gate_test(ev, "gate", mask_available_at=ev["decision_time"], max_hold="2h", n_boot=NB, blocks=False)
    if fam == "rate_daily":             # exp9
        td = np.asarray(cl.trading_day(t_utc[g15]))
        days_u, di = np.unique(td, return_inverse=True)
        pick = rng.random(len(days_u)) < 0.6; sel = pick[di]
        obs = (rng.random(len(days_u)) < 0.4)[di][sel].astype(float)
        tt = t_utc[g15][sel]
        return cl.rate_test(obs, tt, available_at=tt, null_p=np.full(len(obs), 0.4), n_boot=NB, blocks=False)
    raise SystemExit("unknown family")
rows = []
for b in range(b0, b1):
    t0 = time.time(); r = book(b)
    se = (r["ci_hi"] - r["ci_lo"]) / 3.919928
    rows.append(dict(family=fam, book=b, n=r["n"], diff=r["diff"], lo=r["ci_lo"], hi=r["ci_hi"],
                     how=r["ci_method"], z=r["diff"] / se, verdict=r["verdict"],
                     dep=r["dependence"]["day_block_mean_days"], n_eff=r["dependence"]["n_eff"],
                     sec=round(time.time() - t0, 1)))
    print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)
