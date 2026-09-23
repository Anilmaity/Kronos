"""continuation-failure-short-term-target — "scenario two": a continuation whose
closure also takes out a short-term high/low (or whose objective is already hit) is
not tradeable as-is. Claim: those setups are WORSE than the rest ('-').

Baseline book (both readings): the phase-3 bare 15m CISD (series_open, 2/2 swings,
max_wait 3, stop at the protected swing, 2R, 150 min hold), entered at the next M1
open after the confirming bar closes.

Reading a: gate = the confirming 15m bar takes out the most recent confirmed
           short-term swing extreme on the entry side (bullish: a 2/2 swing high
           still unbroken until that bar) — "taking out that short-term high at
           the same time".
Reading b: gate = the day's nearest objective is already taken before the
           decision (long: today's high so far > previous day high; short: low so
           far < previous day low) — "short-term target already reached".
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

CID = "continuation-failure-short-term-target"
TF, MAXW, RR, HOLD = "15min", 3, 2.0, "150min"


def _base(m1):
    b = cl.build_bars(m1, TF)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=MAXW, min_series=1)
    return b, ev


def detect_a(m1):
    b, ev = _base(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "takes_st"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
    hi, lo = b["high"].to_numpy(), b["low"].to_numpy()
    pos_of = {t: i for i, t in enumerate(b.index)}
    sh = np.flatnonzero(sw["swing_high"].to_numpy())
    sl = np.flatnonzero(sw["swing_low"].to_numpy())
    takes = []
    for _, r in ev.iterrows():
        j = pos_of[r["confirm_time"]]
        bull = r["direction"] == "bullish"
        cand = sh if bull else sl
        cand = cand[cand + 2 < j]            # confirmed (right=2) strictly before bar j
        if len(cand) == 0:
            takes.append(False); continue
        k = cand[-1]
        lvl = hi[k] if bull else lo[k]
        between = hi[k + 1:j] if bull else lo[k + 1:j]
        already = (between > lvl).any() if bull else (between < lvl).any()
        now = hi[j] > lvl if bull else lo[j] < lvl
        takes.append(bool(now and not already))
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    return pd.DataFrame({"decision_time": close, "available_at": close,
                         "direction": np.where(ev["direction"] == "bullish", 1, -1),
                         "stop_px": ev["protected_swing"].to_numpy(), "rr": RR,
                         "takes_st": np.array(takes, dtype=bool)})


def detect_b(m1):
    b, ev = _base(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "obj_taken"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    d = cl.build_bars(m1, "1D")
    prev = cl.asof(d, close)                       # last COMPLETED day at decision
    # today's extremes so far: 15m bars of the current trading day closed by decision
    bb = b.copy()
    bb["tday"] = cl.trading_day(bb.index)
    bb["run_hi"] = bb.groupby("tday")["high"].cummax()
    bb["run_lo"] = bb.groupby("tday")["low"].cummin()
    cur = bb.loc[ev["confirm_time"]]
    same_day = cl.trading_day(close - pd.Timedelta(minutes=1)) == cur["tday"].to_numpy()
    bull = (ev["direction"] == "bullish").to_numpy()
    pdh, pdl = prev["high"].to_numpy(), prev["low"].to_numpy()
    taken = np.where(bull, cur["run_hi"].to_numpy() > pdh, cur["run_lo"].to_numpy() < pdl)
    ok = ~np.isnan(pdh) & same_day
    out = pd.DataFrame({"decision_time": close, "available_at": close,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": RR,
                        "obj_taken": taken.astype(bool)})
    return out[ok].reset_index(drop=True)


BASE_RULES = ["baseline: 15m bars (UTC-aligned); CISD = close through the open of the first candle of the opposing series into a 2/2 fractal swing, within 3 bars",
              "decide at the confirming bar's close; enter next M1 open; stop at the protected swing; target 2R; exit after 150 min"]
BASE_PARAMS = {"tf": TF, "level_rule": "series_open", "swing": "2/2", "max_wait": MAXW,
               "rr": RR, "max_hold": HOLD}
BASE_SRC = {k: "phase3: meta/conjunction_preregistration.md locked bare-CISD config (15m stack)"
            for k in BASE_PARAMS}
BASE_SRC["tf"] = "corpus: concept timeframes.ltf includes 15m; phase3 15m entry stack"


def main():
    ev = cl.cache_frame("cfst_a_v1", lambda: detect_a(cl.load_m1()))
    print("a", len(ev), ev["takes_st"].mean())
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.gate_test(ev, "takes_st", mask_available_at="decision_time", max_hold=HOLD,
                       claim="-")
    print({k: res.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars")})
    op = {"rules": BASE_RULES + [
        "gate: the confirming 15m bar trades beyond the most recent confirmed 2/2 swing extreme on the entry side (swing high for longs, low for shorts) that had not been exceeded since it formed",
        "claim '-': gated (short-term extreme taken by the closure) trades are worse than the rest"],
        "params": {**BASE_PARAMS, "short_term_extreme": "latest confirmed 2/2 fractal swing on the entry side, unbroken until the closure bar"}}
    src = {**BASE_SRC, "short_term_extreme": "declared-before-run: 'short-term high' unbounded in corpus (51cZ-2QlZaI); nearest unbroken fractal swing = 'an actual high'"}
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Gate is known at the confirming bar's close (decision_time)."))

    evb = cl.cache_frame("cfst_b_v1", lambda: detect_b(cl.load_m1()))
    print("b", len(evb), evb["obj_taken"].mean())
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="10D")
    resb = cl.gate_test(evb, "obj_taken", mask_available_at="decision_time", max_hold=HOLD,
                        claim="-")
    print({k: resb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars")})
    opb = {"rules": BASE_RULES + [
        "objective = previous trading day's high (longs) / low (shorts), day rolling 18:00 NY",
        "gate: that objective was already traded through earlier in the current trading day, up to the decision bar's close",
        "claim '-': setups whose objective is already taken are worse"],
        "params": {**BASE_PARAMS, "objective": "previous day high/low", "day_open_hour": 18}}
    srcb = {**BASE_SRC, "objective": "corpus: yaml variant 2 'nearest objective (opposite side of the range, previous day high/low)'",
            "day_open_hour": "method_spec: §1.4 daily open 18:00 NY"}
    print(cl.write_result(CID, "b", resb, operationalization=opb, params_source=srcb,
                          script=__file__, probe=probe_b,
                          notes="Events whose confirming bar straddles the daily roll are dropped."))


if __name__ == "__main__":
    main()
