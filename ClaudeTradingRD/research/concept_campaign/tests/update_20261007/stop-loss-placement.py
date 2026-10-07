"""update_20261007 / stop-loss-placement — NEW claim only (prior reading 'a', wick vs body, untouched).

Source (live_06, uW55Tuk-ngY): "Why you not put your stop loss on the protected high? ...
I'm not even getting 2 R. Not worth it for me. And my thing is is if we're going to have a
reversal on this day, I don't want to see it go above the EQ anyways, right? So, I just put
it above the EQ." / "price can go up and tap into it ... I don't want to see price go over
or disrespect the EQ" / "I've already accepted the fact that if price goes up here, I lose
money ... That's what the stop loss is for." (no management short of the stop).

Book: 1h rung-0 CISD (he trades "the daily and hourly"), entry next M1 open. Draw = the
prior day's extreme in the trade direction (PDL for shorts, PDH for longs: the daily
reversal's target), kept only if beyond entry. Condition: R with the stop at the protected
swing < 2 AND R with the EQ stop >= 2 (AUDIT 2026-10-07: the same "not worth it" 2R floor
gates the trade he does take; "It's like five R" — the prior run scored EQ trades down to
0.47R, which the source's own floor rejects). EQ = 50% of the reversal leg = midpoint of the protected swing and the farthest
price reached from the swing bar through the confirm bar. EQ stop sits AT that midpoint
(no buffer is stated); rows whose EQ is not strictly between entry and swing are dropped.
No management: stop, target or 10h time exit only.

u1007a: trade_test of the EQ-stop trades vs matched random entries. claim "+".
u1007b: same entries scored twice (EQ stop = gated, protected-swing stop = complement,
        same target price); gate_test claim "+" (EQ stop is the better placement).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/risk_own_01a")
from _base import cl, np, pd, cisd_events, CISD_KW, PHASE3_SRC, first_open_at_or_after  # noqa: E402

CID = "stop-loss-placement"
HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "eq_stop"]


def setups(m1):
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], **CISD_KW)
    if ev.empty:
        return None
    t = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    s = np.where(ev["direction"] == "bullish", 1, -1)
    swing = ev["protected_swing"].to_numpy(float)
    pos = pd.Index(b.index)
    a = pos.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    c = pos.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    hi, lo = b["high"].to_numpy(float), b["low"].to_numpy(float)
    far = np.array([hi[a[k]:c[k] + 1].max() if s[k] > 0 else lo[a[k]:c[k] + 1].min()
                    for k in range(len(ev))])
    eq = (swing + far) / 2
    entry = ev["confirm_close"].to_numpy(float)   # known at decision; harness fills at next M1 open
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    tgt = np.where(s > 0, pd_["high"].to_numpy(float), pd_["low"].to_numpy(float))
    reward = s * (tgt - entry)
    r_swing = reward / (s * (entry - swing))
    r_eq = reward / (s * (entry - eq))
    ok = (np.isfinite(reward) & (reward > 0) & (s * (entry - swing) > 0) & (r_swing < 2)
          & (s * (entry - eq) > 0) & (s * (eq - swing) > 0) & (r_eq >= 2))
    return pd.DataFrame({"decision_time": t.tz_convert("UTC"), "available_at": t.tz_convert("UTC"), "direction": s,
                         "swing": swing, "eq": eq, "target_px": tgt})[ok].reset_index(drop=True)


def detect_a(m1):
    x = setups(m1)
    if x is None or x.empty:
        return pd.DataFrame(columns=COLS[:-1])
    return x.assign(stop_px=x["eq"])[COLS[:-1]]


def detect_b(m1):
    x = setups(m1)
    if x is None or x.empty:
        return pd.DataFrame(columns=COLS)
    g = x.assign(stop_px=x["eq"], eq_stop=True)
    c = x.assign(stop_px=x["swing"], eq_stop=False)
    return pd.concat([g, c]).sort_values(["decision_time", "eq_stop"], kind="stable") \
        .reset_index(drop=True)[COLS]


RULES = [
    "entries: 1h CISD (series_open, 2/2 swings, max_wait 3), decide at the confirming bar close, enter next M1 open",
    "target: prior completed trading day's high (long) / low (short), min_coverage 0.5; must lie beyond the confirm close",
    "condition: R with the stop at the protected swing (wick extreme) < 2 and R with the EQ stop >= 2 (the same 2R floor gates the trade taken), both measured from the confirm close (the decision-time price; fill is the next M1 open)",
    "EQ = midpoint of the protected swing and the farthest price from it over swing bar..confirm bar (reversal leg); EQ stop placed at EQ; rows with EQ not strictly between the confirm close and swing dropped",
    "no management short of the stop: exit only at stop, target or 10h",
]
PARAMS = {"tf": "1h", "max_hold": HOLD, "target": "PDH/PDL", "rr_floor": 2.0,
          "eq_leg": "protected swing -> farthest extreme through confirm bar", "eq_buffer": 0.0,
          "grid4h": "n/a (no 4h bars)", "pd_min_coverage": 0.5}
SRC = {"tf": "corpus: uW55Tuk-ngY 'I use the daily and hourly uh for myself'; " + PHASE3_SRC,
       "max_hold": PHASE3_SRC,
       "target": "declared-before-run: draw for a daily reversal ('a reversal on this day') = prior day's opposite extreme; the chart draw is not stated",
       "rr_floor": "corpus: uW55Tuk-ngY 'I'm not even getting 2 R. Not worth it for me.' + 'It's like five R.' (floor applies to the swing placement rejected AND the EQ trade taken)",
       "eq_leg": "declared-before-run: draft ambiguity (daily candle vs reversal leg vs swing); the reversal leg on the entry TF is the draft's rule text",
       "eq_buffer": "corpus: uW55Tuk-ngY 'So, I just put it above the EQ.' (no buffer stated)",
       "grid4h": "declared-before-run: no 4h bars used",
       "pd_min_coverage": "declared-before-run: README trap 6 stub-session skip"}


def show(res):
    print({k: res.get(k) for k in ("n", "n_complement", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
                                   "verdict_detail", "ties", "exposure_bars", "ctrl_overlap")})


if __name__ == "__main__":
    ea = cl.cache_frame("slp_u1007_eq_trades_eqfloor2", lambda: detect_a(cl.load_m1()))
    print("a rows", len(ea))
    pa = cl.probe_lookahead(detect_a, ea, lookback="20D")
    ra = cl.trade_test(ea, max_hold=HOLD, claim="+")
    show(ra)
    print("wrote", cl.write_result(CID, "u1007a", ra,
          operationalization={"rules": RULES + ["test: EQ-stop trades vs matched random-entry control, claim +"],
                              "params": PARAMS}, params_source=SRC, script=__file__, probe=pa,
          notes="New claim only (EQ alternative when swing stop < 2R). Prior reading 'a' untouched. AUDIT 2026-10-07 (vault context): fixed — EQ trades below the source's own 2R floor (prior run median EQ RR 2.07, q10 0.47) are no longer scored."))

    eb = cl.cache_frame("slp_u1007_eq_vs_swing_eqfloor2", lambda: detect_b(cl.load_m1()))
    print("b rows", len(eb))
    pb = cl.probe_lookahead(detect_b, eb, lookback="20D")
    rb = cl.gate_test(eb, "eq_stop", mask_available_at="decision_time", max_hold=HOLD, claim="+")
    show(rb)
    print("wrote", cl.write_result(CID, "u1007b", rb,
          operationalization={"rules": RULES + ["test: same entries stacked; gated = EQ stop, complement = protected-swing stop, same target price; claim + (EQ better)"],
                              "params": PARAMS}, params_source=SRC, script=__file__, probe=pb,
          notes="Stacked variant rows on identical entries; each arm adjusted by its own geometry-matched control. AUDIT 2026-10-07 (vault context): fixed — entries restricted to those whose EQ stop clears the source's 2R floor."))
