"""fractal-c2-unicorn-pairing (guest: DTR, 07lOxv39LdY).

"you would pair a 15 minute C2 with a 1 minute unicorn, a 1 hour C2 with a 5 minute
unicorn, a 4 hour C2 with a 15-minute unicorn and so on ... the C2 unicorn can be used
fractally just like the fractal model can."

Claim: the C2U works at every listed pairing (it is fractal). trade_test, claim '+',
on the POOLED book of the three stated pairings, against the matched random-entry
control. Operationalisation = the batch model_guest_01b c2-unicorn book (1H/5m),
generalised to each pairing with every bar-count knob held in C2 / unicorn bars
(declared before the run):
  C2       the current C2-TF candle trades below the previous candle's low (bull;
           bearish mirrored); the trade is taken INSIDE C2 before it closes.
  POI      the C2 extreme so far tags a level not reached by C1: PDL/PWL, the last
           completed Asia/London/NY-AM session low, a C2-TF 2/2 swing low confirmed
           before C2 opened (<= 48 C2 bars old), or the top of a bullish C2-TF FVG
           (<= 48 C2 bars old, completed before C2).
  unicorn  on the paired TF: breaker = highest-high unicorn bar in the 12 bars before
           the C2 low; confirm on a close above it with a bullish FVG after the low
           overlapping the breaker's [body low, high]; breaker->confirm <= 12 bars;
           confirmation closes inside C2. First per C2 candle per direction.
  entry    next M1 open; stop = the C2 extreme so far; target 2R; hold = 4 C2 bars
           (15m -> 1h, 1h -> 4h, 4h -> 16h).
A separate per-pairing breakdown is printed for the notes (not separate verdicts).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, show, swings_confirmed  # noqa: E402

CID = "fractal-c2-unicorn-pairing"
PAIRS = (("15min", "1min", "1h"), ("1h", "5min", "4h"), ("4h", "15min", "16h"))
COUNT_MAX = 12
BREAKER_LOOKBACK = 12
POI_AGE = 48
RR = 2.0
SESSIONS = ("asia", "london", "ny_am")
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold", "pairing"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def detect_pair(m1: pd.DataFrame, c2_tf: str, u_tf: str, hold: str) -> pd.DataFrame:
    empty = pd.DataFrame(columns=COLS)
    H = cl.build_bars(m1, c2_tf)
    F = cl.build_bars(m1, u_tf)
    if len(H) < 60 or len(F) < 200:
        return empty
    hs = _ns(H.index)
    Hh, Hl = H["high"].to_numpy(), H["low"].to_numpy()
    fs = _ns(F.index)
    fct = _ns(F["close_time"])
    o, h, l, c = (F[k].to_numpy().tolist() for k in ("open", "high", "low", "close"))
    hid = np.searchsorted(hs, fs, side="right") - 1
    t_open = pd.DatetimeIndex(H.index)
    D = cl.build_bars(m1, "1D")
    W = cl.build_bars(m1, "1W")
    pdd = cl.asof(D, t_open)
    pww = cl.asof(W, t_open)
    lv_lo = [pdd["low"].to_numpy(), pww["low"].to_numpy()]
    lv_hi = [pdd["high"].to_numpy(), pww["high"].to_numpy()]
    for s in SESSIONS:
        ph = cl.prior_hilo(t_open, s, m1=m1)
        lv_lo.append(ph["low"].to_numpy())
        lv_hi.append(ph["high"].to_numpy())
    lv_lo = np.vstack(lv_lo).T
    lv_hi = np.vstack(lv_hi).T
    sw = swings_confirmed(H)
    sw_conf = _ns(sw["conf"].fillna(pd.Timestamp("2100-01-01", tz="UTC")))
    shi = np.flatnonzero(sw["sh"].to_numpy())
    sli = np.flatnonzero(sw["sl"].to_numpy())
    kk = np.arange(2, len(H))
    bull_k = kk[Hl[kk] > Hh[kk - 2]]
    bear_k = kk[Hh[kk] < Hl[kk - 2]]
    bull_top = Hl[bull_k]
    bear_bot = Hh[bear_k]

    rows = []
    starts = np.searchsorted(hid, np.arange(len(H)), side="left")
    ends = np.searchsorted(hid, np.arange(len(H)), side="right")
    for hi_ in range(1, len(H)):
        s, e = starts[hi_], ends[hi_]
        if e - s < 3:
            continue
        pl, ph_ = Hl[hi_ - 1], Hh[hi_ - 1]
        t0 = hs[hi_]
        lows = [x for x in lv_lo[hi_] if not np.isnan(x)]
        highs = [x for x in lv_hi[hi_] if not np.isnan(x)]
        a, b = np.searchsorted(sli, hi_ - POI_AGE), np.searchsorted(sli, hi_)
        lows += [Hl[j] for j in sli[a:b] if sw_conf[j] <= t0]
        a, b = np.searchsorted(shi, hi_ - POI_AGE), np.searchsorted(shi, hi_)
        highs += [Hh[j] for j in shi[a:b] if sw_conf[j] <= t0]
        a, b = np.searchsorted(bull_k, hi_ - POI_AGE), np.searchsorted(bull_k, hi_)
        fb = bull_top[a:b].tolist()
        a, b = np.searchsorted(bear_k, hi_ - POI_AGE), np.searchsorted(bear_k, hi_)
        fr = bear_bot[a:b].tolist()
        for direc in (1, -1):
            for j in range(s, e):
                if direc == 1:
                    seg = l[s:j + 1]
                    L = min(seg)
                    if not L < pl:
                        continue
                    kL = s + seg.index(L)
                    if j <= kL or kL - BREAKER_LOOKBACK < 0:
                        continue
                    win = h[kL - BREAKER_LOOKBACK:kL]
                    kb = kL - BREAKER_LOOKBACK + win.index(max(win))
                    if not c[j] > h[kb] or j - kb > COUNT_MAX:
                        continue
                    zlo, zhi = min(o[kb], c[kb]), h[kb]
                    if not any(l[i] > h[i - 2] and l[i] >= zlo and h[i - 2] <= zhi
                               for i in range(kL + 2, j + 1)):
                        continue
                    if not (any(L <= x <= pl for x in lows) or any(L <= x <= pl for x in fb)):
                        continue
                    rows.append((fct[j], 1, L))
                    break
                else:
                    seg = h[s:j + 1]
                    Hx = max(seg)
                    if not Hx > ph_:
                        continue
                    kH = s + seg.index(Hx)
                    if j <= kH or kH - BREAKER_LOOKBACK < 0:
                        continue
                    win = l[kH - BREAKER_LOOKBACK:kH]
                    kb = kH - BREAKER_LOOKBACK + win.index(min(win))
                    if not c[j] < l[kb] or j - kb > COUNT_MAX:
                        continue
                    zlo, zhi = l[kb], max(o[kb], c[kb])
                    if not any(h[i] < l[i - 2] and h[i] <= zhi and l[i - 2] >= zlo
                               for i in range(kH + 2, j + 1)):
                        continue
                    if not (any(ph_ <= x <= Hx for x in highs) or any(ph_ <= x <= Hx for x in fr)):
                        continue
                    rows.append((fct[j], -1, Hx))
                    break
    if not rows:
        return empty
    t = pd.DatetimeIndex(np.array([r[0] for r in rows], dtype="datetime64[ns]")).tz_localize("UTC")
    return pd.DataFrame({"decision_time": t, "available_at": t, "direction": [r[1] for r in rows],
                         "stop_px": [r[2] for r in rows], "rr": RR, "max_hold": pd.Timedelta(hold),
                         "pairing": f"{c2_tf}/{u_tf}"})


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    parts = [detect_pair(m1, a, b, hld) for a, b, hld in PAIRS]
    parts = [p for p in parts if len(p)]
    if not parts:
        return pd.DataFrame(columns=COLS)
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["decision_time", "pairing", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), ev["pairing"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.trade_test(ev, claim="+", keep_trades=True)
    show(res)
    tr = res.get("_trades")
    brk = {}
    if tr is not None:
        print("trade cols", tr.columns.tolist())
        tr = tr.assign(pairing=ev["pairing"].to_numpy()[tr["ev_id"].to_numpy()])
        if True:
            for pr_, g in tr.groupby("pairing"):
                brk[pr_] = {"n": int(len(g)), "avg_R": round(float(g["net_R"].mean()), 4),
                            "diff_vs_ctrl": round(float((g["net_R"] - g["ctrl_mean_R"]).mean()), 4)}
    print("breakdown", brk)
    op = {"rules": [
        "pairings pooled: 15m C2 / 1m unicorn, 1h C2 / 5m unicorn, 4h C2 / 15m unicorn (forex 4h grid)",
        "C2 = current C2-TF candle sweeps the previous candle's low (bull) / high (bear); trade inside C2 before it closes",
        "POI: the C2 extreme so far tags, first vs C1, one of PDL/PWL, last Asia/London/NY-AM session low, a C2-TF 2/2 swing low "
        "confirmed before C2 (<= 48 C2 bars), or the top of a bullish C2-TF FVG (<= 48 C2 bars); bearish mirrored",
        "unicorn on the paired TF: breaker = highest-high bar in the 12 bars before the C2 low; confirm on a close above it with a "
        "bullish FVG after the low overlapping the breaker's [body low, high]; breaker->confirm <= 12 bars",
        "entry next M1 open after the confirming close; stop at the C2 extreme so far; 2R; hold 4 C2 bars; first per C2 per direction"],
        "params": {"pairs": [list(p) for p in PAIRS], "count_max": COUNT_MAX, "breaker_lookback": BREAKER_LOOKBACK,
                   "poi_age_bars": POI_AGE, "rr": RR, "hold_c2_bars": 4, "swing": "2/2 on the C2 TF",
                   "sessions": list(SESSIONS), "grid4h": "forex"}}
    src = {"pairs": "corpus: 07lOxv39LdY 'pair a 15 minute C2 with a 1 minute unicorn a 1H hour C2 with a 5 minute unicorn a 4our C2 with a 15-minute unicorn'",
           "count_max": "corpus: 07lOxv39LdY 'within that 10 to 12 candle range or even less'",
           "breaker_lookback": "declared-before-run: same 12-bar budget as c2-unicorn (model_guest_01b)",
           "poi_age_bars": "declared-before-run: c2-unicorn's 48h POI age at 1h, held at 48 C2 bars for every pairing",
           "rr": "corpus: 07lOxv39LdY 'grab my two to two and a half R' (lower end)",
           "hold_c2_bars": "declared-before-run: c2-unicorn's 4h hold at 1h, held at 4 C2 bars for every pairing",
           "swing": "declared-before-run: 2/2 fractal swings, phase-3 locked config",
           "sessions": "session_window_fit: SESSION_WINDOWS asia 20-00, london 02-05, ny_am 08:30-12 (NY)",
           "grid4h": "session_window_fit: forex 4H grid (17/21/01/05/09/13 NY), concept_lab default"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__, probe=probe,
                        notes="Pooled across the three stated pairings; 1h/5m sub-book = the c2-unicorn book. Per-pairing "
                        f"point estimates (diagnostic only, no CI): {brk}. No stop stated in the video: stop at the C2 extreme. "
                        "Re-run once with an identical test only to fill this diagnostic (first run mapped no pairings).")
    print("wrote", p)
