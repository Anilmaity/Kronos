"""monday-trade-rule — The Monday Rule (TTrades own voice, contested).

"The only time I will trade a Monday is when I have a Friday reversal" (FvOUvQ7odiw):
Monday is then candle 3 of Friday's candle-2 closure; otherwise Monday is left to print.
Claim ('+'): Monday trades taken after a Friday reversal beat Monday trades taken
otherwise (the concept's own measurable: 'expectancy of Monday trades with and without a
Friday reversal').

Baseline book (stated): every Monday session, traded from Friday's close in the direction
the spec §2.3 previous-candle engine implies from Friday's candle (continuation closure ->
same way; reversal closure -> opposite; inside -> trend; both sides / range-bound -> no
trade); target = Friday's bias-side extreme (C3 expansion takes C2's extreme), stop =
Friday's opposite extreme; exit after one session of trading time (1380 M1 bars).
Gate (the two readings of the contested 'reversal' qualifier):
  a  Friday is a C2 closure (spec §3.2 test, one-sided) — 'reversal day' as stated.
  b  Friday is a C2 closure AND carries an hourly CISD in the same direction inside the
     Friday candle — the weekly-profile series' standard C2 confirmation (ambiguity 1).
gate_test(mask=friday_rev), claim '+'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, OHLC, daily, show, MIN_DAY_M1   # noqa: E402
from detectors.bias import previous_candle_state, hourly_cisd_in_candle   # noqa: E402

CID = "monday-trade-rule"
READ = sys.argv[1] if len(sys.argv) > 1 else "a"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "friday_rev"]


def detect(m1: pd.DataFrame, read: str = READ) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 3:
        return pd.DataFrame(columns=COLS)
    st = previous_candle_state(d[OHLC])
    bias = st["implied_bias"].to_numpy()
    b_c2 = ((d["low"] < d["p_low"]) & (d["close"] > d["p_low"])).to_numpy()
    s_c2 = ((d["high"] > d["p_high"]) & (d["close"] < d["p_high"])).to_numpy()
    c2 = (b_c2 ^ s_c2)
    fri = (d["wd"].to_numpy() == 4) & d["p_ok"].to_numpy(bool)
    h = cl.build_bars(m1, "1h")[OHLC] if read == "b" else None
    rows = []
    for i in np.flatnonzero(fri & np.isin(bias, ["bullish", "bearish"])):
        r = d.iloc[i]
        s = 1 if bias[i] == "bullish" else -1
        rev = bool(c2[i])
        if rev and (1 if b_c2[i] else -1) != s:          # cannot happen; guard
            rev = False
        if rev and read == "b":
            end = pd.Timestamp(r["close_time"]) - pd.Timedelta(hours=1)
            rev = hourly_cisd_in_candle(h, d.index[i], end, "bullish" if s > 0 else "bearish",
                                        scope="range", level_rule="series_open") is not None
        stop = float(r["low"] if s > 0 else r["high"])
        tgt = float(r["high"] if s > 0 else r["low"])
        if s * (tgt - float(r["close"])) <= 0:
            continue
        ct = pd.Timestamp(r["close_time"])
        rows.append({"decision_time": ct, "available_at": ct, "direction": s,
                     "stop_px": stop, "target_px": tgt, "friday_rev": rev})
    return pd.DataFrame(rows, columns=COLS)


OP = {"rules": [
    "daily candles on the 18:00 NY roll; stub days (<600 M1) dropped; previous day must be "
    "the preceding real session",
    "baseline: every Friday session with a spec §2.3 engine bias (continuation -> same, "
    "reversal -> opposite, inside -> trend); trade Monday from Friday's close in that "
    "direction; target Friday's bias-side extreme, stop its opposite extreme; no-room rows "
    "dropped; exit after 1380 trading M1 bars",
    ("gate a: Friday is a one-sided C2 closure (low<Thu low & close>Thu low, or mirror)"
     if READ == "a" else
     "gate b: Friday is a one-sided C2 closure AND a same-direction 1h CISD (series_open, "
     "scope range) exists inside the Friday candle")],
    "params": {"stub_filter_min_m1": MIN_DAY_M1, "baseline_bias": "previous_candle_state",
               "target": "Friday bias-side extreme", "max_hold": "1380min",
               "hold_basis": "bars", "ctrl_tod_tol_min": 30, "cluster": "none"}}
if READ == "b":
    OP["params"].update({"cisd_scope": "range", "cisd_level_rule": "series_open"})
SRC = {"stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
       "baseline_bias": "method_spec: §2.3 previous-candle engine (the non-reversal Friday "
                        "direction)",
       "target": "corpus: FvOUvQ7odiw Monday = candle 3 of the Friday candle 2 (C3 expansion "
                 "beyond C2's extreme); method_spec §3.3",
       "max_hold": "declared-before-run: the Monday session only",
       "hold_basis": "declared-before-run: README trap 7 — Friday-close holds span the weekend",
       "ctrl_tod_tol_min": "declared-before-run: every entry sits at the Sunday 18:00 reopen; "
                           "hold the NY clock fixed (README trap 9)",
       "cluster": "declared-before-run: one trade per week, no shared outcome",
       "cisd_scope": "method_spec: §2.4 [P] scope default 'range'",
       "cisd_level_rule": "method_spec: §4.2 'carry first-candle-open as the sensible default'"}
SRC = {k: v for k, v in SRC.items() if k in OP["params"]}

if __name__ == "__main__":
    ev = cl.cache_frame(f"monday_rule_{READ}_v1", lambda: detect(cl.load_m1()))
    ev = ev[pd.DatetimeIndex(ev["decision_time"]) <= cl.load_m1().index[-1]].reset_index(drop=True)  # the data\'s last, unfinished day
    print(READ, len(ev), ev["direction"].value_counts().to_dict(),
          ev["friday_rev"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "friday_rev", mask_available_at="decision_time",
                       max_hold="1380min", hold_basis="bars", ctrl_tod_tol_min=30)
    show(res)
    p = cl.write_result(CID, READ, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="The gate is known at Friday's close (mask_available_at = "
                              "decision_time). The rule is framed as his participation filter; "
                              "tested as the corpus's own measurable (Monday expectancy with vs "
                              "without a Friday reversal).")
    print(p)
