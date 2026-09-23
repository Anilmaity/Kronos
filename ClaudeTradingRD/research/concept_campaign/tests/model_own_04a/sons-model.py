"""sons-model — trade_test (batch model_own_04a).

Son's model: draw on liquidity -> stop raid in the OPPOSITE direction -> candle
closing back into the range -> first fair value gap two timeframes down -> stop at
the raided extreme, fixed 1:1. The base version is 1H/15m draw, 5m raid, 30-second
FVG (NQ). The certified data has no sub-minute bars, so the test uses the concept's
own stated higher-timeframe ladder (AdmnWLjf8rY): "4H or 1H draw -> 15-minute stop
raid + candle close -> 1-minute FVG entry".

Declared operationalisation (before run):
  * swings = three-candle fractal (method_spec §1.1); a 15m swing counts while formed
    within the last 12 h (three 4H candles, relevant-swing-lookback for the 15m chart)
  * raid = a 15m bar trading beyond an untaken 15m swing (long: a swing LOW taken);
    close-back-in = an up-close 15m candle closing back above the deepest raided low,
    the raid bar itself or one of the next two (1-3 candles, method_spec §4.2 speed)
  * draw = the NEARER untaken 1H old high / old low (3-candle fractal, formed within
    72 h = three daily candles); if the hour has none, the 15m equivalent (12 h).
    Long only when the draw is ABOVE (sell-side raid against a buy-side draw).
  * entry: the first bullish 1m FVG whose three bars all start after the close-back-in
    candle closes, within 30 min; then the first 1m bar that trades back into the gap
    (low <= gap top) within 30 min of the gap; decide at that bar's close, enter the
    next M1 open (the harness has no limit fills)
  * stop = the raided extreme (lowest low from the raid bar to the close-back-in
    candle); no 12-handle cap (NQ-specific); target fixed 1:1; max hold 150 min
Mirror everything for shorts.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

LB15 = pd.Timedelta(hours=12)
LB1H = pd.Timedelta(hours=72)
FVG_WAIT = pd.Timedelta(minutes=30)
FILL_WAIT = pd.Timedelta(minutes=30)
MAX_HOLD = "150min"


def fractal(h, l):
    n = len(h)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] > h[2:])
    sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] < l[2:])
    return sh, sl


def untaken_nearest(bars_start, bars_close, H, L, sh, sl, t, px, lb, hi15_fn):
    """Nearest untaken swing high above px / low below px among swings whose
    confirming bar (i+1) closed by t and which formed within lb of t."""
    ct = bars_close
    i_hi = np.searchsorted(ct, t, side="right") - 2          # latest swing with i+1 closed <= t
    i_lo = np.searchsorted(bars_start, t - lb, side="left")
    up, dn = np.nan, np.nan
    for i in range(max(i_hi, -1), max(i_lo, 1) - 1, -1):
        if i < 1:
            break
        if sh[i] and H[i] > px:
            if hi15_fn(ct[i], t, True) < H[i] and (np.isnan(up) or H[i] < up):
                up = H[i]
        if sl[i] and L[i] < px:
            if hi15_fn(ct[i], t, False) > L[i] and (np.isnan(dn) or L[i] > dn):
                dn = L[i]
    return up, dn


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    b15 = cl.build_bars(m1, "15min")
    b1h = cl.build_bars(m1, "1h")
    if len(b15) < 10 or len(b1h) < 5:
        return pd.DataFrame(columns=cols)
    s15 = b15.index.as_unit("ns").asi8
    c15 = pd.DatetimeIndex(b15["close_time"]).as_unit("ns").asi8
    O, H, L, C = (b15[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sh15, sl15 = fractal(H, L)
    s1h = b1h.index.as_unit("ns").asi8
    c1h = pd.DatetimeIndex(b1h["close_time"]).as_unit("ns").asi8
    H1, L1 = b1h["high"].to_numpy(float), b1h["low"].to_numpy(float)
    sh1, sl1 = fractal(H1, L1)

    def ext15(t_from, t_to, high):
        """max high / min low of 15m bars that START at/after t_from and CLOSE <= t_to."""
        a = np.searchsorted(s15, t_from, side="left")
        z = np.searchsorted(c15, t_to, side="right")
        if z <= a:
            return -np.inf if high else np.inf
        return H[a:z].max() if high else L[a:z].min()

    mt = m1.index.as_unit("ns").asi8
    mo, mh, ml = (m1[k].to_numpy(float) for k in ("open", "high", "low"))
    ONE = pd.Timedelta(minutes=1).value
    lb15, lb1h = LB15.value, LB1H.value
    rows = []
    act_lo, act_hi = [], []                      # (price, start_ns) active 15m swings
    pend = []                                    # (dir, level, raid_idx, extreme)
    n = len(b15)
    for r in range(n):
        # swings at r-2 confirmed by bar r-1 (closed before bar r starts)
        i = r - 2
        if i >= 1:
            if sl15[i]:
                act_lo.append((L[i], s15[i]))
            if sh15[i]:
                act_hi.append((H[i], s15[i]))
        cut = s15[r] - lb15
        act_lo = [x for x in act_lo if x[1] >= cut]
        act_hi = [x for x in act_hi if x[1] >= cut]
        swept = [x for x in act_lo if L[r] < x[0]]
        if swept:
            act_lo = [x for x in act_lo if not (L[r] < x[0])]
            pend.append([1, min(x[0] for x in swept), r, L[r]])
        swept = [x for x in act_hi if H[r] > x[0]]
        if swept:
            act_hi = [x for x in act_hi if not (H[r] > x[0])]
            pend.append([-1, max(x[0] for x in swept), r, H[r]])
        keep = []
        for p in pend:
            d, lvl, r0, ext = p
            if r > r0:
                ext = min(ext, L[r]) if d == 1 else max(ext, H[r])
                p[3] = ext
            ok = (C[r] > lvl and C[r] > O[r]) if d == 1 else (C[r] < lvl and C[r] < O[r])
            if ok:
                t0 = c15[r]
                up, dn = untaken_nearest(s1h, c1h, H1, L1, sh1, sl1, t0, C[r], lb1h, ext15)
                if np.isnan(up) and np.isnan(dn):
                    up, dn = untaken_nearest(s15, c15, H, L, sh15, sl15, t0, C[r], lb15, ext15)
                if np.isnan(up) and np.isnan(dn):
                    continue
                if np.isnan(dn):
                    draw = 1
                elif np.isnan(up):
                    draw = -1
                else:
                    draw = 1 if (up - C[r]) <= (C[r] - dn) else -1
                if draw == d:
                    ev = entry(t0, d, ext, mt, mo, mh, ml, ONE)
                    if ev is not None:
                        rows.append(ev)
                continue                          # resolved (traded or not)
            if r - r0 < 2:
                keep.append(p)
        pend = keep
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px"])
    out["decision_time"] = pd.to_datetime(out["decision_time"], utc=True)
    out["available_at"] = out["decision_time"]
    out["rr"] = 1.0
    out = out.drop_duplicates("decision_time", keep="first")
    return out[cols].sort_values("decision_time").reset_index(drop=True)


def entry(t0, d, stop, mt, mo, mh, ml, ONE):
    a = np.searchsorted(mt, t0, side="left")
    z = np.searchsorted(mt, t0 + FVG_WAIT.value, side="left")
    for k in range(a + 2, min(z, len(mt))):
        if d == 1 and ml[k] > mh[k - 2]:
            top = ml[k]
        elif d == -1 and mh[k] < ml[k - 2]:
            top = mh[k]
        else:
            continue
        fclose = mt[k] + ONE
        z2 = np.searchsorted(mt, fclose + FILL_WAIT.value, side="left")
        for u in range(k + 1, min(z2, len(mt))):
            if (d == 1 and ml[u] <= stop) or (d == -1 and mh[u] >= stop):
                return None
            if (d == 1 and ml[u] <= top) or (d == -1 and mh[u] >= top):
                return (mt[u] + ONE, d, stop)
        return None
    return None


def run():
    ev = cl.cache_frame("sons_1h_15m_1m", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    op = {"rules": [
        "draw: nearer untaken 1H old high/low (3-candle fractal, formed within 72h); 15m fallback",
        "stop raid on 15m against the draw (untaken 15m 3-candle swing within 12h taken), then an "
        "up-close (long) candle closing back beyond the deepest raided level within 3 candles",
        "entry: first 1m FVG after that close (within 30 min), then the first 1m bar trading back "
        "into the gap (within 30 min); decide at its close, enter next M1 open",
        "stop at the raided extreme; target fixed 1:1; 150 min max hold"],
        "params": {"draw_tf": "1h", "raid_tf": "15min", "entry_tf": "1min", "swing": "1/1 fractal",
                   "draw_lookback": "72h", "raid_lookback": "12h", "close_back_wait": 3,
                   "fvg_wait": "30min", "fill_wait": "30min", "rr": 1.0, "max_hold": MAX_HOLD,
                   "draw_rule": "nearer untaken extreme"}}
    src = {"draw_tf": "corpus: AdmnWLjf8rY 'I want to look for a four hour or one hour draw on liquidity'",
           "raid_tf": "corpus: AdmnWLjf8rY 'looking for a stop rate on the 15 minute chart in the opposite direction'",
           "entry_tf": "corpus: sons-model ladder '15-minute stop raid + candle close -> 1-minute FVG entry'",
           "swing": "method_spec: §1.1 three-candle fractal",
           "draw_lookback": "method_spec: §1.1 relevant-swing look-back, hourly chart -> three days",
           "raid_lookback": "method_spec: §1.1 three higher-timeframe candles (15m -> three 4H candles)",
           "close_back_wait": "method_spec: §4.2 closure within 1-3 candles ('I prefer 1, 2, maybe three')",
           "fvg_wait": "declared-before-run: two 15m candles for the first 1m gap to form",
           "fill_wait": "declared-before-run: two 15m candles for the retrace into the gap",
           "rr": "corpus: q40pRwjuPYQ 'then I'm targeting a fixed one: one'",
           "max_hold": "phase3: 10 structure-TF bars (15m) (§1.13 convention)",
           "draw_rule": "method_spec: §2.2 / detectors.bias.draw_on_liquidity 'proximity' default"}
    notes = ("Sub-minute data does not exist, so the 5m/30s base version is replaced by the concept's own "
             "15m/1m ladder. The NQ 12-handle stop cap has no gold equivalent and is not applied.")
    p = cl.write_result("sons-model", None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "avg_R", "win_rate", "control", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict",
              "verdict_detail", "exposure_bars", "ties", "ctrl_overlap"):
        print("  ", k, res.get(k))


if __name__ == "__main__":
    run()
