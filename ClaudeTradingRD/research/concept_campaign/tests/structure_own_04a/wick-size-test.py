"""wick-size-test — gate_test, two readings of the stated evidence.

Concept: the wick is the OPPOSING RUN (open -> extreme against the candle's direction).
Sizing it is binary: a shallow run (small wick) supports expansion away from the wick; a
LARGE opposing run - evidenced by "a bunch of time and a bunch of range" - does not.
The YAML flags two denominators (range vs the candle's time) that are never reconciled.

Baseline book (stated, identical to the harness-precedent candle-type test so the gate
is the only change): every closed 4h candle (forex grid) with a non-zero body is traded
in its close direction from the next M1 open, stop 1 x ATR(20) of the 4h bars, target
1 x ATR (rr 1) - threshold_fits §1's scale-free symmetric barrier - held 3 candles
(720 trading minutes).

  reading a (the stated evidence, both axes): LARGE := opposing_run/(high-low) > 0.30
            AND time_share_to_extreme > 0.25; gate 'shallow' = not LARGE.
  reading b (the time axis alone, the axis only M1 can measure): shallow :=
            time_share_to_extreme <= 0.25.
time_share_to_extreme = (start of the M1 bar that printed the opposing extreme - first M1
start + 1 min) / (candle's traded span, first to last M1 + 1 min) (first occurrence), so the
17:00 candle's halt hour does not count as elapsed time.
claim '+': shallow-run candles continue better (control-adjusted) than large-run ones.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, atr, complete_bars, empty, ns, M1, GRID_SRC  # noqa: E402

CID = "wick-size-test"
TF = "4h"
GRID = "forex"
ATR_N = 20
K_ATR = 1.0
RR = 1.0
HOLD = "720min"
MIN_M1 = 120
CUT_RANGE = 0.30
CUT_TIME = 0.25
COLS = ["decision_time", "available_at", "direction", "stop_dist", "rr", "shallow_a", "shallow_b"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = cl.build_bars(m1, TF, grid4h=GRID)
    if len(b) < ATR_N + 2:
        return empty(COLS)
    b = b.copy()
    b["atr"] = atr(b, ATR_N)
    b = complete_bars(b, m1)
    m = M1(m1)
    st = ns(b.index)
    ct = ns(b["close_time"])
    k = np.searchsorted(st, m.t, side="right") - 1
    ok = (k >= 0) & (m.t < ct[np.clip(k, 0, None)])
    df = pd.DataFrame({"k": k[ok], "h": m.h[ok], "l": m.l[ok], "t": m.t[ok]})
    ih = df.groupby("k")["h"].idxmax()
    il = df.groupby("k")["l"].idxmin()
    t_hi = pd.Series(df["t"].to_numpy()[ih.to_numpy()], index=ih.index).reindex(range(len(b))).to_numpy()
    t_lo = pd.Series(df["t"].to_numpy()[il.to_numpy()], index=il.index).reindex(range(len(b))).to_numpy()
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    d = np.sign(c - o)
    rng = h - l
    opp = np.where(d > 0, o - l, h - o)
    t_ext = np.where(d > 0, t_lo, t_hi)
    f1 = ns(b["first_m1"]).astype(float)
    l1 = ns(b["last_m1"]).astype(float)
    tshare = (t_ext - f1 + 60e9) / (l1 - f1 + 60e9)     # share of the candle's TRADED span
    keep = ((d != 0) & np.isfinite(b["atr"].to_numpy()) & (b["n_m1"].to_numpy() >= MIN_M1)
            & np.isfinite(tshare) & (rng > 0))
    large_a = (opp / np.where(rng > 0, rng, np.nan) > CUT_RANGE) & (tshare > CUT_TIME)
    t = pd.DatetimeIndex(b["close_time"])
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_dist": K_ATR * b["atr"].to_numpy(), "rr": RR,
                        "shallow_a": ~large_a, "shallow_b": tshare <= CUT_TIME})[keep]
    out["direction"] = out["direction"].astype(int)
    return out.reset_index(drop=True)[COLS]


RULES = [
    "4h candles (forex grid 17/21/01/05/09/13 NY) with >= 120 M1 bars and a non-zero body",
    "direction = sign(close - open); decide at the candle close, enter next M1 open",
    "stop = 1 x ATR(20) of 4h bars known at the close; target = 1 x ATR (rr 1); hold 3 candles = 720 trading minutes",
    "opposing run = open -> extreme against the close direction; time_share_to_extreme = (M1 start of that extreme "
    "(first occurrence) - first M1 start + 1 min) / (traded span first..last M1 + 1 min)",
]
GATE = {"a": "gate shallow_a: NOT (opposing_run/(high-low) > 0.30 AND time_share_to_extreme > 0.25) - large needs both "
              "'a bunch of range' and 'a bunch of time'",
        "b": "gate shallow_b: time_share_to_extreme <= 0.25 (time axis only)"}
SRC = {"tf": "corpus: YAML timeframes htf [1D, 4H, 1H]; threshold_fits §1: wick separation lives on 4h/1D (4h chosen for n)",
       "grid4h": GRID_SRC,
       "atr_n": "threshold_fits: §1 barrier test, symmetric +/-1 ATR(20) from the close",
       "k_atr": "threshold_fits: §1 +/-1 ATR(20)",
       "rr": "threshold_fits: §1 symmetric barrier (rr 1)",
       "max_hold": "threshold_fits: §1 'over the next 3 candles' (3 x 4h)",
       "hold_basis": "declared-before-run: 3 candles = trading time so Friday candles are not cut by the weekend (README trap 7)",
       "min_m1": "declared-before-run: drop stub 4h candles with < half their M1 bars (README trap 6)",
       "cut_range": "threshold_fits: small wick, range parameterisation default 0.30 (grade C)",
       "cut_time": "threshold_fits: small wick, time axis default 0.25 (grade C)"}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_4h_forex", lambda: detect(cl.load_m1()))
    print(len(ev), ev["shallow_a"].mean(), ev["shallow_b"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe["passed"])
    for rd in ("a", "b"):
        col = f"shallow_{rd}"
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD, hold_basis="bars")
        print(rd, {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                           "mde", "exposure_bars", "ties", "ctrl_overlap")})
        params = {"tf": TF, "grid4h": GRID, "atr_n": ATR_N, "k_atr": K_ATR, "rr": RR, "max_hold": HOLD,
                  "hold_basis": "bars", "min_m1": MIN_M1, "cut_range": CUT_RANGE, "cut_time": CUT_TIME}
        if rd == "b":
            params.pop("cut_range")
        src = {k: v for k, v in SRC.items() if k in params}
        p = cl.write_result(CID, rd, res, operationalization={"rules": RULES + [GATE[rd]], "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes=f"gate firing rate {ev[col].mean():.3f}. Same baseline as candle-type-wick-to-body "
                                  "(range/body axes already tested there and in small-wick-expansion-rule); this concept "
                                  "adds the time axis.")
        print(p)
