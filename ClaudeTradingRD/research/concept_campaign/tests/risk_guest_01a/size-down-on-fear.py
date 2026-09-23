"""size-down-on-fear (guest: Trader Kane) - two gate_tests on the sequential baseline book.

"Would a single loss tilt you" is subjective and has no chart test; the concept's two
OBJECTIVE triggers for reducing size are tested. A size reduction on a subset of trades
helps only if that subset has lower expectancy per R than the rest, so each trigger is a
gate with claim '-' (the down-sized trades are WORSE, control-adjusted):

 (a) after an extended winning run ("reduce after an extended winning run rather than
     after the losses arrive"; he expected a losing streak to be due). Gate
     `after_win_run` = the last 3 taken trades were all winners.
 (b) after realised volatility has risen materially. Gate `vol_up` = mean true range of
     the last 96 closed 15m bars (~1 trading day) >= 1.5 x the mean true range of the
     last 1,920 closed 15m bars (~20 trading days). Rows inside the 20-day warm-up
     (ratio undefined) are dropped, never defaulted.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import concept_lab as cl   # noqa: E402
import _book as bk         # noqa: E402

CID = "size-down-on-fear"
RUN_N = 3
VOL_SHORT, VOL_LONG, VOL_MULT = 96, 1920, 1.5
TOD_TOL = 30


def detect_a(m1):
    ev = bk.chain(m1)
    ev["after_win_run"] = ev["consec_wins_before"] >= RUN_N
    return bk.public(ev, ["consec_wins_before", "after_win_run"])


def detect_b(m1):
    ev = bk.chain(m1)
    b = cl.build_bars(m1, bk.TF)
    pc = b["close"].shift(1)
    tr = np.maximum(b["high"], pc.fillna(b["high"])) - np.minimum(b["low"], pc.fillna(b["low"]))
    ratio = (tr.rolling(VOL_SHORT, min_periods=VOL_SHORT).mean() /
             tr.rolling(VOL_LONG, min_periods=VOL_LONG).mean())
    vb = pd.DataFrame({"vol_ratio": ratio.to_numpy(), "close_time": b["close_time"].to_numpy()},
                      index=b.index)
    got = cl.asof(vb, pd.DatetimeIndex(ev["decision_time"]))
    ev["vol_ratio"] = got["vol_ratio"].to_numpy(float)
    ev = ev[np.isfinite(ev["vol_ratio"].to_numpy())].reset_index(drop=True)
    ev["vol_up"] = ev["vol_ratio"] >= VOL_MULT
    return bk.public(ev, ["vol_ratio", "vol_up"])


def run(reading, detect, col, rules, params, srcs):
    ev = cl.cache_frame(f"{CID}_{reading}_{RUN_N}_{VOL_SHORT}_{VOL_LONG}_{VOL_MULT}",
                        lambda: detect(cl.load_m1()), version=bk.VERSION)
    print(reading, len(ev), ev[col].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    res = cl.gate_test(ev, col, mask_available_at="decision_time",
                       max_hold="150min", ctrl_tod_tol_min=TOD_TOL, claim="-")
    for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties"):
        print(" ", k, res.get(k))
    op = {"rules": bk.BASE_RULES + rules,
          "params": {**bk.BASE_PARAMS, **params, "ctrl_tod_tol_min": TOD_TOL}}
    src = {**bk.BASE_SOURCES, **srcs,
           "ctrl_tod_tol_min": "declared-before-run: not a timing rule; hold the NY "
                               "clock in the control (README trap 9)"}
    p = cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Baseline = sequential 15m bare CISD book (see _book.py). "
                              "Re-run ONCE after fixing a bug in _book.py (found by the size-down-on-fear b probe): a clock-hold time exit whose hold ended inside the 17:00 NY halt freed the position slot at the last pre-halt bar instead of at the hold's wall-clock end. Second fix + re-run: same-bar opposite CISD pairs (4 of 32,827) given a deterministic order (this script's b probe caught slice-dependent order). Second run before this fix: a NULL diff +0.0382 [-0.0219, +0.1008]; b never tested (probe failed again). First (buggy-chain) run: a NULL diff +0.0548 [-0.0040, +0.1075]; b never tested (probe failed). "
                              "claim '-': sizing down helps only if the down-sized trades "
                              "are worse per R. The subjective 'would tilt you' trigger "
                              "is not tested.")
    print(p)


if __name__ == "__main__":
    run("a", detect_a, "after_win_run",
        [f"gate after_win_run: the previous {RUN_N} taken trades all closed with gross "
         "R > 0 (streak across days); complement = every other trade; claim '-'"],
        {"win_run_n": RUN_N},
        {"win_run_n": "declared-before-run: 'extended winning run' has no number; 3, as "
                      "in the sibling concept loss-and-gain-limit-rules' measurable "
                      "'trade following a three-win streak'"})
    run("b", detect_b, "vol_up",
        [f"gate vol_up: mean 15m true range over the last {VOL_SHORT} closed bars >= "
         f"{VOL_MULT} x its mean over the last {VOL_LONG} closed bars; warm-up rows "
         "dropped; claim '-'"],
        {"vol_short_bars": VOL_SHORT, "vol_long_bars": VOL_LONG, "vol_mult": VOL_MULT},
        {"vol_short_bars": "declared-before-run: ~1 trading day of 15m bars (his "
                           "examples are intraday: 50 pts in 5 min, 400-pt 2h range)",
         "vol_long_bars": "declared-before-run: ~20 trading days baseline",
         "vol_mult": "declared-before-run: 'risen materially' has no threshold "
                     "(yaml ambiguity); 1.5x"})
