"""weekly-profile — Weekly profile is not weekly bias (TTrades own voice, specified).

"A weekly profile is the chained application of daily bias ... the fractal model already
encodes this as the C2 to C3 to C4 sequence on the daily chart, and it deliberately stops
before C5" (aqnY1yZvfYs). The one decidable, falsifiable content is the chain limit:
anticipating the next day's continuation is worth doing while the next day is C3 or C4
of the chain, and not beyond (C5+).

Baseline book (stated): the day-by-day chained daily bias of the detection rules — for
every day D with a directional closure (spec §2.3 engine: continuation -> same way,
reversal/C2 closure -> the reversal way), trade day D+1 in that direction from D's close;
target = D's bias-side extreme (the 'previous day high/low' objective), stop = D's
opposite extreme; exit after one session (1380 trading M1 bars).
Chain position: r = number of consecutive days ending at D whose directional closure
implies the same bias; the run's first day is the chain's C2, so D+1 is candle C(r+2).
Gate: D+1 is C3 or C4 (r <= 2). Complement: C5 and beyond (r >= 3).
gate_test(mask=within_c4), claim '+'. Inside / range-bound / two-sided days carry no
closure and are not in the book (the chain maps closures).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, OHLC, daily, show, MIN_DAY_M1   # noqa: E402
from detectors.bias import previous_candle_state                 # noqa: E402

CID = "weekly-profile"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "chain_r",
        "within_c4"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS)
    st = previous_candle_state(d[OHLC])
    directional = st["state"].isin(["continuation", "reversal"]).to_numpy()
    bias = np.where(directional, st["implied_bias"].to_numpy(), "none")
    p_ok = d["p_ok"].to_numpy(bool)
    r = np.zeros(len(d), dtype=int)
    for i in range(len(d)):
        if bias[i] == "none" or not p_ok[i]:
            continue
        r[i] = r[i - 1] + 1 if (i > 0 and bias[i - 1] == bias[i] and r[i - 1] > 0) else 1
    rows = []
    for i in np.flatnonzero(r > 0):
        row = d.iloc[i]
        s = 1 if bias[i] == "bullish" else -1
        stop = float(row["low"] if s > 0 else row["high"])
        tgt = float(row["high"] if s > 0 else row["low"])
        if s * (tgt - float(row["close"])) <= 0:
            continue
        ct = pd.Timestamp(row["close_time"])
        rows.append({"decision_time": ct, "available_at": ct, "direction": s,
                     "stop_px": stop, "target_px": tgt, "chain_r": int(r[i]),
                     "within_c4": bool(r[i] <= 2)})
    return pd.DataFrame(rows, columns=COLS)


OP = {"rules": [
    "daily candles on the 18:00 NY roll; stub days (<600 M1) dropped; previous day must be "
    "the preceding real session (a data hole resets the chain)",
    "day D directional closure (spec §2.3): continuation closure -> same way; reversal "
    "closure -> opposite; inside / range-bound / both sides -> not in the book",
    "chain run r = consecutive directional days with the same implied bias ending at D; "
    "D+1 = C(r+2)",
    "trade D+1 from D's close in the bias; target D's bias-side extreme, stop D's opposite "
    "extreme; no-room rows dropped; exit after 1380 trading M1 bars",
    "gate: D+1 is C3 or C4 (r<=2) vs C5+ (r>=3)"],
    "params": {"stub_filter_min_m1": MIN_DAY_M1, "engine": "previous_candle_state",
               "chain_limit": "C4", "target": "D bias-side extreme", "max_hold": "1380min",
               "hold_basis": "bars", "ctrl_tod_tol_min": 30}}
SRC = {"stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
       "engine": "method_spec: §2.3 previous-candle engine ('If a day closes higher, "
                 "anticipate continuation the next day')",
       "chain_limit": "corpus: aqnY1yZvfYs 'C2 to C3 to C4 ... deliberately stops before C5' "
                      "(method_spec §2.5)",
       "target": "corpus: execution 'per the daily model' -> daily-bias targets 'previous day "
                 "high / low'",
       "max_hold": "declared-before-run: bias is per day ('Per day, never per week')",
       "hold_basis": "declared-before-run: README trap 7 — holds cross the halt/weekend",
       "ctrl_tod_tol_min": "declared-before-run: every entry sits at the 18:00 reopen; hold "
                           "the NY clock fixed (README trap 9)"}

if __name__ == "__main__":
    ev = cl.cache_frame("weekly_profile_chain_v1", lambda: detect(cl.load_m1()))
    ev = ev[pd.DatetimeIndex(ev["decision_time"]) <= cl.load_m1().index[-1]].reset_index(drop=True)  # the data\'s last, unfinished day
    print(len(ev), ev["chain_r"].value_counts().sort_index().to_dict(),
          ev["within_c4"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "within_c4", mask_available_at="decision_time",
                       max_hold="1380min", hold_basis="bars", ctrl_tod_tol_min=30)
    show(res)
    p = cl.write_result(CID, None, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="'No weekly bias' itself is a statement of practice, not a "
                              "prediction; the tested content is the chain limit C2->C3->C4, "
                              "not C5. The 'objective hit lets the chain turn' clause is loose "
                              "in the corpus and is not applied.")
    print(p)
