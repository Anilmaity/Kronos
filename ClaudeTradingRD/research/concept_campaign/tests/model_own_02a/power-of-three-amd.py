"""power-of-three-amd — two readings, each a trade test.

a  SESSION AMD ('Asia accumulate, London manipulate, New York distribute', Pcbyc9TdNsU;
   range-level 'you fail one side of the range you want to see the other side', 5rbFskdmEmU):
   accumulation = the Asia range (forex Asia 20:00-00:00 NY high/low). Manipulation = a
   London (02:00-05:00 NY) excursion beyond ONE side of it whose extreme is a 15m swing.
   Confirmation = the aggressive return: a 15m CISD against the excursion whose confirming
   close is back INSIDE the Asia range (between 02:00 and 10:00 NY), with the other side of
   the range still untouched since midnight. Distribution target = the OTHER side of the Asia
   range. Stop = the manipulation extreme. Hold to the daily close. One per day.
b  CANDLE-LEVEL AMD ON THE DAILY OPEN (YXoNowXQirM; 'bullish daily = open, low (manipulation
   below the opening price), high, close'): the day trades beyond its 18:00 open (manipulation);
   a 15m CISD in the opposite direction whose extreme is the day's extreme so far and whose
   confirming close is back through the opening price. Stop = that extreme; target = the -2
   standard-deviation projection of the manipulation leg (open +/- 2 x |open - extreme|,
   method_spec §5.2 first target band). Hold to the daily close. First per day.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import concept_lab as cl    # noqa: E402
from _common import cisd, in_progress, utc  # noqa: E402

CID = "power-of-three-amd"
SD_TARGET = 2.0
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]


def _finish(t, d, stop, tgt, dclose, key, ok):
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": d,
                        "stop_px": stop, "target_px": tgt,
                        "max_hold": pd.Series(dclose - utc(t)).to_numpy(), "_k": key})[ok]
    out = out[out["max_hold"] > pd.Timedelta(0)]
    out = out.sort_values("decision_time").drop_duplicates("_k", keep="first")
    return out.drop(columns="_k").reset_index(drop=True)


def detect_a(m1):
    b15 = cl.build_bars(m1, "15min")
    bd = cl.build_bars(m1, "1D")
    ev = cisd(b15, max_wait=3)
    if ev.empty or len(bd) < 2:
        return pd.DataFrame(columns=COLS)
    asia = cl.window_hilo(cl.KILLZONES["fx_asia"], m1)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    ext = ev["stop_px"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    td = cl.trading_day(t)
    a = asia.reindex(td)
    ahi, alo = a["high"].to_numpy(float), a["low"].to_numpy(float)
    a_av = pd.DatetimeIndex(a["available_at"])
    ok = ~np.isnan(ahi) & np.asarray(a_av <= t)
    # manipulation extreme formed in London; confirmation 02:00-10:00 NY
    ok &= cl.in_window(ev["extreme_start"], *cl.KILLZONES["fx_london"])
    ok &= cl.in_window(ev["confirm_start"], "02:00", "10:00")
    ok &= np.asarray(cl.trading_day(ev["extreme_start"]) == td)
    # bearish: excursion above Asia high, close back inside; bullish mirrored
    ok &= np.where(d < 0, (ext > ahi) & (px < ahi) & (px > alo),
                   (ext < alo) & (px > alo) & (px < ahi))
    # the other side untouched since midnight NY (15m bars from 00:00 to the confirm bar)
    mod = cl.ny_minute_of_day(b15.index)
    post = mod < 17 * 60                                   # after midnight, same trading day
    tday15 = cl.trading_day(b15.index)
    key = pd.Series(np.where(post, tday15.asi8, -1))
    rhi = pd.Series(np.where(post, b15["high"], -np.inf)).groupby(key).cummax().to_numpy()
    rlo = pd.Series(np.where(post, b15["low"], np.inf)).groupby(key).cummin().to_numpy()
    j = b15.index.get_indexer(ev["confirm_start"])
    ok &= np.where(d < 0, rlo[j] > alo, rhi[j] < ahi)
    tgt = np.where(d < 0, alo, ahi)
    pday = in_progress(bd, t)
    dclose = utc(bd["close_time"].to_numpy())[np.clip(pday, 0, None)]
    ok &= pday >= 0
    return _finish(t, d, ext, tgt, dclose, pday, ok)


def detect_b(m1):
    b15 = cl.build_bars(m1, "15min")
    bd = cl.build_bars(m1, "1D")
    ev = cisd(b15, max_wait=3)
    if ev.empty or len(bd) < 2:
        return pd.DataFrame(columns=COLS)
    t = ev["decision_time"]
    d = ev["direction"].to_numpy()
    ext = ev["stop_px"].to_numpy()
    px = ev["confirm_close"].to_numpy()
    pday = in_progress(bd, t)
    pc = np.clip(pday, 0, None)
    dopen = bd["open"].to_numpy()[pc]
    xday = in_progress(bd, ev["extreme_start"])
    bday = in_progress(bd, b15.index)
    key = pd.Series(bday)
    rhi = pd.Series(b15["high"].to_numpy()).groupby(key).cummax().to_numpy()
    rlo = pd.Series(b15["low"].to_numpy()).groupby(key).cummin().to_numpy()
    j = b15.index.get_indexer(ev["confirm_start"])
    ok = (pday >= 0) & (xday == pday)
    # bullish: extreme below the open and = day low so far; confirming close back above open
    ok &= np.where(d > 0, (ext < dopen) & (ext <= rlo[j]) & (px > dopen),
                   (ext > dopen) & (ext >= rhi[j]) & (px < dopen))
    tgt = dopen + d * SD_TARGET * np.abs(dopen - ext)
    ok &= np.where(d > 0, tgt > px, tgt < px)
    dclose = utc(bd["close_time"].to_numpy())[pc]
    return _finish(t, d, ext, tgt, dclose, pday, ok)


BASE_SRC = {"exec_tf": "method_spec: §2.4 London/NY wick confirmation on 15m; §1.2 4H->15m",
            "level_rule": "method_spec: §4.2 first-candle-open default (CISD = the aggressive "
                          "return + structure break the box setup requires)",
            "max_wait": "phase3: locked config max_wait=3",
            "max_hold": "method_spec: §5.5 time-based exit at the HTF (daily) candle close",
            "one_per_day": "method_spec: §2.4 only one CISD per day forms the daily wick",
            "day_open_hour": "method_spec: §1.4 18:00 canon"}
BASE_PARAMS = {"exec_tf": "15min", "level_rule": "series_open", "max_wait": 3,
               "max_hold": "to daily close", "one_per_day": True, "day_open_hour": 18}


def run(reading, fn, key):
    ev = cl.cache_frame(key, lambda: fn(cl.load_m1()))
    print(reading, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(fn, ev, lookback="20D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                    "verdict", "verdict_detail", "exposure_bars", "ties")})
    return res, probe


def main(only=None):
    if only in (None, "a"):
        res, probe = run("a", detect_a, "po3_session_v1")
        op = {"rules": [
            "accumulation: Asia range = high/low of M1 bars 20:00-00:00 NY of the trading day",
            "manipulation: a 15m swing extreme formed in London 02:00-05:00 NY beyond one side "
            "of the Asia range",
            "confirmation: a 15m CISD (series_open, 2/2, max_wait 3) against the excursion, "
            "confirming 02:00-10:00 NY, closing back inside the Asia range; the other side of "
            "the Asia range untouched since 00:00 NY",
            "enter next M1 open; stop = manipulation extreme; target = the opposite Asia "
            "extreme; hold to the daily close; one per day"],
            "params": {**BASE_PARAMS, "asia": "20:00-00:00 NY", "london": "02:00-05:00 NY",
                       "confirm_window": "02:00-10:00 NY",
                       "target": "opposite side of the Asia range"}}
        src = {**BASE_SRC,
               "asia": "session_window_fit: killzones.yaml forex Asia 20:00-00:00",
               "london": "session_window_fit: killzones.yaml forex London 02:00-05:00",
               "confirm_window": "declared-before-run: London open through the end of the "
                                 "forex NY AM kill zone (10:00) — NY distributes",
               "target": "corpus: 5rbFskdmEmU 'you fail one side of the range you want to see "
                         "the other side'"}
        print("wrote", cl.write_result(CID, "a", res, operationalization=op, params_source=src,
                                       script=__file__, probe=probe,
                                       notes="session AMD reading; trade_test vs matched "
                                             "controls (same stop/target distance, same hold)."))
    if only in (None, "b"):
        res, probe = run("b", detect_b, "po3_dailyopen_v1")
        op = {"rules": [
            "day = 18:00 NY trading day; opening price = the 18:00 open",
            "manipulation: the day trades beyond its open against the eventual direction; the "
            "15m swing extreme of that excursion is the day's extreme so far",
            "distribution trigger: a 15m CISD (series_open, 2/2, max_wait 3) in the opposite "
            "direction whose confirming close is back through the opening price",
            "enter next M1 open; stop = the extreme; target = open +/- 2 x |open - extreme| "
            "(-2 SD of the manipulation leg) and must lie beyond the confirming close; hold to "
            "the daily close; first per day"],
            "params": {**BASE_PARAMS, "anchor": "18:00 daily open", "sd_target": SD_TARGET}}
        src = {**BASE_SRC,
               "anchor": "method_spec: §1.4 18:00 is canon (the older AMD video used midnight)",
               "sd_target": "method_spec: §5.2 standard-deviation projection, -2 to -2.5 band "
                            "is the first target (lower edge used)"}
        print("wrote", cl.write_result(CID, "b", res, operationalization=op, params_source=src,
                                       script=__file__, probe=probe,
                                       notes="candle-level AMD on the daily opening price; "
                                             "trade_test vs matched controls."))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
