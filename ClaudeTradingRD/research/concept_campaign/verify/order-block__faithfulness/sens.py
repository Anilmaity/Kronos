"""Faithfulness/robustness sweep for order-block reading b. Ledger redirected (not campaign)."""
import os, sys, importlib.util, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "ledger_scratch.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_02b")
from _common import cl, np, pd, empty, cisd_frame, bar_arrays, M1, first_touch, ONE_MIN

LEVEL_RULE = {"a": "series_extreme", "b": "series_open"}

def build(m1, reading="b", wait_h=24, lvl="open", disp=False):
    b = cl.build_bars(m1, "1h"); d = bar_arrays(b)
    ev = cisd_frame(b, level_rule=LEVEL_RULE[reading])
    sh_idx, sl_idx = np.flatnonzero(d["sh"]), np.flatnonzero(d["sl"])
    m = M1(m1); ct = d["ct"]
    # ATR(20) of 1h for displacement
    h, l, c, o = d["h"], d["l"], d["c"], d["o"]
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h-l, np.abs(h-pc), np.abs(l-pc)]), axis=0)
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy()
    rows = []
    for r in ev.itertuples(index=False):
        x, s, e, cp = int(r.ext_pos), int(r.s_pos), int(r.e_pos), int(r.conf_pos)
        up = r.sgn == 1
        piv = sl_idx if up else sh_idx
        prior = piv[piv + 2 <= x - 1]
        if not len(prior): continue
        p = prior[-1]
        if not ((l[x] < l[p]) if up else (h[x] > h[p])): continue
        if lvl == "open":
            level = o[s]
        else:  # mean threshold of run bodies
            bl = np.minimum(o[s:e+1], c[s:e+1]).min(); bh = np.maximum(o[s:e+1], c[s:e+1]).max()
            level = 0.5 * (bl + bh)
        ext = float(r.protected_swing)
        if not ((ext < level) if up else (ext > level)): continue
        if disp:
            body = abs(c[cp] - o[cp])
            if not (np.isfinite(atr[cp]) and body >= atr[cp]): continue
        t0, t1 = ct[cp], ct[min(cp + wait_h, len(ct) - 1)]
        if t1 <= t0: continue
        j = first_touch(m, t0, t1, level, up, cancel=ext)
        if j < 0: continue
        if (m.l[j] <= ext) if up else (m.h[j] >= ext): continue
        rows.append((m.t[j] + ONE_MIN, 1 if up else -1, ext, int(b.index[x].value)))
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "xt"])
    t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": 2.0,
                         "ext_start": pd.to_datetime(out["xt"].to_numpy(np.int64), utc=True)}
                        ).sort_values(["decision_time", "direction"], kind="stable").reset_index(drop=True)

def summ(tag, res):
    bl = {k: round(v["diff"], 3) for k, v in (res.get("blocks") or {}).items()}
    hv = {k: round(res["halves"][k]["diff"], 3) for k in ("H1", "H2")}
    print(json.dumps({"tag": tag, "n": res["n"], "diff": round(res["diff"], 4), "ci": [round(res["ci_lo"], 4), round(res["ci_hi"], 4)],
          "p": round(res["p"], 4), "verdict": res["verdict"], "halves": hv, "blocks": bl,
          "ties": res["ties"].get("verdict_stop_first"), "ties_alt": {k: v for k, v in res["ties"].items() if "coin" in k or "5050" in k},
          "ovl": round(res["ctrl_overlap"], 4), "exp": res["exposure_bars"]}), flush=True)

if __name__ == "__main__":
    m1 = cl.load_m1()
    COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    base = build(m1)
    print("base n", len(base))
    r = cl.trade_test(base[COLS], max_hold="10h", keep_trades=True); summ("base", r)
    tr = r["_trades"]; tr.to_parquet(os.path.join(HERE, "base_trades.parquet"))
    summ("tod30", cl.trade_test(base[COLS], max_hold="10h", ctrl_tod_tol_min=30))
    summ("bars", cl.trade_test(base[COLS], max_hold="10h", hold_basis="bars"))
    for hold in ("5h", "20h"):
        summ(f"hold{hold}", cl.trade_test(base[COLS], max_hold=hold))
    for rr in (1.0, 1.5, 3.0):
        summ(f"rr{rr}", cl.trade_test(base[COLS].assign(rr=rr), max_hold="10h"))
    # important level: extreme bar swept prior-day H/L, or prior 4h H/L (both grids)
    xt = pd.DatetimeIndex(base["ext_start"])
    dirn = base["direction"].to_numpy()
    xh = cl.build_bars(m1, "1h")
    hx = xh["high"].reindex(xt).to_numpy(); lx = xh["low"].reindex(xt).to_numpy()
    def swept(ph):
        return np.where(dirn == -1, hx >= ph["high"].to_numpy(), lx <= ph["low"].to_numpy())
    pd1 = cl.prior_hilo(xt, "1D")
    m_pd = swept(pd1)
    m_4f = swept(cl.prior_hilo(xt, "4h", grid4h="forex"))
    m_4u = swept(cl.prior_hilo(xt, "4h", grid4h="futures"))
    for tag, mk in (("PDHL_swept", m_pd), ("P4H_fx", m_4f), ("P4H_fut", m_4u), ("PDHL_or_P4Hfx", m_pd | m_4f),
                    ("no_important_level_fx", ~(m_pd | m_4f))):
        e = base.loc[mk, COLS].reset_index(drop=True)
        print(tag, "n", len(e))
        if len(e) > 50: summ(tag, cl.trade_test(e, max_hold="10h"))
    for kw in (dict(wait_h=12), dict(wait_h=48), dict(disp=True), dict(lvl="mt")):
        e = build(m1, **kw)[COLS]
        summ(str(kw), cl.trade_test(e, max_hold="10h"))
