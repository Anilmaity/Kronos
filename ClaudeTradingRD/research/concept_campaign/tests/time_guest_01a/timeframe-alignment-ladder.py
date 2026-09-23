"""timeframe-alignment-ladder (guests: $niper 5aRB_ZY3474, Ash Trades zXtJSSkiNmo, DTR 07lOxv39LdY).

"Monthly level -> watch the daily; weekly -> 4H; daily -> 1H; 4H -> 15m; 1H -> 5m;
15m -> 1m ... judge the reaction only on the paired timeframe."

Measurable (yaml): "whether entries taken on the paired LTF outperform the same entry
taken one or two timeframes lower or higher". gate_test, claim '+', declared before
the run, using $niper's pairs (the only complete ladder). Each pair skips one rung of
the ladder 1D > 4H > 1H > 15m > 5m > 1m, so every HTF level gets three otherwise
identical books: the paired LTF, one rung higher, one rung lower:
    HTF 1D  -> 4h | **1h** | 15m          HTF 4h -> 1h | **15m** | 5m
    HTF 1h  -> 15m | **5m** | 1m
  level     the previous completed HTF bar's low (bullish reaction; high mirrored).
  tag       the first M1 of the current HTF bar trading beyond it.
  reaction  on LTF X, starting with the LTF bar containing the tag: track the running
            extreme; its CISD level = open of the first candle of the contiguous
            down-close run (<= 10 bars, ending <= 2 bars before the extreme bar)
            into it; confirmation = the first later LTF CLOSE above that level
            (a new extreme resets it). Must close within one HTF period after the
            current HTF bar closes (nominal wall-clock period, no future bars read).
  trade     decide at the confirming LTF close, next M1 open; stop = the running
            extreme ('beyond the extreme that tagged the HTF level'); target = the
            previous HTF bar's opposite extreme ('the next opposing pool on the higher
            timeframe'); hold = one HTF period (1D 24h, 4h 4h, 1h 1h) for all three
            LTFs of that HTF. One trade per HTF bar, side and LTF.
  gate      paired LTF vs the two mismatched LTFs; cluster = the HTF level (the three
            books share it).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, show  # noqa: E402

CID = "timeframe-alignment-ladder"
LADDER = {"1D": (("4h", "1h", "15min"), "1h", "24h"),
          "4h": (("1h", "15min", "5min"), "15min", "4h"),
          "1h": (("15min", "5min", "1min"), "5min", "1h")}
PERIOD = {"1D": pd.Timedelta("24h"), "4h": pd.Timedelta("4h"), "1h": pd.Timedelta("1h")}
RUN_MAX = 10
TURN_GAP = 2
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold",
        "htf", "ltf", "paired", "level_id"]


def _ns(x):
    return pd.DatetimeIndex(x).tz_convert("UTC").as_unit("ns").asi8


def _react(xo, xh, xl, xc, xct, k0, dl, last_ns, bull):
    """Scan LTF bars from k0 while close_time <= dl. Returns (k, stop) or None."""
    ext = None
    ext_i = -1
    lvl = None
    n = len(xo)
    k = k0
    while k < n and xct[k] <= dl and xct[k] <= last_ns:
        lo_k, hi_k = xl[k], xh[k]
        new = (ext is None) or (lo_k <= ext if bull else hi_k >= ext)
        if new:
            ext = lo_k if bull else hi_k
            ext_i = k
            lvl = None
            end = k
            q = (lambda i: xc[i] < xo[i]) if bull else (lambda i: xc[i] > xo[i])
            while end >= 0 and not q(end) and k - end <= TURN_GAP:
                end -= 1
            if end >= 0 and q(end) and k - end <= TURN_GAP:
                st = end
                while st > 0 and q(st - 1) and (end - st + 1) < RUN_MAX:
                    st -= 1
                lvl = xo[st]
        elif lvl is not None and k > ext_i and ((xc[k] > lvl) if bull else (xc[k] < lvl)):
            return k, ext
        k += 1
    return None


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=COLS)
    if len(m1) < 3000:
        return empty
    mt = _ns(m1.index)
    ml, mh = m1["low"].to_numpy(), m1["high"].to_numpy()
    last_ns = mt[-1] + 60_000_000_000
    rows = []
    bars = {}
    for htf, (ltfs, paired, hold) in LADDER.items():
        H = cl.build_bars(m1, htf)
        if len(H) < 3:
            continue
        hs, hct = _ns(H.index), _ns(H["close_time"])
        Hh, Hl = H["high"].to_numpy(), H["low"].to_numpy()
        per = PERIOD[htf].value
        i_s = np.searchsorted(mt, hs, side="left")
        i_e = np.searchsorted(mt, hct, side="left")
        for ltf in ltfs:
            if ltf not in bars:
                X = cl.build_bars(m1, ltf)
                bars[ltf] = (_ns(X.index), X["open"].to_numpy().tolist(), X["high"].to_numpy().tolist(),
                             X["low"].to_numpy().tolist(), X["close"].to_numpy().tolist(),
                             _ns(X["close_time"]).tolist())
        for b in range(1, len(H)):
            a, e = i_s[b], i_e[b]
            if e - a < 1:
                continue
            dl = hct[b] + per
            for bull in (True, False):
                lv = Hl[b - 1] if bull else Hh[b - 1]
                seg = ml[a:e] < lv if bull else mh[a:e] > lv
                if not seg.any():
                    continue
                it = a + int(np.argmax(seg))
                t_tag = mt[it]
                tgt = Hh[b - 1] if bull else Hl[b - 1]
                for ltf in ltfs:
                    xs, xo, xh, xl, xc, xct = bars[ltf]
                    k0 = int(np.searchsorted(xs, t_tag, side="right") - 1)
                    if k0 < 0:
                        continue
                    r = _react(xo, xh, xl, xc, xct, k0, dl, last_ns, bull)
                    if r is None:
                        continue
                    k, stop = r
                    rows.append((xct[k], 1 if bull else -1, stop, tgt, hold, htf, ltf, ltf == paired,
                                 f"{htf}|{hs[b]}|{int(bull)}"))
    if not rows:
        return empty
    t = pd.DatetimeIndex(np.array([r[0] for r in rows], dtype="datetime64[ns]")).tz_localize("UTC")
    out = pd.DataFrame({"decision_time": t, "available_at": t,
                        "direction": [r[1] for r in rows], "stop_px": [r[2] for r in rows],
                        "target_px": [r[3] for r in rows],
                        "max_hold": pd.to_timedelta([r[4] for r in rows]),
                        "htf": [r[5] for r in rows], "ltf": [r[6] for r in rows],
                        "paired": np.array([r[7] for r in rows], bool),
                        "level_id": [r[8] for r in rows]})
    return out.sort_values(["decision_time", "htf", "ltf", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print("n", len(ev), "paired share", ev["paired"].mean())
    print(ev.groupby(["htf", "ltf"]).size())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    res = cl.gate_test(ev, "paired", mask_available_at="decision_time", claim="+", cluster="level_id",
                       keep_trades=True)
    show(res)
    brk = {}
    tr = res.get("_trades")
    if tr is not None and "ev_id" in tr.columns:
        tr = tr.assign(htf=ev["htf"].to_numpy()[tr["ev_id"].to_numpy()],
                       ltf=ev["ltf"].to_numpy()[tr["ev_id"].to_numpy()])
        for (hh, ll), g in tr.groupby(["htf", "ltf"]):
            d = {"n": int(len(g)), "avg_R": round(float(g["net_R"].mean()), 4)}
            if "ctrl_mean_R" in g.columns:
                d["diff_vs_ctrl"] = round(float((g["net_R"] - g["ctrl_mean_R"]).mean()), 4)
            brk[f"{hh}->{ll}"] = d
    print("breakdown", brk)
    op = {"rules": [
        "ladder ($niper pairs, each skipping one rung): 1D->{4h,[1h],15m}, 4h->{1h,[15m],5m}, 1h->{15m,[5m],1m}; [] = paired",
        "level = previous completed HTF bar's low (bull) / high (bear); tag = first M1 of the current HTF bar beyond it",
        "reaction on LTF X from the LTF bar containing the tag: running extreme; CISD level = open of the first candle of the "
        "contiguous opposing-close run (<=10, ending <=2 bars before the extreme bar); confirm = first later LTF close through it; "
        "must close within one HTF period after the current HTF bar closes",
        "entry next M1 open; stop = running extreme; target = previous HTF bar's opposite extreme; hold one HTF period",
        "gate: paired LTF (pass) vs the two mismatched LTFs (complement); cluster = HTF level"],
        "params": {"ladder": {k: [list(v[0]), v[1], v[2]] for k, v in LADDER.items()}, "run_max": RUN_MAX,
                   "turn_gap": TURN_GAP, "grid4h": "forex", "level_rule": "series_open"}}
    src = {"ladder": "corpus: 5aRB_ZY3474 $niper pairs 'daily -> 1H; 4H -> 15m; 1H -> 5m' (concept yaml detection_rules); "
                     "hold = one HTF period declared-before-run",
           "run_max": "phase3: detectors/cisd.py _run_into_extreme max_len=10",
           "turn_gap": "phase3: detectors/cisd.py turn candle within 2 bars of the run",
           "grid4h": "session_window_fit: forex 4H grid (concept_lab default)",
           "level_rule": "phase3: meta/conjunction_preregistration.md CISD series_open level (locked config)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__, probe=probe,
                        notes=f"Per HTF->LTF point estimates (diagnostic only, no CI): {brk}. Monthly/weekly rungs not "
                        "tested (too few levels). Stop/target from the concept's execution block.")
    print("wrote", p)
