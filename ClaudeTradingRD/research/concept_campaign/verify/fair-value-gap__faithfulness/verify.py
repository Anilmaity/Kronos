"""Faithfulness/robustness verification of fair-value-gap reading b (scratch; ledger redirected)."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02b")
import importlib.util
spec = importlib.util.spec_from_file_location("fvg", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02b/fair-value-gap.py")
fvg = importlib.util.module_from_spec(spec); spec.loader.exec_module(fvg)
from _common import cl, np, pd, fvg_arrays

m1 = cl.load_m1(); mkt = cl.get_market()
H = 1440
rng = np.random.default_rng(12345)

def fill(times, level, below):
    out = np.full(len(times), np.nan)
    for side, s in (("below", below), ("above", ~below)):
        if s.any():
            out[s] = cl.touch(times[s], level[s], side, horizon_bars=HB)["hit"].to_numpy()
    return out

def dayboot(d, times, nb=2000):
    """paired diff per event; stationary-ish bootstrap over trading days (iid days)."""
    day = pd.DatetimeIndex(times).tz_convert("America/New_York").floor("D") if False else None
    td = cl.trading_day(times) if hasattr(cl, "trading_day") else pd.DatetimeIndex(times).floor("D")
    df = pd.DataFrame({"d": d, "g": np.asarray(td)}).dropna()
    s = df.groupby("g")["d"].agg(["sum", "count"])
    S, C = s["sum"].to_numpy(), s["count"].to_numpy()
    idx = rng.integers(0, len(S), (nb, len(S)))
    bs = S[idx].sum(1) / C[idx].sum(1)
    m = S.sum() / C.sum()
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(n=int(C.sum()), diff=round(float(m), 5), lo=round(float(lo), 5), hi=round(float(hi), 5))

def run(tf=fvg.TF, hb=1440, merge=False, label=""):
    global HB; HB = hb
    b = cl.build_bars(m1, tf)
    h, l = b.high.to_numpy(float), b.low.to_numpy(float)
    bull, bear, glo, ghi = fvg_arrays(h, l)
    sel = bull | bear
    idx = np.flatnonzero(sel)
    up_all = bull
    far_all = np.where(bull, glo, ghi)
    if merge:   # stacked consecutive same-direction gaps -> one gap; far edge = first gap's far edge; decide at last
        keep, far_m = [], []
        k = 0
        while k < len(idx):
            j = k
            while j + 1 < len(idx) and idx[j+1] == idx[j] + 1 and up_all[idx[j+1]] == up_all[idx[k]]:
                j += 1
            fe = np.min(far_all[idx[k:j+1]]) if up_all[idx[k]] else np.max(far_all[idx[k:j+1]])
            keep.append(idx[j]); far_m.append(fe); k = j + 1
        idx = np.array(keep); far = np.array(far_m)
    else:
        far = far_all[idx]
    up = up_all[idx]
    t = pd.DatetimeIndex(b.close_time.to_numpy()[idx])
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    dist = np.abs(px - far)
    obs = fill(t, far, up)
    # original null (+-30d random moments, same dist, same side)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)
    nul = []
    for k in range(5):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC"); ok = ~tk.isna()
        o = np.full(len(t), np.nan); pk = mkt.o[mkt.pos_at_or_after(tk[ok])]
        o[ok] = fill(tk[ok], np.where(up[ok], pk - dist[ok], pk + dist[ok]), up[ok]); nul.append(o)
    nul = np.nanmean(np.vstack(nul), 0)
    # same-moment opposite side (local vol matched exactly)
    opp = fill(t, np.where(up, px + dist, px - dist), ~up)
    out = {"label": label, "tf": tf, "hb": hb, "merge": merge, "n": len(t),
           "obs": round(float(np.nanmean(obs)), 4), "null": round(float(np.nanmean(nul)), 4),
           "opp_same_moment": round(float(np.nanmean(opp)), 4),
           "vs_null": dayboot(obs - nul, t), "vs_opp": dayboot(obs - opp, t)}
    # range+direction matched non-FVG triplets within +-30d (trailing 3-bar range, same net direction)
    c = b.close.to_numpy(float); o_ = b.open.to_numpy(float)
    rng3 = pd.Series(h).rolling(3).max().to_numpy() - pd.Series(l).rolling(3).min().to_numpy()
    net = c - np.r_[np.nan, np.nan, o_[:-2]]
    ct = b.close_time.to_numpy()
    cand = np.flatnonzero(~sel & np.isfinite(rng3) & np.isfinite(net))
    ctn = ct.astype("datetime64[ns]").astype(np.int64); W = 30 * 86400 * 10**9
    ctrl_t, ctrl_ok = [], []
    for ii, i in enumerate(idx):
        lo_, hi_ = np.searchsorted(ctn[cand], [ctn[i] - W, ctn[i] + W])
        cc = cand[lo_:hi_]
        cc = cc[np.sign(net[cc]) == (1 if up[ii] else -1)]
        if len(cc) < 5:
            ctrl_t.append([ct[i]] * 5); ctrl_ok.append(False); continue
        best = cc[np.argsort(np.abs(np.log(rng3[cc] / rng3[i])))[:5]]
        ctrl_t.append(list(ct[best])); ctrl_ok.append(True)
    ctrl_t = np.array(ctrl_t); ctrl_ok = np.array(ctrl_ok)
    vm = []
    for k in range(5):
        tk = pd.DatetimeIndex(ctrl_t[:, k])
        tk = tk.tz_localize("UTC") if tk.tz is None else tk
        pk = mkt.o[np.minimum(mkt.pos_at_or_after(tk), len(mkt.o) - 1)]
        vm.append(fill(tk, np.where(up, pk - dist, pk + dist), up))
    vm = np.nanmean(np.vstack(vm), 0); vm[~ctrl_ok] = np.nan
    out["rangedir_matched_nonfvg"] = round(float(np.nanmean(vm)), 4)
    out["vs_rangedir"] = dayboot(obs - vm, t)
    # calendar blocks vs original null
    yrs = t.year
    out["by_block_vs_null"] = {str(a): dayboot((obs - nul)[(yrs >= a) & (yrs < a + 3)], t[(yrs >= a) & (yrs < a + 3)], 500)["diff"] for a in (2016, 2019, 2022, 2025)}
    out["by_block_vs_rangedir"] = {str(a): dayboot((obs - vm)[(yrs >= a) & (yrs < a + 3)], t[(yrs >= a) & (yrs < a + 3)], 500)["diff"] for a in (2016, 2019, 2022, 2025)}
    print(json.dumps(out), flush=True)
    return out

res = [run(label="as_tested"),
       run(merge=True, label="merge_rule"),
       run(hb=720, label="h720"), run(hb=2880, label="h2880"),
       run(tf="15min", label="15m"), run(tf="4h", label="4h")]
json.dump(res, open(os.path.join(HERE, "verify_out.json"), "w"), indent=1)
