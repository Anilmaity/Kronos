"""Faithfulness/robustness check for intraday-reversal (scratch; ledger disabled, no write_result)."""
import os, sys
os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_04b")
import numpy as np, pandas as pd
import concept_lab as cl
from _helpers import c2_flags, cisd_in_candle, day_end_bars, matched_touch_null

m1 = cl.load_m1(); mkt = cl.get_market()
BLOCKS = [("B1","2016-01-01","2018-08-22 11:01"),("B2","2018-08-22 11:01","2021-04-12 08:43"),
          ("B3","2021-04-12 08:43","2023-12-02 06:25"),("B4","2023-12-02 06:25","2027-01-01")]

def detect(grid="forex", need_c2=True, need_cisd=True, need_dayext=True):
    b4 = cl.build_bars(m1, "4h", grid4h=grid); b1 = cl.build_bars(m1, "1h")
    o4, h4, l4, c4 = (b4[k].to_numpy(float) for k in ("open","high","low","close"))
    o1, h1, l1, c1 = (b1[k].to_numpy(float) for k in ("open","high","low","close"))
    ct4 = pd.DatetimeIndex(b4["close_time"]); st4 = pd.DatetimeIndex(b4.index); i1 = pd.DatetimeIndex(b1.index)
    td4 = cl.trading_day(pd.DatetimeIndex(b4["first_m1"])).to_numpy()
    c2 = c2_flags(o4, h4, l4, c4)
    a = i1.searchsorted(st4); b = i1.searchsorted(ct4)
    skip_h = 17 if grid == "forex" else 18
    nyh = ct4.tz_convert("America/New_York").hour
    rows = []
    for i in range(1, len(b4)):
        if nyh[i] == skip_h: continue
        cands = [c2[i] > 0] if (need_c2 and c2[i] != 0) else ([] if need_c2 else [True, False])
        same = np.flatnonzero(td4[:i+1] == td4[i])
        for bull in cands:
            if need_dayext:
                if bull and l4[i] > l4[same].min(): continue
                if (not bull) and h4[i] < h4[same].max(): continue
            if need_cisd:
                j, e = cisd_in_candle(o1, h1, l1, c1, a[i], b[i], bull)
                if j < 0: continue
            rows.append((ct4[i], 1 if bull else -1, l4[i] if bull else h4[i]))
    ev = pd.DataFrame(rows, columns=["decision_time","direction","level"])
    return ev[ev.decision_time < m1.index[-1] - pd.Timedelta(hours=1)].reset_index(drop=True)

def score(ev, label, extra=True):
    t = pd.DatetimeIndex(ev["decision_time"]); hb = day_end_bars(m1.index, t)
    keep = hb > 0; ev = ev[keep].reset_index(drop=True); t = t[keep]; hb = hb[keep]
    px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o)-1)]
    lvl = ev["level"].to_numpy(); side = np.where(ev["direction"].to_numpy() > 0, "below", "above")
    obs = np.zeros(len(ev), bool)
    for sd in ("above","below"):
        m = side == sd
        obs[m] = ~cl.touch(t[m], lvl[m], sd, horizon_bars=hb[m])["hit"].to_numpy()
    nf = matched_touch_null(t, lvl - px, side, hb, tod_tol_min=30, invert=True)
    res = cl.rate_test(obs.astype(float), t, available_at=t, null_fn=nf)
    print(f"{label:38s} n={res['n']:5d} obs={res['observed_rate']:.3f} null={res['null_rate']:.3f} "
          f"diff={res['diff']:+.4f} [{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] H1={res['halves']['H1']['diff']:+.3f} "
          f"H2={res['halves']['H2']['diff']:+.3f} {res['verdict']}", flush=True)
    if extra:
        print("   blocks:", {k: round(v['diff'], 4) for k, v in res['blocks'].items()})
        # per-year and per-close-hour diff using the null mean over 5 reps
        rng = np.random.default_rng(0)
        nulls = np.nanmean(np.vstack([nf(rng, k) for k in range(5)]), 0)
        df = pd.DataFrame({"obs": obs.astype(float), "null": nulls, "yr": t.year,
                           "h": t.tz_convert("America/New_York").hour, "dir": ev["direction"].to_numpy()})
        df["d"] = df.obs - df.null
        print("   by year:", df.groupby("yr")["d"].agg(["mean","count"]).round(3).T.to_dict())
        print("   by NY close hour:", df.groupby("h")["d"].agg(["mean","count"]).round(3).T.to_dict())
        print("   by dir:", df.groupby("dir")["d"].agg(["mean","count"]).round(3).T.to_dict())
    return res

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    score(detect("forex", need_c2=False, need_cisd=False), "forex dayext only", extra=False)
    score(detect("forex", need_dayext=False), "forex C2+CISD (no dayext)", extra=False)
    score(detect("futures", need_c2=False, need_cisd=False), "futures dayext only", extra=False)
