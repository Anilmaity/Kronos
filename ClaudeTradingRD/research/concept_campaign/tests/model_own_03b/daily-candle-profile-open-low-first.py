"""daily-candle-profile-open-low-first — after an ideal daily C2 closure, the next
(bullish) day is expected to open, trade lower first, respect the previous day's EQ,
then trade through the previous day's high (bearish mirror).

Reading a (definition 1, the three-mark chart): trade it. On a C3 day, when price
  first trades below the 18:00 open (while still above the EQ, before 10:30 NY),
  buy; stop = the previous day's EQ (respect the EQ); target = previous day high.
Reading b (definition 2, the timing cut): the day's low must form before ~10:30 NY.
  Gate test on the book of bias-direction 15m CISDs that turn on the day's
  extreme so far: gated = that extreme formed before 10:30 NY. Claim '+'.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events

CID = "daily-candle-profile-open-low-first"
CUTOFF = "10:30"


def _daily(m1):
    d = cl.build_bars(m1, "1D")
    d = d[d["n_m1"] >= 600].copy()
    h, l, c = d["high"], d["low"], d["close"]
    ph, pl = h.shift(1), l.shift(1)
    bull = (l < pl) & (c > pl)
    bear = (h > ph) & (c < ph)
    c2 = pd.Series(0, index=d.index)
    c2[bull & ~bear] = 1
    c2[bear & ~bull] = -1
    d["c2"] = c2
    d["eq"] = (h + l) / 2
    return d


def detect_a(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    d = _daily(m1)
    mm = m1[["open", "high", "low", "close"]]
    idx = pd.DatetimeIndex(mm.index)
    tday = pd.DatetimeIndex(cl.trading_day(idx)).as_unit("ns").asi8
    rows = []
    dtd = pd.DatetimeIndex(d["trading_day"]).as_unit("ns").asi8         # completed non-stub sessions
    for tdn in np.unique(tday):
        k = np.searchsorted(dtd, tdn, "left") - 1            # last non-stub day before today
        if k < 0:
            continue
        y = d.iloc[k]
        if y["c2"] == 0:
            continue
        td = pd.Timestamp(tdn)
        s0, s1 = np.searchsorted(tday, tdn, "left"), np.searchsorted(tday, tdn, "right")
        if s1 <= s0:
            continue
        o_day = float(mm["open"].iloc[s0])
        eq, dirn = float(y["eq"]), int(y["c2"])
        tgt = float(y["high"] if dirn == 1 else y["low"])
        if dirn == 1 and not (eq < o_day < tgt):
            continue
        if dirn == -1 and not (tgt < o_day < eq):
            continue
        seg = mm.iloc[s0:s1]
        hit = (seg["low"].to_numpy() < o_day) if dirn == 1 else (seg["high"].to_numpy() > o_day)
        pos = np.flatnonzero(hit)
        if len(pos) == 0:
            continue
        j = pos[0]
        bar = seg.iloc[j]
        # still respecting the EQ and not yet through the objective at the decision bar
        if dirn == 1 and not (bar["low"] > eq and seg["high"].iloc[:j + 1].max() < tgt):
            continue
        if dirn == -1 and not (bar["high"] < eq and seg["low"].iloc[:j + 1].min() > tgt):
            continue
        t = seg.index[j] + pd.Timedelta(minutes=1)          # M1 bar close
        loc = t.tz_convert("America/New_York")
        if not cl.in_window(pd.DatetimeIndex([t]), "18:00", CUTOFF)[0]:
            continue
        sess_end = (pd.Timestamp(td).tz_localize("America/New_York")
                    + pd.Timedelta(days=1, hours=17)).tz_convert("UTC")
        rows.append({"decision_time": t, "available_at": t, "direction": dirn,
                     "stop_px": eq, "target_px": tgt, "max_hold": sess_end - t})
    out = pd.DataFrame(rows, columns=cols)
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = pd.to_datetime(out["available_at"], utc=True)
    out["max_hold"] = pd.to_timedelta(out["max_hold"])
    return out


def detect_b(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "early_ext"]
    d = _daily(m1)
    b = cl.build_bars(m1, "15min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    y = cl.asof(d, close)
    bias = np.nan_to_num(y["c2"].to_numpy(dtype=float))
    dirn = np.where(ev["direction"] == "bullish", 1, -1)
    bb = b[["high", "low"]].copy()
    bb["tday"] = cl.trading_day(bb.index)
    bb["run_hi"] = bb.groupby("tday")["high"].cummax()
    bb["run_lo"] = bb.groupby("tday")["low"].cummin()
    cur = bb.loc[ev["confirm_time"]]
    ext_t = pd.DatetimeIndex(ev["extreme_time"])
    same_day = cl.trading_day(ext_t) == cur["tday"].to_numpy()
    is_dx = np.where(dirn == 1, ev["protected_swing"].to_numpy() <= cur["run_lo"].to_numpy(),
                     ev["protected_swing"].to_numpy() >= cur["run_hi"].to_numpy())
    keep = (bias == dirn) & same_day & is_dx
    early = cl.in_window(ext_t, "18:00", CUTOFF)
    out = pd.DataFrame({"decision_time": close, "available_at": close, "direction": dirn,
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0,
                        "early_ext": early.astype(bool)})
    return out[keep].reset_index(drop=True)


def main(which=("a", "b")):
  if "a" in which:
    ev = cl.cache_frame("dcpolf_a_v1", lambda: detect_a(cl.load_m1()))
    print("a", len(ev))
    probe = cl.probe_lookahead(detect_a, ev, lookback="10D")
    res = cl.trade_test(ev, claim="+", hold_basis="bars")
    print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "daily bars roll 18:00 NY, stub sessions (<600 M1) skipped; bias = yesterday's daily C2 closure (bull: low < prior low, close > prior low; bear mirror; two-sided = none)",
        "marks: previous day high, low and EQ = (high+low)/2",
        "bull day requires EQ < today's 18:00 open < PDH (mirror for bear)",
        "decision = close of the first M1 bar that trades below the open (trade lower first), provided that bar stays above the EQ and PDH not yet taken; only if decided 18:00-10:30 NY",
        "long at next M1 open; stop = EQ (respect the EQ); target = PDH; exit at the session end 17:00 NY"],
        "params": {"bias": "previous-day C2 closure", "open": "18:00 NY daily open", "stop": "previous-day EQ",
                   "target": "previous-day high/low", "cutoff": CUTOFF, "max_hold": "to 17:00 NY session end",
                   "hold_basis": "bars"}}
    src = {"bias": "corpus: a6s8N_WciY4 'this is an ideal candle to closure' (C2)",
           "open": "method_spec: §1.4 daily open 18:00 canon (the Short does not say which open)",
           "stop": "corpus: a6s8N_WciY4 'trade lower first, respect the EQ'",
           "target": "corpus: a6s8N_WciY4 'trades higher through the previous day high'",
           "cutoff": "corpus: yaml variant 2 'low of day formed after roughly 10:30 is not accepted'",
           "max_hold": "declared-before-run: a one-day profile, flat at the session end",
           "hold_basis": "declared-before-run: README trap 7 - first (clock) run showed real/control exposure 1350 vs 1173 bars (>10%), so rerun in trading time as the README prescribes"}
    print(cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Rerun once with hold_basis='bars' per README trap 7 (clock run: n=675, diff -0.068 [-0.156,+0.026] UNDERPOWERED, exposure gap 15%)."))

  if "b" in which:
    evb = cl.cache_frame("dcpolf_b_v1", lambda: detect_b(cl.load_m1()))
    print("b", len(evb), evb["early_ext"].mean())
    probe_b = cl.probe_lookahead(detect_b, evb, lookback="10D")
    resb = cl.gate_test(evb, "early_ext", mask_available_at="decision_time", max_hold="150min",
                        claim="+")
    print({k: resb.get(k) for k in ("n", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "exposure_bars", "ties")})
    opb = {"rules": [
        "bias = yesterday's daily C2 closure (as reading a)",
        "baseline: 15m bare CISDs (series_open, 2/2, max_wait 3) in the bias direction whose protected swing is the trading day's extreme so far (a low-of-day turn for longs), swing inside today's session",
        "enter next M1 open after the confirming bar; stop = protected swing; 2R; 150 min",
        "gate: that day extreme formed 18:00-10:30 NY (before the cutoff); complement = formed after 10:30",
        "claim '+': early-formed day extremes give better trades"],
        "params": {"bias": "previous-day C2 closure", "cutoff": CUTOFF, "tf": "15min",
                   "cisd": "series_open 2/2 max_wait 3", "rr": 2.0, "max_hold": "150min"}}
    srcb = {"bias": "corpus: a6s8N_WciY4 'ideal candle to closure'",
            "cutoff": "corpus: yaml variant 2 'probably around 10:30' (NY)",
            "tf": "corpus: concept timeframes.ltf 15m",
            "cisd": "phase3: locked bare-CISD config",
            "rr": "phase3: locked 2R", "max_hold": "phase3: 10 entry-TF bars"}
    print(cl.write_result(CID, "b", resb, operationalization=opb, params_source=srcb,
                          script=__file__, probe=probe_b))


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("a", "b"))
