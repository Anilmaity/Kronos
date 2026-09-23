"""nfp-week-protocol (contested, mixed voice; AM Trades protocol restated by TTrades).

reading a -- the day map (hKCMqh0ZsY0 own voice + variants): in an NFP week,
    allowed = Tuesday/Wednesday sessions that are not the day before the release, the
              release day from 08:30 NY on, and any session after the release that week;
    blocked = Monday, the session before the release day, the release day before 08:30 NY.
    Gate test on the phase-3 bare 15m CISD book RESTRICTED to NFP-week sessions (hold
    150 min), claim '+' (allowed beats blocked, control-adjusted).
reading b -- the Friday fade (QmGJFxfSHxM): classify Mon..day-before-release. If the week so
    far 'remained internal' -- declared as: one single session of those days holds BOTH the
    week-so-far high and low (the other days sit inside that expansion day's range) -- then
    after 08:30 NY on release day expect the release to run an external level (week-so-far
    high WH or low WL) and return: the first 5m bar (08:30..12:00 NY, he watches the AM
    session only) that CLOSES back inside after trading beyond WH (WL) triggers a short
    (long) at the next M1 open; stop = the extreme made since 08:30 (stop not stated ->
    declared); target = the opposing external level; exit by 16:00 NY the same day. If the
    release never runs an external level (or runs it without a close back inside) -> no trade.
    trade_test, claim '+'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize, nfp_dates

READING = sys.argv[1] if len(sys.argv) > 1 else "a"
TF = "15min"
NFP = nfp_dates()


def _week_start(d):
    d = pd.DatetimeIndex(d)
    return d - pd.to_timedelta(d.dayofweek, unit="D")


def detect_a(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    sd = pd.DatetimeIndex(cl.session_date(t)).tz_localize(None).normalize()
    ws = _week_start(sd)
    rel = pd.Series(NFP, index=_week_start(NFP))
    rel = rel[~rel.index.duplicated()]
    rd = pd.DatetimeIndex(rel.reindex(ws).to_numpy())
    keep = ~pd.isna(rd)
    ev, t, sd, rd = ev[keep].reset_index(drop=True), t[keep], sd[keep], rd[keep]
    dow = np.asarray(sd.dayofweek)
    mod = cl.ny_minute_of_day(t)
    day_before = np.asarray(sd == (rd - pd.Timedelta(days=1)))
    rel_day = np.asarray(sd == rd)
    after_rel = np.asarray(sd > rd)
    allowed = ((np.isin(dow, [1, 2]) & ~day_before & ~rel_day & ~after_rel)
               | (rel_day & (mod >= 8 * 60 + 30) & (mod < 18 * 60))
               | after_rel)
    # Monday never allowed (covers a Monday release too)
    allowed &= dow != 0
    ev["allowed"] = allowed
    return ev


def detect_b(m1):
    ny = cl.to_ny(m1.index)
    sd_all = pd.DatetimeIndex(cl.session_date(m1.index)).tz_localize(None).normalize()
    rows = []
    b5 = cl.build_bars(m1, "5min")
    b5_ny = cl.to_ny(pd.DatetimeIndex(b5["close_time"]))
    for rd in NFP:
        ws = rd - pd.Timedelta(days=rd.dayofweek)
        pre_days = pd.date_range(ws, rd - pd.Timedelta(days=1), freq="D")
        pre_days = [d for d in pre_days if d.dayofweek < 5]
        if len(pre_days) < 2:
            continue
        sess = {}
        for d in pre_days:
            msk = np.asarray(sd_all == d)
            if msk.sum() < 300:          # stub / missing session -> skip the week
                sess = None
                break
            sess[d] = (float(m1["high"].to_numpy()[msk].max()), float(m1["low"].to_numpy()[msk].min()))
        if not sess:
            continue
        WH = max(h for h, _ in sess.values()); WL = min(l for _, l in sess.values())
        internal = any(h == WH and l == WL for h, l in sess.values())
        if not internal:
            continue
        rel = pd.Timestamp(rd.date()).tz_localize("America/New_York") + pd.Timedelta(hours=8, minutes=30)
        end = pd.Timestamp(rd.date()).tz_localize("America/New_York") + pd.Timedelta(hours=12)
        last_pre = pd.Timestamp(pre_days[-1].date()).tz_localize("America/New_York") + pd.Timedelta(hours=17)
        # every pre-day session must be complete in the input (slice guard)
        if m1.index[-1] < last_pre.tz_convert("UTC") - pd.Timedelta(minutes=5):
            continue
        ct = pd.DatetimeIndex(b5["close_time"])
        w = np.where((ct > rel.tz_convert("UTC")) & (ct <= end.tz_convert("UTC")))[0]
        run_hi, run_lo = -np.inf, np.inf
        swept_hi = swept_lo = False
        for i in w:
            h, l, c = b5["high"].iat[i], b5["low"].iat[i], b5["close"].iat[i]
            run_hi, run_lo = max(run_hi, h), min(run_lo, l)
            swept_hi |= run_hi > WH
            swept_lo |= run_lo < WL
            if swept_hi and c < WH and not (swept_lo and c > WL):
                rows.append((ct[i], -1, run_hi, WL, rd)); break
            if swept_lo and c > WL:
                rows.append((ct[i], 1, run_lo, WH, rd)); break
    cols = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "target_px", "rd"])
    df["available_at"] = df["decision_time"]
    exit_t = pd.DatetimeIndex([pd.Timestamp(d.date()).tz_localize("America/New_York")
                               + pd.Timedelta(hours=16) for d in df["rd"]]).tz_convert("UTC")
    df["max_hold"] = exit_t - pd.DatetimeIndex(df["decision_time"])
    df["decision_time"] = pd.DatetimeIndex(df["decision_time"])
    return df[cols].reset_index(drop=True)


if __name__ == "__main__":
    if READING == "a":
        ev = cl.cache_frame(f"to02b_nfpweek_a_{TF}", lambda: detect_a(cl.load_m1()))
        print(len(ev), "events; allowed share", ev["allowed"].mean())
        probe = cl.probe_lookahead(detect_a, ev, lookback="30D")
        res = cl.gate_test(ev, "allowed", mask_available_at="decision_time", max_hold="150min", claim="+")
        summarize(res)
        bp, bs = base_params(TF)
        params = {**bp, "nfp_rule": "BLS reference-week rule + 2025 shutdown cases", "release_time": "08:30 NY",
                  "universe": "decisions on sessions of NFP weeks only"}
        src = {**bs, "nfp_rule": "declared-before-run: BLS Employment Situation scheduling convention",
               "release_time": "corpus: QmGJFxfSHxM (08:30 release as the volatility driver)",
               "universe": "corpus: hKCMqh0ZsY0 'I will also watch Tuesday and Wednesday but avoid Thursday'"}
        rules = [base_rule(TF), "universe = baseline events on NFP-week sessions (session date, 18:00 NY roll)",
                 "allowed = Tue/Wed (not the day before release), release day at/after 08:30 NY, sessions after the release",
                 "blocked = Monday, the session before the release, release day before 08:30 NY"]
        p = cl.write_result("nfp-week-protocol", "a", res, operationalization={"rules": rules, "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="Tuesday 'only if Monday engaged a HTF PD array' variant not applied (reading uses the hKCMqh0ZsY0 own-voice day map: Tue/Wed eligible). The 'convincing signature' qualifier is discretionary and not modelled.")
    else:
        ev = cl.cache_frame("to02b_nfpweek_b_fade", lambda: detect_b(cl.load_m1()))
        print(len(ev), "events"); print(ev.head(20))
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        res = cl.trade_test(ev, claim="+")
        summarize(res)
        params = {"nfp_rule": "BLS reference-week rule + 2025 shutdown cases", "release_time": "08:30 NY",
                  "internal_test": "one session of Mon..day-before holds both the week-so-far high and low",
                  "trigger": "first 5m close back inside after trading beyond WH/WL, 08:30-12:00 NY",
                  "stop": "extreme made since 08:30", "target": "opposing external level (WL for shorts, WH for longs)",
                  "exit": "16:00 NY release day", "min_session_m1": 300}
        src = {"nfp_rule": "declared-before-run: BLS Employment Situation scheduling convention",
               "release_time": "corpus: QmGJFxfSHxM 'upon that news release at 8:30'",
               "internal_test": "declared-before-run: QmGJFxfSHxM 'remained internal in between this low and high which formed during that expansion'",
               "trigger": "declared-before-run: QmGJFxfSHxM 'manipulate that external high and then return right back into that range'; AM window from wGYde-h84cs 'I only watch am session'",
               "stop": "declared-before-run: stop not stated in corpus; sweep extreme",
               "target": "corpus: execution.targets 'the opposing external level'",
               "exit": "declared-before-run: flat before the Friday close",
               "min_session_m1": "declared-before-run: stub-session guard (trap 6)"}
        rules = ["NFP weeks only; classify Mon..day-before-release sessions",
                 "internal week: a single session holds both the week-so-far high WH and low WL",
                 "after 08:30 NY on release day, first 5m bar (to 12:00 NY) closing back inside after trading beyond WH (WL) -> short (long) next M1 open",
                 "stop = extreme since 08:30; target = opposing external level; exit 16:00 NY"]
        p = cl.write_result("nfp-week-protocol", "b", res, operationalization={"rules": rules, "params": params},
                            params_source=src, script=__file__, probe=probe,
                            notes="At most one trade per NFP week (~126 weeks in span) and only internal weeks qualify, so this reading cannot be powered on 10.5 years.")
    print(p)
