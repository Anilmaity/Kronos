"""open-uncertainty-wait-ladder — update_20261007_live_12, new concept (gate_test).

Source rTomJ8URFnw (New York Open Live Q&A), own voice:
  "If you don't know what is going on ... Just wait five minutes. If you still don't,
   wait for 15. If you still don't, wait for 10:00 a.m."
  "If 9:30 move doesn't get a continuation, it's chopped. Wait for 10:00 a.m."
  "You just kind of wait for closures to tell you"

NOT re-tested: the UNCONDITIONAL deferral (5m CISD in [09:30,10:00) vs [10:00,10:30)) is
already entry-time-window b / u1007b (both NULL). New here: the CONDITIONAL, staged wait.
"Unreadable" in the source is correlated indices switching relative strength (NQ/ES/YM),
which gold-only data lacks, so it is replaced by a price-only proxy, one per reading:

  u1007a  the ladder, readability = a decisive CLOSURE at each step. Checkpoints: the first
          5m candle (09:30-09:35, closes 09:35) and the first 15m candle (09:30-09:45,
          closes 09:45). A checkpoint "reads" if it is an expansion candle:
          opposing_run/|body| <= 1.0 (threshold_fits small-wick cut, grade A); a doji never
          reads. Permitted: decision >= 10:00; or >= 09:35 and the 5m read; or >= 09:45
          and the 5m or 15m read. Forbidden: every other decision in [09:30, 10:00).
  u1007b  the companion chop rule. The 9:30 move = the first 5m candle's direction
          (doji -> no move). Continuation = a later 5m candle CLOSES beyond that candle's
          extreme in its direction (threshold_fits: structural displacement = close beyond,
          hard gate), checked at each 5m close before 10:00. Permitted: decision >= 10:00,
          or at/after the continuation close. Forbidden: decisions in [09:30, 10:00) with
          no continuation yet (so 09:30 and 09:35 always).

Baseline book (both readings): batch time_own_01a 5m bare CISD (phase-3 locked config,
2R, 50 min), decisions in [09:30, 10:30) NY — the same band as entry-time-window u1007b,
so the conditional element is the only change. Claim '+': permitted beats forbidden
(control-adjusted R). Direction is the baseline's: the rule says when, not which way.
Declared before any run. Clock: America/New_York with DST.

RERUN WITH VAULT CONTEXT (2026-10-07, readings u1007va / u1007vb; u1007a/b kept as-is):
In u1007a/b the permitted arm is 84% / 65% of rows and mostly post-10:00 decisions, which
the ladder permits unconditionally. Their diff therefore largely re-measures the
unconditional 10:00 deferral already tested NULL (entry-time-window u1007b; vault: do not
repeat a tested element as if new), and it mixes NY clock between the arms (vault Session
Timing on Gold: time of day buys opportunity, not accuracy). The new readings test ONLY
the staged condition, with both arms in the same pre-10:00 window:
  u1007va  ladder: band [09:35, 10:00) (a step has closed and the verdict depends on it).
           09:30 decisions (no step closed yet, always forbidden) and >= 10:00 (always
           permitted) are excluded. Same readability rule as u1007a.
  u1007vb  chop rule: band [09:40, 10:00) (a continuation close can exist). 09:30/09:35
           (always forbidden) and >= 10:00 (always permitted) excluded. Same continuation
           rule as u1007b.
The 09:30 anchor transfers to gold: vault Concept Campaign, the gold volatility step is
09:30 NY (73.6%, Holm). Declared before running u1007va/vb; u1007a/b results were seen
(both UNDERPOWERED), so the narrower band is not chosen for power: it lowers n.
Run: `python open-uncertainty-wait-ladder.py [reading ...]` (default u1007va u1007vb).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "time_own_01a"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import _common as C  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "open-uncertainty-wait-ladder"
TZ = "America/New_York"
WICK_CUT = 1.0
M930, M935, M945, M1000 = 570, 575, 585, 600
TZ_SRC = ("session_window_fit: America/New_York with DST (settled, 99.8% of 605 daily "
          "breaks resume at 18:00 NY)")


def _opening_bar(m1, tf):
    """The bar starting 09:30 NY for each NY date: o/h/l/c + close_time, indexed by date."""
    b = cl.build_bars(m1, tf)
    ny = b.index.tz_convert(TZ)
    sel = (ny.hour == 9) & (ny.minute == 30)
    out = b.loc[sel, ["open", "high", "low", "close", "close_time"]].copy()
    out.index = pd.DatetimeIndex(ny[sel].tz_localize(None).normalize())
    return out


def _reads(o, h, l, c):
    """Decisive closure: an expansion candle, opposing run (open -> extreme against the
    close) <= WICK_CUT x |body|. A doji (body 0) never reads."""
    body = c - o
    opp = np.where(body > 0, o - l, h - o)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (body != 0) & (opp <= WICK_CUT * np.abs(body))


BAND = ("09:30", "10:30")
BAND_VA = ("09:35", "10:00")
BAND_VB = ("09:40", "10:00")


def _band(ev, band=BAND):
    ev = ev[C.window_mask(ev["decision_time"], [band])].copy()
    t = pd.DatetimeIndex(ev["decision_time"])
    ev["_m"] = cl.ny_minute_of_day(t)
    ev["_d"] = pd.DatetimeIndex(t.tz_convert(TZ).tz_localize(None).normalize())
    return ev


def _finish(ev, keep):
    ev = ev[keep].drop(columns=["_m", "_d"])
    ev["permitted"] = ev["permitted"].astype(bool)
    return ev.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def gate_a(ev, m1, band=BAND):
    ev = _band(ev, band)
    c5, c15 = _opening_bar(m1, "5min"), _opening_bar(m1, "15min")
    m, d = ev["_m"].to_numpy(), ev["_d"]
    t = pd.DatetimeIndex(ev["decision_time"])
    r5 = pd.Series(_reads(*(c5[k].to_numpy(float) for k in "open high low close".split())),
                   index=c5.index)
    r15 = pd.Series(_reads(*(c15[k].to_numpy(float) for k in "open high low close".split())),
                    index=c15.index)
    has5 = d.isin(c5.index).to_numpy()
    has15 = d.isin(c15.index).to_numpy()
    R5 = r5.reindex(d).fillna(False).to_numpy(bool)
    R15 = r15.reindex(d).fillna(False).to_numpy(bool)
    ct5 = pd.DatetimeIndex(c5["close_time"].reindex(d))
    ct15 = pd.DatetimeIndex(c15["close_time"].reindex(d))
    early5 = (m >= M935) & (m < M945)        # 09:35, 09:40: only the 5m step has closed
    early15 = (m >= M945) & (m < M1000)      # 09:45..09:55: 5m and 15m steps closed
    permitted = (m >= M1000) | (early5 & R5) | (early15 & (R5 | R15))
    # "never evaluated" must not look like "passed": drop rows whose step is missing
    keep = ~((early5 & ~has5) | (early15 & ~(has5 & has15)))
    gate_at = t.tz_convert("UTC")
    gate_at = gate_at.where(~early5, ct5).where(~early15, ct15)
    ev["permitted"] = permitted
    ev["gate_at"] = pd.DatetimeIndex(gate_at).tz_convert("UTC")
    return _finish(ev, keep)


def _continuation_time(m1):
    """Per NY date: close_time of the first 5m candle (09:35..09:50 starts, closing before
    10:00) that closes beyond the 09:30 5m candle's extreme in its direction; NaT if none.
    Also returns the dates that have a 09:30 5m candle."""
    b = cl.build_bars(m1, "5min")
    ny = b.index.tz_convert(TZ)
    mod = ny.hour * 60 + ny.minute
    date = pd.DatetimeIndex(ny.tz_localize(None).normalize())
    first = _opening_bar(m1, "5min")
    sgn = np.sign(first["close"].to_numpy(float) - first["open"].to_numpy(float))
    ref = pd.DataFrame({"dir": sgn, "hi": first["high"].to_numpy(float),
                        "lo": first["low"].to_numpy(float)}, index=first.index)
    sel = (mod >= M935) & (mod < M1000 - 5)
    x = b.loc[sel, ["close", "close_time"]].copy()
    x["date"] = date[sel]
    x = x[x["date"].isin(ref.index)]
    r = ref.reindex(x["date"])
    cont = ((r["dir"].to_numpy() > 0) & (x["close"].to_numpy() > r["hi"].to_numpy())) | \
           ((r["dir"].to_numpy() < 0) & (x["close"].to_numpy() < r["lo"].to_numpy()))
    ct = x.loc[cont].groupby("date")["close_time"].min()
    return ct, ref.index


def gate_b(ev, m1, band=BAND):
    ev = _band(ev, band)
    ct, dates = _continuation_time(m1)
    m, d = ev["_m"].to_numpy(), ev["_d"]
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    cstar = pd.DatetimeIndex(ct.reindex(d)).tz_convert("UTC")
    mid = (m >= M935 + 5) & (m < M1000)      # 09:40..09:55: continuation can exist
    has = d.isin(dates).to_numpy()
    cont_by_t = (~cstar.isna()) & (cstar <= t)
    permitted = (m >= M1000) | (mid & np.asarray(cont_by_t))
    keep = ~(mid & ~has)
    gate_at = t.where(~(mid & np.asarray(cont_by_t)), cstar)
    ev["permitted"] = permitted
    ev["gate_at"] = pd.DatetimeIndex(gate_at).tz_convert("UTC")
    return _finish(ev, keep)


def detect_a(m1):
    return gate_a(C.cisd5(m1), m1)


def detect_b(m1):
    return gate_b(C.cisd5(m1), m1)


def detect_va(m1):
    return gate_a(C.cisd5(m1), m1, BAND_VA)


def detect_vb(m1):
    return gate_b(C.cisd5(m1), m1, BAND_VB)


BAND_SRC = ("declared-before-run: same band as entry-time-window u1007b ([09:30,10:30), "
            "equal 30-min arm after 10:00) so only the conditional element changes; corpus: "
            "rTomJ8URFnw 'Wait for 10:00 a.m.'")
COMMON_PARAMS = dict(C.BASE_PARAMS, band=[("09:30", "10:30")], deadline="10:00",
                     tz="America/New_York")
COMMON_SRC = dict(C.BASE_SRC, band=BAND_SRC,
                  deadline="corpus: rTomJ8URFnw 'If you still don't, wait for 10:00 a.m.'",
                  tz=TZ_SRC)

READINGS = {
    "u1007a": dict(
        detect=detect_a, frame=lambda: gate_a(C.base_cached(), cl.load_m1()),
        rules=["baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
               "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min "
               "exit; only decisions in [09:30, 10:30) New York",
               "ladder steps: first 5m candle 09:30-09:35 (closed 09:35), first 15m candle "
               "09:30-09:45 (closed 09:45); a step 'reads' if opposing_run/|body| <= 1.0 "
               "(expansion candle; doji never reads)",
               "gate (permitted): decision >= 10:00; or decision in [09:35, 09:45) and the 5m "
               "step read; or decision in [09:45, 10:00) and the 5m or 15m step read",
               "complement (forbidden): decisions in [09:30, 10:00) while no step so far has "
               "read (09:30 decisions always)",
               "rows whose consulted step candle is missing are dropped (not passed)"],
        params=dict(COMMON_PARAMS, step1="5min close 09:35", step2="15min close 09:45",
                    wick_cut=WICK_CUT),
        src=dict(COMMON_SRC,
                 step1="corpus: rTomJ8URFnw 'Just wait five minutes.'",
                 step2="corpus: rTomJ8URFnw 'If you still don't, wait for 15.'",
                 wick_cut="threshold_fits: small wick / expansion candle opposing_run/|body| "
                          "<= 1.0 (grade A); corpus rTomJ8URFnw 'wait for closures to tell "
                          "you' (readable = decisive closure)"),
        notes="Reading a: the staged ladder with readability = a decisive (expansion) closure "
              "of the 5m / 15m opening candle. Price-only proxy: the source's 'unreadable' is "
              "correlated indices switching strength, not available for gold."),
    "u1007b": dict(
        detect=detect_b, frame=lambda: gate_b(C.base_cached(), cl.load_m1()),
        rules=["baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
               "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min "
               "exit; only decisions in [09:30, 10:30) New York",
               "9:30 move = direction of the first 5m candle 09:30-09:35 (doji = no move)",
               "continuation = first later 5m candle (closing 09:40..09:55) whose close is "
               "beyond the 9:30 candle's high (up move) / low (down move)",
               "gate (permitted): decision >= 10:00, or decision at/after the continuation "
               "close",
               "complement (forbidden, 'chopped'): decisions in [09:30, 10:00) with no "
               "continuation yet (09:30 and 09:35 always)",
               "rows in [09:40, 10:00) on a date with no 09:30 5m candle are dropped"],
        params=dict(COMMON_PARAMS, move_bar="5min 09:30-09:35",
                    continuation="5m close beyond the 9:30 candle's extreme, before 10:00"),
        src=dict(COMMON_SRC,
                 move_bar="corpus: rTomJ8URFnw 'most people are probably better off waiting "
                          "5 minutes' (the 9:30 move is read on the first 5m close)",
                 continuation="corpus: rTomJ8URFnw 'If 9:30 move doesn't get a continuation, "
                              "it's chopped.'; threshold_fits: structural displacement = "
                              "candle closes beyond the reference level (hard gate, grade A)"),
        notes="Reading b: the companion chop rule. No distance/time threshold for "
              "'continuation' in the source; close beyond the opening 5m candle's extreme "
              "before 10:00 is the declared structural reading."),
}

VAULT_SRC = ("vault: Concept Campaign 2026-09-23 (gold volatility step is 09:30 NY, 73.6% "
             "Holm) for the 09:30 anchor; isolation from the unconditional 10:00 deferral "
             "already tested NULL (entry-time-window u1007b) and same-clock arms per vault "
             "Session Timing on Gold / Backtest Methodology Traps")
VAULT_NOTE = ("Rerun with vault context: tests ONLY the staged condition, both arms inside "
              "the pre-10:00 window; the unconditional 10:00 deferral (entry-time-window "
              "u1007b, NULL) and the always-forbidden first-5-minute rows are excluded. ")
_BASE_RULE = ("baseline: 5m bare CISD (series_open, 2/2 swings, max_wait 3), decide at the "
              "confirming 5m close, enter next M1 open, stop = protected swing, 2R, 50 min "
              "exit; only decisions in [{}, {}) New York")
READINGS["u1007va"] = dict(
    detect=detect_va, frame=lambda: gate_a(C.base_cached(), cl.load_m1(), BAND_VA),
    rules=[_BASE_RULE.format(*BAND_VA)] + READINGS["u1007a"]["rules"][1:3] + [
        "complement (forbidden): decisions in [09:35, 10:00) while no step so far has read",
        "excluded: 09:30 decisions (no step closed: always forbidden) and >= 10:00 (always "
        "permitted), so only the staged condition separates the arms",
        "rows whose consulted step candle is missing are dropped (not passed)"],
    params=dict(READINGS["u1007a"]["params"], band=[BAND_VA]),
    src=dict(READINGS["u1007a"]["src"],
             band="declared-before-run: [09:35, 10:00) = the minutes where a ladder step has "
                  "closed and the verdict depends on readability; " + VAULT_SRC),
    notes=VAULT_NOTE + READINGS["u1007a"]["notes"])
READINGS["u1007vb"] = dict(
    detect=detect_vb, frame=lambda: gate_b(C.base_cached(), cl.load_m1(), BAND_VB),
    rules=[_BASE_RULE.format(*BAND_VB)] + READINGS["u1007b"]["rules"][1:3] + [
        "gate (permitted): decision at/after the continuation close",
        "complement (forbidden, 'chopped'): decisions in [09:40, 10:00) with no continuation "
        "yet (doji 9:30 candle = no move = no continuation)",
        "excluded: 09:30/09:35 decisions (continuation impossible yet: always forbidden) and "
        ">= 10:00 (always permitted)",
        "rows on a date with no 09:30 5m candle are dropped"],
    params=dict(READINGS["u1007b"]["params"], band=[BAND_VB]),
    src=dict(READINGS["u1007b"]["src"],
             band="declared-before-run: [09:40, 10:00) = the minutes where a continuation "
                  "close can exist and the verdict depends on it; " + VAULT_SRC),
    notes=VAULT_NOTE + READINGS["u1007b"]["notes"])


if __name__ == "__main__":
    for rd in sys.argv[1:] or ["u1007va", "u1007vb"]:
        s = READINGS[rd]
        ev = s["frame"]()
        print(rd, "events", len(ev), "permitted share", round(float(ev["permitted"].mean()), 3),
              "forbidden n", int((~ev["permitted"]).sum()))
        probe = cl.probe_lookahead(s["detect"], ev, lookback="10D")
        print("  probe", probe.get("passed"))
        res = cl.gate_test(ev, "permitted", mask_available_at="gate_at",
                           max_hold=C.BASE_MAX_HOLD, claim="+")
        p = cl.write_result(CID, rd, res,
                            operationalization={"rules": s["rules"], "params": s["params"]},
                            params_source=s["src"], script=__file__, probe=probe,
                            notes="New concept (update_20261007_live_12), not yet in "
                                  "batches.json. " + s["notes"],
                            allow_unknown_id=True)
        print(rd, p)
        for k in ("n", "verdict", "verdict_detail", "diff", "ci_lo", "ci_hi", "p", "mde",
                  "ties", "halves", "gate"):
            print("  ", k, res.get(k))
