"""consolidation-open-whipsaw — update_20261007_live_02 (rate_test), new readings only.

New claim (h1ZQWWQDhKA): "If we break out of this range, you don't want to see us close
back in the range. You want to see us retest or get a continuation. We close back in
this range. AMD accumulation manipulation going higher."  => after a range breach,
  close back inside   = deviation -> rotation to the OPPOSITE boundary   (reading u1007a, claim +)
  close held outside  = breakout  -> no rotation to the opposite boundary (reading u1007b, claim -)

Declared before run:
  * range = the library entry's pre-open range: trading-day high/low 18:00 -> 09:30 NY
    (>=600 M1 bars), weekdays (same range as prior readings a/b; no bias filter: the new
    claim is a generic range-breach rule, not tied to no-bias days)
  * deciding close = 5-minute close (the chart he spoke over; draft timeframes htf 5m)
  * session = 5m bars 09:30-16:00 NY; first breach = first 5m bar whose high > RH or low < RL
    (a bar breaching both sides -> day dropped); scan stops if the opposite side is breached
  * u1007a event: first 5m close strictly inside the range after the first breach
  * u1007b event: the first 5m close after the breach (incl. the breach bar) if it is
    beyond the breached boundary (held outside), before any close back in
  * outcome: opposite boundary touched (M1) from the decision to 16:00 NY
  * null: same distance from the last close, same direction, same M1 bar count, at a random
    moment within +/-30 days at the same NY clock +/-15 min
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl

TZ = "America/New_York"
TOD_TOL = 15
COLS = ["decision_time", "available_at", "kind", "side", "rh", "rl", "ref"]


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    ny = m1.index.tz_convert(TZ)
    mod = ny.hour * 60 + ny.minute
    tday = (ny.tz_localize(None) + pd.Timedelta(hours=6)).normalize()     # 18:00 roll
    pre = (mod < 9 * 60 + 30) | (mod >= 18 * 60)
    g = m1[pre].groupby(tday[pre])
    agg = pd.DataFrame({"rh": g["high"].max(), "rl": g["low"].min(), "n": g["close"].size()})
    agg = agg[(agg["n"] >= 600) & (agg.index.dayofweek < 5)]
    b = cl.build_bars(m1, "5min")
    bny = b.index.tz_convert(TZ)
    bmod = bny.hour * 60 + bny.minute
    sess = (bmod >= 9 * 60 + 30) & (bmod < 16 * 60)
    b = b[sess]
    bday = pd.DatetimeIndex(bny[sess].tz_localize(None).normalize())
    rows = []
    H, L, C = b["high"].to_numpy(float), b["low"].to_numpy(float), b["close"].to_numpy(float)
    CT = pd.DatetimeIndex(b["close_time"])
    starts = np.flatnonzero(np.r_[True, bday[1:] != bday[:-1]])
    ends = np.r_[starts[1:], len(b)]
    for s, e in zip(starts, ends):
        d = bday[s]
        if d not in agg.index:
            continue
        rh, rl = agg.at[d, "rh"], agg.at[d, "rl"]
        side = 0
        got_b = False
        for i in range(s, e):
            up, dn = H[i] > rh, L[i] < rl
            if side == 0:
                if up and dn:
                    break
                if not (up or dn):
                    continue
                side = 1 if up else -1
            elif (side == 1 and dn) or (side == -1 and up):
                break                                   # opposite breached before any close-in
            inside = rl < C[i] < rh
            if inside:
                rows.append((CT[i], CT[i], "a", side, rh, rl, C[i]))
                break
            beyond = C[i] > rh if side == 1 else C[i] < rl
            if beyond and not got_b:
                rows.append((CT[i], CT[i], "b", side, rh, rl, C[i]))
                got_b = True
    out = pd.DataFrame(rows, columns=COLS)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = out["decision_time"]
    return out.sort_values(["decision_time", "kind"]).reset_index(drop=True)


def horizon_bars(times, mkt):
    i0 = mkt.pos_at_or_after(times)
    loc = times.tz_convert(TZ)
    end = pd.DatetimeIndex([pd.Timestamp(t.date()).tz_localize(TZ) + pd.Timedelta(hours=16)
                            for t in loc]).tz_convert("UTC")
    return mkt.pos_at_or_after(end) - i0


def run():
    mkt = cl.get_market()
    full = cl.cache_frame("u1007_cow_breach_5m", lambda: detect(cl.load_m1()))
    probe = cl.probe_lookahead(detect, full, lookback="20D")
    params = {"range_start": "18:00", "range_end": "09:30", "session": "09:30-16:00 NY",
              "close_tf": "5min", "horizon_end": "16:00", "day_open_hour": 18,
              "null_tod_tol_min": TOD_TOL, "null_window_days": 30, "min_pre_m1": 600}
    src = {"range_start": "method_spec: §1.4 daily candle opens 18:00 NY (canon); same range as library readings a/b",
           "range_end": "corpus: xraklBJHW5k the 9:30 open (pre-open range); h1ZQWWQDhKA 'we haven't really left the range of morning open'",
           "session": "declared-before-run: equity session the 09:30 anchor belongs to (as readings a/b)",
           "close_tf": "corpus: h1ZQWWQDhKA 'you don't want to see us close back in the range' spoken over a 5-minute chart (draft timeframes htf 5m)",
           "horizon_end": "declared-before-run: source gives no time limit; 16:00 NY ends the session",
           "day_open_hour": "session_window_fit: 18:00 NY roll settled",
           "null_tod_tol_min": "declared-before-run: hold NY clock fixed (trap 9), as readings a/b",
           "null_window_days": "phase3: locked +/-30-day regime window",
           "min_pre_m1": "declared-before-run: skip stub sessions (trap 6), as readings a/b"}
    for reading, kind, claim, txt in (
            ("u1007a", "a", "+", "after first breach, first 5m close back inside -> opposite boundary touched by 16:00 (deviation rotates)"),
            ("u1007b", "b", "-", "after first breach, first 5m close held beyond the breached boundary -> opposite boundary NOT reached (breakout)")):
        # each reading is detect() filtered to its kind INSIDE a detector so the probe sees the exact frame
        def det_k(m1, kind=kind):
            x = detect(m1)
            return x[x["kind"] == kind].reset_index(drop=True)
        ev = full[full["kind"] == kind].reset_index(drop=True)
        pr = cl.probe_lookahead(det_k, ev, lookback="20D")
        t = pd.DatetimeIndex(ev["decision_time"])
        hb = horizon_bars(t, mkt)
        side = ev["side"].to_numpy()
        opp = np.where(side == 1, ev["rl"].to_numpy(), ev["rh"].to_numpy())
        ref = ev["ref"].to_numpy()
        dist = np.abs(ref - opp)
        ok = hb > 0

        def touch_opp(tt, rref, hbb, sd, dd):
            o = np.zeros(len(tt))
            for s_, nm in ((1, "below"), (-1, "above")):
                m = sd == s_
                if m.any():
                    lvl = rref[m] - dd[m] if s_ == 1 else rref[m] + dd[m]
                    o[m] = cl.touch(tt[m], lvl, nm, horizon_bars=hbb[m])["hit"].to_numpy(float)
            return o

        obs = np.full(len(t), np.nan)
        obs[ok] = touch_opp(t[ok], ref[ok], hb[ok], side[ok], dist[ok])
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

        def null_fn(rng, k):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
            m = ~tk.isna() & ok
            out = np.full(len(t), np.nan)
            pos = mkt.pos_at_or_after(tk[m])
            rref = mkt.c[np.maximum(pos - 1, 0)]
            out[m] = touch_opp(tk[m], rref, hb[m], side[m], dist[m])
            return out

        res = cl.rate_test(obs, t, available_at=ev["available_at"], predictors=ev,
                           null_fn=null_fn, claim=claim)
        op = {"rules": [f"outcome: {txt}",
                        "range = trading-day high/low 18:00-09:30 NY (>=600 M1 bars), weekdays, no bias filter",
                        "first breach = first 5m bar 09:30-16:00 NY with high>RH or low<RL; both-sides bar drops the day; scan stops at an opposite-side breach",
                        "decision = that 5m bar's close; ref = its close; outcome = M1 touch of the opposite boundary until 16:00 NY",
                        "null = same distance/direction from the last close, same M1 bar count, random moment +/-30d at same NY clock +/-15 min"],
              "params": params}
        p = cl.write_result("consolidation-open-whipsaw", reading, res, operationalization=op,
                            params_source=src, script=__file__, probe=pr)
        print(reading, p)
        for kk in ("n", "observed_rate", "null_rate", "diff", "ci_lo", "ci_hi", "p", "mde",
                   "verdict", "verdict_detail"):
            print("  ", kk, res.get(kk))


if __name__ == "__main__":
    run()
