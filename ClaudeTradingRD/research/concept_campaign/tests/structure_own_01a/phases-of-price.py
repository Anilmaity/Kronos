"""phases-of-price (TTrades own voice, contested) -> two readings, both on DAILY closures
(the concept classifies phases "from daily closures, not from the shape of intraday price").

Declared before the first run:
  Common: 18:00-NY daily candles, stub sessions (<600 M1) dropped. An EXPANSION day is a
  previous-candle continuation closure: takes the previous day's high (low) AND closes beyond
  it (detection rule "Count consecutive expansion candles closing outside the previous
  candle's range"; method_spec §2.3).

  reading a -- "three days of expansion -> a new phase, not a fourth continuation"
    (detection rules: 'after three days of expansion in one direction, anticipate a new phase
    of price rather than a further continuation'; AArNO58yBiw / caaS6_Q7O78).
    gate_test, claim '-'. Baseline book = the mechanical previous-candle continuation read on
    EVERY expansion day d: trade d's direction from the next session open, stop = EQ of d's
    range (the continuation branch 'respects the EQ', method_spec §2.4), target = d's own
    extreme (the next previous-candle level), max_hold one session (23h of trading bars).
    Gate = d is the 3rd (or later) consecutive expansion day in the same direction
    (d, d-1, d-2 all expansion closures the same way). The concept says the gated
    continuation trades are WORSE (claim '-').

  reading b -- "expansion met with expansion = reversal" ('the ONLY way to form a reversal
    is to get expansion opposite'; 08MZAXZ5WAM; 'at a reversal you trade away from the swept
    extreme'). trade_test, claim '+'. Day d-1 is an expansion day one way and day d is an
    expansion day the other way (closes beyond d-1's opposite extreme). Trade d's direction
    from the next session open; stop = the extreme of the two-day wick (max high of d-1, d
    for a short); target 2R (method_spec §5.3 floor); max_hold 5 sessions of trading bars;
    control held to the same NY time of day (+/-30 min) since every entry is the 18:00 open.
    [Run 2: that control left 60/127 trades with no draw; re-run once with ctrl_grid="1D",
    i.e. controls entered at the 18:00 session open of other days within +/-30 days.]
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/structure_own_01a")
import numpy as np
import pandas as pd
from _common import cl, daily, continuation_flags, show

CID = "phases-of-price"
COLS_A = ["decision_time", "available_at", "direction", "stop_px", "target_px", "three_exp"]
COLS_B = ["decision_time", "available_at", "direction", "stop_px", "rr"]


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 5:
        return pd.DataFrame(columns=COLS_A)
    up, dn = continuation_flags(d)
    H, L = d["high"].to_numpy(float), d["low"].to_numpy(float)
    ct = pd.DatetimeIndex(d["close_time"])
    up1, dn1 = np.r_[False, up[:-1]], np.r_[False, dn[:-1]]
    up2, dn2 = np.r_[False, False, up[:-2]], np.r_[False, False, dn[:-2]]
    sel = np.flatnonzero(up | dn)
    sgn = np.where(up[sel], 1, -1)
    ev = pd.DataFrame({
        "decision_time": ct[sel], "available_at": ct[sel], "direction": sgn,
        "stop_px": 0.5 * (H[sel] + L[sel]),
        "target_px": np.where(sgn > 0, H[sel], L[sel]),
        "three_exp": np.where(sgn > 0, up[sel] & up1[sel] & up2[sel],
                              dn[sel] & dn1[sel] & dn2[sel]).astype(bool),
    })
    return ev[COLS_A].reset_index(drop=True)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    d = daily(m1)
    if len(d) < 4:
        return pd.DataFrame(columns=COLS_B)
    up, dn = continuation_flags(d)
    H, L = d["high"].to_numpy(float), d["low"].to_numpy(float)
    ct = pd.DatetimeIndex(d["close_time"])
    up1, dn1 = np.r_[False, up[:-1]], np.r_[False, dn[:-1]]
    H1, L1 = np.r_[np.nan, H[:-1]], np.r_[np.nan, L[:-1]]
    short = dn & up1
    long_ = up & dn1
    sel = np.flatnonzero(short | long_)
    sgn = np.where(long_[sel], 1, -1)
    stop = np.where(sgn < 0, np.fmax(H[sel], H1[sel]), np.fmin(L[sel], L1[sel]))
    ev = pd.DataFrame({"decision_time": ct[sel], "available_at": ct[sel], "direction": sgn,
                       "stop_px": stop, "rr": 2.0})
    return ev[COLS_B].reset_index(drop=True)


def run_a():
    ev = cl.cache_frame("phases_a_daily_exp3", lambda: detect_a(cl.load_m1()))
    print("a events", len(ev), "gated", int(ev["three_exp"].sum()))
    probe = cl.probe_lookahead(detect_a, ev, lookback="60D", recent="3D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "three_exp", mask_available_at="decision_time", claim="-",
                       max_hold="23h", hold_basis="bars")
    show(res)
    op = {"rules": [
        "18:00-NY daily candles; stub sessions (<600 M1) dropped",
        "expansion day = previous-candle continuation closure (takes prior high/low and closes beyond it)",
        "baseline: every expansion day d -> trade d's direction at the next session open; stop = EQ of d; "
        "target = d's extreme in the trade direction; max hold 23h of trading bars",
        "gate: d, d-1 and d-2 are all expansion closures in the same direction (3+ days of expansion)",
        "claim '-': continuation trades after 3+ expansion days are worse than other continuation trades"],
        "params": {"tf": "1D", "day_open": "18:00 NY", "stub_min_m1": 600, "streak": 3,
                   "stop": "EQ of expansion day", "target": "expansion day extreme",
                   "max_hold": "23h", "hold_basis": "bars", "grid4h": "n/a (1D)"}}
    src = {"tf": "corpus: iEaMbuFZb24 'I use the daily candles to tell me what is happening'",
           "day_open": "method_spec: §1.4 daily open 18:00 canon [P]",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "streak": "corpus: AArNO58yBiw 'three days of expansion lower so we can get a new phase'",
           "stop": "method_spec: §2.4 continuation branch respects the EQ of the previous day",
           "target": "method_spec: §2.3 continuation closure -> next candle reaches the candle's extreme",
           "max_hold": "declared-before-run: one trading session (next-candle read)",
           "hold_basis": "declared-before-run: trading-time hold so Friday decisions are not emptied by the weekend (trap 7)",
           "grid4h": "declared-before-run: not used"}
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading a: the 3-days-of-expansion exhaustion rule as a gate on the "
                                "mechanical daily continuation book."))


def run_b():
    ev = cl.cache_frame("phases_b_daily_expexp", lambda: detect_b(cl.load_m1()))
    print("b events", len(ev))
    probe = cl.probe_lookahead(detect_b, ev, lookback="60D", recent="3D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold="115h", hold_basis="bars", ctrl_grid="1D")
    show(res)
    op = {"rules": [
        "18:00-NY daily candles; stub sessions (<600 M1) dropped",
        "expansion day = previous-candle continuation closure",
        "reversal = expansion day d-1 met by an expansion day d in the opposite direction "
        "(d closes beyond d-1's opposite extreme)",
        "trade d's direction at the next session open; stop = the two-day wick extreme; target 2R; "
        "max hold 5 sessions of trading bars; control entries drawn on daily-bar closes (the 18:00 session open) within +/-30 days"],
        "params": {"tf": "1D", "day_open": "18:00 NY", "stub_min_m1": 600,
                   "stop": "two-day wick extreme", "rr": 2.0, "max_hold": "115h",
                   "hold_basis": "bars", "ctrl_grid": "1D", "grid4h": "n/a (1D)"}}
    src = {"tf": "corpus: iEaMbuFZb24 'I use the daily candles to tell me what is happening'",
           "day_open": "method_spec: §1.4 daily open 18:00 canon [P]",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "stop": "corpus: 08MZAXZ5WAM expansion met with expansion = reversal = the HTF wick; trade away from the swept extreme",
           "rr": "method_spec: §5.3 2R floor",
           "max_hold": "declared-before-run: one trading week (5 sessions x 23h) for a daily setup",
           "hold_basis": "declared-before-run: trading-time hold (trap 7)",
           "ctrl_grid": "declared-before-run: every entry is the 18:00 session open; controls drawn on the same daily grid (trap 9). Replaces a first run with ctrl_tod_tol_min=30 whose control fill was 53% (60/127 trades had no control draw because no :00 M1 bar sat within 30 min of 18:00 on those windows) - an operationalisation defect, re-run once",
           "grid4h": "declared-before-run: not used"}
    print(cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Reading b: 'expansion met with expansion' reversal traded away from the "
                                "two-day wick. Run 2 of 2: run 1 (ctrl_tod_tol_min=30) left 60/127 trades "
                                "without a control (fill 53%), so the diff mixed paired and unpaired trades; "
                                "re-run once with controls on the daily grid. Both runs are UNDERPOWERED "
                                "by construction (n=127 < 200)."))


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        {"a": run_a, "b": run_b}[r]()
