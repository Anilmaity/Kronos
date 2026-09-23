"""unicorn-entry-model (NickDoesFutures, guest) — trade_test.

Model as stated (G44VpidBD_U): New York AM 09:00-11:30, no new entries after 11:00;
price tags a pre-marked HTF point of interest (a high/low - frequently the Asia range
extreme); a short-term stop run; displacement leaving an FVG with a breaker
overlapping it; LIMIT at the breaker edge; stop at the FVG candle edge or the breaker
itself (never the swing low); 80% off at 2R, rest at 3R.

Operationalised on 5m (his 1H POI -> 5m execution pairing):
  * unicorn = the batch's breaker+FVG detector (_common.py);
  * stop hunt at the POI = the unicorn's lower low (higher high) trades beyond the
    Asia range low (high) of the day or the previous day's low (high);
  * unicorn completes at/after 09:00 NY and before 11:00 NY; the limit (near edge of
    the breaker/FVG overlap) rests until min(60 min, 11:00 NY), cancelled if 2R trades
    first; stop = breaker far edge; target 2R (the 80% leg).
Daily bias is omitted (no mechanical rule is given for it) — both directions traded.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from _common import unicorn_book, ny_at, asia_range  # noqa: E402

CID = "unicorn-entry-model"
P = dict(tf="5min", W=48, fill_min=60, rr=2.0, max_hold="50min", window=("09:00", "11:00"),
         poi="Asia range extreme (20:00-00:00 NY) or previous-day extreme swept by the "
             "unicorn's stop run", day_open_hour=18)


def detect(m1):
    ev = unicorn_book(m1, tf=P["tf"], W=P["W"], fill_min=P["fill_min"], rr=P["rr"],
                      deadline_fn=lambda t: ny_at(t, P["window"][1]))
    if ev.empty:
        return ev
    ct = pd.DatetimeIndex(ev["confirm_time"])
    mod = cl.ny_minute_of_day(ct)
    a0 = int(P["window"][0][:2]) * 60 + int(P["window"][0][3:])
    a1 = int(P["window"][1][:2]) * 60 + int(P["window"][1][3:])
    in_win = (mod >= a0) & (mod < a1)
    # POI levels, all complete before the formation's first swing point
    ta = pd.DatetimeIndex(ev["t_a"])
    td = cl.trading_day(ta)
    asia = asia_range(m1).reindex(td)
    asia_ok = (~asia["asia_done"].isna().to_numpy()) & \
        (pd.DatetimeIndex(asia["asia_done"]).as_unit("ns").asi8 <= ta.as_unit("ns").asi8)
    d = cl.build_bars(m1, "1D")
    dtd = pd.DatetimeIndex(d["trading_day"])
    pos = np.searchsorted(dtd.asi8, td.as_unit(dtd.unit).asi8, "left") - 1   # previous day
    pv = pos >= 0
    pc = np.clip(pos, 0, None)
    pdh = np.where(pv, d["high"].to_numpy()[pc], np.nan)
    pdl = np.where(pv, d["low"].to_numpy()[pc], np.nan)
    pd_ct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8[pc]
    pv &= pd_ct <= ta.as_unit("ns").asi8
    s = ev["direction"].to_numpy()
    sw = ev["sweep_px"].to_numpy()
    lvl_asia = np.where(s > 0, asia["asia_low"].to_numpy(), asia["asia_high"].to_numpy())
    lvl_pd = np.where(s > 0, pdl, pdh)
    hit_asia = asia_ok & (s * (sw - lvl_asia) < 0)
    hit_pd = pv & (s * (sw - lvl_pd) < 0)
    keep = in_win & (hit_asia | hit_pd)
    return ev[keep].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev))
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    op = {"rules": [
        "5m unicorn: 3-candle swings; swing low L1 -> swing high H1 -> lower low below L1 "
        "-> 5m close above H1 (within 48 bars of L1); breaker zone = up-close bodies L1..H1; "
        "a bullish 3-bar FVG from the leg out of the lower low overlapping the zone "
        "(bearish mirror)",
        "stop hunt at a pre-marked high/low: the lower low (higher high) trades beyond that "
        "day's Asia range low (high) or the previous trading day's low (high)",
        "unicorn completes 09:00-11:00 NY; limit at the near edge of the breaker/FVG "
        "overlap rests until min(60 min, 11:00 NY), cancelled if 2R trades first; filled on "
        "first M1 touch, entered at the next M1 open with the planned stop distance",
        "stop = breaker far edge; target 2R (80% leg); time exit 50 min; no daily-bias gate"],
        "params": P}
    src = {
        "tf": "corpus: G44VpidBD_U '1H POI maps to 5m execution' (t_talks_02 study unit)",
        "W": "declared-before-run: unicorn formation window 48 bars, as the batch's base book",
        "fill_min": "declared-before-run: limit rests 12 entry-TF bars (60 min), cut at 11:00",
        "rr": "corpus: G44VpidBD_U 'takes 80% at 2R, the rest at 3R' - the 80% leg",
        "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 50 min on 5m",
        "window": "corpus: G44VpidBD_U 'New York AM kill zone, 9:00-11:30; no new entries "
                  "after 11:00'",
        "poi": "corpus: G44VpidBD_U 'short-term stop run (often the Asia range high/low)'; "
               "POIs 'a high/low, an FVG...' - highs/lows reading",
        "day_open_hour": "session_window_fit: 18:00 NY daily roll; Asia 20:00-00:00 per "
                         "concept_lab SESSION_WINDOWS"}
    notes = ("Daily bias omitted (no mechanical derivation given; phase 3 found bias gates add "
             "nothing). The 20% 3R leg is not modelled; the book is the 80% 2R leg. Limit "
             "fills emulated at the next M1 open after the touch. FVG-POI and volume-imbalance "
             "POIs not modelled - only the high/low POIs.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "verdict", "verdict_detail", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi",
              "p", "ties", "exposure_bars", "halves", "control"):
        print(k, res.get(k))
