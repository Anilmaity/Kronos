"""Faithfulness check of propulsion-block reading b (scratch; does not write results)."""
import sys, importlib.util, time
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl
from concept_lab.engine import get_market, resolve_trades
spec = importlib.util.spec_from_file_location("pb", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_03a/propulsion-block.py")
pb = importlib.util.module_from_spec(spec); spec.loader.exec_module(pb)

m1 = cl.load_m1(); mkt = get_market(m1)

def raw_touches(m1, kind, tf="15min", fill_bars=150):
    """same detector, but keep EVERY first touch (no 'touch-bar close above stop' filter)."""
    b = cl.build_bars(m1, tf)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = b["close_time"].to_numpy()
    mt = cl.data.utc_ns(m1.index)
    ml, mh, mc = m1["low"].to_numpy(float), m1["high"].to_numpy(float), m1["close"].to_numpy(float)
    rows = []
    for d, arrs in ((1, (o, h, l, c)), (-1, (-o, -l, -h, -c))):
        for j2, opx, lowpx, bodyb in pb._bull_blocks(*arrs):
            stop = lowpx if kind == "low" else bodyb
            if not stop < opx: continue
            t_close = cl.data.utc_ns(pd.DatetimeIndex([ct[j2]]))[0]
            i0 = int(np.searchsorted(mt, t_close, side="left")); i1 = min(len(mt), i0 + fill_bars)
            if i0 >= i1: continue
            seg = ml[i0:i1] if d > 0 else -mh[i0:i1]
            hit = np.flatnonzero(seg <= opx)
            if not len(hit): continue
            k = i0 + int(hit[0])
            ck = mc[k] if d > 0 else -mc[k]
            rows.append((k, d, d * stop, d * opx, ck > stop, j2))
    return pd.DataFrame(rows, columns=["k", "d", "stop", "opx", "passes", "j2"])

def limit_book(r):
    """Faithful limit fill at opx on bar k (or at k's open if it gapped through opx)."""
    k = r.k.to_numpy(); d = r.d.to_numpy(); stop = r.stop.to_numpy(); opx = r.opx.to_numpy()
    long = d > 0
    fill = np.where(long, np.minimum(opx, mkt.o[k]), np.maximum(opx, mkt.o[k]))
    risk = d * (fill - stop)
    ok = risk > 0
    tgt = fill + d * 2 * risk
    # stop inside the fill bar: scored as a stop (can't order intrabar; conservative) 
    stop_in_k = np.where(long, mkt.l[k] <= stop, mkt.h[k] >= stop)
    t_end = mkt.tn[k] + np.int64(150 * 60e9)
    i1 = np.searchsorted(mkt.tn, t_end, side="left")
    i0 = k + 1
    good = ok & (i1 > i0)
    res = resolve_trades(mkt, long[good], stop[good], tgt[good], i0[good], i1[good])
    g = np.full(len(k), np.nan)
    gr = d[good] * (res["exit_px"] - fill[good]) / risk[good]
    g[good] = gr
    g = np.where(stop_in_k & ok, -1.0, g)
    return pd.DataFrame({"k": k, "d": d, "fill": fill, "stop": stop, "risk": risk, "gross": g,
                         "passes": r.passes.to_numpy(), "stop_in_k": stop_in_k, "ok": good | (stop_in_k & ok)})

def ctrl_for(book):
    """matched control via trade_test: decision at bar k START, same stop_dist and rr=2."""
    b = book[book.ok].copy()
    dt = cl.data.from_ns(mkt.tn[b.k.to_numpy()])
    ev = pd.DataFrame({"decision_time": dt, "available_at": dt, "direction": b.d.to_numpy(),
                       "stop_dist": b.risk.to_numpy(), "rr": 2.0})
    ev["_row"] = np.arange(len(ev))
    ev = ev.drop_duplicates(["decision_time", "direction"]).reset_index(drop=True)
    res = cl.trade_test(ev[["decision_time","available_at","direction","stop_dist","rr"]], max_hold="150min", keep_trades=True, n_boot=500)
    tr = res["_trades"]
    b = b.iloc[ev["_row"].to_numpy()].reset_index(drop=True)
    return b, tr, res

def boot_diff(t, x, seed=1, n=2000):
    days = pd.DatetimeIndex(t).tz_convert("America/New_York").normalize()
    codes = pd.factorize(days)[0]; nd = codes.max() + 1
    s = np.bincount(codes, weights=x, minlength=nd); c = np.bincount(codes, minlength=nd)
    rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        idx = rng.integers(0, nd, nd)
        out.append(s[idx].sum() / c[idx].sum())
    return x.mean(), np.percentile(out, [2.5, 97.5])

if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "body"
    t0 = time.time()
    raw = raw_touches(m1, kind)
    print(kind, "raw touches", len(raw), "pass close>stop filter", raw.passes.mean().round(3), f"{time.time()-t0:.0f}s")
    book = limit_book(raw)
    b, tr, res = ctrl_for(book)
    print("harness real arm (enter bar-k OPEN, lookahead, just for ref):", round(res["diff"],4), res["verdict"])
    cm = tr["ctrl_mean_R"].to_numpy(); cm_g = cm + 0.04
    # tr rows are in decision_time order; align b by k order
    b = b.sort_values("k").reset_index(drop=True)
    assert len(b) == len(tr)
    x = b.gross.to_numpy() - cm_g
    t = cl.data.from_ns(mkt.tn[b.k.to_numpy()])
    m = np.isfinite(x)
    d, ci = boot_diff(t[m], x[m])
    print(f"FAITHFUL LIMIT (all touches) n={m.sum()} avgR_gross={b.gross[m].mean():.4f} ctrl_gross={cm_g[m].mean():.4f} diff={d:+.4f} CI {ci.round(4)}")
    for lab, sel in (("passes filter", b.passes.to_numpy()), ("fails filter", ~b.passes.to_numpy())):
        mm = m & sel
        d, ci = boot_diff(t[mm], x[mm]); print(f"  {lab}: n={mm.sum()} diff={d:+.4f} CI {ci.round(4)} gross={b.gross[mm].mean():.3f}")
    yr = pd.DatetimeIndex(t).year
    print(pd.Series(x[m]).groupby(yr[m]).agg(["mean","count"]).round(3).T)
    b.assign(ctrl_g=cm_g, t=t).to_pickle(f"/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/verify/propulsion-block__faithfulness/limit_{kind}.pkl")
