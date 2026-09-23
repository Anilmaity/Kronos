"""nine-thirty-expansion-invalidation — "I want to see 9:30 just push us into that low".

Concept (live_streams_05, tDiwwMRWF2k): the 09:30 open should push price directly into
the target marked before the open (previous day low/high); the single kill condition is
the protected swing that framed the move being taken out; after it, no re-entry.

Operationalisation (trade_test, claim '+'; declared before the first run):
  * each NY weekday, decide at 09:30 NY. Inputs (all closed by 09:30): the prior
    trading day's high/low (18:00 NY roll, prior_hilo min_coverage 0.5), the current
    trading day's running high/low, and the 08:30-09:30 NY pre-open M1 range.
  * target = the previous-day extreme not yet traded through this trading day; if both
    are untaken, the one nearer to the 09:29 close. Direction = toward it.
  * protected swing framing the move = the pre-open (08:30-09:30) extreme on the far
    side (short: its high, long: its low); it must lie beyond the 09:29 close.
  * enter the 09:30 M1 open; stop = that swing (its take-out is the kill condition,
    no re-entry); target = the previous-day extreme; otherwise time exit at 12:00 NY
    (end of the NY a.m. session) - max_hold 150 min.
  * control holds the NY clock (ctrl_tod_tol_min=30): all entries are at 09:30.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, np, pd, ny_dates, at_ny, utc_ns, empty  # noqa: E402

CID = "nine-thirty-expansion-invalidation"
PRE = ("08:30", "09:30")
HOLD = "150min"


def detect(m1):
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px"]
    if len(m1) < 2000:
        return empty(cols)
    mkt = cl.get_market(m1)
    dates = ny_dates(m1)
    t = at_ny(dates, PRE[1])
    t0 = at_ny(dates, PRE[0])
    ok = ~pd.isna(t) & ~pd.isna(t0)
    t, t0 = t[ok], t0[ok]
    i0 = np.searchsorted(mkt.tn, utc_ns(t0), side="left")
    i1 = np.searchsorted(mkt.tn, utc_ns(t), side="left")      # bars strictly before 09:30
    has = (i1 - i0) >= 45
    t, i0, i1 = t[has], i0[has], i1[has]
    if len(t) == 0:
        return empty(cols)
    pre_hi = np.array([mkt.h[a:b].max() for a, b in zip(i0, i1)])
    pre_lo = np.array([mkt.l[a:b].min() for a, b in zip(i0, i1)])
    ref = mkt.c[i1 - 1]                                       # 09:29 close
    pd_ = cl.prior_hilo(t, "1D", m1=m1, min_coverage=0.5)
    run = cl.running_hilo(t, "1D", m1=m1)
    pdh, pdl = pd_["high"].to_numpy(float), pd_["low"].to_numpy(float)
    rh, rl = run["high"].to_numpy(float), run["low"].to_numpy(float)
    up_ok = np.isfinite(pdh) & np.isfinite(rh) & (rh < pdh)
    dn_ok = np.isfinite(pdl) & np.isfinite(rl) & (rl > pdl)
    du = np.where(up_ok, pdh - ref, np.inf)
    dd = np.where(dn_ok, ref - pdl, np.inf)
    long_ = up_ok & (du <= dd)
    short = dn_ok & ~long_
    direction = np.where(long_, 1, np.where(short, -1, 0))
    stop = np.where(long_, pre_lo, pre_hi)
    target = np.where(long_, pdh, pdl)
    valid = (direction != 0) & np.where(long_, stop < ref, stop > ref) & \
        np.where(long_, target > ref, target < ref)
    out = pd.DataFrame({"decision_time": t[valid], "available_at": t[valid],
                        "direction": direction[valid], "stop_px": stop[valid],
                        "target_px": target[valid]})
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame("ny930_drive_pd_target", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["direction"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, max_hold=HOLD, claim="+", ctrl_tod_tol_min=30)
    print({k: res.get(k) for k in ("n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p",
                                   "mde", "verdict", "verdict_detail", "ties",
                                   "ctrl_overlap", "halves", "exposure_bars", "exit_mix",
                                   "sanity_flags")})
    op = {"rules": [
        "decide 09:30 NY each weekday; inputs closed by 09:30",
        "target = previous trading day's high/low (18:00 roll, min_coverage 0.5) not yet "
        "traded through today; nearer to the 09:29 close if both untaken; direction toward it",
        "stop = the 08:30-09:30 pre-open extreme on the far side (protected swing framing "
        "the move), beyond the 09:29 close",
        "enter the 09:30 M1 open; target the previous-day extreme; time exit 12:00 NY",
        "control: same direction/stop/target distances at the same NY clock (+/-30 min) "
        "on other days within +/-30 days"],
        "params": {"pre_open_window": PRE, "max_hold": HOLD, "pd_min_coverage": 0.5,
                   "target_choice": "nearer untaken previous-day extreme",
                   "ctrl_tod_tol_min": 30}}
    src = {"pre_open_window": "declared-before-run: the framing swing is the pre-open "
                              "extreme from 08:30 (the attested NY a.m. start, 08:30-12:00) "
                              "to the 09:30 open",
           "max_hold": "session_window_fit: NY a.m. window 08:30-12:00 (corpus gives no "
                       "time limit; the drive is an a.m.-session idea)",
           "pd_min_coverage": "declared-before-run: README trap 6, skip stub sessions",
           "target_choice": "corpus: tDiwwMRWF2k 'I want to see 9:30 just push us into that "
                            "low' (target = previous day low/high marked before the open); "
                            "declared-before-run: the nearer untaken one when both remain",
           "ctrl_tod_tol_min": "declared-before-run: README trap 9, every entry at 09:30 NY"}
    print(cl.write_result(CID, None, res, operationalization=op, params_source=src,
                          script=__file__, probe=probe,
                          notes="The kill condition (framing swing taken) is the stop; "
                                "no re-entry is modelled. The pre-open extreme stands in "
                                "for his discretionary protected swing. Corpus context is "
                                "index futures; tested on gold."))
