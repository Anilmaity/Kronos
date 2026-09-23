"""Faithfulness / robustness verification of the sons-model EDGE.
Scratch ledger (does not touch the campaign ledger). Never writes results."""
import os, sys, json, importlib.util, types
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["CONCEPT_LAB_LEDGER"] = os.path.join(HERE, "scratch_ledger.jsonl")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np, pandas as pd
import concept_lab as cl

SRC = "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_04a/sons-model.py"


def load_mod(name):
    spec = importlib.util.spec_from_file_location(name, SRC)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


M1 = cl.load_m1()


def summarize(tag, res):
    b = res.get("blocks") or {}
    h = res.get("halves") or {}
    t = res["ties"]
    print(f"{tag:38s} n={res['n']:6d} avgR={res['avg_R']:+.4f} diff={res['diff']:+.4f} "
          f"[{res['ci_lo']:+.4f},{res['ci_hi']:+.4f}] {res['verdict']:12s} "
          f"H1={h.get('H1',{}).get('diff',np.nan):+.3f} H2={h.get('H2',{}).get('diff',np.nan):+.3f} "
          + " ".join(f"{k}={v['diff']:+.3f}" for k, v in b.items())
          + f" ties r/c={t['real_ambiguous']:.3f}/{t['control_ambiguous']:.3f} ovl={res['ctrl_overlap']:.3f}",
          flush=True)


def run_variant(tag, patch=None, tf_draw=None, grid=None, **tt):
    m = load_mod("sons_" + tag.replace(" ", "_").replace("=", "").replace("/", ""))
    for k, v in (patch or {}).items():
        setattr(m, k, v)
    if tf_draw:
        real = cl.build_bars
        def bb(m1, tf, *a, **k):
            if tf == "1h":
                return real(m1, tf_draw, grid4h=grid) if tf_draw == "4h" else real(m1, tf_draw)
            return real(m1, tf, *a, **k)
        m.cl = types.SimpleNamespace(build_bars=bb)
    ev = m.detect(M1)
    res = cl.trade_test(ev, max_hold=m.MAX_HOLD, keep_trades=True, **tt)
    summarize(tag, res)
    return ev, res


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "base"
    out = {}
    if which == "base":
        ev, res = run_variant("base (reproduce)")
        tr = res["_trades"]
        tr["y"] = pd.DatetimeIndex(tr["decision_time"]).year
        tr["d"] = tr["net_R"] - tr["ctrl_mean_R"]
        tr["d5"] = tr["net_R_5050"] - tr["ctrl_mean_R_5050"]
        print("50/50 diff:", round(tr["d5"].mean(), 4), " stop-first diff:", round(tr["d"].mean(), 4))
        print(tr.groupby("y")["d"].agg(["count", "mean"]).round(4).to_string())
        tr["hr"] = cl.to_ny(pd.DatetimeIndex(tr["decision_time"])).hour
        print(tr.groupby("hr")["d"].agg(["count", "mean"]).round(3).T.to_string())
        print(tr.groupby("direction")["d"].agg(["count", "mean"]).round(4).to_string())
        tr["risk_q"] = pd.qcut(tr["risk"] / tr["entry"], 5, labels=False)
        print(tr.groupby("risk_q")["d"].agg(["count", "mean"]).round(4).to_string())
        _, r = run_variant("base tod30", ctrl_tod_tol_min=30)
        _, r = run_variant("base hold=bars", hold_basis="bars")
    elif which == "params":
        TD = pd.Timedelta
        for tag, p in [("fvg15 fill15", dict(FVG_WAIT=TD(minutes=15), FILL_WAIT=TD(minutes=15))),
                       ("fvg60 fill60", dict(FVG_WAIT=TD(minutes=60), FILL_WAIT=TD(minutes=60))),
                       ("raid_lb 24h", dict(LB15=TD(hours=24))),
                       ("raid_lb 6h", dict(LB15=TD(hours=6))),
                       ("draw_lb 24h", dict(LB1H=TD(hours=24))),
                       ("draw_lb 120h", dict(LB1H=TD(hours=120))),
                       ("hold 60min", dict(MAX_HOLD="60min")),
                       ("hold 300min", dict(MAX_HOLD="300min"))]:
            run_variant(tag, p)
    elif which == "draw4h":
        for g in ("forex", "futures"):
            run_variant(f"4H draw grid={g}", tf_draw="4h", grid=g,
                        patch=dict(LB1H=pd.Timedelta(hours=72)))
