"""Direct check: reported SE vs a setup-cluster bootstrap SE on the same book."""
from common import *
L, K = 60, 1500
ny_ok = np.flatnonzero((NY.minute.to_numpy() == 0))
def boot_cluster(vals, cl_id, B=1000, seed=1):
    u, inv = np.unique(cl_id, return_inverse=True)
    s = np.bincount(inv, weights=vals); c = np.bincount(inv)
    rng = np.random.default_rng(seed); out = []
    for _ in range(B):
        k = rng.integers(0, len(u), len(u)); out.append(s[k].sum() / c[k].sum())
    return np.std(out)
for sd in range(3):
    rng = np.random.default_rng(3000 + sd)
    starts = np.sort(rng.choice(ny_ok, K, replace=False))
    pos = (starts[:, None] + np.arange(L)[None, :]).ravel(); own = np.repeat(np.arange(K), L)
    keep = np.r_[True, np.diff(pos) > 0] & (pos < len(TN)); pos, own = pos[keep], own[keep]
    dirs = rng.choice([-1, 1], K)[own]; gate = (rng.random(K) < 0.4)[own]
    ev = events_from_pos(pos, dirs, 3.0, 2.0); ev["own"] = own; ev["g"] = gate
    r = cl.trade_test(ev, max_hold="2h", n_boot=1000, blocks=False, keep_trades=True)
    tr = r["_trades"]; o = ev["own"].to_numpy()[tr.ev_id]; g = ev["g"].to_numpy()[tr.ev_id]
    d = (tr.net_R - tr.ctrl_mean_R).to_numpy(); ok = np.isfinite(d)
    se_cl = boot_cluster(d[ok], o[ok])
    print(f"trade_test book {sd}: n={r['n']} setups={K}  reported SE {(r['ci_hi']-r['ci_lo'])/3.92:.4f} ({r['ci_method']})  setup-cluster SE {se_cl:.4f}  ratio {se_cl/((r['ci_hi']-r['ci_lo'])/3.92):.2f}")
    rg = cl.gate_test(ev, gate, mask_available_at=ev["decision_time"], max_hold="2h", n_boot=1000, blocks=False)
    # cluster bootstrap of gated-minus-complement
    u = np.unique(o[ok]); rngb = np.random.default_rng(2); bs = []
    dd, oo, gg = d[ok], o[ok], g[ok]
    ss = pd.DataFrame({"o": oo, "g": gg, "d": dd}).groupby("o").agg(s=("d", "sum"), c=("d", "size"), g=("g", "first"))
    S, C, G = ss.s.to_numpy(), ss.c.to_numpy(), ss.g.to_numpy()
    for _ in range(1000):
        k = rngb.integers(0, len(S), len(S))
        bs.append(S[k][G[k]].sum() / C[k][G[k]].sum() - S[k][~G[k]].sum() / C[k][~G[k]].sum())
    print(f"   gate_test: diff {rg['diff']:+.4f} reported SE {(rg['ci_hi']-rg['ci_lo'])/3.92:.4f} ({rg['ci_method']})  setup-cluster SE {np.std(bs):.4f}  ratio {np.std(bs)/((rg['ci_hi']-rg['ci_lo'])/3.92):.2f}  verdict {rg['verdict']}")
