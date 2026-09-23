"""relevant-htf-pd-array-test (contested) -> two rate_tests, one per reading.

Source 2ctrcNs4tFo: "London never reached a relevant PD array" -> NY reversal; if London
reached one, the reversal stands in London. Variant (xdzyejskSKE): a London structure
shift with no relevant level behind it "is going to be a fake change in the state of
delivery" - the liquidity there is expected to be run again the same day.

Common event (declared before the first run):
  * London = 02:00-05:00 NY (method_spec 2.5 / SESSION_WINDOWS). A London RUN on a side =
    the London high exceeds the day's high before 02:00 (18:00-02:00 NY), or the London low
    undercuts the pre-London low.
  * London reversal attempt = a 15m CISD (phase-3 config: series_open level, 2/2 swings,
    max_wait 3) whose protected swing IS the London extreme, confirmed by the London close.
  * Relevant HTF PD array = previous trading day's high (for a London high) / low (for a
    London low); reached = wick at or beyond it. (The worked examples also use wick CE,
    daily FVGs and range extremes; only PDH/PDL is mechanical enough to fix in advance.)
  * Prediction at 05:00 NY; horizon = the rest of the trading day in M1 bars.
  * Null: the same level distance from price at 5 random moments within +/-30 days at the
    same NY time of day (+/-30 min), same M1-bar horizon.

Reading a (claim '+'): London extremes that reached PDH/PDL and printed a CISD HOLD
  (are not traded through again) for the rest of the day more often than the null.
Reading b (claim '+'): London CISD extremes that did NOT reach PDH/PDL (fake CISD) ARE
  traded through again the same day more often than the null.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import concept_lab as cl  # noqa: E402
from detectors.cisd import cisd_events  # noqa: E402
from _common import show  # noqa: E402

CID = "relevant-htf-pd-array-test"
COLS = ["decision_time", "available_at", "direction", "level", "reached"]


def detect_all(m1: pd.DataFrame) -> pd.DataFrame:
    lon = cl.window_hilo("london", m1=m1)
    pre = cl.window_hilo(("18:00", "02:00"), m1=m1)
    if lon.empty:
        return pd.DataFrame(columns=COLS)
    lon = lon.join(pre[["high", "low"]].rename(columns={"high": "pre_h", "low": "pre_l"}),
                   how="inner")
    b = cl.build_bars(m1, "15min")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    if ev.empty or lon.empty:
        return pd.DataFrame(columns=COLS)
    ev = ev.assign(confirm_close_time=pd.DatetimeIndex(b.loc[ev["confirm_time"],
                                                             "close_time"]).to_numpy(),
                   td=cl.trading_day(pd.DatetimeIndex(ev["extreme_time"])).to_numpy())
    av = pd.DatetimeIndex(lon["available_at"])
    pdl = cl.prior_hilo(av, "1D", m1=m1)
    rows = []
    for j, (tdk, r) in enumerate(lon.iterrows()):
        sub = ev[ev["td"] == np.datetime64(tdk)]
        for side in (1, -1):
            ext = r["high"] if side > 0 else r["low"]
            if not ((ext > r["pre_h"]) if side > 0 else (ext < r["pre_l"])):
                continue
            want = "bearish" if side > 0 else "bullish"
            s = sub[(sub["direction"] == want) & (sub["extreme_price"] == ext)
                    & (pd.DatetimeIndex(sub["extreme_time"]) >= r["first_m1"])
                    & (pd.DatetimeIndex(sub["confirm_close_time"]) <= av[j])]
            if s.empty:
                continue
            lvl = pdl["high"].iloc[j] if side > 0 else pdl["low"].iloc[j]
            if not np.isfinite(lvl):
                continue
            reached = bool(ext >= lvl) if side > 0 else bool(ext <= lvl)
            rows.append((av[j], side, float(ext), reached))
    if not rows:
        return pd.DataFrame(columns=COLS)
    out = pd.DataFrame(rows, columns=["decision_time", "direction", "level", "reached"])
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = out["decision_time"]
    return out.sort_values(["decision_time", "direction"]).reset_index(drop=True)[COLS]


def detect_a(m1):
    e = detect_all(m1)
    return e[e["reached"].astype(bool)].reset_index(drop=True)


def detect_b(m1):
    e = detect_all(m1)
    return e[~e["reached"].astype(bool)].reset_index(drop=True)


def run(reading, detect, claim_outcome):
    ev = cl.cache_frame(f"{CID}_{reading}", lambda: detect(cl.load_m1()))
    print(reading, len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    dclose = pd.DatetimeIndex(cl.asof(cl.bars("1D"), t, avail_col="first_m1")["close_time"]) \
        if False else None
    d = cl.bars("1D")
    ctn = cl.data.utc_ns(pd.DatetimeIndex(d["close_time"]))
    k = np.searchsorted(ctn, cl.data.utc_ns(t), side="right")      # the current day
    end = pd.DatetimeIndex(d["close_time"].to_numpy()[k]).tz_localize("UTC") \
        if pd.DatetimeIndex(d["close_time"]).tz is None else pd.DatetimeIndex(d["close_time"])[k]
    i0 = mkt.pos_at_or_after(t)
    hb = (mkt.pos_at_or_after(end) - i0).astype(np.int64)
    up = ev["direction"].to_numpy() > 0
    lvl = ev["level"].to_numpy(float)
    p0 = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
    dist = lvl - p0

    def taken(times, level, u, hb_):
        o = np.zeros(len(times))
        for side, sel in (("above", u), ("below", ~u)):
            if sel.any():
                o[sel] = cl.touch(times[sel], level[sel], side,
                                  horizon_bars=hb_[sel])["hit"].to_numpy()
        return o

    tk_obs = taken(t, lvl, up, hb)
    obs = (1 - tk_obs) if claim_outcome == "hold" else tk_obs
    rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=30)

    def null_fn(rng, kk):
        tk = pd.DatetimeIndex(rt[:, kk]).tz_localize("UTC")
        ok = ~tk.isna()
        out = np.full(len(t), np.nan)
        tt = tk[ok]
        px = mkt.o[np.minimum(mkt.pos_at_or_after(tt), len(mkt.o) - 1)]
        x = taken(tt, px + dist[ok], up[ok], hb[ok])
        out[ok] = (1 - x) if claim_outcome == "hold" else x
        return out

    res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                       null_fn=null_fn, predictors=ev)
    print("reading", reading); show(res)
    op = {"rules": [
        "London 02:00-05:00 NY; a run = London high above the 18:00-02:00 high (low below)",
        "London reversal attempt = 15m CISD (series_open, 2/2, max_wait 3) whose protected "
        "swing is the London extreme, confirmed by 05:00",
        "relevant HTF PD array = previous trading day high/low; reached = wick at/beyond",
        ("reading a: reached group; hit = the London extreme is NOT traded through again "
         "for the rest of the trading day" if claim_outcome == "hold" else
         "reading b: not-reached group (fake CISD); hit = the London extreme IS traded "
         "through again the same trading day"),
        "null = same level distance from price at 5 random moments within +/-30 days at "
        "the same NY time (+/-30 min), same M1-bar horizon"],
        "params": {"london": "02:00-05:00", "pre_window": "18:00-02:00", "cisd_tf": "15min",
                   "cisd_max_wait": 3, "htf_level": "PDH/PDL", "horizon": "rest of day",
                   "null_tod_tol_min": 30}}
    src = {"london": "method_spec: 2.5 London 02:00-05:00 (daily-profile-session-windows)",
           "pre_window": "declared-before-run: a London 'run' must take the day's prior "
                         "(Asia/overnight) extreme",
           "cisd_tf": "corpus: daily-wick-confirmation-timeframes - London CISD on 15m or 30m",
           "cisd_max_wait": "phase3: locked CISD config max_wait=3",
           "htf_level": "declared-before-run: 'relevant' undefined; previous day high/low is "
                        "the first level type in the worked examples",
           "horizon": "corpus: xdzyejskSKE / measurable 'taken out again the same day'",
           "null_tod_tol_min": "declared-before-run: the prediction is about a fixed clock "
                               "time (05:00 NY), so the null holds the clock fixed"}
    print(cl.write_result(CID, reading, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="Both branches of the discriminator; a and b use the same "
                                "event family split by the reached flag."))


if __name__ == "__main__":
    run("a", detect_a, "hold")
    run("b", detect_b, "taken")
