"""order-block-series-is-htf-candle — gate_test.

Concept: order blocks are marked as the whole SERIES of consecutive same-direction closes,
not the last candle, BECAUSE the series is one candle a timeframe up (the LTF rendering of
the HTF order block). Detection rule 2 is an explicit equivalence test: the run should
collapse into a single candle on the next timeframe up.

Baseline book (stated): 5m CISD-born blocks (phase-3 CISD: series_open, 2/2, max_wait 3)
with a series of >= 2 opposing candles; the block's level = the series open (its body
edge facing the retest). Entry: first M1 touch of that level after max(CISD close, close
of the 15m candle containing the series' last candle) and within 24 5m bars (2 h) of the
CISD close; decide at that M1 close, fill next M1 open; skipped if the same minute
reaches the protected swing. Stop = protected swing, 2R, 50 min.
Gate htf_candle: the whole series lies inside ONE 15m candle and that 15m candle closed
in the series' direction (the run literally collapses into one opposing candle a
timeframe up).
claim '+': series that ARE one HTF candle make better blocks than series that are not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, complete_bars, cisd_frame, empty, ns, to_ts, M1, ONE_MIN,  # noqa: E402
                     PHASE3_SRC)

CID = "order-block-series-is-htf-candle"
LTF, HTF = "5min", "15min"
MIN_SERIES = 2
RETEST_BARS = 24
RR = 2.0
HOLD = "50min"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "htf_candle"]
M15 = 15 * 60_000_000_000
M5 = 5 * 60_000_000_000


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = complete_bars(cl.build_bars(m1, LTF), m1)
    hb = cl.build_bars(m1, HTF)
    if len(b) < 40:
        return empty(COLS)
    ev = cisd_frame(b)
    ev = ev[ev["series_len"] >= MIN_SERIES].reset_index(drop=True)
    if ev.empty:
        return empty(COLS)
    m = M1(m1)
    bst = ns(b.index)
    bo = b["open"].to_numpy(float)
    hst = ns(hb.index)
    ho, hc = hb["open"].to_numpy(float), hb["close"].to_numpy(float)
    hct = ns(hb["close_time"])
    end_data = m.t[-1] + ONE_MIN
    rows = []
    for d, sp, ep, cp, stop, cct in zip(ev["sgn"].to_numpy(int), ev["s_pos"].to_numpy(int), ev["e_pos"].to_numpy(int),
                                        ev["conf_pos"].to_numpy(int), ev["protected_swing"].to_numpy(float),
                                        ns(ev["conf_close_time"])):
        f_s = bst[sp] - bst[sp] % M15
        f_e = bst[ep] - bst[ep] % M15
        k = int(np.searchsorted(hst, f_e, side="left"))
        if k >= len(hst) or hst[k] != f_e:
            continue
        bucket_close = hct[k]
        start = max(cct, bucket_close)
        if start > end_data:           # the 15m candle (or the CISD) is not closed within this slice
            continue
        same = f_s == f_e
        # the series direction is opposite the trade: bullish block = run of down closes
        htf_dir = np.sign(hc[k] - ho[k])
        gate = bool(same and htf_dir == -d)
        level = bo[sp]
        end = cct + RETEST_BARS * M5
        i0 = int(np.searchsorted(m.t, start, side="left"))
        i1 = int(np.searchsorted(m.t, min(end, end_data), side="left"))
        if i1 <= i0:
            continue
        seg = (m.l[i0:i1] <= level) if d > 0 else (m.h[i0:i1] >= level)
        kk = np.flatnonzero(seg)
        if not len(kk):
            continue
        q = i0 + int(kk[0])
        if (d > 0 and m.l[q] <= stop) or (d < 0 and m.h[q] >= stop):
            continue
        rows.append((m.t[q] + ONE_MIN, d, stop, gate))
    if not rows:
        return empty(COLS)
    arr = np.array(rows, dtype=object)
    t = to_ts(arr[:, 0].astype(np.int64))
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": arr[:, 1].astype(int),
                        "stop_px": arr[:, 2].astype(float), "rr": RR, "htf_candle": arr[:, 3].astype(bool)})
    out = out.drop_duplicates(subset=["decision_time", "direction"], keep="first")
    return out.sort_values("decision_time").reset_index(drop=True)[COLS]


OP = {"rules": [
    "5m CISD (series_open, 2/2 swings, max_wait 3) with >= 2 opposing candles in the series; block level = series open",
    "entry: first M1 touch of the level after max(CISD close, close of the 15m candle holding the series' last candle), "
    "within 24 5m bars of the CISD close; decide at that M1 close, enter next M1 open; skip if that minute reaches the stop",
    "stop = protected swing; 2R; 50 min",
    "gate htf_candle: every series candle inside one 15m candle AND that 15m candle closed in the series' direction"],
    "params": {"ltf": LTF, "htf": HTF, "min_series": MIN_SERIES, "retest_bars": RETEST_BARS, "level_rule": "series_open",
               "swing": "2/2", "max_wait": 3, "rr": RR, "max_hold": HOLD}}
SRC = {"ltf": "corpus: order-block-series-is-htf-candle.yaml timeframes ltf [5m, 1m]",
       "htf": "declared-before-run: 'which higher timeframe is meant is not stated'; the next chart timeframe up from 5m (15m) "
              "is the one a 2-3 candle run can collapse into",
       "min_series": "corpus: 'two or more consecutive candles close in the same direction' (detection rule 1)",
       "retest_bars": "declared-before-run: no retest window given; 24 5m bars = 2 h",
       "level_rule": PHASE3_SRC, "swing": PHASE3_SRC, "max_wait": PHASE3_SRC, "rr": PHASE3_SRC, "max_hold": PHASE3_SRC}


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_5m_15m", lambda: detect(cl.load_m1()))
    print(len(ev), ev["htf_candle"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    print("probe", probe["passed"])
    res = cl.gate_test(ev, "htf_candle", mask_available_at="decision_time", max_hold=HOLD)
    print({k: res.get(k) for k in ("verdict", "verdict_detail", "n", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "exposure_bars", "ties", "ctrl_overlap")})
    print(cl.write_result(CID, None, res, operationalization=OP, params_source=SRC, script=__file__, probe=probe,
                          notes=f"gate firing rate {ev['htf_candle'].mean():.3f}. Tests the stated rationale (series == "
                                "one HTF candle); a direct series-zone vs last-candle-zone comparison is not a single-"
                                "baseline gate and was not run."))
