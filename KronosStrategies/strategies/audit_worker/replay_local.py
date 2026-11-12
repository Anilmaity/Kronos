"""Run a /strategy-data backtest replay off the box and print the result JSON.

The production backtest_worker is capped at half a core (a 62-day replay takes
~2 h there); the same replay on a dev machine takes minutes. Push the output
onto a ManagerBacktestRun row labelled "strategy:<userStrategyId>".

    OANDA_API_KEY=... python -m audit_worker.replay_local "S101 Asia Range Fade" \
        2026-09-11 2026-11-12 cache_dir > trades.json

Skips the worker's S5 ambiguity resolver: same-bar SL/TP ties keep the
engine's M1 verdict.
"""
import json
import sys
from pathlib import Path

import pandas as pd

from audit_worker import bars, results, roster
from backtest.manager_sim_engine import SimConfig, load_frames, run_sim


def main(name, start, end, cache):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    s, e = (pd.Timestamp(d).tz_localize("UTC") for d in (start, end))
    bars.ensure_frames(cache, s, e)
    specs, notes = roster.build_specs(
        [{"name": name, "policy_key": "always_on", "policy_params": {}}])
    assert specs, notes
    # same knobs as the RunStrategyBacktest mutation
    cfg = SimConfig(start=s.to_pydatetime(), end=e.to_pydatetime(), spread_pts=0.30,
                    slippage_pts=0.10, lots=0.01, kill_switch_usd=1e9,
                    max_concurrent=10, regime_cadence_min=5, gated=True)
    sim = run_sim(load_frames(cache, s, e), cfg, specs=specs,
                  progress_cb=lambda f: print(f"{f:.0%}", file=sys.stderr))
    json.dump({"trades": results.trades_frame(sim.trades).to_dict("records")},
              sys.stdout)


if __name__ == "__main__":
    main(*sys.argv[1:5])
