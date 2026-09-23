"""session-cascade (underspecified, own voice, 00iZXPAdR5A): a session can only expand if a
prior session supplied the manipulation. Asia quiet => London manipulates => New York expands;
'the question is only which session is positioned to expand' and 'take the model in the
session identified as the expansion session'.

Operationalisation (declared before any run):
- Session windows = the corpus's forex kill zones (NY clock): Asia 20:00-00:00,
  London 02:00-05:00, NY AM 07:00-10:00 (cl.KILLZONES, verbatim-verified in session_window_fit).
- Chain of windows: prior session's NY AM -> Asia -> London -> NY AM.
- A window MANIPULATES when it trades beyond the preceding window's high or low AND its last
  M1 close is back inside the preceding window's range (sweep and reversal -- the corpus's
  implicit reading, ambiguities list).
- Predicted expansion session: Asia manipulated -> London; else London manipulated -> NY AM;
  else neither (NY manipulates, expansion later) -> no window of the three is predicted.
- Gate test on the phase-3 bare 15m CISD book, universe = events decided inside the three
  windows: gated = event inside the predicted expansion window; complement = the rest.
  The gate's verdict is known at the end of the manipulating window (00:00 NY for London,
  05:00 NY for NY AM), always before the decision. Events whose required windows are missing
  (data holes) are dropped, never defaulted.
- ctrl_tod_tol_min=30: the concept is a conditional session selection, not a clock claim; the
  control holds the NY clock fixed so the fixed hour-of-day expectancy (trap 9) cancels and
  the differential measures the cascade's conditional information.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _common import cl, np, pd, cisd_book, base_params, base_rule, summarize

TF = "15min"
WIN = {"asia": (20 * 60, 24 * 60), "london": (2 * 60, 5 * 60), "ny": (7 * 60, 10 * 60)}


def window_table(m1):
    mod = cl.ny_minute_of_day(m1.index)
    sd = pd.DatetimeIndex(cl.session_date(m1.index)).tz_localize(None).normalize()
    out = {}
    for name, (a, b) in WIN.items():
        msk = (mod >= a) & (mod < b)
        g = pd.DataFrame({"sd": sd[msk], "high": m1["high"].to_numpy()[msk],
                          "low": m1["low"].to_numpy()[msk], "close": m1["close"].to_numpy()[msk],
                          "t": m1.index[msk]})
        agg = g.groupby("sd").agg(high=("high", "max"), low=("low", "min"),
                                  close=("close", "last"), last_t=("t", "max"), n=("t", "size"))
        out[name] = agg
    return out


def manip(cur, prev):
    swept = (cur["high"] > prev["high"]) | (cur["low"] < prev["low"])
    back = (cur["close"] <= prev["high"]) & (cur["close"] >= prev["low"])
    return swept & back


def detect(m1):
    ev = cisd_book(m1, TF)
    t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    mod = cl.ny_minute_of_day(t)
    sd = pd.DatetimeIndex(cl.session_date(t)).tz_localize(None).normalize()
    W = window_table(m1)
    asia, lon, nyw = W["asia"], W["london"], W["ny"]
    # previous session's NY AM window for each Asia window
    pos = np.searchsorted(nyw.index.values, asia.index.values, side="left") - 1
    has_prev = pos >= 0
    prev_ny = nyw.iloc[np.clip(pos, 0, None)].set_axis(asia.index)
    a_known = has_prev & (asia["n"].to_numpy() >= 120) & (prev_ny["n"].to_numpy() >= 90)
    a_val = manip(asia, prev_ny).to_numpy() & a_known
    asia_r = asia.reindex(lon.index)
    l_known = asia_r["n"].notna().to_numpy() & (asia_r["n"].fillna(0).to_numpy() >= 120) \
        & (lon["n"].to_numpy() >= 90)
    l_val = manip(lon, asia_r).to_numpy() & l_known
    A_known = pd.Series(a_known, index=asia.index).reindex(sd, fill_value=False).to_numpy(bool)
    A_val = pd.Series(a_val, index=asia.index).reindex(sd, fill_value=False).to_numpy(bool)
    L_known = pd.Series(l_known, index=lon.index).reindex(sd, fill_value=False).to_numpy(bool)
    L_val = pd.Series(l_val, index=lon.index).reindex(sd, fill_value=False).to_numpy(bool)

    in_asia = (mod >= WIN["asia"][0]) & (mod < WIN["asia"][1])
    in_lon = (mod >= WIN["london"][0]) & (mod < WIN["london"][1])
    in_ny = (mod >= WIN["ny"][0]) & (mod < WIN["ny"][1])
    am_known, lm_known, amb, lmb = A_known, L_known, A_val, L_val

    keep = in_asia | (in_lon & am_known) | (in_ny & am_known & lm_known)
    gated = (in_lon & amb) | (in_ny & ~amb & lmb)
    # verdict availability: London events -> end of Asia (00:00 NY); NY events -> end of London (05:00 NY)
    base = pd.DatetimeIndex([pd.Timestamp(d).tz_localize("America/New_York") for d in sd]) \
        if len(sd) else pd.DatetimeIndex([], tz="America/New_York")
    asia_end = (base).tz_convert("UTC")
    lon_end = (base + pd.Timedelta(hours=5)).tz_convert("UTC")
    mask_at = np.where(in_lon, asia_end.as_unit("ns").asi8,
                       np.where(in_ny, lon_end.as_unit("ns").asi8, t.as_unit("ns").asi8))
    ev["gated"] = gated
    ev["mask_at"] = pd.DatetimeIndex(pd.to_datetime(mask_at, utc=True))
    ev["window"] = np.where(in_asia, "asia", np.where(in_lon, "london", np.where(in_ny, "ny", "none")))
    ev = ev[keep].reset_index(drop=True)
    return ev


if __name__ == "__main__":
    ev = cl.cache_frame(f"to02b_cascade_{TF}", lambda: detect(cl.load_m1()))
    print(len(ev), "events"); print(pd.crosstab(ev["window"], ev["gated"]))
    probe = cl.probe_lookahead(detect, ev, lookback="30D")
    res = cl.gate_test(ev, "gated", mask_available_at="mask_at", max_hold="150min", claim="+",
                       ctrl_tod_tol_min=30)
    summarize(res)
    bp, bs = base_params(TF)
    params = {**bp, "windows": "fx kill zones Asia 20-00, London 02-05, NY AM 07-10 (NY)",
              "manipulation": "window trades beyond the preceding window's high/low and its last close is back inside it",
              "chain": "prior session NY AM -> Asia -> London -> NY AM",
              "min_window_m1": "Asia>=120, London/NY>=90 M1 bars", "ctrl_tod_tol_min": 30}
    src = {**bs, "windows": "session_window_fit: corpus kill-zone windows verbatim-verified (MPeeE55rNOw)",
           "manipulation": "declared-before-run: concept ambiguities 'implicitly a sweep and reversal'",
           "chain": "corpus: 00iZXPAdR5A Asia -> London -> New York cascade; prior-NY link declared-before-run",
           "min_window_m1": "declared-before-run: data-hole guard (trap 6)",
           "ctrl_tod_tol_min": "declared-before-run: trap 9, hold NY clock fixed so the cascade's conditional selection is measured"}
    rules = [base_rule(TF), "universe = baseline events decided inside Asia/London/NY AM kill zones",
             "Asia manipulated -> London is the expansion session; else London manipulated -> NY AM; else none",
             "gated = event in the predicted expansion window; complement = all other universe events"]
    p = cl.write_result("session-cascade", None, res, operationalization={"rules": rules, "params": params},
                        params_source=src, script=__file__, probe=probe,
                        notes="Session boundaries are not defined in the source transcript; the corpus kill-zone windows were used. 'Expansion' is scored as the entry model's control-adjusted R inside the predicted session.")
    print(p)
