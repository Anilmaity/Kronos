"""killzone-execution-sequence (Jokerszn, guest) — trade_test.

Sequence (JABOO4LYNjQ): HTF POI -> kill zone (London or New York; Asia skipped) ->
sweep of the opposing liquidity (session highs/lows, previous-day high/low, Monday
high/low) -> lower-timeframe change in order flow -> entry; entry 1 at the M15/M5
balanced price range, entry 2 on the close through the order block turned breaker,
stop above the session high used for the sweep; targets the previous session lows
(Asia, Monday), previous-week lows, the daily draw.

Operationalised on 15m (bearish; bullish mirrored):
  * sweep: a 15m swing high inside a kill zone trades above the day's Asia high, the
    previous day's high or the week's Monday high, which the day had not traded above
    before that bar;
  * change in order flow / entry 2: a 15m close below the opening price of the up-close
    series that made that high (the order block closed through = breaker), within 3 bars,
    inside the same kill zone -> short at that close;
  * stop = the swept high; target = the nearest of {Asia low, Monday low, previous-day
    low} below the entry close; time exit 150 min.
Entry 1 (the balanced-price-range limit) and the break-even move it implies are not
modelled; the daily-bias / H1-POI stages are not modelled (no mechanical rule given).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from _common import asia_range  # noqa: E402

CID = "killzone-execution-sequence"
P = dict(tf="15min", killzones={"london": ("02:00", "05:00"), "ny": ("07:00", "10:00")},
         cisd=dict(level_rule="series_open", left=2, right=2, max_wait=3),
         liquidity=["asia", "pdh/pdl", "monday"], max_hold="150min", day_open_hour=18)


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "kz"]
    b = cl.build_bars(m1, P["tf"])
    if len(b) < 20:
        return pd.DataFrame(columns=cols)
    ev = cisd_events(b[["open", "high", "low", "close"]], **P["cisd"])
    if ev.empty:
        return pd.DataFrame(columns=cols)
    idx = pd.DatetimeIndex(b.index)
    ct = pd.DatetimeIndex(b["close_time"])
    pos_x = idx.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    pos_c = idx.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    tx = idx[pos_x]
    dec = ct[pos_c]
    # kill zone: the swing bar starts inside it and the confirming close is inside it
    kz = np.full(len(ev), "", dtype=object)
    for name, (a, z) in P["killzones"].items():
        zz = f"{int(z[:2]):02d}:{z[3:]}"
        inz = cl.in_window(tx, a, z) & cl.in_window(dec - pd.Timedelta(minutes=1), a, zz)
        kz[inz] = name
    # liquidity levels
    td_b = cl.trading_day(idx)
    tdn = td_b.asi8
    hi, lo = b["high"].to_numpy(float), b["low"].to_numpy(float)
    grp = pd.Series(tdn)
    hi_before = pd.Series(hi).groupby(grp).transform(lambda s: s.cummax().shift(1)).to_numpy()
    lo_before = pd.Series(lo).groupby(grp).transform(lambda s: s.cummin().shift(1)).to_numpy()
    d = cl.build_bars(m1, "1D")
    dtd = pd.DatetimeIndex(d["trading_day"])
    dct = pd.DatetimeIndex(d["close_time"]).as_unit("ns").asi8
    dh, dl, dn = d["high"].to_numpy(), d["low"].to_numpy(), d["n_m1"].to_numpy()
    td_x = td_b[pos_x]
    txn = tx.as_unit("ns").asi8
    p_prev = np.searchsorted(dtd.asi8, td_x.as_unit(dtd.unit).asi8, "left") - 1
    okp = (p_prev >= 0)
    pc = np.clip(p_prev, 0, None)
    okp &= (dct[pc] <= txn) & (dn[pc] >= 600)
    pdh, pdl = np.where(okp, dh[pc], np.nan), np.where(okp, dl[pc], np.nan)
    # Monday of the current week (session date = trading_day + 1 day)
    sdate = pd.DatetimeIndex(dtd) + pd.Timedelta(days=1)
    d_mon = sdate.dayofweek == 0
    cur_sd = pd.DatetimeIndex(td_x) + pd.Timedelta(days=1)
    week_mon = cur_sd.normalize() - pd.to_timedelta(cur_sd.dayofweek, unit="D")
    mon_rows = pd.Series(np.flatnonzero(d_mon), index=sdate[d_mon].normalize())
    mon_rows = mon_rows[~mon_rows.index.duplicated()]
    mp = mon_rows.reindex(week_mon).to_numpy()
    okm = ~np.isnan(mp) & (cur_sd.dayofweek.to_numpy() > 0)
    mpi = np.where(okm, mp, 0).astype(int)
    okm &= (dct[mpi] <= txn)
    mh, ml = np.where(okm, dh[mpi], np.nan), np.where(okm, dl[mpi], np.nan)
    asia = asia_range(m1).reindex(td_x)
    oka = (~asia["asia_done"].isna().to_numpy()) & \
        (pd.DatetimeIndex(asia["asia_done"]).as_unit("ns").asi8 <= txn)
    ah = np.where(oka, asia["asia_high"].to_numpy(), np.nan)
    al = np.where(oka, asia["asia_low"].to_numpy(), np.nan)

    bear = (ev["direction"] == "bearish").to_numpy()
    s = np.where(bear, -1, 1)
    xp = ev["extreme_price"].to_numpy(float)
    before = np.where(bear, hi_before[pos_x], lo_before[pos_x])
    swept = np.zeros(len(ev), bool)
    for up, dn_ in ((ah, al), (pdh, pdl), (mh, ml)):
        L = np.where(bear, up, dn_)
        fresh = np.isnan(before) | (np.where(bear, before <= L, before >= L))
        swept |= np.isfinite(L) & (np.where(bear, xp > L, xp < L)) & fresh
    entry_ref = ev["confirm_close"].to_numpy(float)
    cand = np.vstack([np.where(bear, al, ah), np.where(bear, ml, mh), np.where(bear, pdl, pdh)])
    beyond = np.where(bear, cand < entry_ref, cand > entry_ref) & np.isfinite(cand)
    dist = np.where(beyond, np.abs(cand - entry_ref), np.inf)
    k = np.argmin(dist, axis=0)
    tgt = cand[k, np.arange(len(ev))]
    has_t = np.isfinite(dist.min(axis=0))
    keep = (kz != "") & swept & has_t
    out = pd.DataFrame({"decision_time": dec[keep], "available_at": dec[keep],
                        "direction": s[keep], "stop_px": ev["protected_swing"].to_numpy(float)[keep],
                        "target_px": tgt[keep], "kz": kz[keep].astype(str)})
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_{P}", lambda: detect(cl.load_m1()))
    print(len(ev), ev.kz.value_counts().to_dict(), ev.direction.value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=P["max_hold"])
    op = {"rules": [
        "15m bars; CISD (detectors.cisd, series_open, 2/2 swings, max_wait 3): a close "
        "through the opening price of the opposing-close series that made the swing extreme",
        "kill zone: the swing-extreme bar starts, and the confirming bar closes, inside "
        "London 02:00-05:00 or New York 07:00-10:00 NY (Asia skipped)",
        "sweep of opposing liquidity: the extreme trades beyond that day's Asia range "
        "(20:00-00:00) high/low, the previous day's high/low or the current week's Monday "
        "high/low, which the day had not traded beyond before the extreme bar",
        "entry = next M1 open after the CISD close (his entry 2, close through the order "
        "block turned breaker); stop = the swept extreme; target = nearest of Asia / Monday / "
        "previous-day opposite extreme beyond the entry close (no target -> no trade); "
        "time exit 150 min"],
        "params": P}
    src = {
        "tf": "corpus: JABOO4LYNjQ 'Entry 1 at the M15/M5 balanced price range'; M15 entry "
              "walkthrough (t_talks_02)",
        "killzones": "session_window_fit: forex kill zones London 02:00-05:00, NY AM "
                     "07:00-10:00 (killzones.yaml); he trades EURUSD and never states clock "
                     "times",
        "cisd": "phase3: locked CISD config (conjunction_preregistration 1.8-1.13: "
                "series_open, 2/2, max_wait 3)",
        "liquidity": "corpus: JABOO4LYNjQ 'opposing liquidity (session highs/lows, previous "
                     "day high/low, Monday high/low) is swept'",
        "max_hold": "phase3: 10 entry-TF bars (conjunction_preregistration 1.13) = 150 min on 15m",
        "day_open_hour": "session_window_fit: 18:00 NY daily roll"}
    notes = ("Not modelled: daily bias with confirmed draw, H1 POI refinement, the BPR entry 1 "
             "and the break-even move of entry 1 on the breaker close (so the tested book is "
             "entry 2 alone). 'Order block turned breaker close' operationalised as the "
             "phase-3 CISD close through the opening price of the series that made the swept "
             "extreme.")
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe, notes=notes)
    print(p)
    for k in ("n", "dropped", "verdict", "verdict_detail", "avg_R", "win_rate", "diff", "ci_lo",
              "ci_hi", "p", "ties", "exposure_bars", "halves", "exit_mix"):
        print(k, res.get(k))
