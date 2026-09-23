"""large-wick-target-adjustment (contested) — on a large opposing run, do not target the
far extreme; target back to the daily open.

Entry is "unchanged" per the concept (execution.entry), so the entry model is the
campaign's canonical 1h CISD book (phase-3 locked; stop at the protected swing, 10h hold).
At each CISD decision the running daily candle (18:00 NY trading day) is read from M1
bars closed by the decision:
  O   = daily open (first M1 open at/after 18:00 NY, within 60 min, same trading day)
  H,L = running high/low of the day so far
  P   = the CISD confirm close
  opposing run = O - L (long) / H - O (short) — one-sided open->extreme against the trade
  body_d       = direction * (P - O)
  LARGE wick   = opposing run > 1.0 * max(body_d, 0)   (threshold_fits cut 1.0; a price
                 still on the wick side of the open is all wick, so it counts as large)

Reading a (the "do not expect expansion" half, gate_test):
  book = CISD trades with the EXPANSION target = the previous day's extreme in the trade
  direction (PDH long / PDL short; method_spec §5.2 item 1, previous candles' extremes,
  which the concept says NOT to target on a large wick), kept only where it lies beyond P.
  gate = LARGE wick; claim '-' (large-wick trades aimed at expansion do worse than
  small-wick ones, control-adjusted).
Reading b (the substitute target, trade_test):
  book = CISD trades on LARGE-wick days with price still on the wick side of the open
  (d*(O-P) > 0), target = the daily open; claim '+' (the adjusted target beats a matched
  random entry with the same stop/target distance).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _base import cl, np, pd, cisd_book, show, PHASE3_SRC, HOLD_SRC  # noqa: E402

CID = "large-wick-target-adjustment"
HOLD = "10h"
WICK_CUT = 1.0
OPEN_DELAY = 60


def _frame(m1):
    ev = cisd_book(m1, "1h")
    if ev.empty:
        return ev.assign(O=[], H=[], L=[], pdx=[], av2=[])
    dt = pd.DatetimeIndex(ev["decision_time"])
    op = cl.open_at(dt, "18:00", m1=m1, max_delay_min=OPEN_DELAY)
    rh = cl.running_hilo(dt, "1D", m1=m1)
    ph = cl.prior_hilo(dt, "1D", m1=m1, min_coverage=0.5)
    s = ev["direction"].to_numpy()
    ev["O"] = op["price"].to_numpy(float)
    ev["H"] = rh["high"].to_numpy(float)
    ev["L"] = rh["low"].to_numpy(float)
    ev["pdx"] = np.where(s > 0, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    pav = pd.DatetimeIndex(ph["available_at"]).tz_convert("UTC")
    oav = pd.DatetimeIndex(op["time"]).tz_convert("UTC") + pd.Timedelta(minutes=1)
    av = np.maximum(np.maximum(dt.asi8, pav.asi8), oav.asi8)
    ev["av2"] = pd.to_datetime(av, utc=True)
    ok = np.isfinite(ev["O"]) & np.isfinite(ev["H"]) & np.isfinite(ev["L"])
    ev = ev[ok.to_numpy()].reset_index(drop=True)
    s = ev["direction"].to_numpy()
    P, O, H, L = (ev[k].to_numpy() for k in ("confirm_close", "O", "H", "L"))
    opp = np.where(s > 0, O - L, H - O)
    body_d = s * (P - O)
    ev["large"] = opp > WICK_CUT * np.maximum(body_d, 0.0)
    return ev


def detect_a(m1):
    ev = _frame(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "large"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    s = ev["direction"].to_numpy()
    keep = np.isfinite(ev["pdx"].to_numpy()) & (s * (ev["pdx"] - ev["confirm_close"]) > 0)
    ev = ev[keep.to_numpy()]
    out = pd.DataFrame({"decision_time": ev["decision_time"], "available_at": ev["av2"],
                        "direction": ev["direction"], "stop_px": ev["stop_px"],
                        "target_px": ev["pdx"], "large": ev["large"].astype(bool)})
    return out.reset_index(drop=True)


def detect_b(m1):
    ev = _frame(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    s = ev["direction"].to_numpy()
    keep = ev["large"].to_numpy() & (s * (ev["O"] - ev["confirm_close"]) > 0).to_numpy()
    ev = ev[keep]
    out = pd.DataFrame({"decision_time": ev["decision_time"], "available_at": ev["av2"],
                        "direction": ev["direction"], "stop_px": ev["stop_px"],
                        "target_px": ev["O"]})
    return out.reset_index(drop=True)


BASE_RULES = [
    "entry: 1h CISD (series_open, 2/2 swings, max_wait 3, min_series 1), decide at the "
    "confirming 1h close, enter next M1 open, stop at the protected swing, hold 10h",
    "running daily candle at the decision (18:00 NY trading day, M1 bars closed by then): "
    "O = first M1 open in 18:00-19:00 NY, H/L = running high/low, P = confirm close",
    "large wick = opposing run (O-L long, H-O short) > 1.0 x max(direction*(P-O), 0)"]
PARAMS = {"entry_tf": "1h", "max_hold": HOLD, "wick_cut": WICK_CUT, "daily_open": "18:00 NY",
          "open_max_delay_min": OPEN_DELAY, "pdx_min_coverage": 0.5}
SRC = {"entry_tf": PHASE3_SRC, "max_hold": HOLD_SRC,
       "wick_cut": "threshold_fits: large wick = opposing_run/|body| > 1.0 (grade A)",
       "daily_open": "method_spec §1.4: the 18:00 NY daily candle anchor (the concept's "
                     "ambiguity names 18:00 as the corpus's preferred open)",
       "open_max_delay_min": "declared-before-run: first traded minute of the reopen hour",
       "pdx_min_coverage": "declared-before-run: README trap 6, skip stub sessions"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in which:
        ev = cl.cache_frame("lwta_a_cisd1h_pdx_large1.0", lambda: detect_a(cl.load_m1()))
        print("a rows", len(ev), "large share", ev["large"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="20D")
        res = cl.gate_test(ev, "large", mask_available_at="decision_time", max_hold=HOLD,
                           claim="-")
        show(res)
        op = {"rules": BASE_RULES + [
            "target = previous trading day's high (long) / low (short), kept only if beyond P",
            "gate = large wick; claim '-': large-wick trades aimed at the expansion target "
            "do worse (control-adjusted) than small-wick ones"], "params": PARAMS}
        print(cl.write_result(CID, "a", res, operationalization=op, params_source={
            **SRC, "target": "method_spec §5.2 item 1 (previous candle's extreme) — the "
                             "expansion target the concept says not to use on a large wick"},
            script=__file__, probe=probe,
            notes="Gate stamp = decision time: the wick class is read from M1 closed by the "
                  "CISD close. The far extreme uses PDH/PDL because 'the far side of the "
                  "range' is not otherwise defined."))
    if "b" in which:
        ev = cl.cache_frame("lwta_b_cisd1h_large_target_open", lambda: detect_b(cl.load_m1()))
        print("b rows", len(ev))
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        res = cl.trade_test(ev, max_hold=HOLD, claim="+")
        show(res)
        op = {"rules": BASE_RULES + [
            "keep large-wick events with price still on the wick side of the daily open "
            "(direction*(O-P) > 0)", "target = the daily open O; claim '+' vs matched random "
            "entry"], "params": PARAMS}
        print(cl.write_result(CID, "b", res, operationalization=op, params_source={
            **SRC, "target": "corpus: 5UsKZ7pZqvY 'my expectations is favoring back towards "
                             "that daily open'"},
            script=__file__, probe=probe,
            notes="Target 2 (current high/low of day) and the session-lows alternative are "
                  "not scored; T1 (the daily open) is the one both Shorts name first."))
