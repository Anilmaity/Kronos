"""daily-open-eighteen-hundred (TTrades own voice, contested: an evolution).  A level
definition whose stated measurable is 'respect rate of the 18:00 open vs the midnight open
as intraday support/resistance' ('that opening price is supporting the candles and nothing
is closing below it').  -> rate_test with a geometry-matched null, one reading per level:

(a) later canon: the daily open = the open of the actual daily candle on the feed (the
    trading day's first M1 bar, 18:00 NY session open; 'I always use 1,800').
(b) earlier recording: the midnight (00:00 NY) opening price (YXoNowXQirM).

Event, per trading day and level L (declared before the run):
  k      = 0.10 x the range of the previous trading day that has >= 600 M1 bars
  arm    = after L prints, the first M1 bar that trades >= k away from L (high >= L+k -> from
           above, s=+1; low <= L-k -> from below, s=-1; a bar doing both -> day skipped)
  touch  = the first later M1 bar that trades back to L (low <= L if s=+1; high >= L if s=-1),
           before 17:00 NY; decision = that bar's close
  outcome from the next M1 open: 'respected' = L + s*k trades before L - s*k (a same-bar tie
           counts as NOT respected), within the M1 bars left until 17:00 NY; neither -> dropped
Null: 5 matched random minutes within +/-30 days (cl.sample_times, locked seed); at each, the
same two target DISTANCES from that minute's open and the same number of M1 bars -- so the
cushion geometry is identical (README trap 4).  claim '+': the open is respected more often
than a random price at the same geometry.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402
from _common import cl, show  # noqa: E402

K_FRAC = 0.10
MIN_PREV_M1 = 600


def make_detect(level):
    def detect(m1):
        idx = m1.index
        tn = idx.as_unit("ns").asi8
        td = cl.trading_day(idx).as_unit("ns").asi8
        mod = cl.ny_minute_of_day(idx)
        H, L_, O = m1["high"].to_numpy(), m1["low"].to_numpy(), m1["open"].to_numpy()
        brk = np.flatnonzero(np.diff(td)) + 1
        starts = np.r_[0, brk]
        ends = np.r_[brk, len(td)]
        rows = []
        prev_rng = np.nan
        for a, b in zip(starts, ends):
            day = pd.Timestamp(td[a])
            if level == "18:00":
                ok_lv = 18 * 60 <= mod[a] < 18 * 60 + 10          # the real session open
                i_lv = a
            else:
                cand = np.flatnonzero((mod[a:b] >= 0) & (mod[a:b] < 5))
                ok_lv = len(cand) > 0
                i_lv = a + cand[0] if ok_lv else a
            if ok_lv and np.isfinite(prev_rng):
                lv = O[i_lv]
                k = K_FRAC * prev_rng
                # arm: first bar (from the level bar on) trading >= k away
                seg = slice(i_lv, b)
                up = H[seg] >= lv + k
                dn = L_[seg] <= lv - k
                j = np.flatnonzero(up | dn)
                if len(j):
                    ia = i_lv + j[0]
                    if not (up[j[0]] and dn[j[0]]):
                        s = 1 if up[j[0]] else -1
                        seg2 = slice(ia + 1, b)
                        back = (L_[seg2] <= lv) if s == 1 else (H[seg2] >= lv)
                        jt = np.flatnonzero(back)
                        if len(jt):
                            it = ia + 1 + jt[0]
                            dec = pd.Timestamp(tn[it], tz="UTC") + pd.Timedelta(minutes=1)
                            end = (day + pd.Timedelta(days=1, hours=17)).tz_localize(
                                "America/New_York").tz_convert("UTC")
                            if dec < end:
                                rows.append((dec, lv, s, k, end))
            n_day = b - a
            if n_day >= MIN_PREV_M1:
                prev_rng = float(H[a:b].max() - L_[a:b].min())
        # NB: prev_rng is only set after the day ends (it is used from the NEXT day on)
        cols = ["decision_time", "available_at", "level", "side", "k", "day_end"]
        if not rows:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(rows, columns=["decision_time", "level", "side", "k", "day_end"])
        df["decision_time"] = pd.DatetimeIndex(df["decision_time"]).as_unit("ns")
        df["day_end"] = pd.DatetimeIndex(df["day_end"]).as_unit("ns")
        df.insert(1, "available_at", df["decision_time"])
        return df
    return detect


if __name__ == "__main__":
    mkt = cl.get_market()
    for reading, level in (("a", "18:00"), ("b", "00:00")):
        det = make_detect(level)
        ev = cl.cache_frame(f"to02a_dailyopen_respect_{level.replace(':', '')}_k10",
                            lambda: det(cl.load_m1()))
        print(reading, level, len(ev), "touch events")
        probe = cl.probe_lookahead(det, ev, lookback="10D")
        t = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
        i0 = mkt.pos_at_or_after(t)
        nb = mkt.pos_at_or_after(pd.DatetimeIndex(ev["day_end"]).tz_convert("UTC")) - i0
        ref = mkt.o[np.minimum(i0, len(mkt.o) - 1)]
        s = ev["side"].to_numpy()
        lv, k = ev["level"].to_numpy(float), ev["k"].to_numpy(float)
        d_resp = lv + s * k - ref           # distance to the 'respected' target
        d_thru = lv - s * k - ref           # distance to the 'through' target

        def resolve(tt, base, dr, dt, sd, nbars):
            out = np.full(len(tt), np.nan)
            BIG = np.iinfo(np.int64).max
            hr = np.full(len(tt), False); ht = np.full(len(tt), BIG, dtype=np.int64)
            hx = np.full(len(tt), False); hxt = np.full(len(tt), BIG, dtype=np.int64)
            for sg, side_r, side_t in ((1, "above", "below"), (-1, "below", "above")):
                m = sd == sg
                if not m.any():
                    continue
                r = cl.touch(tt[m], base[m] + dr[m], side_r, horizon_bars=nbars[m])
                x = cl.touch(tt[m], base[m] + dt[m], side_t, horizon_bars=nbars[m])
                hr[m], hx[m] = r["hit"].to_numpy(), x["hit"].to_numpy()
                ht[m] = np.where(hr[m], pd.DatetimeIndex(r["hit_time"]).as_unit("ns").asi8, BIG)
                hxt[m] = np.where(hx[m], pd.DatetimeIndex(x["hit_time"]).as_unit("ns").asi8, BIG)
            resp = hr & (~hx | (ht < hxt))
            thru = hx & (~hr | (hxt <= ht))
            out[resp] = 1.0
            out[thru] = 0.0
            return out

        obs = resolve(t, ref, d_resp, d_thru, s, nb)
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED)

        def null_fn(rng, kk):
            tk = pd.DatetimeIndex(rt[:, kk]).tz_localize("UTC")
            ok = ~tk.isna()
            out = np.full(len(t), np.nan)
            j0 = mkt.pos_at_or_after(tk[ok])
            base = mkt.o[np.minimum(j0, len(mkt.o) - 1)]
            out[ok] = resolve(tk[ok], base, d_resp[ok], d_thru[ok], s[ok], nb[ok])
            return out

        print("  observed respected", np.nanmean(obs), "resolved", np.isfinite(obs).mean())
        res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                           predictors=ev, null_fn=null_fn)
        show(res)
        lvl_rule = ("L = open of the trading day's first M1 bar, required to print in [18:00, 18:10) NY (the feed's daily candle open)"
                    if level == "18:00" else
                    "L = open of the first M1 bar in [00:00, 00:05) NY of the trading day (midnight opening price)")
        op = {"rules": [lvl_rule,
                        "k = 0.10 x range of the previous trading day with >= 600 M1 bars",
                        "arm = first M1 bar from L's bar that trades >= k away (side s); both sides in one bar -> skip the day",
                        "touch = first later M1 bar back at L before 17:00 NY; decision = its close; one event per day",
                        "outcome from the next M1 open: 1 if L+s*k trades before L-s*k (same bar -> 0), 0 if the reverse, NaN if neither by 17:00 NY (horizon in M1 bars)",
                        "null: 5 random minutes within +/-30d (locked seed), same two target distances from that minute's open, same M1-bar horizon"],
              "params": {"level": level, "k_frac": K_FRAC, "k_basis": "previous trading day range",
                         "min_prev_m1": MIN_PREV_M1, "horizon": "to 17:00 NY, in M1 bars",
                         "tie": "same-bar -> not respected", "tz": "America/New_York"}}
        src = {"level": ("corpus: sdZkE-naNiY 'I always use 1,800'" if level == "18:00" else
                         "corpus: YXoNowXQirM 'using midnight opening price as the open for this daily candle'"),
               "k_frac": "declared-before-run: symmetric respect/through distance of 10% of the prior day's range (corpus gives no distance)",
               "k_basis": "declared-before-run: range-relative units (README trap 6)",
               "min_prev_m1": "declared-before-run: skip stub sessions (README trap 6)",
               "horizon": "declared-before-run: the rest of the trading day; M1-bar horizon (README trap 7)",
               "tie": "declared-before-run: conservative, identical in real and null arms",
               "tz": "method_spec: §1.4 DST settled, America/New_York"}
        print(cl.write_result("daily-open-eighteen-hundred", reading, res, operationalization=op,
                              params_source=src, script=__file__, probe=probe))
