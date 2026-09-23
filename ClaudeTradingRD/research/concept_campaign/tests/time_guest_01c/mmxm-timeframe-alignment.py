"""mmxm-timeframe-alignment (guest: The MMXM Trader) -> gate_test.

Claim ('+'): the MMXM should be drawn on the timeframe PAIRED with the PD array's
timeframe (monthly->daily, weekly->4H, daily->1H, 4H->15m, 1H->5m, 15m->1m); adhering to
the table "is what produces clean and identifiable market maker models". Tested on the
1H -> 5m row: a 5m model reversing at a 1H PD array beats the same 5m model reversing at
a PD array of an ADJACENT timeframe (15m or 4H), which the table pairs with 1m / 15m.
Declared before the run:
  * 5m MMXM reversal = the phase-3 bare 5m CISD (smart-money reversal: swept extreme,
    close through the opposing series open), 2R, stop at the protected swing, 50 min.
  * PD array = a 3-bar fair value gap of the HTF (detectors.primitives.fair_value_gaps),
    same polarity as the reversal (bullish FVG for a long), whose third bar CLOSED at or
    before the start of the 5m extreme bar and at most 20 HTF bars earlier. The reversal
    "is at" the array when the swept extreme price lies inside the gap.
  * gated = the extreme sits in a 1H FVG (paired); complement = it sits in a 15m or 4H
    (forex grid) FVG but in no 1H FVG. Events at no HTF FVG are dropped.
  * Range selection itself is not tested (the table excludes it).
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/time_guest_01c")
from _common import PHASE3, cl, np, pd, summary  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from detectors.primitives import fair_value_gaps  # noqa: E402

CID = "mmxm-timeframe-alignment"
TF, HOLD = "5min", "50min"
PAIRED, ADJ = "1h", ("15min", "4h")
N_BARS = 20


def fvg_table(m1, tf):
    b = cl.build_bars(m1, tf, grid4h="forex")
    f = fair_value_gaps(b[["open", "high", "low", "close"]])
    ct = cl.data.utc_ns(pd.DatetimeIndex(b["close_time"]))
    out = {}
    for d, col in ((1, "bullish_fvg"), (-1, "bearish_fvg")):
        m = f[col].to_numpy()
        out[d] = (ct[m], f["gap_low"].to_numpy()[m], f["gap_high"].to_numpy()[m])
    return out, cl.tf_delta(tf)


def at_array(ext_t_ns, ext_px, dirs, table):
    tab, dt = table
    win = np.int64(N_BARS) * np.int64(dt.value)
    hit = np.zeros(len(ext_px), bool)
    for d in (1, -1):
        ct, lo, hi = tab[d]
        idx = np.flatnonzero(dirs == d)
        if not len(ct) or not len(idx):
            continue
        a = np.searchsorted(ct, ext_t_ns[idx] - win, side="left")
        b = np.searchsorted(ct, ext_t_ns[idx], side="right")
        for k, (i, j) in enumerate(zip(a, b)):
            if j > i:
                p = ext_px[idx[k]]
                if np.any((lo[i:j] <= p) & (p <= hi[i:j])):
                    hit[idx[k]] = True
    return hit


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "paired"]
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return pd.DataFrame(columns=cols)
    close = pd.DatetimeIndex(b.loc[ev["confirm_time"], "close_time"])
    dirs = np.where(ev["direction"] == "bullish", 1, -1)
    ext_t = cl.data.utc_ns(pd.DatetimeIndex(ev["extreme_time"]))
    ext_p = ev["extreme_price"].to_numpy(float)
    p_hit = at_array(ext_t, ext_p, dirs, fvg_table(m1, PAIRED))
    a_hit = np.zeros(len(ev), bool)
    for tf in ADJ:
        a_hit |= at_array(ext_t, ext_p, dirs, fvg_table(m1, tf))
    out = pd.DataFrame({"decision_time": close, "available_at": close, "direction": dirs,
                        "stop_px": ev["protected_swing"].to_numpy(float), "rr": 2.0,
                        "paired": p_hit})
    out = out[p_hit | a_hit]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("tg01c_mmxm_1h_vs_adj_5mcisd", lambda: detect(cl.load_m1()))
    print(len(ev), ev["paired"].mean())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.gate_test(ev, "paired", mask_available_at="decision_time", max_hold=HOLD)
    print(summary(res))
    op = {"rules": [
        "5m MMXM reversal = bare 5m CISD (series_open, swing 2/2, max_wait 3), next M1 open, "
        "stop protected swing, 2R, 50 min",
        "PD array = same-polarity 3-bar HTF FVG closed <= the 5m extreme bar's start and within "
        "20 HTF bars; reversal 'at' the array when the swept extreme lies inside the gap",
        "gated: at a 1H FVG (paired 1H->5m); complement: at a 15m or 4H FVG only (adjacent); "
        "events at no HTF FVG dropped"],
        "params": {"pair": "1H->5m", "adjacent": "15m, 4H", "pd_array": "FVG",
                   "fvg_age_bars": N_BARS, "grid4h": "forex", "level_rule": "series_open",
                   "swing": "2/2", "max_wait": 3, "rr": 2.0, "max_hold": HOLD}}
    src = {"pair": "corpus: Ibw4saRtYMk alignment table row '1-hour with 5-minute'",
           "adjacent": "corpus: Ibw4saRtYMk table pairs 15m->1m and 4H->15m (the neighbouring rows)",
           "pd_array": "declared-before-run: FVG as the HTF PD array (most common internal-range array)",
           "fvg_age_bars": "declared-before-run: FVG formed within the last 20 HTF bars",
           "grid4h": "session_window_fit: forex grid for gold (weak; recorded as a knob)",
           "level_rule": PHASE3, "swing": PHASE3, "max_wait": PHASE3, "rr": PHASE3,
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Only the 1H->5m row of the table is tested; the MMXM is reduced "
                              "to its smart-money-reversal (CISD) leg, and 'clean and "
                              "identifiable' is scored as outcome R, not chart legibility.")
    print(p)
