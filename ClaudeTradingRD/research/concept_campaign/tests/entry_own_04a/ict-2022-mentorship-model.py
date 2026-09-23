"""ict-2022-mentorship-model — "The 2022 mentorship setup" (TTrades, Njs-eRpeP9Q).

Batch entry_own_04a. trade_test, claim '+'.

Operationalisation (declared BEFORE the first run; stop and target are not stated in the
source video, and 'displacement' uses the threshold_fits definition):
  pool: a 15m fractal (2/2) swing low / high, usable once its 2 right candles closed; taken
    by the first M1 candle trading beyond it. Direction = away from the pool (sell-side
    taken -> long).
  on 1m (long case; short mirrors):
    leg low = lowest low since the pool was taken (updates while new lows print);
    short-term high = the most recent confirmed 1m 2/2 swing high;
    displacement over it = the first 1m candle to CLOSE above it (structural gate) within
      60 1m candles of the pool being taken, AND the N=4 window from that candle has
      win_range/pre_range >= 1.5 and distance/pre_range >= 0.65 (threshold_fits);
    fib over the displacement range = leg low .. highest high through the window's end;
    FVG: a bullish 1m three-candle gap formed between the leg low and the window's end whose
      TOP is at or below the range's 0.5 (discount). If several, the highest such top.
  entry: the first M1 candle within 60 candles after the window closes that trades down to the
    FVG top -> decide at its close (cancel if the leg low trades first, or that candle closes
    below the leg low). stop = leg low. target 2R. max_hold 10 x 15m... see P.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "ict-2022-mentorship-model"
P = {"pool_tf": "15min", "exec_tf": "1min", "swing": "2/2", "disp_N": 4, "disp_r": 1.5,
     "disp_d": 0.65, "disp_wait_bars": 60, "discount_level": 0.5, "entry_wait_bars": 60,
     "stop": "leg low/high (the sweep extreme)", "rr": 2.0, "max_hold": "150min"}


def _swings(h, l):
    n = len(h)
    ish = np.zeros(n, bool)
    isl = np.zeros(n, bool)
    if n >= 5:
        m = slice(2, n - 2)
        ish[m] = (h[m] > h[1:n - 3]) & (h[m] > h[0:n - 4]) & (h[m] >= h[3:n - 1]) & (h[m] >= h[4:n])
        isl[m] = (l[m] < l[1:n - 3]) & (l[m] < l[0:n - 4]) & (l[m] <= l[3:n - 1]) & (l[m] <= l[4:n])
    return ish, isl


def _current_level(flag, px):
    """Level of the most recent swing whose confirmation (bar i+2) closed by bar j-1."""
    n = len(px)
    pos = np.where(flag)[0]
    eff = pos + 3
    ok = eff < n
    lvl = np.full(n, np.nan)
    lvl[eff[ok]] = px[pos[ok]]
    return pd.Series(lvl).ffill().to_numpy()


def detect(m1):
    b15 = cl.build_bars(m1, P["pool_tf"])
    b1 = cl.build_bars(m1, P["exec_tf"])
    o, h, l, c = (b1[k].to_numpy() for k in ("open", "high", "low", "close"))
    st = b1.index.asi8
    ct = pd.DatetimeIndex(b1["close_time"])
    n = len(b1)
    # 15m pools, mapped onto M1: level current at an M1 candle's start
    h15, l15 = b15["high"].to_numpy(), b15["low"].to_numpy()
    ct15 = pd.DatetimeIndex(b15["close_time"]).asi8
    ish15, isl15 = _swings(h15, l15)
    # 1m short-term swings
    ish1, isl1 = _swings(h, l)
    sth = _current_level(ish1, h)
    stl = _current_level(isl1, l)
    N, R, D = P["disp_N"], P["disp_r"], P["disp_d"]
    rows = []
    for d, flag15, px15 in ((1, isl15, l15), (-1, ish15, h15)):
        pos = np.where(flag15)[0]
        pos = pos[pos + 2 < len(b15)]
        conf = ct15[pos + 2]                      # usable from this close
        lvls = px15[pos]
        for q in range(len(pos)):
            a = np.searchsorted(st, conf[q], "left")
            # the pool is live until the next 15m swing of the same side is usable
            z = np.searchsorted(st, conf[q + 1], "left") if q + 1 < len(pos) else n
            if a >= z:
                continue
            seg = l[a:z] < lvls[q] if d == 1 else h[a:z] > lvls[q]
            hit = np.flatnonzero(seg)
            if not len(hit):
                continue
            s = a + hit[0]                        # M1 candle that takes the pool
            ext_i = s
            done = False
            j = s + 1
            while j < min(n, s + 1 + P["disp_wait_bars"]) and not done:
                if (d == 1 and l[j] < l[ext_i]) or (d == -1 and h[j] > h[ext_i]):
                    ext_i = j
                    j += 1
                    continue
                ref = sth[j] if d == 1 else stl[j]
                if not np.isfinite(ref) or not ((c[j] > ref) if d == 1 else (c[j] < ref)):
                    j += 1
                    continue
                # structural break at j; magnitude window j..j+N-1
                if j + N - 1 >= n or j - N < 0:
                    done = True
                    break
                wh, wl = h[j:j + N].max(), l[j:j + N].min()
                pre = h[j - N:j].max() - l[j - N:j].min()
                dist = (wh - ref) if d == 1 else (ref - wl)
                done = True
                if pre <= 0 or (wh - wl) / pre < R or dist / pre < D:
                    break
                w_end = j + N - 1
                leg_ext = l[ext_i] if d == 1 else h[ext_i]
                leg_far = h[ext_i:w_end + 1].max() if d == 1 else l[ext_i:w_end + 1].min()
                eq = leg_ext + P["discount_level"] * (leg_far - leg_ext)
                best = None
                for k in range(ext_i + 2, w_end + 1):
                    if d == 1 and l[k] > h[k - 2]:
                        top = l[k]
                        if top <= eq and (best is None or top > best):
                            best = top
                    if d == -1 and h[k] < l[k - 2]:
                        bot = h[k]
                        if bot >= eq and (best is None or bot < best):
                            best = bot
                if best is None:
                    break
                for e in range(w_end + 1, min(n, w_end + 1 + P["entry_wait_bars"])):
                    if (d == 1 and l[e] < leg_ext) or (d == -1 and h[e] > leg_ext):
                        break
                    if (d == 1 and l[e] <= best) or (d == -1 and h[e] >= best):
                        rows.append((ct[e], d, leg_ext, st[s]))
                        break
                break
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr"]
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "pool_t"])
    ev["decision_time"] = pd.to_datetime(ev["decision_time"], utc=True)
    ev["available_at"] = ev["decision_time"]
    ev["rr"] = P["rr"]
    ev = ev.sort_values(["decision_time", "direction"]).drop_duplicates(
        ["decision_time", "direction"]).reset_index(drop=True)
    return ev[cols]


if __name__ == "__main__":
    ev = cl.cache_frame("ict2022_15m_pool_1m_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "pool: 15m 2/2 swing low/high, taken by an M1 candle; trade away from it",
        "1m: first close through the latest confirmed 1m 2/2 short-term high/low within 60 "
        "candles, with N=4 displacement magnitude (r>=1.5, d>=0.65)",
        "FVG formed in the leg (leg extreme .. window end) whose near edge is in the discount "
        "(<=0.5) of the displacement range; highest such for longs",
        "entry: first M1 touch of the FVG near edge within 60 candles (cancel if the leg "
        "extreme trades first); stop leg extreme; 2R; 150min time exit"], "params": P}
    src = {"pool_tf": "corpus: Njs-eRpeP9Q liquidity mapped on the 15-minute chart",
           "exec_tf": "corpus: Njs-eRpeP9Q drop to the 1-minute chart",
           "swing": "phase3: 2/2 fractal swings (locked config)",
           "disp_N": "threshold_fits: displacement magnitude N=4 (grade B)",
           "disp_r": "threshold_fits: win_range/pre_range >= 1.5",
           "disp_d": "threshold_fits: distance/pre_range >= 0.65",
           "disp_wait_bars": "declared-before-run: 1h on 1m for the run+displacement",
           "discount_level": "corpus: Njs-eRpeP9Q 'drawing a fib from our displacement range, "
                             "You are entering in a discount'; 0.5 = premium/discount divide "
                             "(method_spec §3.7 EQ)",
           "entry_wait_bars": "declared-before-run: 1h on 1m for the retrace",
           "stop": "declared-before-run: not stated in the video; sweep extreme (method_spec "
                   "§5.1 stop behind already-swept liquidity)",
           "rr": "method_spec: §5.3 2R described as normal",
           "max_hold": "phase3: 10 bars of the pool timeframe (15m) -> 150min"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="Status underspecified: stop/target are declared defaults and "
                              "displacement uses the threshold_fits N-window, not a corpus "
                              "number from this video.")
    print(p)
