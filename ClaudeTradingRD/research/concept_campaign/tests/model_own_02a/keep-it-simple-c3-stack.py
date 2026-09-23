"""keep-it-simple-c3-stack — trade test of the stacked-candle-3 model, both stated routes.

Day filter (both routes): the previous daily candle is a C2 closure in the direction AND an
hourly CISD in the same direction confirmed inside that daily candle (method_spec §2.4
'daily C2 closure + hourly CISD') -> today is the daily candle 3; trade only that side.
  a  4H route: a 4H C2 closure in the direction closes inside today (POI NOT required);
     trade the next 4H candle (the 4H C3): 15m CISD in the direction confirmed inside it.
  b  1H route: a 1H C2 closure in the direction closes inside today AND its sweep is at a
     point of interest (it took out an untaken, confirmed 1H 2/2 swing low/high, or traded
     into an untouched 1H FVG, both from the prior 72 1H bars = the 3-HTF-candle look-back);
     trade the next 1H candle (the 1H C3): 5m CISD in the direction confirmed inside it.
Execution: first CISD per C3 candle; enter next M1 open; stop = protected swing; 2R;
hold to the close of the C3 candle the trade runs inside (§5.5).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, c2_flags, containing, in_progress, last_closed, swings, fvgs, utc  # noqa: E402

CID = "keep-it-simple-c3-stack"
POI_LOOKBACK = 72


def poi_flags(b):
    """Per bar: its C2 sweep hit a POI (bull side, bear side)."""
    bull2, bear2 = c2_flags(b)
    lo, hi = b["low"].to_numpy(), b["high"].to_numpy()
    sh, sl, known = swings(b)
    st = cl.data.utc_ns(utc(b.index)).astype("int64")
    fv = fvgs(b)
    fv_known = cl.data.utc_ns(utc(fv["known_at"])).astype("int64") if len(fv) else np.array([], np.int64)
    n = len(b)
    pb = np.zeros(n, bool)
    pr = np.zeros(n, bool)
    for i in np.flatnonzero(bull2 | bear2):
        a = max(0, i - POI_LOOKBACK)
        for side, flag in ((1, bull2[i]), (-1, bear2[i])):
            if not flag:
                continue
            hit = False
            # (i) untaken confirmed swing extreme swept by bar i
            cand = np.flatnonzero((sl if side > 0 else sh)[a:i]) + a
            for s in cand[::-1]:
                if known[s] < 0 or known[s] > st[i]:
                    continue
                if side > 0:
                    if lo[i] < lo[s] and (s + 1 > i - 1 or lo[s + 1:i].min() >= lo[s]):
                        hit = True
                        break
                else:
                    if hi[i] > hi[s] and (s + 1 > i - 1 or hi[s + 1:i].max() <= hi[s]):
                        hit = True
                        break
            # (ii) untouched same-side FVG traded into by bar i
            if not hit and len(fv):
                sel = np.flatnonzero((fv["direction"].to_numpy() == side)
                                     & (fv["mid_pos"].to_numpy() >= a)
                                     & (fv_known <= st[i]))
                for q in sel[::-1]:
                    m = int(fv["mid_pos"].iloc[q]) + 2          # first bar after known
                    top, bot = fv["top"].iloc[q], fv["bottom"].iloc[q]
                    if side > 0:
                        untouched = m > i - 1 or lo[m:i].min() > top
                        if untouched and lo[i] <= top:
                            hit = True
                            break
                    else:
                        untouched = m > i - 1 or hi[m:i].max() < bot
                        if untouched and hi[i] >= bot:
                            hit = True
                            break
            if side > 0:
                pb[i] = hit
            else:
                pr[i] = hit
    return pb, pr


def detect_route(m1, route):
    bd = cl.build_bars(m1, "1D")
    b1 = cl.build_bars(m1, "1h")
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    if route == "4h":
        bs = cl.build_bars(m1, "4h", grid4h="forex")
        be = cl.build_bars(m1, "15min")
    else:
        bs = b1
        be = cl.build_bars(m1, "5min")
    ev = cisd(be, max_wait=3)
    if ev.empty or len(bd) < 3:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    # day bias: prev daily C2 in direction + 1H CISD in direction inside that day
    h1 = cisd(b1, max_wait=3)
    hday = containing(bd, h1["decision_time"])
    conf = set(zip(hday.tolist(), h1["direction"].tolist()))
    bull_d, bear_d = c2_flags(bd)
    pday = in_progress(bd, t)
    pc = np.clip(pday, 1, None)
    ok = pday >= 2
    ok &= np.where(d > 0, bull_d[pc - 1], bear_d[pc - 1])
    ok &= np.array([(p - 1, x) in conf for p, x in zip(pday.tolist(), d.tolist())])
    # structure: C2 at k-1 on the structure TF, inside today; trade inside candle k (C3)
    # kp = last CLOSED structure bar (must be the C2); the entry trades in the candle after
    kp = last_closed(bs, t)
    ok &= kp >= 1
    kc = np.clip(kp, 0, None)
    bull_s, bear_s = c2_flags(bs)
    if route == "1h":
        pb, pr = poi_flags(bs)
        bull_s, bear_s = bull_s & pb, bear_s & pr
    ok &= np.where(d > 0, bull_s[kc], bear_s[kc])
    kp_close = utc(bs["close_time"].to_numpy())[kc]
    ok &= kp_close.asi8 > utc(bd.index)[pc].asi8                      # C2 closes inside today
    k_close = kp_close + pd.Timedelta("4h" if route == "4h" else "1h")  # C3 nominal close
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ev["stop_px"].to_numpy(), "rr": 2.0,
                        "max_hold": pd.Series(k_close - utc(t)).to_numpy(), "_k": kp})[ok]
    out = out.sort_values("decision_time").drop_duplicates("_k", keep="first")
    return out.drop(columns="_k").reset_index(drop=True)


def detect_a(m1):
    return detect_route(m1, "4h")


def detect_b(m1):
    return detect_route(m1, "1h")


COMMON_RULES = [
    "daily = 18:00 NY trading day; 4H forex grid; 1H/15m/5m UTC-aligned",
    "C2 closure: bull low<prev low & close>prev low (mirror) — method_spec §3.2",
    "CISD everywhere: series_open, 2/2 swing, max_wait 3 (detectors.cisd)",
    "day filter: previous daily candle is a C2 in the direction AND a 1H CISD in the same "
    "direction confirmed inside that daily candle -> today = daily C3, trade that side only",
    "first CISD per C3 candle; enter next M1 open; stop = protected swing; 2R; hold to the "
    "close of the structure-TF C3 candle"]
COMMON_SRC = {
    "level_rule": "method_spec: §4.2 first-candle-open default",
    "max_wait": "phase3: locked config max_wait=3",
    "rr": "corpus: q3nauvjT3q0 (concept execution.targets '2R minimum'); method_spec §5.3",
    "max_hold": "method_spec: §5.5 time-based exit at the HTF (C3) candle close",
    "one_per_c3": "declared-before-run: one entry per C3 candle ('enter on a continuation "
                  "inside candle 3')",
    "grid4h": "session_window_fit: forex grid for gold",
    "day_open_hour": "method_spec: §1.4 18:00 canon",
    "day_bias": "corpus: q3nauvjT3q0 'Daily candle 2 closure + hourly CISD' / method_spec §2.4"}
COMMON_PARAMS = {"level_rule": "series_open", "max_wait": 3, "rr": 2.0,
                 "max_hold": "to C3 candle close", "one_per_c3": True, "grid4h": "forex",
                 "day_open_hour": 18, "day_bias": "D C2 + H1 CISD inside it"}


def run(reading, fn, key):
    ev = cl.cache_frame(key, lambda: fn(cl.load_m1()))
    print(reading, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(fn, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "verdict",
                                    "verdict_detail", "exposure_bars")})
    return res, probe


def main(only=None):
  if only in (None, "a"):
    res, probe = run("a", detect_a, "kis_4h_route_v2")
    op = {"rules": COMMON_RULES + [
        "route a (4H): a 4H C2 closure in the direction, closing inside today, NO point of "
        "interest required; trade the next 4H candle; entry = 15m CISD inside it"],
        "params": {**COMMON_PARAMS, "structure_tf": "4h", "entry_tf": "15min", "poi": False}}
    src = {**COMMON_SRC,
           "structure_tf": "corpus: q3nauvjT3q0 4-hour route; method_spec §1.2 4H->15m pair",
           "entry_tf": "method_spec: §1.2 pairing 4H->15m",
           "poi": "corpus: q3nauvjT3q0 'on the 4-hour a point of interest is NOT required'"}
    print("wrote", cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="4H route of the stated model; trade_test vs matched "
                                         "random entries."))
  if only in (None, "b"):
    res, probe = run("b", detect_b, "kis_1h_route_v2")
    op = {"rules": COMMON_RULES + [
        "route b (1H): a 1H C2 closure in the direction, closing inside today, whose sweep is "
        "at a POI: it took out a confirmed, still-untaken 1H 2/2 swing extreme, or traded into "
        "a still-untouched same-side 1H FVG, both from the prior 72 1H bars; trade the next 1H "
        "candle; entry = 5m CISD inside it"],
        "params": {**COMMON_PARAMS, "structure_tf": "1h", "entry_tf": "5min", "poi": True,
                   "poi_lookback_bars": POI_LOOKBACK}}
    src = {**COMMON_SRC,
           "structure_tf": "corpus: q3nauvjT3q0 hourly route; method_spec §1.2 1H->5m pair",
           "entry_tf": "method_spec: §1.2 pairing 1H->5m",
           "poi": "corpus: q3nauvjT3q0 hourly requires a point of interest; method_spec §4.1 "
                  "(FVG or a high/low taken out)",
           "poi_lookback_bars": "method_spec: §1.1 relevant-swing look-back = three HTF "
                                "candles (hourly chart -> three days)"}
    print("wrote", cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="1H route of the stated model; trade_test vs matched "
                                         "random entries."))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
