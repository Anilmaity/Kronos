"""candle-type-wick-to-body — gate_test.

Concept (specified): reversal candle := the wick (the one made FIRST, i.e. the opposing
run open -> extreme against the close direction) is larger than the body; the directional
/ expansion candle is the complement (small wick, large body). The measurable claim the
YAML lists: "next-candle expansion rate conditional on wick>body versus body>wick" — price
expands out of a body>wick candle and not out of a reversal candle.

Baseline book (stated): every closed 4h candle (forex grid) with a non-zero body is traded
in its close direction from the next M1 open, stop 1 x ATR(20) of the 4h bars, target
1 x ATR (rr 1) — the scale-free symmetric barrier threshold_fits §1 used — held 3 candles
(720 trading minutes, hold_basis bars).
Gate body_ge_wick: opposing_run <= body (NOT a reversal candle).
claim '+': the expansion-shaped candles continue better than the reversal-shaped ones,
control-adjusted (the matched control neutralises regime/geometry; entry is at the next
open with fixed-ATR barriers, so there is no banked cushion -> no C2-wick confound).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, atr, complete_bars, empty  # noqa: E402

CID = "candle-type-wick-to-body"
TF = "4h"
GRID = "forex"
ATR_N = 20
K_ATR = 1.0
RR = 1.0
HOLD = "720min"
MIN_M1 = 120
COLS = ["decision_time", "available_at", "direction", "stop_dist", "rr", "body_ge_wick"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF, grid4h=GRID)
    if len(b) < ATR_N + 2:
        return empty(COLS)
    b = b.copy()
    b["atr"] = atr(b, ATR_N)
    b = complete_bars(b, m1)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    d = np.sign(c - o)
    body = np.abs(c - o)
    opp = np.where(d > 0, o - l, h - o)            # opposing run, open -> extreme against close
    keep = (d != 0) & np.isfinite(b["atr"].to_numpy()) & (b["n_m1"].to_numpy() >= MIN_M1)
    t = pd.DatetimeIndex(b["close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d.astype(int),
                        "stop_dist": K_ATR * b["atr"].to_numpy(), "rr": RR,
                        "body_ge_wick": opp <= body})[keep]
    return out.reset_index(drop=True)[COLS]


OP = {"rules": [
    "4h candles (forex grid 17/21/01/05/09/13 NY) with >= 120 M1 bars and a non-zero body",
    "direction = sign(close - open); decide at the candle close, enter next M1 open",
    "stop = 1 x ATR(20) of 4h bars known at the close; target = 1 x ATR (rr 1); hold 3 candles = 720 trading minutes",
    "gate body_ge_wick: opposing run (bullish: open - low; bearish: high - open) <= |close - open|; "
    "complement = reversal candle (wick larger than the body)"],
    "params": {"tf": TF, "grid4h": GRID, "atr_n": ATR_N, "k_atr": K_ATR, "rr": RR,
               "max_hold": HOLD, "hold_basis": "bars", "min_m1": MIN_M1, "wick_body_cut": 1.0}}
SRC = {"tf": "corpus: YAML timeframes htf [1D, 4H]; threshold_fits §1: the wick/body separation is a 4h/1D phenomenon",
       "grid4h": "session_window_fit: forex grid for gold (carried as knob per Conjunction Test)",
       "atr_n": "threshold_fits: §1 barrier test uses a symmetric +/-1 ATR(20) barrier from the close",
       "k_atr": "threshold_fits: §1 +/-1 ATR(20)",
       "rr": "threshold_fits: §1 symmetric barrier (rr 1)",
       "max_hold": "threshold_fits: §1 'over the next 3 candles' (3 x 4h)",
       "hold_basis": "declared-before-run: 3 candles = trading time, so Friday-close candles are not truncated by the weekend (README trap 7)",
       "min_m1": "declared-before-run: drop stub 4h candles with < half their M1 bars (README trap 6)",
       "wick_body_cut": "corpus: 'the wick is larger than the body' (candle-type-wick-to-body.yaml); threshold_fits grade A crossover 1.0"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h_forex", lambda: detect(cl.load_m1()))
    print(len(ev), ev["body_ge_wick"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "body_ge_wick", mask_available_at="decision_time", max_hold=HOLD,
                       hold_basis="bars")
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap", "gate")})
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__,
                        probe=probe,
                        notes=f"gate firing rate {ev['body_ge_wick'].mean():.3f}. Indecision candle "
                              "(two long wicks, small body) is a named type with no directional claim; not tested.")
    print(p)
