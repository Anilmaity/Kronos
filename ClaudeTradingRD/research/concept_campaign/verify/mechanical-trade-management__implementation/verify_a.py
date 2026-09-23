"""Independent re-implementation of reading (a) of mechanical-trade-management.
Ledger redirected to a scratch file so the campaign multiplicity is not polluted."""
import os, sys, json, importlib.util
V = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(V, "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
T = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_guest_01a"
sys.path.insert(0, T)
import numpy as np, pandas as pd
import concept_lab as cl
from concept_lab.data import utc_ns
import _book as bk

spec = importlib.util.spec_from_file_location("orig", T + "/mechanical-trade-management.py")
orig = importlib.util.module_from_spec(spec); spec.loader.exec_module(orig)

m1 = cl.load_m1()
# ---- A: re-run original detector + test
evA = orig.detect_a(m1)
print("orig frame", len(evA), orig.DIAG, cl.frame_fingerprint(evA))
res_json = json.load(open("/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/results/mechanical-trade-management__a.json"))
print("result events_fp", res_json.get("events_fp"))
rA = cl.trade_test(evA, ctrl_tod_tol_min=30, claim="+")
print("A rerun", {k: rA.get(k) for k in ("n","avg_R_gross","diff","ci_lo","ci_hi","p","verdict")})

# ---- B: independent loop implementation
raw = bk.raw_cisd(m1)
t_ns = utc_ns(pd.DatetimeIndex(m1.index)).astype(np.int64)
O = m1["open"].to_numpy(float); H = m1["high"].to_numpy(float); L = m1["low"].to_numpy(float); C = m1["close"].to_numpy(float)
N = len(t_ns); MIN = 60_000_000_000; HOLD = 150 * MIN
rows = []; paired = []   # paired: (retest_time, fixed_R_orig, BE_R, included_flag)
dec_ns = utc_ns(pd.DatetimeIndex(raw["decision_time"])).astype(np.int64)
for d, s, sp in zip(dec_ns, raw["direction"].to_numpy(), raw["stop_px"].to_numpy(float)):
    i = np.searchsorted(t_ns, d, "left")
    if i >= N: continue
    end = d + HOLD
    j1 = np.searchsorted(t_ns, end, "left")
    if j1 <= i: continue
    e = O[i]; risk = s * (e - sp)
    if not (risk > 0): continue
    tgt = e + s * 2 * risk; one = e + s * risk
    state = 0; t1 = None; fixed = None; be = None
    stage = "pre"; retest = None
    for b in range(i, j1):
        fav = H[b] if s > 0 else L[b]; adv = L[b] if s > 0 else H[b]
        hs = (adv <= sp) if s > 0 else (adv >= sp)
        ht = (fav >= tgt) if s > 0 else (fav <= tgt)
        h1 = (fav >= one) if s > 0 else (fav <= one)
        he = (adv <= e) if s > 0 else (adv >= e)
        if stage == "pre":
            if hs:  # stop first (stop-first ties)
                fixed = -1.0 if ((O[b] > sp) if s > 0 else (O[b] < sp)) else s*(O[b]-e)/risk; break
            if ht: fixed = 2.0; break
            if h1: stage = "tagged"; continue
        elif stage == "tagged":
            if ht and not he: fixed = 2.0; break   # target before any retest
            if he:
                retest = b
                # fixed from here on
                if hs:
                    fx = s*(min(O[b], sp) - e)/risk if s > 0 else s*(max(O[b], sp) - e)/risk
                    paired.append((t_ns[b], fx, 0.0, False)); stage = "done"; break
                if ht:  # entry-touch and target in the same bar: ambiguous; orig skips
                    paired.append((t_ns[b], np.nan, 0.0, False)); stage = "done"; break
                # continue fixed resolution after b
                fixed2 = None
                for b2 in range(b + 1, j1):
                    adv2 = L[b2] if s > 0 else H[b2]; fav2 = H[b2] if s > 0 else L[b2]
                    if (adv2 <= sp) if s > 0 else (adv2 >= sp):
                        fp = min(O[b2], sp) if s > 0 else max(O[b2], sp)
                        fixed2 = s*(fp - e)/risk; break
                    if (fav2 >= tgt) if s > 0 else (fav2 <= tgt):
                        fixed2 = 2.0; break
                if fixed2 is None: fixed2 = s*(C[j1-1]-e)/risk
                paired.append((t_ns[b], fixed2, 0.0, True))
                dt = t_ns[b] + MIN
                rem = end - dt
                if rem > 0:
                    rows.append((dt, s, sp, tgt, rem))
                stage = "done"; break
ev = pd.DataFrame(rows, columns=["t","direction","stop_px","target_px","rem"])
tt = pd.to_datetime(ev.t.to_numpy(), utc=True)
evB = pd.DataFrame({"decision_time": tt, "available_at": tt, "direction": ev.direction.to_numpy(),
                    "stop_px": ev.stop_px.to_numpy(), "target_px": ev.target_px.to_numpy(),
                    "max_hold": pd.to_timedelta(ev.rem.to_numpy(), unit="ns")})
evB = evB.sort_values(["decision_time","direction","stop_px"], ascending=[True,False,True], kind="stable").reset_index(drop=True)
P = pd.DataFrame(paired, columns=["t","fixed","be","incl"])
print("B frame", len(evB), "dropped stop-in-retest", int(((~P.incl) & P.fixed.notna()).sum()), "tgt+entry same bar", int(P.fixed.isna().sum()))
# compare frames
mA = evA.merge(evB, on=["decision_time","direction"], how="outer", indicator=True, suffixes=("_a","_b"))
print(mA["_merge"].value_counts().to_dict())
both = mA[mA._merge=="both"]
print("max stop diff", float(np.nanmax(np.abs(both.stop_px_a-both.stop_px_b))) if len(both) else None)
rB = cl.trade_test(evB, ctrl_tod_tol_min=30, claim="+", keep_trades=True)
print("B test", {k: rB.get(k) for k in ("n","avg_R","avg_R_gross","diff","ci_lo","ci_hi","p","verdict","halves")})
print("ties", rB.get("ties"), "exposure", rB.get("exposure_bars"), "overlap", rB.get("ctrl_overlap"))

# ---- C: the concept's own statistic: fixed - BE (orig R units, gross) on affected trades
def dayboot(x, t, n=2000, seed=0):
    days = pd.to_datetime(t, utc=True).tz_convert("America/New_York")
    codes = pd.factorize((days + pd.Timedelta(hours=6)).date)[0]
    ud = np.unique(codes); rng = np.random.default_rng(seed)
    sums = np.bincount(codes, weights=x); cnts = np.bincount(codes)
    bs = []
    for _ in range(n):
        s = rng.choice(ud, len(ud)); bs.append(sums[s].sum()/cnts[s].sum())
    return x.mean(), np.percentile(bs, [2.5, 97.5])
Pi = P[P.incl]; Pa = P[P.fixed.notna()]
for name, df in (("scored only", Pi), ("incl. dropped stop-in-retest", Pa)):
    x = df.fixed.to_numpy(); m, ci = dayboot(x, df.t.to_numpy())
    h1 = df[pd.to_datetime(df.t, utc=True) < pd.Timestamp("2021-01-01", tz="UTC")].fixed.mean()
    h2 = df[pd.to_datetime(df.t, utc=True) >= pd.Timestamp("2021-01-01", tz="UTC")].fixed.mean()
    print(f"fixed-minus-BE {name}: n={len(x)} mean={m:+.4f} CI [{ci[0]:+.4f},{ci[1]:+.4f}] H1 {h1:+.4f} H2 {h2:+.4f}")
# retest-close location relative to entry in R (for evB)
tr = rB["_trades"]
print(tr.columns.tolist()[:30])
# ---- D: decomposition - where does the harness trade enter relative to the BE exit price?
s = tr["direction"].to_numpy(); r0 = np.abs(tr["target"].to_numpy() - tr["stop"].to_numpy()) / 3.0
e0 = tr["stop"].to_numpy() + s * r0
gap = s * (tr["entry"].to_numpy() - e0) / r0
fixed_orig = s * (tr["exit_px"].to_numpy() - e0) / r0
print(f"harness entry vs original entry (orig R): mean {gap.mean():+.4f}, share below entry {(gap<0).mean():.3f}")
print(f"fixed-minus-BE on the SAME {len(tr)} scored trades in original R: {fixed_orig.mean():+.4f}; harness gross (new R) {tr.gross_R.mean():+.4f}")
