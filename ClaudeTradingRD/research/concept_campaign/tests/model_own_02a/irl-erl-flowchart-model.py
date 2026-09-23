"""irl-erl-flowchart-model — trade test of the four/five-step IRL/ERL flowchart.

  1. HTF bias: the previous daily candle is a C2 closure (a daily sweep-and-close-back-
     inside, one of the two bias forms shown) in the direction.
  2. One timeframe down (1H): internal range liquidity = a 1H FVG, external = a 1H swing
     high/low (2/2), both from the prior 72 1H bars (3-HTF-candle look-back).
  3. Rotation / reaction point: bullish -> price reaches into a still-untouched bullish 1H
     FVG (IRL) or takes a still-untaken 1H swing low (ERL); mirror for bearish. Only 1H bars
     closed before the reach are read.
  4. Lower timeframe (5m, paired with 1H): a stop raid (the reversal extreme takes out the
     latest 5m 2/2 swing low confirmed before it) then a CISD in the direction.
  5. Kill zone: the extreme bar and the CISD bar both start inside forex London 02:00-05:00
     or NY AM 07:00-10:00 NY.
Execution: enter next M1 open after the CISD close; stop = the protected swing (extreme);
target ~2R; hold to the daily candle close; first setup per side per day.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, c2_flags, in_progress, swings, fvgs, utc  # noqa: E402

CID = "irl-erl-flowchart-model"
LOOKBACK_1H = 72
KZ = ("fx_london", "fx_ny_am")


def _ns(x):
    return cl.data.utc_ns(utc(x)).astype("int64")


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "max_hold"]
    bd = cl.build_bars(m1, "1D")
    b1 = cl.build_bars(m1, "1h")
    b5 = cl.build_bars(m1, "5min")
    ev = cisd(b5, max_wait=3)
    if ev.empty or len(bd) < 3 or len(b1) < 10:
        return pd.DataFrame(columns=cols)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    ext = ev["stop_px"].to_numpy()
    # 1. daily bias
    pday = in_progress(bd, t)
    pc = np.clip(pday, 1, None)
    bull_d, bear_d = c2_flags(bd)
    ok = (pday >= 2) & np.where(d > 0, bull_d[pc - 1], bear_d[pc - 1])
    # 5. kill zone on extreme bar and CISD bar
    kz_e = np.zeros(len(ev), bool)
    kz_c = np.zeros(len(ev), bool)
    for z in KZ:
        kz_e |= cl.in_window(ev["extreme_start"], *cl.KILLZONES[z])
        kz_c |= cl.in_window(ev["confirm_start"], *cl.KILLZONES[z])
    ok &= kz_e & kz_c
    # 4. stop raid on 5m: extreme beyond the latest 5m swing confirmed before the extreme bar
    sh5, sl5, kn5 = swings(b5)
    st5 = _ns(b5.index)
    xi = b5.index.get_indexer(ev["extreme_start"])
    # latest confirmed swing (by close <= extreme start) prices, via forward fill in time
    def last_conf(mask, price):
        idx = np.flatnonzero(mask)
        kt = kn5[idx]
        order = np.argsort(kt, kind="stable")
        idx, kt = idx[order], kt[order]
        p = np.searchsorted(kt, st5[xi], side="right") - 1
        return np.where(p >= 0, price[idx[np.clip(p, 0, None)]], np.nan)
    lsl = last_conf(sl5 & (kn5 >= 0), b5["low"].to_numpy())
    lsh = last_conf(sh5 & (kn5 >= 0), b5["high"].to_numpy())
    ok &= np.where(d > 0, ext < lsl, ext > lsh)
    # 2-3. 1H reaction point, reading only 1H bars closed by the extreme bar's start
    sh1, sl1, kn1 = swings(b1)
    fv = fvgs(b1)
    fv_dir = fv["direction"].to_numpy()
    fv_mid = fv["mid_pos"].to_numpy()
    fv_top, fv_bot = fv["top"].to_numpy(), fv["bottom"].to_numpy()
    fv_kn = _ns(fv["known_at"]) if len(fv) else np.array([], np.int64)
    ct1 = _ns(b1["close_time"].to_numpy())
    h1, l1 = b1["high"].to_numpy(), b1["low"].to_numpy()
    react = np.zeros(len(ev), bool)
    for e in np.flatnonzero(ok):
        te = st5[xi[e]]
        last = np.searchsorted(ct1, te, side="right") - 1      # last 1H bar closed by te
        if last < 2:
            continue
        a = max(0, last - LOOKBACK_1H)
        bull = d[e] > 0
        hit = False
        # ERL: untaken confirmed 1H swing
        sw = np.flatnonzero((sl1 if bull else sh1)[a:last + 1]) + a
        for s in sw[::-1]:
            if kn1[s] < 0 or kn1[s] > te:
                continue
            if bull:
                if ext[e] < l1[s] and (s + 1 > last or l1[s + 1:last + 1].min() >= l1[s]):
                    hit = True
                    break
            else:
                if ext[e] > h1[s] and (s + 1 > last or h1[s + 1:last + 1].max() <= h1[s]):
                    hit = True
                    break
        # IRL: untouched same-side 1H FVG reached into
        if not hit and len(fv):
            sel = np.flatnonzero((fv_dir == (1 if bull else -1)) & (fv_mid >= a)
                                 & (fv_kn <= te))
            for q in sel[::-1]:
                m = fv_mid[q] + 2
                if bull:
                    if (m > last or l1[m:last + 1].min() > fv_top[q]) and ext[e] <= fv_top[q]:
                        hit = True
                        break
                else:
                    if (m > last or h1[m:last + 1].max() < fv_bot[q]) and ext[e] >= fv_bot[q]:
                        hit = True
                        break
        react[e] = hit
    ok &= react
    dclose = utc(bd["close_time"].to_numpy())[pc]
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": ext, "rr": 2.0,
                        "max_hold": pd.Series(dclose - utc(t)).to_numpy(),
                        "_key": pday * 2 + (d > 0)})[ok]
    out = out.sort_values("decision_time").drop_duplicates("_key", keep="first")
    return out.drop(columns="_key").reset_index(drop=True)


def main():
    ev = cl.cache_frame("irlerl_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                    "verdict", "verdict_detail", "exposure_bars", "ties")})
    op = {"rules": [
        "1. bias: previous daily candle (18:00 NY day) is a C2 closure in the direction",
        "2. 1H: IRL = 3-bar FVG, ERL = 2/2 swing extreme, from the prior 72 1H bars",
        "3. reaction: the 5m reversal extreme reaches into a still-untouched same-side 1H FVG "
        "or takes a still-untaken 1H swing low/high (1H bars closed before the extreme only)",
        "4. 5m stop raid: extreme beyond the latest 5m 2/2 swing confirmed before it; then a 5m "
        "CISD (series_open, max_wait 3) in the direction",
        "5. extreme bar and CISD bar both start in forex London 02-05 or NY AM 07-10 NY",
        "enter next M1 open; stop = protected swing (extreme); 2R; hold to daily close; first "
        "setup per side per day"],
        "params": {"bias": "prev daily C2", "mid_tf": "1h", "exec_tf": "5min",
                   "lookback_1h": LOOKBACK_1H, "level_rule": "series_open", "max_wait": 3,
                   "killzones": "fx_london 02-05, fx_ny_am 07-10 NY", "rr": 2.0,
                   "max_hold": "to daily close", "one_per_side_day": True,
                   "day_open_hour": 18}}
    src = {"bias": "corpus: vWv1jAiKjJ4 / kv9aH7fb2Hc bias forms incl. 'a daily sweep-and-close-"
                   "back-inside' (concept preconditions)",
           "mid_tf": "corpus: vWv1jAiKjJ4 'drop ONE timeframe'; method_spec §1.2 daily->1H",
           "exec_tf": "method_spec: §1.2 pairing 1H->5m",
           "lookback_1h": "method_spec: §1.1 three-HTF-candle look-back (hourly -> 3 days)",
           "level_rule": "method_spec: §4.2 first-candle-open default",
           "max_wait": "phase3: locked config max_wait=3",
           "killzones": "session_window_fit: killzones.yaml forex London / NY AM (hours never "
                        "given in the videos; London is the one labelled)",
           "rr": "corpus: TfHlNgAZ_II 'just around a 2R trade'",
           "max_hold": "method_spec: §5.5 time-based exit at the HTF (daily) candle close",
           "one_per_side_day": "method_spec: §2.4 only one CISD per day forms the wick",
           "day_open_hour": "method_spec: §1.4 18:00 canon"}
    print("wrote", cl.write_result(CID, None, res, operationalization=op, params_source=src,
                                   script=__file__, probe=probe,
                                   notes="contested concept tested on its common flowchart "
                                         "(both source definitions agree on steps 1-5; the "
                                         "contested points are the unstated kill-zone hours and "
                                         "the discretionary strong-narrative override, not "
                                         "separable readings). trade_test vs matched controls."))


if __name__ == "__main__":
    main()
