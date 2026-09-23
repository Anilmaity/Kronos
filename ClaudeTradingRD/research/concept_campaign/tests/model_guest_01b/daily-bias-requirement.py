"""daily-bias-requirement (guest, CONTESTED: Ash Trades / $niper vs DTR / HolyAngelBruv).

Baseline book (both readings): the phase-3 locked rung-0 book, bare 1h CISD (series_open,
2/2 swings, max_wait 3), decided at the confirming bar's close, stop at the protected
swing, 2R, 10h hold — a structure-break entry taken in either direction, i.e. the
bias-free "point of interest / structure" entry.

Daily bias (declared before the first run): the previous-candle engine of the method
spec (§2.3, detectors.bias.previous_candle_state) on the last COMPLETED 18:00-NY daily
candle: took one side and closed beyond it -> continuation that way; took one side and
closed back inside -> reversal; both sides / range-bound -> no bias; inside -> trend.
This is the mechanical form of the guests' "external liquidity taken -> draw to the
other side" read.

reading a (bias REQUIRED, Ash Trades / $niper): gate_test, claim '+': CISD trades
  aligned with the daily bias beat the rest (counter-bias and no-bias trades).
reading b (bias-FREE, HolyAngelBruv / DTR): "if the daily bias is uncertain, do not
  force one - trade market-structure breaks with displacement instead and you should
  still be fine": trade_test, claim '+', of the CISD book restricted to no-bias days.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cisd_1h, cl, daily, np, pd  # noqa: E402

CID = "daily-bias-requirement"
MAX_HOLD = "10h"


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    from detectors.bias import previous_candle_state
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr",
            "bias_dir", "aligned", "bias_at"]
    ev = cisd_1h(m1)
    d = daily(m1)
    if ev.empty or len(d) < 3:
        return pd.DataFrame(columns=cols)
    pcs = previous_candle_state(d[["open", "high", "low", "close"]])
    b = pd.DataFrame({"bias_dir": pcs["implied_bias"].map({"bullish": 1, "bearish": -1}).fillna(0).to_numpy(),
                      "close_time": pd.DatetimeIndex(d["close_time"])}, index=d.index)
    b = b.iloc[1:]                                   # first row has no previous candle
    a = cl.asof(b, pd.DatetimeIndex(ev["decision_time"]))
    ok = a["available_at"].notna().to_numpy()
    ev = ev[ok].reset_index(drop=True)
    a = a[ok]
    ev["bias_dir"] = a["bias_dir"].to_numpy().astype(int)
    ev["aligned"] = (ev["bias_dir"].to_numpy() == ev["direction"].to_numpy())
    ev["bias_at"] = pd.DatetimeIndex(a["available_at"]).tz_convert("UTC")
    ev["available_at"] = np.maximum(ev["available_at"].to_numpy(), ev["bias_at"].to_numpy())
    return ev[cols]


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    ev = detect_a(m1)
    return ev[ev["bias_dir"] == 0].reset_index(drop=True)


def op_common():
    return ["baseline: 1h bare CISD (series_open level, 2/2 swings, max_wait 3), decide at the confirming 1h close,"
            " enter next M1 open, stop at the protected swing, 2R target, 10h hold",
            "daily bias: previous_candle_state (method_spec §2.3) of the last completed 18:00-NY daily candle"
            " (stub days < 600 M1 dropped), read with asof at the decision time"]


SRC = {"baseline": "phase3: meta/conjunction_preregistration.md locked rung-0 config (1h, series_open, 2/2, max_wait 3, 2R, 10h)",
       "bias_engine": "method_spec: §2.3 previous-candle engine (detectors.bias.previous_candle_state, range_lookback 3)",
       "day_open_hour": "session_window_fit: settled 18:00 NY daily roll",
       "stub_min_m1": "declared-before-run: README trap 6 stub sessions"}
PARAMS = {"baseline": "1h CISD rung 0", "bias_engine": "previous_candle_state", "day_open_hour": 18,
          "stub_min_m1": 600}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_a_v1", lambda: detect_a(cl.load_m1()))
    print("n", len(ev), "aligned share", ev["aligned"].mean(), "no-bias share", (ev["bias_dir"] == 0).mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="30D")
    res = cl.gate_test(ev, "aligned", mask_available_at="bias_at", max_hold=MAX_HOLD, claim="+")
    for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties"):
        print("a", k, res.get(k))
    op = {"rules": op_common() + ["gate: trade direction == daily bias; complement = counter-bias and no-bias trades"],
          "params": {**PARAMS, "max_hold": MAX_HOLD}}
    p = cl.write_result(CID, "a", res, operationalization=op, params_source={**SRC, "max_hold": SRC["baseline"]},
                        script=__file__, probe=probe,
                        notes="Reading a = the bias-required position (Ash Trades / $niper). Bias engine is the "
                        "method-spec previous-candle read, the mechanical form of 'external liquidity taken'.")
    print("wrote", p)

    evb = cl.cache_frame(f"{CID}_b_v1", lambda: detect_b(cl.load_m1()))
    print("b n", len(evb))
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="30D")
    resb = cl.trade_test(evb, max_hold=MAX_HOLD, claim="+")
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties"):
        print("b", k, resb.get(k))
    opb = {"rules": op_common() + ["events: only CISD trades taken while the daily bias is 'none' (both sides taken /"
                                   " range-bound): the no-bias, structure-only book"],
           "params": {**PARAMS, "max_hold": MAX_HOLD}}
    p = cl.write_result(CID, "b", resb, operationalization=opb, params_source={**SRC, "max_hold": SRC["baseline"]},
                        script=__file__, probe=probe_b,
                        notes="Reading b = the bias-free position (HolyAngelBruv / DTR): with no bias, trade "
                        "structure breaks (CISD = close through the opposing series; no displacement magnitude filter).")
    print("wrote", p)
