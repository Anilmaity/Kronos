"""protected-swing — update u1007 (TTrades, New York Open Live Q&A, 4rNC3QXxC20).

NEW claim only (the protected swing as a trade was tested in structure_own_01b, readings a/b):
  "When would you expect a protected swing to fail and then continue in the direction of
   trend? ... It is when we have taken out some sort of significant liquidity ... we have a
   protected swing here, it takes out that liquidity, then re-sweeps it and then goes."
  He gives no mechanical rule ("I just don't know how to explain it that mechanically").

rate_test. Fixed BEFORE the first run:
  * protected swing = the structure_own_01b reading-a construct: 1h bars, 2/2 swing extreme,
    close through the opposing series' OPEN within 3 bars, POI strict (swept a prior swing or
    reached into an FVG). Confirmed at the 1h closing bar's close.
  * "significant liquidity" = the previous day's high (bullish) / low (bearish), 18:00 NY roll,
    stub days skipped (min_coverage 0.5), still untaken at confirmation (above the highest high
    from the extreme bar through the confirming bar).
  * the liquidity must be taken (M1 touch) within 10h wall-clock of confirmation while the
    protected swing still holds (a same-M1-bar touch of both is dropped). Decision = the close
    of the M1 bar that takes the liquidity.
  * outcome, reading u1007a ("fails / re-sweeps"): price trades through the protected swing
    within 600 M1 bars (10 trading hours) of the decision.
    reading u1007b ("re-sweeps and then goes"): it re-sweeps AND afterwards trades back to the
    decision price (the taken-liquidity zone), still inside the same 600-bar window.

AUDIT 2026-10-07 (vault context), null replaced, events unchanged:
  The first run's null was an ARBITRARY level at the same distance from a random moment.
  Protected swings with NO liquidity take, measured from their own confirmation, already
  score -2.5pp (a) / -2.7pp (b) against that null: a fresh swing extreme is simply touched
  less than an arbitrary level (vault: Concept Campaign 2026-09-23, methodology lesson 1),
  and the real moments ran ~46% hotter (60-bar range) than the null moments (lesson 3).
  So that null measured "protected swing vs arbitrary level", not the claim's condition.
  STRUCTURAL null now: for each event, a protected swing from the SAME base population
  (same detector, same direction, confirmed within +/-30 d, not the event's own swing) at
  the first M1 bar where price has moved the SAME distance (PS -> taken level) away from it
  within 10h, while that swing still holds and its own PDH/PDL is still UNTAKEN. Same
  outcome, same 600-bar horizon, level = that swing. Only the liquidity take differs.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "structure_own_01b"))
import numpy as np           # noqa: E402
import pandas as pd          # noqa: E402

import _common as C          # noqa: E402
import concept_lab as cl     # noqa: E402
from detectors.cisd import cisd_events      # noqa: E402
from detectors.poi import poi_gate          # noqa: E402

CID = "protected-swing"
TF = "1h"
WIN = 200
LIQ_WAIT = pd.Timedelta("10h")
HBARS = 600
NULL_DAYS = pd.Timedelta(days=30)
COLS = ["decision_time", "available_at", "direction", "ps", "liq", "confirm_time"]
BCOLS = ["ct", "ps", "liq", "room", "direction"]


def base_frame(m1):
    """Every POI-strict 1h protected swing whose PDH/PDL is beyond its extreme-to-confirm range."""
    b = cl.build_bars(m1, TF)
    if len(b) < 10:
        return C.empty_frame(BCOLS)
    o = b[C.OHLC]
    ev = cisd_events(o, level_rule="series_open", left=2, right=2, max_wait=3, min_series=1)
    if ev.empty:
        return C.empty_frame(BCOLS)
    ext = b.index.get_indexer(pd.DatetimeIndex(ev["extreme_time"]))
    conf = b.index.get_indexer(pd.DatetimeIndex(ev["confirm_time"]))
    dirs = np.where(ev["direction"].to_numpy() == "bullish", 1, -1)
    keep = np.zeros(len(ev), bool)
    for k, (e, j, dr) in enumerate(zip(ext, conf, ev["direction"].to_numpy())):
        s0 = max(0, j - WIN)
        r = poi_gate(o.iloc[s0: j + 1], int(e - s0), dr, timeframe=TF, setup_type="reversal",
                     require_both_when_both_exist=False, level_rule="series_open")
        keep[k] = bool(r.passed) and (r.kind_used in ("fvg", "swing"))
    ct = pd.DatetimeIndex(b["close_time"].to_numpy()[conf])
    ps = ev["protected_swing"].to_numpy(float)
    hh = np.array([b["high"].to_numpy()[e:j + 1].max() for e, j in zip(ext, conf)])
    ll = np.array([b["low"].to_numpy()[e:j + 1].min() for e, j in zip(ext, conf)])
    ph = cl.prior_hilo(ct, "1D", m1=m1, min_coverage=0.5)
    liq = np.where(dirs == 1, ph["high"].to_numpy(float), ph["low"].to_numpy(float))
    room = np.where(dirs == 1, hh, ll)
    keep &= np.isfinite(liq) & np.where(dirs == 1, liq > hh, liq < ll)
    return pd.DataFrame({"ct": ct[keep], "ps": ps[keep], "liq": liq[keep], "room": room[keep],
                         "direction": dirs[keep]}).reset_index(drop=True)


def first_reach(ct, ps, lvl, liq, dirs, m1=None):
    """First M1 bar within LIQ_WAIT of ct reaching `lvl` while `ps` holds and `liq` is untaken
    (a same-bar touch counts as taken). Returns (valid, decision = that bar's close)."""
    n = len(ct)
    ok = np.zeros(n, bool)
    t_l = np.full(n, np.datetime64("NaT", "ns"))
    until = ct + LIQ_WAIT
    for d, sl, sp in ((1, "above", "below"), (-1, "below", "above")):
        m = dirs == d
        if not m.any():
            continue
        r1 = cl.touch(ct[m], lvl[m], sl, until=until[m], m1=m1)
        r2 = cl.touch(ct[m], ps[m], sp, until=until[m], m1=m1)
        h1, h2 = r1["hit"].to_numpy(), r2["hit"].to_numpy()
        t1 = pd.DatetimeIndex(r1["hit_time"]).tz_convert(None).to_numpy("datetime64[ns]")
        t2 = pd.DatetimeIndex(r2["hit_time"]).tz_convert(None).to_numpy("datetime64[ns]")
        good = h1 & (~h2 | (t2 > t1))
        if liq is not None:
            r3 = cl.touch(ct[m], liq[m], sl, until=until[m], m1=m1)
            t3 = pd.DatetimeIndex(r3["hit_time"]).tz_convert(None).to_numpy("datetime64[ns]")
            good &= ~r3["hit"].to_numpy() | (t3 > t1)
        ok[m] = good
        t_l[m] = t1
    dt = pd.DatetimeIndex(t_l).tz_localize("UTC") + pd.Timedelta(minutes=1)
    return ok, dt


def detect(m1):
    bf = base_frame(m1)
    if bf.empty:
        return C.empty_frame(COLS)
    ct = pd.DatetimeIndex(bf["ct"])
    ps, liq, dirs = bf["ps"].to_numpy(), bf["liq"].to_numpy(), bf["direction"].to_numpy()
    # liquidity taken while the protected swing still holds (strictly earlier M1 bar or never)
    ok, dt = first_reach(ct, ps, liq, None, dirs, m1=m1)
    if not ok.any():
        return C.empty_frame(COLS)
    return pd.DataFrame({"decision_time": dt[ok], "available_at": dt[ok], "direction": dirs[ok],
                         "ps": ps[ok], "liq": liq[ok],
                         "confirm_time": ct[ok]}).reset_index(drop=True)


PARAMS_SOURCE = {
    "protected_swing": "phase3: structure_own_01b reading a construct (1h, 2/2, series_open, max_wait 3, "
                       "POI sweep|fvg) — the library's own protected-swing operationalization",
    "tf": "phase3: structure_own_01b reading a (concept ltf list 1H)",
    "swing": "phase3: §1.8 swing left=2,right=2",
    "level_rule": "phase3: structure_own_01b reading a, close through the series open",
    "max_wait": "phase3: §1.8 max_wait=3 ('1, 2, maybe three')",
    "poi": "corpus: G1IIdQ3RAkY 'we have to sweep out a low or reach into a gap'",
    "liquidity": "corpus: 4rNC3QXxC20 'It is when we have taken out some sort of significant liquidity'; "
                 "same stream 'your reference points are previous day high, previous day low' — "
                 "declared-before-run: PDH/PDL as the significant liquidity",
    "liq_wait": "declared-before-run: 10h = phase3 10 entry-TF bars hold",
    "horizon_bars": "declared-before-run: 600 M1 bars (10 trading hours), phase3 10-bar hold",
    "outcome": "corpus: 4rNC3QXxC20 'It takes out that liquidity then re- sweeps it and then goes' — "
               "a: re-sweep only; b: re-sweep then back to the decision price",
    "null": "declared-before-run (audit 2026-10-07): structural null — the claim is conditional "
            "('when we have taken out some sort of significant liquidity'), so the baseline is a "
            "protected swing at the same distance WITHOUT the take; vault Concept Campaign 2026-09-23 "
            "lesson 1 (matching distance is not matching placement): un-taken protected swings score "
            "-2.5pp/-2.7pp vs the arbitrary-level null, which therefore manufactured the sign",
    "null_window_days": "phase3: locked window_days=30 (+/-30 d regime match)",
    "min_coverage": "declared-before-run: skip stub days (trap 6)",
}


def outcome(mkt, times, px, lvl, dirs, cont):
    """a: `lvl` traded through within HBARS M1 bars; b: and then back to `px` in the same window."""
    out = np.zeros(len(times))
    for d, sp, sb in ((1, "below", "above"), (-1, "above", "below")):
        m = dirs == d
        if not m.any():
            continue
        tt = times[m]
        r = cl.touch(tt, lvl[m], sp, horizon_bars=np.full(m.sum(), HBARS, np.int64))
        h = r["hit"].to_numpy()
        if cont:
            end = mkt.pos_at_or_after(tt) + HBARS
            h2 = np.zeros(len(tt), bool)
            if h.any():
                st = pd.DatetimeIndex(r["hit_time"])[h] + pd.Timedelta(minutes=1)
                rem = np.maximum(end[h] - mkt.pos_at_or_after(st), 0)
                h2[h] = cl.touch(st, px[m][h], sb, horizon_bars=rem)["hit"].to_numpy() & (rem > 0)
            h = h2
        out[m] = h
    return out


def control_pairs(ev, base, mkt):
    """All valid (event i, base swing j) structural-control pairs, with both outcomes."""
    t = pd.DatetimeIndex(ev["decision_time"])
    c = pd.DatetimeIndex(ev["confirm_time"]).asi8
    d = ev["direction"].to_numpy()
    L = (ev["liq"] - ev["ps"]).to_numpy()                 # signed PS -> taken-level distance
    bn = pd.DatetimeIndex(base["ct"]).asi8
    bd, bps, bliq, broom = (base[k].to_numpy() for k in ("direction", "ps", "liq", "room"))
    lo = np.searchsorted(bn, (t - NULL_DAYS).asi8, "left")
    hi = np.searchsorted(bn, (t + NULL_DAYS).asi8, "right")
    I, J = [], []
    for i in range(len(ev)):
        j = np.arange(lo[i], hi[i])
        trig = bps[j] + L[i]
        j = j[(bd[j] == d[i]) & (bn[j] != c[i]) & np.where(d[i] == 1, trig > broom[j], trig < broom[j])]
        I.append(np.full(len(j), i)); J.append(j)
    I, J = np.concatenate(I), np.concatenate(J)
    ct = pd.DatetimeIndex(base["ct"])[J]
    ok, dt = first_reach(ct, bps[J], bps[J] + L[I], bliq[J], bd[J])
    I, J, dt = I[ok], J[ok], dt[ok]
    px = mkt.o[np.minimum(mkt.pos_at_or_after(dt), len(mkt.o) - 1)]
    oa = outcome(mkt, dt, px, bps[J], bd[J], False)
    ob = outcome(mkt, dt, px, bps[J], bd[J], True)
    return I, dt, oa, ob


def run_all():
    ev = cl.cache_frame("u1007_ps_liq_1h", lambda: detect(cl.load_m1()))
    base = cl.cache_frame("u1007_ps_base_1h", lambda: base_frame(cl.load_m1()))
    print("events", len(ev), "base swings", len(base))
    probe = cl.probe_lookahead(detect, ev, lookback="45D")
    mkt = cl.get_market()
    t = pd.DatetimeIndex(ev["decision_time"])
    dirs = ev["direction"].to_numpy()
    p0 = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
    I, cdt, oa, ob = control_pairs(ev, base, mkt)
    order = np.argsort(I, kind="stable")
    I, cdt, oa, ob = I[order], cdt[order], oa[order], ob[order]
    cnt = np.bincount(I, minlength=len(ev))
    start = np.concatenate([[0], np.cumsum(cnt)[:-1]])

    def rng60(times):
        i = mkt.pos_at_or_after(times)
        return np.array([mkt.h[max(0, j - 60):j].max() - mkt.l[max(0, j - 60):j].min() for j in i])

    diag = (f"structural null: {int((cnt > 0).sum())}/{len(ev)} events have >=1 valid control "
            f"(median {int(np.median(cnt))} candidates); median 60-bar range real "
            f"{np.median(rng60(t)):.2f} vs control {np.median(rng60(cdt)):.2f}")
    print(diag)

    for reading, cont in (("u1007a", False), ("u1007b", True)):
        obs = outcome(mkt, t, p0, ev["ps"].to_numpy(), dirs, cont)
        pair_out = ob if cont else oa

        def null_fn(rng, k):
            pick = start + np.floor(rng.random(len(ev)) * np.maximum(cnt, 1)).astype(np.int64)
            return np.where(cnt > 0, pair_out[np.minimum(pick, len(pair_out) - 1)], np.nan)

        res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                           null_fn=null_fn, predictors=ev)
        rules = ["protected swing: 1h 2/2 extreme, close through series open within 3 bars, POI sweep|fvg "
                 "(structure_own_01b reading a); confirmed at the 1h close",
                 "significant liquidity: PDH (bull) / PDL (bear) as of confirmation, min_coverage 0.5, "
                 "beyond the extreme-to-confirm range",
                 "liquidity taken by M1 touch within 10h of confirmation while the protected swing holds; "
                 "decision = close of that M1 bar",
                 ("hit: price trades through the protected swing within 600 M1 bars" if not cont else
                  "hit: price trades through the protected swing, then back to the decision-bar open, within 600 M1 bars"),
                 "null (structural): a protected swing from the same base population (same detector and "
                 "direction, confirmed within +/-30 d, not the event's own) at the first M1 bar within 10h "
                 "where price is the same PS->taken-level distance away, that swing still holding and its "
                 "own PDH/PDL still untaken; same outcome on that swing, same 600-bar horizon; 5 random draws"]
        params = {"tf": TF, "swing": "2/2", "level_rule": "series_open", "max_wait": 3,
                  "poi": "sweep|fvg", "liquidity": "PDH/PDL", "min_coverage": 0.5,
                  "liq_wait": "10h", "horizon_bars": HBARS,
                  "outcome": "re-sweep" if not cont else "re-sweep then return to decision price",
                  "null": "structural: same-distance protected swing without the liquidity take",
                  "null_window_days": 30}
        p = cl.write_result(CID, reading, res, operationalization={"rules": rules, "params": params},
                            params_source=PARAMS_SOURCE, script=__file__, probe=probe,
                            notes="Tests only the u1007 claim: after PDH/PDL (significant liquidity) is "
                                  "taken, the protected swing is re-swept more than a protected swing "
                                  "the same distance away whose liquidity is untaken. AUDIT: the first "
                                  "run's arbitrary-level null replaced (it scored un-taken protected "
                                  "swings -2.5pp/-2.7pp too). " + diag)
        print(reading, {k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo",
                                                 "ci_hi", "p", "verdict", "verdict_detail")})
        print(p)


if __name__ == "__main__":
    run_all()
