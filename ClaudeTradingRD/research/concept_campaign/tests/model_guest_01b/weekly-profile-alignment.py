"""weekly-profile-alignment (guest: AM Trades, QmGJFxfSHxM).

Claim: name the week's profile from the days already printed, then trade the
remaining days as continuations of it at the New York open. trade_test vs a
matched random-entry control.

Profiles, reconstructed from the three worked weeks (declared before the first run;
daily candles on the 18:00-NY trading day, Monday = the session opening Sunday 18:00):
  classic expansion   bull: Tue low >= Mon low, Tue high > Mon high, Tue close > Tue open
                      (Monday holds the low, Tuesday expands up); confirmed at Tue close;
                      trade Wed, Thu, Fri long. Bear mirrored.
  midweek reversal    (only if no classic) Mon range <= ADR20 (Monday consolidates);
                      Tue runs down (Tue low < Mon low, Tue close < Tue open); Wed reverses
                      (Wed close > Tue open and Wed close > Wed open); trade Thu, Fri long.
                      Bear mirrored.
  consolidation rev.  (only if neither) Mon-Wed range <= 1.5 x ADR20; Thu trades below the
                      Mon-Wed low and closes back inside it -> long Fri (above the high and
                      back inside -> short Fri).
Entry: 09:30 New York on each remaining day (next M1 open). Stop: the current week's
extreme against the trade as of 09:30, floored at 0.25 x ADR20 from the last M1 close before 09:30 (a 09:30 NY M1 bar must exist within 5 min).
Target 2R. Hold to 16:00 NY (6h30).
The hourly-CISD confirmation and the overnight-invalidation rule are not modelled.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import cl, daily, np, pd  # noqa: E402

CID = "weekly-profile-alignment"
ENTRY_HHMM = "09:30"
MIN_STOP_ADR = 0.25
CONS_MULT = 1.5
RR = 2.0
MAX_HOLD = "390min"


def profile_trades(d: pd.DataFrame) -> list:
    """(session_date, direction, profile, adr_at_confirm) for each remaining day."""
    out = []
    for wk, g in d.groupby("wk", sort=True):
        byd = {int(r.wd): r for r in g.itertuples()}
        if not all(k in byd for k in (0, 1)):
            continue
        mo, tu = byd[0], byd[1]
        days = lambda ks: [wk + pd.Timedelta(days=k) for k in ks]   # noqa: E731
        if tu.low >= mo.low and tu.high > mo.high and tu.close > tu.open:
            out += [(s, 1, "classic", tu.adr) for s in days((2, 3, 4))]
            continue
        if tu.high <= mo.high and tu.low < mo.low and tu.close < tu.open:
            out += [(s, -1, "classic", tu.adr) for s in days((2, 3, 4))]
            continue
        if 2 not in byd:
            continue
        we = byd[2]
        if not np.isnan(mo.adr) and (mo.high - mo.low) <= mo.adr:
            if tu.low < mo.low and tu.close < tu.open and we.close > tu.open and we.close > we.open:
                out += [(s, 1, "midweek", we.adr) for s in days((3, 4))]
                continue
            if tu.high > mo.high and tu.close > tu.open and we.close < tu.open and we.close < we.open:
                out += [(s, -1, "midweek", we.adr) for s in days((3, 4))]
                continue
        if 3 not in byd:
            continue
        th = byd[3]
        hi3, lo3 = max(mo.high, tu.high, we.high), min(mo.low, tu.low, we.low)
        if not np.isnan(we.adr) and (hi3 - lo3) <= CONS_MULT * we.adr:
            if th.low < lo3 and lo3 < th.close < hi3 and not th.high > hi3:
                out.append((wk + pd.Timedelta(days=4), 1, "cons_rev", th.adr))
            elif th.high > hi3 and lo3 < th.close < hi3 and not th.low < lo3:
                out.append((wk + pd.Timedelta(days=4), -1, "cons_rev", th.adr))
    return out


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "profile"]
    d = daily(m1)
    if len(d) < 30:
        return pd.DataFrame(columns=cols)
    tr = profile_trades(d)
    if not tr:
        return pd.DataFrame(columns=cols)
    sd = pd.DatetimeIndex([x[0] for x in tr])
    hh, mm = map(int, ENTRY_HHMM.split(":"))
    loc = (sd + pd.Timedelta(hours=hh, minutes=mm)).tz_localize("America/New_York")
    t = loc.tz_convert("UTC")
    # last M1 CLOSE known at t (the bar ending at t); must be within 5 minutes of t
    mclose = (m1.index + pd.Timedelta(minutes=1)).as_unit("ns").asi8
    k = np.searchsorted(mclose, t.as_unit("ns").asi8, side="right") - 1
    kk = np.clip(k, 0, None)
    px = np.where(k >= 0, m1["close"].to_numpy()[kk], np.nan)
    fresh = (k >= 0) & (t.as_unit("ns").asi8 - mclose[kk] <= 5 * 60 * 10**9)
    wk = cl.running_hilo(t, "1W", m1=m1)
    direc = np.array([x[1] for x in tr])
    adr = np.array([x[3] for x in tr], dtype=float)
    ok = fresh & ~np.isnan(px) & ~np.isnan(adr) & ~np.isnan(wk["low"].to_numpy())
    stop = np.where(direc > 0, np.minimum(wk["low"].to_numpy(), px - MIN_STOP_ADR * adr),
                    np.maximum(wk["high"].to_numpy(), px + MIN_STOP_ADR * adr))
    out = pd.DataFrame({"decision_time": t, "available_at": t, "direction": direc,
                        "stop_px": stop, "rr": RR, "profile": [x[2] for x in tr]})
    return out[ok].reset_index(drop=True)


if __name__ == "__main__":
    ev = cl.cache_frame(f"{CID}_v1", lambda: detect(cl.load_m1()))
    print(len(ev), ev["profile"].value_counts().to_dict(), "long share", (ev.direction > 0).mean())
    probe = cl.probe_lookahead(detect, ev, lookback="60D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ("n", "avg_R", "ctrl_avg_R", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail",
              "ties", "exposure_bars"):
        print(k, res.get(k))
    op = {"rules": [
        "daily candles on the 18:00-NY trading day; weeks Mon-Fri by session date; stub days (< 600 M1) dropped",
        "classic expansion (bull): Tue low >= Mon low, Tue high > Mon high, Tue close > open -> long Wed/Thu/Fri; bear mirrored",
        "midweek reversal (if no classic; bull): Mon range <= ADR20, Tue low < Mon low and closes down, Wed close > Tue open and > Wed open -> long Thu/Fri; bear mirrored",
        "consolidation reversal (if neither): Mon-Wed range <= 1.5 x ADR20; Thu runs one side and closes back inside -> Fri the other way",
        "entry at 09:30 NY (next M1 open); stop = the week's extreme against the trade as of 09:30, at least 0.25 x ADR20 from the last M1 close before 09:30; 2R target; hold 6h30 (to 16:00 NY)"],
        "params": {"entry_hhmm": ENTRY_HHMM, "min_stop_adr": MIN_STOP_ADR, "cons_mult": CONS_MULT, "rr": RR,
                   "max_hold": MAX_HOLD, "adr_n": 20, "stub_min_m1": 600, "day_open_hour": 18}}
    src = {"entry_hhmm": "declared-before-run: 'New York open' (QmGJFxfSHxM, futures) read as the 09:30 NY open",
           "min_stop_adr": "declared-before-run: stop not stated; floor avoids degenerate stops",
           "cons_mult": "declared-before-run: 'Monday, Tuesday and Wednesday consolidate' as a 3-day range <= 1.5 ADR20",
           "rr": "declared-before-run: target not quantified ('external level'); 2R as the phase-3 locked target",
           "max_hold": "declared-before-run: AM-session continuation trade, flat by 16:00 NY",
           "adr_n": "declared-before-run: 20-day average daily range",
           "stub_min_m1": "declared-before-run: README trap 6 stub sessions",
           "day_open_hour": "session_window_fit: settled 18:00 NY daily roll"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src, script=__file__,
                        probe=probe, notes="Profile definitions reconstructed from the three worked weeks; hourly CISD "
                        "confirmation and overnight invalidation omitted. Profile counts: "
                        + str(ev["profile"].value_counts().to_dict()))
    print("wrote", p)
