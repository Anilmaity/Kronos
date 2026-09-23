import sys, json
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b")
from _common import *  # noqa
import importlib.util
spec = importlib.util.spec_from_file_location("adr", "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01b/average-daily-range.py")
adr = importlib.util.module_from_spec(spec); spec.loader.exec_module(adr)

m1 = cl.load_m1()
ev = cl.cache_frame("verify_adr_gate_15min_lb20_opp1.0_n600", lambda: adr.detect(cl.load_m1()))
print("n", len(ev), "fp", cl.frame_fingerprint(ev) if hasattr(cl, "frame_fingerprint") else "")

def ref_variant(lookback, opp_cut, stat):
    d = cl.build_bars(m1, "1D"); d = d[d["n_m1"] >= 600].copy()
    rng = (d["high"] - d["low"]).to_numpy(float)
    o, c, h, l_ = (d[k].to_numpy(float) for k in ("open", "close", "high", "low"))
    body = np.abs(c - o); opp = np.where(c >= o, o - l_, h - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        is_exp = (body > 0) & (opp / np.where(body > 0, body, np.nan) <= opp_cut)
    exp_r = pd.Series(np.where(is_exp, rng, np.nan)).rolling(lookback, min_periods=1)
    val = {"median": exp_r.median(), "min": exp_r.min(), "max": exp_r.max(), "mean": exp_r.mean(),
           "q25": exp_r.quantile(0.25), "q75": exp_r.quantile(0.75)}[stat].to_numpy()
    n_exp = pd.Series(is_exp.astype(float)).rolling(lookback, min_periods=lookback).sum().to_numpy()
    val = np.where(n_exp >= 3, val, np.nan)
    return pd.DataFrame({"close_time": d["close_time"].to_numpy(), "band": val}, index=d.index)

def run(name, mask, sub=None, **kw):
    e = ev if sub is None else ev[sub].reset_index(drop=True)
    mk = mask if sub is None else mask[sub]
    e = e.copy(); e["g"] = np.asarray(mk, bool)
    r = cl.gate_test(e, "g", mask_available_at="decision_time", max_hold="150min", claim="+", **kw)
    h = r["halves"]; b = r.get("blocks") or {}
    print(f"{name:40s} n={r['n']:6d} gate={r['gate_firing_rate']:.3f} diff={r['diff']:+.4f} [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] "
          f"H1={h['H1']['diff']:+.4f} H2={h['H2']['diff']:+.4f} "
          f"B=" + ",".join(f"{v['diff']:+.3f}" for v in b.values()) +
          f" gatedVsCtrl={r['gated_vs_own_control']['diff']:+.4f} compVsCtrl={r['complement']['vs_own_control']['diff']:+.4f} "
          f"ovl={r['ctrl_overlap']:.3f} {r['verdict']}", flush=True)
    return r

base = ev["open_exp"].to_numpy()
run("repro reading b", base)
run("reading b + ctrl_tod_tol_min=30", base, ctrl_tod_tol_min=30)
run("reading b + hold_basis=bars", base, hold_basis="bars")

# continuation vs reversal (concept: stop seeking CONTINUATIONS once band covered)
op = cl.open_at(ev["decision_time"], "18:00", m1=m1)
dopen = op["price"].to_numpy(float)
run_ = cl.running_hilo(ev["decision_time"], "1D", m1=m1)
# price at decision approx: use day move sign via midpoint of running range vs open is ambiguous; use last M1 close before decision
tn, o_, h_, l_, c_ = m1_arrays(m1)
pos = np.searchsorted(tn, cl.data.utc_ns(pd.DatetimeIndex(ev["decision_time"])), side="left") - 1
px = c_[pos]
daydir = np.sign(px - dopen)
cont = (ev["direction"].to_numpy() == daydir)
print("cont share", np.nanmean(cont), "cont share in complement", cont[~base].mean())
run("cont-direction entries only", base, sub=cont)
run("reversal-direction entries only", base, sub=~cont)

# band robustness
for lb in (10, 20, 30):
    for oc in (0.5, 1.0):
        for stat in ("median", "min", "q25", "mean", "q75", "max"):
            if lb != 20 and oc != 1.0: continue
            rf = asof_ref(ref_variant(lb, oc, stat), ev["decision_time"])
            band = rf["band"].to_numpy(float)
            ok = np.isfinite(band)
            g = ev["day_covered"].to_numpy() < np.where(ok, band, np.inf)
            run(f"lb{lb} opp{oc} {stat}", g)
