"""upper-half-eq-expansion-filter — gate_test, two readings (contested: wick vs close).

Concept: when price is expanding, the next candle must make its LOW in the upper half of
the previous candle's range (bearish: its high in the lower half) and then expand; enter
inside the required half after a lower-timeframe CISD, stop on the low, 2R. A violation of
the EQ disqualifies the candle as an expansion candle.

Baseline book (stated): 1h CISDs (phase-3 rung-0 config) during a daily candle, taken in the
direction of the PREVIOUS daily candle's close (bullish close -> longs; "when price is
expanding" = the reference candle closed in the direction). Decide at the CISD close, stop =
protected swing, target 2R (the 4th-day worked example), hold 10 x 1h.
EQ = 50% of the previous day's wick-to-wick range (method_spec §3.7: 'wick high to wick low,
not bodies').
Readings (the YAML: "whether 'respected' means no wick through the 50% level or no CLOSE
through it is not stated"):
  (a) wick  — the day's running low (M1, up to the decision) is >= EQ (bearish: high <= EQ)
  (b) close — no 1h close of the day so far (through the confirming bar) is below EQ
claim '+': entries while the required half holds beat entries after it failed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ns, empty, cisd_frame, M1, PHASE3_SRC  # noqa: E402

CID = "upper-half-eq-expansion-filter"
HTF, LTF, HOLD, RR, MIN_M1 = "1D", "1h", "10h", 2.0, 690
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "eq_wick", "eq_close"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    d = cl.build_bars(m1, HTF)
    lb = cl.build_bars(m1, LTF)
    if len(d) < 3 or len(lb) < 20:
        return empty(COLS)
    ev = cisd_frame(lb)
    if ev.empty:
        return empty(COLS)
    dst, dct = ns(d.index), ns(d["close_time"])
    do, dh, dl, dc = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    dn = d["n_m1"].to_numpy()
    lst, lct = ns(lb.index), ns(lb["close_time"])
    lc = lb["close"].to_numpy(float)
    m = M1(m1)
    rows = []
    for r in ev.itertuples(index=False):
        cp = int(r.conf_pos)
        k = int(np.searchsorted(dst, lst[cp], "right") - 1)
        if k < 1 or lst[cp] >= dct[k] or dn[k - 1] < MIN_M1:
            continue
        pdir = np.sign(dc[k - 1] - do[k - 1])
        if pdir != r.sgn:
            continue                                   # only in the previous candle's direction
        eq = 0.5 * (dh[k - 1] + dl[k - 1])
        tconf = int(lct[cp])
        a = int(np.searchsorted(m.t, dst[k], "left"))
        z = int(np.searchsorted(m.t, tconf, "left"))
        if z <= a:
            continue
        j0 = int(np.searchsorted(lst, dst[k], "left"))
        closes = lc[j0:cp + 1]
        if r.sgn == 1:
            w = bool(m.l[a:z].min() >= eq)
            cl_ok = bool((closes >= eq).all())
        else:
            w = bool(m.h[a:z].max() <= eq)
            cl_ok = bool((closes <= eq).all())
        rows.append((tconf, int(r.sgn), float(r.protected_swing), w, cl_ok))
    if not rows:
        return empty(COLS)
    out = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "eq_wick", "eq_close"])
    t = pd.DatetimeIndex(pd.to_datetime(out["t"].to_numpy(np.int64), utc=True))
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": out["direction"].to_numpy(),
                         "stop_px": out["stop_px"].to_numpy(), "rr": RR,
                         "eq_wick": out["eq_wick"].to_numpy(bool),
                         "eq_close": out["eq_close"].to_numpy(bool)}
                        ).sort_values("decision_time", kind="stable").reset_index(drop=True)[COLS]


READINGS = {"a": ("eq_wick", "wick: the day's running M1 low (bullish) / high (bearish) up to the decision has not traded through the previous day's EQ",
                  "corpus: YAML 'the next candle's low must form above that 50% level' (wick reading)"),
            "b": ("eq_close", "close: no 1h close of the day (through the confirming bar) beyond the previous day's EQ against the direction",
                  "corpus: YAML invalidation 'A close through the EQ against the direction being held' (close reading)")}
SRC = {"htf": "corpus: YAML htf [1D, 4H, 1H]; method_spec §3.4 C4 low in upper half of C3 (daily)",
       "ltf": "method_spec: §1.2 daily -> hourly pairing; YAML ltf [1H, 15m, 5m]",
       "eq": "method_spec: §3.7 EQ = 50% of the previous candle's wick-to-wick range",
       "cisd": PHASE3_SRC, "max_hold": PHASE3_SRC,
       "rr": "corpus: YAML execution targets '2R (stated in the 4th-day example)'",
       "direction": "declared-before-run: 'when price is expanding' operationalised as the previous daily candle closing in the trade direction",
       "min_m1": "declared-before-run: skip stub previous days (README trap 6)"}

if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_1D_1h", lambda: detect(cl.load_m1()))
    print(len(ev), ev[["eq_wick", "eq_close"]].mean().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    print("probe", probe["passed"])
    for rd, (col, rule, src) in READINGS.items():
        res = cl.gate_test(ev, col, mask_available_at="decision_time", max_hold=HOLD)
        print(rd, {k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                           "mde", "exposure_bars", "ties", "ctrl_overlap")})
        op = {"rules": [
            "1h CISD = phase-3 rung 0 (series_open, 2/2 swing, max_wait 3); decide at the confirming 1h close",
            "trade only in the direction of the previous NY daily candle's close (prev day >= 690 M1 bars)",
            "EQ = (prev day high + prev day low) / 2; stop = protected swing; 2R; hold 10h",
            f"gate {col}: {rule}"],
            "params": {"htf": HTF, "ltf": LTF, "rr": RR, "max_hold": HOLD, "eq": "0.5 prev-day wick range",
                       "cisd": "series_open 2/2 max_wait 3", "direction": "prev day close", "min_m1": MIN_M1,
                       "gate": col}}
        p = cl.write_result(CID, rd, res, operationalization=op, params_source={**SRC, "gate": src},
                            script=__file__, probe=probe,
                            notes=f"gate firing rate {ev[col].mean():.3f} on {len(ev)} with-direction 1h CISDs")
        print(p)
