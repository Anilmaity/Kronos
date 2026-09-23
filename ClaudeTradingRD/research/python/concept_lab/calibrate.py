"""Calibration: reproduce published phase-3 figures THROUGH THE NEW HARNESS.

    cd research/python && ../../.venv/bin/python -m concept_lab.calibrate [--fast]

Targets (from `meta/backtest_conjunction.md`, certified span, locked parameters):
  §2 rung 0, 1h stack    n=7,995   win 42.2%  exp -0.021R  diff +0.009 [-0.015, +0.034]
  §2 rung 0, 15min stack n=32,745  win 41.6%  exp -0.044R  diff -0.006 [-0.018, +0.007]
  §2 coordinator 1h      n=13,051  real +0.030 ctrl +0.006 diff +0.024 [+0.000, +0.047]
                         (max_wait=40, 3 control reps, zero cost)

Rung 0 = bare CISD (`detectors.cisd.cisd_events`, series_open, swings 2/2,
max_wait 3, min_series 1) on UTC-aligned bars; entry at the confirming bar's close;
stop at the protected swing; 2R; max hold 10 entry-TF bars; 0.04R cost; M1
resolution with stop-first ties; K=5 controls within +/-30 days.

Two harness configurations are run per target:
  "faithful" — entry_mode="prev_close" (phase 3 entered AT the signal close) and
               controls drawn on the entry-TF bar-close grid (ctrl_grid=tf).
  "default"  — what campaign agents get: entry at the next M1 OPEN, controls on
               the event's minute-of-hour M1 grid ("auto").

TOLERANCES, declared before running:
  n            |n - published| / published <= 1%
  diff         |diff - published| <= 0.010 R   (the control arm is re-drawn with a
               different RNG stream; the published 1h CI half-width is 0.025 R)
  CI width     within 25% of the published width
  CI sign      same "CI contains 0" reading as published, at the published 3-dp
               precision (refined after run 1 — see `check`)
rules-2: the reported CI is now the WIDEST of the phase-3 CI and the dependence-aware
components (trading-day block, clusters). Calibration reproduces PHASE 3, so the
width and sign checks read the phase-3 component (`ci_components["phase3_*"]`);
the final CI is reported beside it (`ci_final`) and must be at least as wide. Calibration
runs are kept out of the campaign run ledger.
Writes research/concept_campaign/calibration.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402

PUBLISHED = {
    "R0_1h": dict(tf="1h", max_wait=3, reps=5, cost="0.04R", n=7995, win=0.422,
                  exp=-0.021, diff=0.009, lo=-0.015, hi=0.034,
                  src="meta/backtest_conjunction.md §2, rung-0 table, 1h row"),
    "R0_15min": dict(tf="15min", max_wait=3, reps=5, cost="0.04R", n=32745, win=0.416,
                     exp=-0.044, diff=-0.006, lo=-0.018, hi=0.007,
                     src="meta/backtest_conjunction.md §2, rung-0 table, 15min row"),
    "coord_1h": dict(tf="1h", max_wait=40, reps=3, cost=0.0, n=13051, win=None,
                     exp=0.030, ctrl=0.006, diff=0.024, lo=0.000, hi=0.047,
                     src="meta/backtest_conjunction.md §2, coordinator reconciliation, 1h"),
}
TOL = {"n_rel": 0.01, "diff_abs": 0.010, "ci_width_rel": 0.25}


def rung0_events(tf: str, max_wait: int) -> pd.DataFrame:
    def build():
        b = cl.bars(tf)[["open", "high", "low", "close"]]
        return cisd_events(b, level_rule="series_open", left=2, right=2,
                           max_wait=max_wait, min_series=1)
    ev = cl.cache_frame(f"calib_cisd_{tf}_mw{max_wait}", build)
    ct = cl.close_time_of(ev["confirm_time"], tf)
    return pd.DataFrame({"decision_time": ct, "available_at": ct,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0})


def _phase3(res: dict) -> tuple[float, float]:
    (k, (lo, hi)), = [(k, v) for k, v in res["ci_components"].items()
                      if k.startswith("phase3")]
    return lo, hi


def check(res: dict, pub: dict) -> dict:
    lo, hi = _phase3(res)
    out = {"n": res["n"], "win": res["win_rate"], "exp_R": res["avg_R"],
           "ctrl_R": res["control"]["avg_R"], "diff": res["diff"],
           "ci": [lo, hi], "ci_final": [res["ci_lo"], res["ci_hi"]],
           "ci_final_method": res["ci_method"], "dependence": res["dependence"],
           "ties": {k: res["ties"].get(k) for k in ("real_ambiguous", "control_ambiguous")},
           "ctrl_overlap": res["ctrl_overlap"], "verdict": res["verdict"],
           "runtime_sec": res["runtime_sec"]}
    n_ok = abs(res["n"] - pub["n"]) / pub["n"] <= TOL["n_rel"]
    d_ok = abs(res["diff"] - pub["diff"]) <= TOL["diff_abs"]
    w_pub = pub["hi"] - pub["lo"]
    w_ok = abs((hi - lo) - w_pub) / w_pub <= TOL["ci_width_rel"]
    # compared at the PUBLISHED precision (3 dp). Refined after the first run:
    # the coordinator row publishes a lower bound of "+0.000", which cannot say
    # whether zero is inside; the unrounded check failed on +0.0001 vs "+0.000".
    lo3, hi3 = round(lo, 3), round(hi, 3)
    pub_null = pub["lo"] <= 0 <= pub["hi"]
    v_ok = (lo3 <= 0 <= hi3) == pub_null
    wider = (res["ci_hi"] - res["ci_lo"]) >= (hi - lo) - 1e-12   # widest-of, by design
    out.update(pass_n=n_ok, pass_diff=d_ok, pass_ci_width=w_ok, pass_ci_sign=v_ok,
               final_at_least_phase3_width=wider,
               PASS=bool(n_ok and d_ok and w_ok and v_ok and wider),
               delta_diff=res["diff"] - pub["diff"])
    return out


def run(names=None) -> dict:
    """Harness self-checks are not campaign readings: the ledger is off for the
    duration of the run only (restored afterwards, even on error)."""
    prev = os.environ.get("CONCEPT_LAB_LEDGER_DISABLE")
    os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = "1"
    try:
        return _run(names)
    finally:
        if prev is None:
            os.environ.pop("CONCEPT_LAB_LEDGER_DISABLE", None)
        else:
            os.environ["CONCEPT_LAB_LEDGER_DISABLE"] = prev


def _run(names=None) -> dict:
    report = {"tolerances": TOL, "published": PUBLISHED, "results": {}}
    for name, pub in PUBLISHED.items():
        if names and name not in names:
            continue
        t0 = time.time()
        ev = rung0_events(pub["tf"], pub["max_wait"])
        hold = pd.Timedelta(pub["tf"]) * 10
        row = {"events": len(ev), "detect_sec": round(time.time() - t0, 1)}
        for cfg, kw in (("faithful", dict(entry_mode="prev_close", ctrl_grid=pub["tf"])),
                        ("default", dict(entry_mode="next_open", ctrl_grid="auto"))):
            r = cl.trade_test(ev, max_hold=hold, reps=pub["reps"], cost=pub["cost"], **kw)
            row[cfg] = check(r, pub)
            lo, hi = _phase3(r)
            print(f"{name:9s} {cfg:8s} n={r['n']:,} exp={r['avg_R']:+.4f} "
                  f"diff={r['diff']:+.4f} phase3 [{lo:+.4f},{hi:+.4f}] "
                  f"pub {pub['diff']:+.3f} [{pub['lo']:+.3f},{pub['hi']:+.3f}] "
                  f"final [{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}] ({r['ci_method']}, "
                  f"{r['verdict']}) -> {'PASS' if row[cfg]['PASS'] else 'FAIL'} "
                  f"({r['runtime_sec']}s)", flush=True)
        report["results"][name] = row
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="1h targets only")
    ap.add_argument("--out", default=str(cl.CAMPAIGN_DIR / "calibration.json"))
    a = ap.parse_args(argv)
    rep = run(["R0_1h", "coord_1h"] if a.fast else None)
    rep["written_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    rep["harness_version"] = cl.HARNESS_VERSION
    rep["rules_version"] = cl.RULES_VERSION
    Path(a.out).write_text(json.dumps(rep, indent=1, default=str))
    ok = all(v["faithful"]["PASS"] for v in rep["results"].values())
    print("calibration (faithful config):", "PASS" if ok else "FAIL", "->", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
