"""fifteen-second-execution-timeframe — Alex's Options: fix the HTF point of interest and the HTF
liquidity target, drop to the 1-minute (then 15-second), enter at the midpoint of the FVG left
by the displacement through the intermediate-term swing, stop at the swing extreme -> a tiny
stop against an unchanged HTF target (1:5-1:10 payoffs, low win rate).

Reading a (1-minute execution — the worked ES example is the 1-minute FVG): trade_test.
  HTF POI (long; short mirrored) = the first 1h bar that trades into a bullish 1h FVG
  (low <= gap_high) within 120 bars of its formation and closes >= gap_low; decide at its close.
  Then on M1, within 120 minutes: the first M1 close above the most recent confirmed 2/2 M1
  swing high (known before that bar) = displacement through the intermediate-term high;
  the bullish 3-bar M1 FVG whose third bar is that bar or one of the next two = the entry FVG.
  entry = the first M1 bar within 30 bars after the FVG completes whose low trades to the
  FVG midpoint (decide at its close; next M1 open).
  stop = the lowest M1 low from the POI 1h bar's start through the entry bar.
  target = the nearest 1h swing high (2/2, confirmed, within the last 120 1h bars, not yet
  traded through) above the entry bar's close — the HTF liquidity; no target -> no trade.
  max hold 8h.
Reading b (15-second execution): UNTESTABLE — the certified data is M1; no sub-minute bars.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

CID = "fifteen-second-execution-timeframe"
POI_WITHIN = 120
LTF_WINDOW = 120
ENTRY_WAIT = 30
TGT_LOOK = 120
MAX_HOLD = "8h"
ONE = 60_000_000_000


def swings(h, l, left=2, right=2):
    hs = pd.Series(h); ls = pd.Series(l)
    prev_h = hs.shift(1).rolling(left).max(); prev_l = ls.shift(1).rolling(left).min()
    next_h = hs[::-1].shift(1).rolling(right).max()[::-1]
    next_l = ls[::-1].shift(1).rolling(right).min()[::-1]
    return ((hs > prev_h) & (hs >= next_h)).to_numpy(), ((ls < prev_l) & (ls <= next_l)).to_numpy()


def long_events(H1, M):
    """H1: dict of 1h arrays (h,l,c,start_ns,close_ns); M: dict of M1 arrays (h,l,c,t_ns)."""
    h1, l1, c1, s1, e1 = H1["h"], H1["l"], H1["c"], H1["s"], H1["e"]
    n1 = len(h1)
    sh1, _ = swings(h1, l1)
    sh1_piv = np.where(sh1)[0]
    sh1_piv = sh1_piv[sh1_piv + 2 < n1]
    sh1_conf = e1[sh1_piv + 2]
    mh, ml, mc, mt = M["h"], M["l"], M["c"], M["t"]
    nm = len(mh)
    shm, _ = swings(mh, ml)
    last = np.full(nm, -1)
    pv = np.where(shm)[0]
    pv = pv[pv + 2 < nm]
    last[pv + 2] = pv
    last = np.maximum.accumulate(last)          # most recent pivot confirmed at/before bar i
    # POIs: first touch of bullish 1h FVGs
    fv = np.where(np.r_[False, False, l1[2:] > h1[:-2]])[0]
    poi_bars = set()
    for k in fv:
        glo, ghi = h1[k - 2], l1[k]
        end = min(n1, k + 1 + POI_WITHIN)
        tt = np.where(l1[k + 1:end] <= ghi)[0]
        if len(tt):
            t = k + 1 + tt[0]
            if c1[t] >= glo:
                poi_bars.add(t)
    out = []
    for t in sorted(poi_bars):
        a = np.searchsorted(mt, e1[t])            # first M1 starting at/after the POI close
        b = min(nm, a + LTF_WINDOW)
        if a < 1 or a >= b:
            continue
        piv_prev = last[a - 1:b - 1]              # swing known before each bar
        ok = piv_prev >= 0
        lv = np.where(ok, mh[np.maximum(piv_prev, 0)], np.inf)
        brk = np.where(mc[a:b] > lv)[0]
        if not len(brk):
            continue
        i = a + brk[0]
        k = None
        for kk in (i, i + 1, i + 2):
            if kk < nm and kk >= 2 and ml[kk] > mh[kk - 2]:
                k = kk; break
        if k is None:
            continue
        mid = (ml[k] + mh[k - 2]) / 2.0
        e_end = min(nm, k + 1 + ENTRY_WAIT)
        jj = np.where(ml[k + 1:e_end] <= mid)[0]
        if not len(jj):
            continue
        j = k + 1 + jj[0]
        s0 = np.searchsorted(mt, s1[t])
        stop = ml[s0:j + 1].min()
        entry_ref = mc[j]
        if not stop < entry_ref:
            continue
        dec = mt[j] + ONE
        # nearest untaken, confirmed 1h swing high above entry_ref
        cand = sh1_piv[(sh1_conf <= dec)]
        cand = cand[cand >= t - TGT_LOOK]
        best = None
        for p in cand[::-1]:
            lvl = h1[p]
            if lvl <= entry_ref:
                continue
            # not traded through since: 1h bars after the pivot that closed by dec, plus M1 since
            q_end = np.searchsorted(e1, dec, side="right")
            if (h1[p + 1:q_end] >= lvl).any():
                continue
            m0 = np.searchsorted(mt, e1[q_end - 1]) if q_end > 0 else 0
            if m0 <= j and (mh[m0:j + 1] >= lvl).any():
                continue
            if best is None or lvl < best:
                best = lvl
        if best is None:
            continue
        out.append((dec, stop, best))
    return out


def detect(m1):
    b = cl.build_bars(m1, "1h")
    s = b.index.tz_convert("UTC").as_unit("ns").asi8
    e = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC").as_unit("ns").asi8
    mt = m1.index.tz_convert("UTC").as_unit("ns").asi8
    h1, l1, c1 = (b[x].to_numpy() for x in ("high", "low", "close"))
    mh, ml, mc = (m1[x].to_numpy() for x in ("high", "low", "close"))
    rows = []
    for sgn in (1, -1):
        if sgn == 1:
            H1 = {"h": h1, "l": l1, "c": c1, "s": s, "e": e}; M = {"h": mh, "l": ml, "c": mc, "t": mt}
        else:
            H1 = {"h": -l1, "l": -h1, "c": -c1, "s": s, "e": e}; M = {"h": -ml, "l": -mh, "c": -mc, "t": mt}
        for dec, stop, tgt in long_events(H1, M):
            rows.append((dec, sgn, sgn * stop, sgn * tgt))
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px"])
    df["t"] = pd.to_datetime(df["t"], utc=True)
    df = df.sort_values(["t", "direction"]).drop_duplicates(["t", "direction"]).reset_index(drop=True)
    return pd.DataFrame({"decision_time": df.t, "available_at": df.t,
                         "direction": df.direction.astype(int), "stop_px": df.stop_px,
                         "target_px": df.target_px})


OP_A = {"rules": [
    "HTF POI = first 1h bar trading into a same-direction 1h FVG within 120 bars of it forming and "
    "closing on the respecting side; decide at its close",
    "M1 within 120 min: first close through the most recent confirmed 2/2 M1 swing high (long) = "
    "displacement through the intermediate-term swing; its FVG = a same-direction M1 FVG completing "
    "on that bar or the next two",
    "entry = first M1 within 30 bars trading to the FVG midpoint; decide at its close, enter next open",
    "stop = extreme of the move from the POI bar's start to entry; target = nearest untaken confirmed "
    "1h swing high (low for shorts) within 120 1h bars beyond the entry; 8h max hold"],
    "params": {"poi": "1h FVG first touch", "poi_within_bars": POI_WITHIN,
               "ltf_window_min": LTF_WINDOW, "entry_wait_min": ENTRY_WAIT, "fvg_entry": "midpoint",
               "target": "nearest untaken 1h swing high/low", "target_lookback_1h": TGT_LOOK,
               "swing": "2/2", "max_hold": MAX_HOLD}}
SRC_A = {"poi": "corpus: V8P6lNIisvc preconditions 'weekly or daily fair value gap, hourly optimal trade entry' (1h FVG chosen for sample size)",
         "poi_within_bars": "declared-before-run: FVG counts as a live POI for 120 1h bars",
         "ltf_window_min": "declared-before-run: the 1m displacement must come within 2 hours of the POI reaction",
         "entry_wait_min": "declared-before-run: the retrace to the FVG midpoint must come within 30 minutes",
         "fvg_entry": "corpus: V8P6lNIisvc 'Enter at the bottom or the midpoint of that fair value gap; the midpoint is preferred'",
         "target": "corpus: V8P6lNIisvc 'higher-timeframe liquidity pool' (relatively equal highs/lows approximated by the nearest untaken 1h swing)",
         "target_lookback_1h": "declared-before-run: swing targets from the last 120 1h bars",
         "swing": "phase3: meta/conjunction_preregistration.md §1.8 left=2,right=2",
         "max_hold": "declared-before-run: one 8h session for the HTF target to be reached"}

if __name__ == "__main__":
    reading = sys.argv[1]
    if reading == "b":
        p = cl.write_untestable(
            CID, "The rule's defining step is execution on the 15-second chart (entry at a 15s FVG, "
            "stop at a 15s swing, 'sloppier when volume is thin'). The certified XAUUSD data is M1 "
            "(2016-2026, 3.69M one-minute bars); no sub-minute bars exist, so neither the 15s FVG nor "
            "a 15s stop can be located or resolved. The 1-minute step of the same method is tested as "
            "reading a.", reading="b", script=__file__)
        print(p); raise SystemExit
    ev = cl.cache_frame(f"{CID}_a_{POI_WITHIN}_{LTF_WINDOW}_{ENTRY_WAIT}_{TGT_LOOK}", lambda: detect(cl.load_m1()))
    risk = None
    print(len(ev), ev.direction.value_counts().to_dict())
    if "--dry" in sys.argv:
        m = cl.get_market()
        print(ev.head()); raise SystemExit
    probe = cl.probe_lookahead(detect, ev, lookback="15D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD, claim="+")
    for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars"):
        print(k, res.get(k))
    notes = ("Tests the 1-minute execution step (the worked ES example's own chart). The payoff claim is "
             "tested as the book's net R against a matched random entry with the same stop and target "
             "distances; the win rate is not the verdict statistic (matched geometry cancels it).")
    p = cl.write_result(CID, "a", res, operationalization=OP_A, params_source=SRC_A,
                        script=__file__, notes=notes, probe=probe)
    print(p)
