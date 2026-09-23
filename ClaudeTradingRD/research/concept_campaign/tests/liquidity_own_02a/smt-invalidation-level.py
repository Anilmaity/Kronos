"""smt-invalidation-level — is the diverging asset's held low/high a real invalidation?

Claim (eHQ4nE-TQ2w): the level the diverging asset held is where the SMT dies — "if these
lows or highs are broken or taken the divergence is invalidated" — so it is the stop. If
the level carries information it must HOLD more often than an arbitrary level at the same
distance: measurable "stop-out rate of SMT-invalidation stops".

rate_test. Events: hourly gold/XAG SMTs where silver swept and GOLD held (gold is the
diverging asset whose level is the stop). Outcome: gold trades through its held level
(bullish: any M1 low <= held low; bearish: any M1 high >= held high) within the next 600
trading minutes (10 x 1h, the phase-3 hold). Null: the same distance from the first M1
open at matched random moments (+/-30d, locked reps/seed), same side, same bar horizon.
claim '-': the invalidation level is taken LESS often than a same-distance level.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c                        # noqa: E402
import concept_lab as cl                   # noqa: E402

CID = "smt-invalidation-level"
HORIZON_BARS = 600          # phase3: 10 x 1h hold, in trading minutes


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    f = c.smt_frame(m1)
    cols = ["decision_time", "available_at", "direction", "level"]
    if f.empty:
        return pd.DataFrame(columns=cols)
    f = f[f["held_by"] == "gold"]
    f = f.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return pd.DataFrame({"decision_time": f["decision_time"].to_numpy(),
                         "available_at": f["decision_time"].to_numpy(),
                         "direction": f["direction"].to_numpy(int),
                         "level": f["invalidation"].to_numpy(float)}).reset_index(drop=True)


def main():
    ev = cl.cache_frame(f"{CID}_goldheld", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    px0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    d = ev["direction"].to_numpy(int)
    lvl = ev["level"].to_numpy(float)
    # distance from the first tradable price to the level, measured toward the stop side
    dist = (px0 - lvl) * d        # geometry to preserve (can be <= 0 on a gap; the
                                  # null then gets the same immediate touch)
    probe_note = (f"{int((dist <= 0).sum())} events whose first M1 open was already through "
                  "the level are kept; their nulls carry the same negative distance")

    def hit(times, level, dirs):
        out = np.zeros(len(times), bool)
        for s, side in ((1, "below"), (-1, "above")):
            m = dirs == s
            if m.any():
                out[m] = cl.touch(times[m], level[m], side,
                                  horizon_bars=HORIZON_BARS)["hit"].to_numpy()
        return out

    obs = hit(t, lvl, d)
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

    def null_fn(rng, k):
        tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        p = mkt.o[mkt.pos_at_or_after(tk[ok])]
        out[ok] = hit(tk[ok], p - d[ok] * dist[ok], d[ok])
        return out

    res = cl.rate_test(obs, t, available_at=t, null_fn=null_fn, claim="-", predictors=ev)
    print(res["n"], res["observed_rate"], res["null_rate"], res["diff"], res["ci_lo"],
          res["ci_hi"], res["verdict"], res["verdict_detail"])
    op = {"rules": ["hourly gold/XAG SMT (detectors.bias.smt_events, 2/2 swings, 20-bar "
                    "lookback); keep silver-swept / gold-held SMTs",
                    "level = gold's held low (bullish) / high (bearish), known at the "
                    "divergence bar's close",
                    "hit = gold trades through the level within 600 M1 bars after the close",
                    "null = same distance from the first M1 open at matched random moments "
                    "(+/-30d, 5 reps), same side, same 600-bar horizon"],
          "params": {"tf": "1h", "correlate": "XAG_USD H1", "smt_lookback": 20,
                     "swing": "2/2", "horizon_bars": HORIZON_BARS}}
    src = {"tf": "declared-before-run: SMT is fractal; silver held only at H1",
           "correlate": "corpus: silver allowed as gold's correlate; phase3 load_correlate",
           "smt_lookback": "phase3: detectors.bias.smt_events default",
           "swing": "phase3: 2/2 swings (§1.8)",
           "horizon_bars": "phase3: 10 entry-TF bars hold (§1.13), as trading minutes"}
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe, notes=probe_note))


if __name__ == "__main__":
    main()
