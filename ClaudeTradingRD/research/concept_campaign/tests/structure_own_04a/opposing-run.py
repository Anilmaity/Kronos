"""opposing-run — gate_test on the LIVE (in-progress) candle.

Concept: opposing_run := distance from the candle's opening price to the extreme against
the intended direction, measured WHILE THE CANDLE IS STILL OPEN (that is why he prefers
the term to 'wick'). Shallow run -> the candle supports expansion in the intended
direction; large run -> it does not (targets revert to the open).

Operationalisation (the live measurement is the point of this concept; the closed-candle
version is wick-size-test / small-wick-expansion-rule):
  * every 4h candle (forex grid), measured at its midpoint (open + 120 min), from M1 bars
    closed by then;
  * intended direction = the side of the open price is on at that moment (price above the
    open -> the candle is bullish so far -> opposing run = open - low so far);
  * baseline trade: enter at the next M1 open in that direction, stop at the opposing
    extreme so far (the end of the opposing run - the level his invalidation names), no
    target, exit at the candle's scheduled close (120 min wall clock) - i.e. "does the
    candle expand for the rest of its period";
  * gate shallow: opposing_run / (high - low so far) <= 0.30.
claim '+': shallow-run candles do better, control-adjusted, than large-run candles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, empty, ns, to_ts, M1, LiveCandle, ONE_MIN, GRID_SRC  # noqa: E402

CID = "opposing-run"
TF = "4h"
GRID = "forex"
MID_MIN = 120
HOLD = "120min"
MIN_M1_FIRST_HALF = 60
CUT_RANGE = 0.30
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "shallow"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    if len(m1) < 300:
        return empty(COLS)
    m = M1(m1)
    lc = LiveCandle(m1, m, TF, GRID)
    st = lc.bstart
    ct = lc.bclose
    tdec = st + MID_MIN * ONE_MIN
    keep = (tdec < ct) & (tdec <= m.t[-1] + ONE_MIN)
    tdec = tdec[keep]
    bidx = np.flatnonzero(keep)
    s = lc.at(tdec)
    # number of M1 bars of this candle closed by the decision
    n_first = (np.searchsorted(m.t + ONE_MIN, tdec, side="right")
               - np.searchsorted(m.t, st[bidx], side="left"))
    ok = s["ok"] & (s["bucket"] == bidx) & (n_first >= MIN_M1_FIRST_HALF)
    d = np.sign(s["price"] - s["open"])
    ok &= (d != 0)
    rng = s["hi"] - s["lo"]
    ok &= rng > 0
    opp = np.where(d > 0, s["open"] - s["lo"], s["hi"] - s["open"])
    stop = np.where(d > 0, s["lo"], s["hi"])
    shallow = opp / np.where(rng > 0, rng, np.nan) <= CUT_RANGE
    t = to_ts(tdec)
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": stop, "rr": np.nan, "shallow": shallow})[ok]
    out["direction"] = out["direction"].astype(int)
    return out.reset_index(drop=True)[COLS]


RULES = [
    "every 4h candle (forex grid 17/21/01/05/09/13 NY); measure at candle open + 120 min from M1 bars closed by then "
    "(>= 60 of them)",
    "intended direction = sign(price - candle open) at that moment; opposing run = open -> extreme against it so far",
    "baseline: enter next M1 open in that direction, stop = the opposing extreme so far, no target, exit at the "
    "candle's scheduled close (120 min clock)",
    "gate shallow: opposing_run / (high - low so far) <= 0.30",
]
PARAMS = {"tf": TF, "grid4h": GRID, "mid_min": MID_MIN, "max_hold": HOLD, "hold_basis": "clock",
          "min_m1_first_half": MIN_M1_FIRST_HALF, "cut_range": CUT_RANGE, "target": "none (time exit at candle close)"}
SRC = {"tf": "corpus: YAML timeframes htf [1D, 4H, 1H]; threshold_fits §1: wick effects live on 4h/1D",
       "grid4h": GRID_SRC,
       "mid_min": "declared-before-run: measure live at half the candle's period (SlWxhzhLo3A 'we use almost half the time' - the corpus's live grading point)",
       "max_hold": "declared-before-run: to the candle's scheduled close - the expansion the candle is said to support",
       "hold_basis": "declared-before-run: clock, the exit is the candle's own close time",
       "min_m1_first_half": "declared-before-run: >= half the M1 bars of the first 120 min (stub guard, README trap 6)",
       "cut_range": "threshold_fits: small wick / shallow run, range parameterisation default 0.30 (grade C); 'shallow' on a candle is the same parameter",
       "target": "corpus: opposing-run.yaml gives no target for the supported expansion; time exit declared-before-run"}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h_mid", lambda: detect(cl.load_m1()))
    print(len(ev), ev["shallow"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "shallow", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    p = cl.write_result(CID, None, res, operationalization={"rules": RULES, "params": PARAMS},
                        params_source=SRC, script=__file__, probe=probe,
                        notes=f"gate firing rate {ev['shallow'].mean():.3f}. Live (mid-candle) reading; the "
                              "large-run target-reversion claim is large-wick-target-adjustment's, not tested here.")
    print(p)
