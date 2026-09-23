"""consolidation-sweep-entry — "Trade from the consolidation low after the sweep" (TTrades own voice).

Batch entry_own_04a. trade_test, claim '+'.

Operationalisation (declared BEFORE the first run; the corpus gives no width/length):
  consolidation (30m, the timeframe of IzOQmcgLyA0): W=8 consecutive 30m candles whose
    high-low span <= 1.5 x ATR14(30m) at the window's last close. Active from that close
    until a side is taken or 24h pass; one range at a time.
  sweep: the first 5m candle trading beyond one extreme (a candle taking BOTH = range broken,
    abandon). Low swept -> long idea; high swept -> short idea.
  HTF POI (1H): the swept extreme (lowest low since the sweep, for a long) must sit INSIDE an
    unmitigated same-direction 1H fair value gap (3-candle gap, known at its 3rd candle's
    close, formed <=120 1H bars before the sweep, not traded through its far edge before the
    sweep): "the sweep and the higher-timeframe level must coincide".
  LTF reversal (5m): CISD — a 5m close back through the opening price of the contiguous
    opposing-close series that made the extreme (method spec §4.2 series_open), within 24
    5m candles of the sweep start; abandon if the opposite range extreme trades first.
  decide at the CISD candle close; stop = swept extreme; target = the opposite range extreme
    (the concept's own TP); skip if the target is not beyond the CISD close. max_hold 12h.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
import concept_lab as cl  # noqa: E402

CID = "consolidation-sweep-entry"
P = {"range_tf": "30min", "W": 8, "atr_n": 14, "width_atr": 1.5, "range_expiry": "24h",
     "exec_tf": "5min", "cisd_wait_bars": 24, "poi_tf": "1h", "poi_max_age_bars": 120,
     "stop": "swept extreme", "target": "opposite range extreme", "max_hold": "12h"}


def _fvgs(b):
    h, l = b["high"].to_numpy(), b["low"].to_numpy()
    ct = b["close_time"].to_numpy()
    k = np.arange(2, len(b))
    bull = l[k] > h[k - 2]
    bear = h[k] < l[k - 2]
    out = []
    for sgn, m in ((1, bull), (-1, bear)):
        kk = k[m]
        bot = np.where(sgn == 1, h[kk - 2], h[kk])
        top = np.where(sgn == 1, l[kk], l[kk - 2])
        out.append(pd.DataFrame({"known": pd.to_datetime(ct[kk], utc=True), "sgn": sgn,
                                 "bot": bot, "top": top, "k": kk}))
    return pd.concat(out, ignore_index=True).sort_values("known").reset_index(drop=True)


def _series_level(o, c, i, bullish, max_len=10):
    """Mirror of detectors.cisd._run_into_extreme + series_open level."""
    q = (lambda k: c[k] < o[k]) if bullish else (lambda k: c[k] > o[k])
    end = i
    while end > 0 and not q(end):
        end -= 1
        if i - end > 2:
            return None
    if not q(end):
        return None
    start = end
    while start > 0 and q(start - 1) and (end - start + 1) < max_len:
        start -= 1
    return o[start]


def detect(m1):
    b30 = cl.build_bars(m1, P["range_tf"])
    b5 = cl.build_bars(m1, P["exec_tf"])
    b1h = cl.build_bars(m1, P["poi_tf"])
    # ---- 30m consolidation candidates
    h30, l30, c30 = (b30[k].to_numpy() for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c30[:-1]]
    tr = np.nanmax(np.c_[h30 - l30, np.abs(h30 - pc), np.abs(l30 - pc)], axis=1)
    atr = pd.Series(tr).rolling(P["atr_n"]).mean().to_numpy()
    hi = pd.Series(h30).rolling(P["W"]).max().to_numpy()
    lo = pd.Series(l30).rolling(P["W"]).min().to_numpy()
    ok = (hi - lo) <= P["width_atr"] * atr
    cand_t = pd.DatetimeIndex(b30["close_time"])[ok].asi8
    cand_hi, cand_lo = hi[ok], lo[ok]
    # ---- 1H FVGs
    fv = _fvgs(b1h)
    fv_known = fv["known"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    ct1h = pd.DatetimeIndex(b1h["close_time"]).asi8
    # ---- 5m arrays
    o5, h5, l5, c5 = (b5[k].to_numpy() for k in ("open", "high", "low", "close"))
    st5 = b5.index.asi8
    ct5 = pd.DatetimeIndex(b5["close_time"]).asi8
    expiry = pd.Timedelta(P["range_expiry"]).value
    age_ns = P["poi_max_age_bars"] * pd.Timedelta("1h").value
    rows = []
    ci = 0                               # pointer into consolidation candidates
    state = "idle"
    t_free = np.iinfo(np.int64).min
    n5 = len(b5)
    i = 0
    while i < n5:
        if state == "idle":
            # only ranges whose window closed AFTER the previous range/sweep ended
            while ci < len(cand_t) and cand_t[ci] <= t_free:
                ci += 1
            if ci < len(cand_t) and cand_t[ci] <= st5[i]:
                while ci + 1 < len(cand_t) and cand_t[ci + 1] <= st5[i]:
                    ci += 1
                RH, RL, t_on = cand_hi[ci], cand_lo[ci], cand_t[ci]
                ci += 1
                state = "active"
            else:
                i += 1
                continue
        if state == "active":
            if st5[i] - t_on > expiry:
                state = "idle"
                t_free = st5[i]
                continue
            up, dn = h5[i] > RH, l5[i] < RL
            if up and dn:
                state = "idle"
                t_free = st5[i]
                i += 1
                continue
            if not (up or dn):
                i += 1
                continue
            d = 1 if dn else -1
            s0 = i
            ext_i = i
            state = "sweep"
        if state == "sweep":
            # i is a bar inside the sweep phase; update extreme / check CISD
            if i > s0 and ((d == 1 and h5[i] > RH) or (d == -1 and l5[i] < RL)):
                state = "idle"
                t_free = st5[i]
                i += 1
                continue
            if i - s0 > P["cisd_wait_bars"]:
                state = "idle"
                t_free = st5[i]
                continue
            newext = (l5[i] < l5[ext_i]) if d == 1 else (h5[i] > h5[ext_i])
            if i == s0 or newext:
                ext_i = i
                i += 1
                continue
            # level = open of the opposing-close series into the extreme (cisd.py rule)
            level = _series_level(o5, c5, ext_i, d == 1)
            if level is None:
                i += 1
                continue
            fire = (c5[i] > level) if d == 1 else (c5[i] < level)
            if not fire:
                i += 1
                continue
            # CISD confirmed at bar i -> POI check
            ext = l5[ext_i] if d == 1 else h5[ext_i]
            tgt = RH if d == 1 else RL
            state = "idle"
            t_free = st5[i]
            if (d == 1 and tgt <= c5[i]) or (d == -1 and tgt >= c5[i]):
                i += 1
                continue
            sweep_start = st5[s0]
            lo_k = np.searchsorted(fv_known, sweep_start - age_ns, "left")
            hi_k = np.searchsorted(fv_known, sweep_start, "right")
            poi = False
            for r in range(lo_k, hi_k):
                if fv["sgn"].iat[r] != d:
                    continue
                bot, top = fv["bot"].iat[r], fv["top"].iat[r]
                if not (bot <= ext <= top):
                    continue
                # unmitigated: no 5m trade through the far edge between known and sweep start
                a = np.searchsorted(st5, fv_known[r], "left")
                seg = slice(a, s0)
                if d == 1 and a < s0 and l5[seg].min() < bot:
                    continue
                if d == -1 and a < s0 and h5[seg].max() > top:
                    continue
                poi = True
                break
            if poi:
                rows.append((ct5[i], d, ext, tgt))
            i += 1
            continue
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if not rows:
        return pd.DataFrame(columns=cols)
    ev = pd.DataFrame(rows, columns=["t", "direction", "stop_px", "target_px"])
    ev["decision_time"] = pd.to_datetime(ev["t"], utc=True)
    ev["available_at"] = ev["decision_time"]
    return ev[cols].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("cons_sweep_30m_5m_1hfvg_v1", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars", "ctrl_overlap"):
        print(k, res.get(k))
    op = {"rules": [
        "30m consolidation: 8 candles spanning <= 1.5 x ATR14(30m); active 24h, one at a time",
        "sweep: first 5m candle beyond one extreme (both = abandon); low -> long, high -> short",
        "swept extreme must lie inside an unmitigated same-direction 1H FVG formed <=120 1H "
        "bars before the sweep",
        "5m CISD (close through the open of the opposing-close series into the extreme) within "
        "24 5m candles; abandon if the opposite extreme trades first",
        "decide at CISD close, enter next M1 open; stop swept extreme; target opposite range "
        "extreme; 12h time exit"], "params": P}
    src = {"range_tf": "corpus: IzOQmcgLyA0 consolidation identified on the 30-minute chart",
           "W": "declared-before-run: no minimum candle count in the corpus (ambiguity)",
           "atr_n": "declared-before-run: ATR yardstick for width (trap 6: ATR units)",
           "width_atr": "declared-before-run: no minimum/maximum width in the corpus",
           "range_expiry": "declared-before-run: one trading day",
           "exec_tf": "corpus: concept timeframes.ltf [30m, 5m, 1m]; 5m chosen",
           "cisd_wait_bars": "declared-before-run: 2h on 5m for the reversal to form",
           "poi_tf": "corpus: concept timeframes.htf [1D, 1H]; UBTl7za9obc FVG as the POI",
           "poi_max_age_bars": "declared-before-run: 5 days of 1H candles",
           "stop": "corpus: execution.stop 'Below the swept low'",
           "target": "corpus: execution.targets 'the opposite range extreme' / TP at "
                     "consolidation high",
           "max_hold": "declared-before-run: 12h"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes="'Consolidation vs retracement' is not rule-based in the corpus; "
                              "a tight-span 30m window is the declared stand-in. Reversal "
                              "structure = CISD per method spec §4.2.")
    print(p)
