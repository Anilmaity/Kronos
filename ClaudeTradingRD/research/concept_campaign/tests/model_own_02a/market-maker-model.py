"""market-maker-model — two readings.

a  THE WORKED SELL/BUY MODEL TRADE (0R61Y6Pn74Q), mechanised, 1D / 5m:
   original consolidation = previous day low (sell model; the example's consolidation 'is
   also the previous day low' and is the target). Manipulation leg = price trades above the
   previous day high. Smart-money reversal = a bearish 5m CISD (series_open, max_wait 3)
   whose swing-high extreme is above PDH and is the day's high so far. Dealing range = that
   high H down to the running low L after it. Short when price retraces into the PREMIUM of
   the range (an M1 high reaching the range's 50%) before the target (PDL) has been reached;
   stop = H (the confirmed intermediate-term high); target = PDL (the original
   consolidation); hold to the daily close. Buy model mirrored (PDL swept, target PDH).
   First setup per side per day.
b  THE CURVE (sell side -> smart money reversal -> buy side, zones dragged across the curve)
   -> UNTESTABLE: no video defines the curve's phases, how to know which side of the curve
   price is on, or which/how many zones to drag forward (concept ambiguities; method_spec
   §3.9 market-curve-side [GAP]).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, in_progress, utc  # noqa: E402

CID = "market-maker-model"
PREMIUM = 0.5
MIN = 60_000_000_000


def _ns(x):
    return cl.data.utc_ns(utc(x)).astype("int64")


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    bd = cl.build_bars(m1, "1D")
    b5 = cl.build_bars(m1, "5min")
    ev = cisd(b5, max_wait=3)
    if ev.empty or len(bd) < 2:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    H = ev["stop_px"].to_numpy()                       # the reversal extreme
    pday = in_progress(bd, t)
    xday = in_progress(bd, ev["extreme_start"])
    pc = np.clip(pday, 1, None)
    pdh, pdl = bd["high"].to_numpy()[pc - 1], bd["low"].to_numpy()[pc - 1]
    dclose = _ns(bd["close_time"].to_numpy())[pc]
    # extreme is the day's extreme so far (5m bars of today up to the confirm bar)
    st5 = _ns(b5.index)
    bday = in_progress(bd, b5.index)
    hi5, lo5 = b5["high"].to_numpy(), b5["low"].to_numpy()
    key = pd.Series(bday)
    run_hi = pd.Series(hi5).groupby(key).cummax().to_numpy()
    run_lo = pd.Series(lo5).groupby(key).cummin().to_numpy()
    ci = b5.index.get_indexer(ev["confirm_start"])
    xi = b5.index.get_indexer(ev["extreme_start"])
    ok = (pday >= 1) & (xday == pday)
    # sell model: d=-1, extreme above PDH and = day high so far; buy mirrored
    ok &= np.where(d < 0, (H > pdh) & (H >= run_hi[ci]), (H < pdl) & (H <= run_lo[ci]))
    m1s = _ns(m1.index)
    m1h, m1l = m1["high"].to_numpy(float), m1["low"].to_numpy(float)
    tn = _ns(t)
    rows = []
    for e in np.flatnonzero(ok):
        s = d[e]                                          # -1 sell, +1 buy
        # running opposite extreme from the extreme bar through the confirm bar
        seg = slice(xi[e], ci[e] + 1)
        if s < 0:
            L0 = lo5[seg].min()
            tgt = pdl[e]
        else:
            L0 = hi5[seg].max()
            tgt = pdh[e]
        a = np.searchsorted(m1s, tn[e], side="left")
        bnd = np.searchsorted(m1s, dclose[e], side="left")
        if bnd <= a:
            continue
        if s < 0:
            Lp = np.minimum.accumulate(np.r_[L0, m1l[a:bnd][:-1]])   # low known before bar
            eq = Lp + PREMIUM * (H[e] - Lp)
            trig = m1h[a:bnd] >= eq
            reached = Lp <= tgt                                    # objective already hit
        else:
            Lp = np.maximum.accumulate(np.r_[L0, m1h[a:bnd][:-1]])
            eq = Lp - PREMIUM * (Lp - H[e])
            trig = m1l[a:bnd] <= eq
            reached = Lp >= tgt
        if (L0 <= tgt if s < 0 else L0 >= tgt):
            continue
        f = np.flatnonzero(trig)
        if not len(f):
            continue
        q = f[0]
        if reached[q]:
            continue
        rows.append((m1s[a + q] + MIN, s, H[e], tgt, dclose[e], pday[e]))
    if not rows:
        return pd.DataFrame(columns=cols)
    r = pd.DataFrame(rows, columns=["dec", "direction", "stop_px", "target_px", "dclose", "day"])
    r = r.sort_values("dec").drop_duplicates(["day", "direction"], keep="first")
    dt = pd.DatetimeIndex(pd.to_datetime(r["dec"].to_numpy(), utc=True))
    dc = pd.DatetimeIndex(pd.to_datetime(r["dclose"].to_numpy(), utc=True))
    out = pd.DataFrame({"decision_time": dt, "available_at": dt,
                        "direction": r["direction"].to_numpy(),
                        "stop_px": r["stop_px"].to_numpy(), "target_px": r["target_px"].to_numpy(),
                        "max_hold": pd.Series(dc - dt).to_numpy()})
    out = out[out["max_hold"] > pd.Timedelta(0)]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


def main():
    ev = cl.cache_frame("mmxm_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                    "verdict", "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "daily = 18:00 NY trading day; execution 5m; entries resolved on M1",
        "sell model: original consolidation = previous day low (the target); manipulation = "
        "price above previous day high; reversal = bearish 5m CISD whose swing-high extreme is "
        "above PDH and is the day's high so far (extreme and CISD inside today)",
        "dealing range = extreme H to the running low L after it; short when an M1 high reaches "
        "L + 0.5 (H - L) (premium), with L updated only from bars before the trigger bar, and "
        "only if the running low has not yet reached PDL; searched until the daily close",
        "stop = H; target = PDL; hold to the daily close; buy model mirrored; first setup per "
        "side per day",
        "not modelled: the 'daily PD array' the manipulation must reach, the FVG/mitigation-block "
        "confluence at the premium entry, the news-wick exclusion from the fib"],
        "params": {"exec_tf": "5min", "level_rule": "series_open", "max_wait": 3,
                   "premium": PREMIUM, "original_consolidation": "PDL (sell) / PDH (buy)",
                   "max_hold": "to daily close", "one_per_side_day": True,
                   "day_open_hour": 18}}
    src = {"exec_tf": "corpus: 0R61Y6Pn74Q (concept timeframes ltf 5m)",
           "level_rule": "method_spec: §4.2 first-candle-open default (smart-money reversal "
                         "confirmation)",
           "max_wait": "phase3: locked config max_wait=3",
           "premium": "method_spec: §3.7 EQ = 50% of the range; concept 'take the short in the "
                      "premium of that range'",
           "original_consolidation": "corpus: 0R61Y6Pn74Q 'that is our original consolidation' "
                                     "= previous day low, and it is the target",
           "max_hold": "method_spec: §5.5 time-based exit at the HTF (daily) candle close",
           "one_per_side_day": "declared-before-run: one sell and one buy model per day",
           "day_open_hour": "method_spec: §1.4 18:00 canon"}
    print("wrote", cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="reading a = the worked MMXM trade as a mechanical "
                                         "book; trade_test vs matched controls with the same "
                                         "stop/target distance and per-row hold."))
    print("wrote", cl.write_untestable(
        CID, "The market-maker CURVE reading (sell side -> smart money reversal -> buy side, "
             "with order blocks / FVGs dragged across the curve and reused) is not decidable "
             "from OHLC as taught: the source never defines the curve's phases or proportions, "
             "gives no rule for knowing in advance which side of the curve price is on "
             "(method_spec §3.9 market-curve-side [GAP]), and does not say which zones or how "
             "many to drag forward or how far back. Any mechanisation would be an invented "
             "model, not this one. The mechanisable part (the sell/buy model trade into the "
             "original consolidation) is tested as reading a.",
        reading="b", script=__file__))


if __name__ == "__main__":
    main()
