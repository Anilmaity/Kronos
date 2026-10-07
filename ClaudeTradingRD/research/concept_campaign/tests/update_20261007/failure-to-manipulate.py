"""failure-to-manipulate — update 2026-10-07 (live_07, live_13, edu_02 drafts). NEW claims only.

Prior reading (results/failure-to-manipulate.json, expansion-into-PDL/PDH book) is untouched.

Shared detector (1h, phase-3 CISD config, PDL/PDH of the last complete non-stub day):
  break    = first 1h bar of the trading day whose low < PDL (mirror: high > PDH)
  branch   = the FIRST 1h CISD confirmed at/after the break bar's close, whose extreme
             formed at/after the break bar, before 17:00 NY:
               opposite direction (bullish at PDL) -> manipulation / reversal, no event
               same direction (bearish at PDL)     -> failure to manipulate = a new
                 continuation with a new protected swing; event at its confirming close
Readings:
  u1007a  rate_test (live_13 wa9m30UHrm0 "Do we form a reversal here? No, we form a
          continuation, which means lower, which means hello, the market is trending";
          live_07 9YVBe-20Hdg): hit = price trades beyond the day's running extreme
          (closed 1h bars to the decision) before the 17:00 NY session end. Null = same
          distance from price in local-volatility units (trailing 240 M1 bars mean
          high-low), same M1-bar horizon, at matched random moments (+/-30 d, NY clock
          +/-30 min) -- campaign lesson 3: rate nulls match time of day and local vol.
  u1007b  trade_test (edu_02 8yt3jn8L6O4): enter on that continuation, stop on its
          protected swing, 2R, only when the daily previous-candle bias (bias.py §2.3)
          agrees with the breakout direction ("paired with a daily time frame").
Not testable here: the cross-asset drag / YM->ES->NQ cascade (other assets), and the
discretionary HTF candle override of a mechanical CISD.

Vault audit (rerun 2026-10-07, KronosVault Backtest Methodology Traps + Concept Campaign):
logic unchanged from the first u1007 run, so the hypotheses (hyp_key) are the same ones.
  trap 1 geometry      : u1007a null keeps the event's distance to the running extreme (vol units)
  trap 2/3 M1, label   : harness M1 exits, stop-first ties; every stamp is a 1h close_time
  trap 4 regime        : harness +/-30 d controls
  trap 6 power         : MDE reported; both readings were UNDERPOWERED on the first run
  trap 7 never-eval    : bias 'none' -> excluded, not passed; exact per-day join, no forward fill
  trap 8 structure     : certified 2016+ only; level rule, no absolute-point thresholds
  trap 9 in-progress   : symmetric probe on the scored frame; CISD stamped at the confirm close
  campaign lesson 1    : the random control matches stop distance, not placement; the 1h bare
                         CISD (rung 0, same stop rule) is NULL +0.009R vs that control
  campaign lesson 3    : null matches NY clock +/-30 min and local volatility
Not re-tested: PDL as a magnet (previous-period-high-low: reached slightly less often than an
equidistant level); the live_07 PDL target is only new through its cross-asset trigger.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/concept_campaign/tests/model_own_02b")
import numpy as np
import pandas as pd
import concept_lab as cl
import _common as C
from detectors.bias import previous_candle_state

READ = sys.argv[1] if len(sys.argv) > 1 else "u1007a"
TF = "1h"
VOL_BARS = 240          # trailing M1 bars for the local-volatility scale of the null distance
TOD_TOL = 30
RR = 2.0
MAX_HOLD = "10h"
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr", "lvl", "bias_ok"]


def detect_all(m1):
    h = C.complete_bars(m1, TF)
    d = C.daily(m1)
    imp = previous_candle_state(d[["open", "high", "low", "close"]])["implied_bias"]
    bias_by_td = pd.Series(imp.to_numpy(), index=d["td"])
    h["td"] = pd.DatetimeIndex(cl.trading_day(h.index))
    tds = pd.DatetimeIndex(h["td"].unique())
    lv = C.prev_day_levels(d, tds)
    cz = C.cisd_table(h).sort_values(["t", "extreme_start", "dir"], kind="stable")
    cz["td"] = pd.DatetimeIndex(cl.trading_day(pd.DatetimeIndex(cz["t"]) - pd.Timedelta("1min")))
    send = C.ny_local(tds, 17 * 60, day_offset=1)
    rows = []
    for i, td in enumerate(tds):
        pdh, pdl, ptd = lv.loc[td, "pdh"], lv.loc[td, "pdl"], lv.loc[td, "pd_td"]
        if np.isnan(pdh):
            continue
        hb = h[h["td"] == td]
        cd = cz[cz["td"] == td]
        bias = bias_by_td.get(ptd, "none")
        for dr, brk in ((-1, hb["low"] < pdl), (1, hb["high"] > pdh)):
            if not brk.any():
                continue
            bstart = brk.idxmax()
            bclose = hb.loc[bstart, "close_time"]
            c = cd[(cd["t"] >= bclose) & (cd["extreme_start"] >= bstart) & (cd["t"] < send[i])]
            if c.empty or c.iloc[0]["dir"] != dr:
                continue
            e = c.iloc[0]
            if (e["stop"] - e["confirm_close"]) * dr >= 0:      # stop must be behind entry side
                continue
            done = hb[hb["close_time"] <= e["t"]]
            lvl = done["low"].min() if dr == -1 else done["high"].max()
            rows.append({"decision_time": e["t"], "available_at": e["t"], "direction": dr,
                         "stop_px": float(e["stop"]), "rr": RR, "lvl": float(lvl),
                         "bias_ok": bias == ("bullish" if dr == 1 else "bearish")})
    out = pd.DataFrame(rows, columns=COLS)
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"])
    out["available_at"] = pd.DatetimeIndex(out["available_at"])
    out["bias_ok"] = out["bias_ok"].astype(bool)
    return out.sort_values("decision_time", kind="stable").reset_index(drop=True)


def detect_b(m1):
    ev = detect_all(m1)
    return ev[ev["bias_ok"]].reset_index(drop=True)


RULES_COMMON = [
    "1h bars (18:00 NY roll); PDL/PDH = last complete trading day with >= 600 M1 bars",
    "break = first 1h bar of the day trading below PDL (mirror above PDH)",
    "first 1h CISD (series_open, swing 2/2, max_wait 3, min_series 1) confirmed at/after the "
    "break bar close, with its extreme at/after the break bar, before 17:00 NY: opposite "
    "direction = reversal (no event); same direction = failure to manipulate (new continuation, "
    "new protected swing) -> event at its confirming close",
]
SRC_COMMON = {
    "tf": "corpus: 8yt3jn8L6O4 'usually on the hourly or 30-minute time frame paired with a daily time frame' (1h picked, the first named)",
    "level": "corpus: wa9m30UHrm0 'Here's our previous day low. ... We trade through it'; 9YVBe-20Hdg 'go towards its previous day low'",
    "min_day_m1": "declared-before-run: trap 6 stub sessions skipped (same as prior reading)",
    "cisd": "phase3: locked CISD config; corpus 8yt3jn8L6O4 'failing to form a change in the state of delivery in the other direction'",
    "continuation": "corpus: 8yt3jn8L6O4 'a bearish continuation, a new protected swing' / 'I'm going to first wait for a continuation to form'",
    "grid4h": "declared-before-run: not used (1h bars, 18:00 NY day roll; trap 8)",
    "session_end": "corpus: wa9m30UHrm0 'Don't try to catch lows on a trend day' (one session); declared 17:00 NY close",
}

NOTES = ("Rerun with vault context: logic identical to the first u1007 run. Single-asset XAUUSD "
         "reading; the cross-asset drag (YM->ES->NQ) and the discretionary HTF-candle override are "
         "not tested. PDL-as-magnet is not re-tested (previous-period-high-low). The trade-test "
         "control matches stop distance, not placement (campaign lesson 1); cost 0.04R is below "
         "the real ~0.6 pt spread on short stops (lesson 2) and cancels in diff.")

if __name__ == "__main__":
    m1 = cl.load_m1()
    if READ == "u1007a":
        ev = cl.cache_frame("ftm_u1007a_1h_v1", lambda: detect_all(cl.load_m1()))
        print(len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_all, ev, lookback="20D")
        print("probe", probe.get("passed"))
        mkt = cl.get_market()
        t = pd.DatetimeIndex(ev["decision_time"])
        dr = ev["direction"].to_numpy()
        send = C.session_end(t)
        idx = m1.index.as_unit("ns").asi8
        nb = (np.searchsorted(idx, send.as_unit("ns").asi8, side="left")
              - np.searchsorted(idx, t.as_unit("ns").asi8, side="left"))
        first_px = mkt.o[np.minimum(mkt.pos_at_or_after(t), len(mkt.o) - 1)]
        g = (ev["lvl"].to_numpy() - first_px) * dr               # >0 when level is beyond price
        # local volatility: mean M1 high-low over the VOL_BARS bars closed before a moment
        cs = np.concatenate([[0.0], np.cumsum(mkt.h - mkt.l)])

        def lvol(times):
            p = mkt.pos_at_or_after(times)
            v = (cs[p] - cs[np.maximum(p - VOL_BARS, 0)]) / VOL_BARS
            return np.where(p >= VOL_BARS, v, np.nan)

        vol_e = lvol(t)

        def hits(times, px, rows, gg):
            out = np.full(len(rows), np.nan)
            for s, side in ((1, "above"), (-1, "below")):
                m = (dr[rows] == s) & np.isfinite(gg)
                if m.any():
                    out[m] = cl.touch(times[m], px[m] + s * gg[m], side,
                                      horizon_bars=nb[rows][m])["hit"].to_numpy()
            return out

        allr = np.arange(len(t))
        obs = hits(t, first_px, allr, g)
        rt = cl.sample_times(t, 5, 30, seed=cl.rules.SEED, tod_tol_min=TOD_TOL)

        def null_fn(rng, k):
            tk = pd.DatetimeIndex(rt[:, k]).tz_localize("UTC")
            ok = np.flatnonzero(~tk.isna())
            out = np.full(len(t), np.nan)
            px = mkt.o[mkt.pos_at_or_after(tk[ok])]
            gg = g[ok] * lvol(tk[ok]) / vol_e[ok]                 # same distance in local-vol units
            out[ok] = hits(tk[ok], px, ok, gg)
            return out

        print("g median pts", float(np.median(g)), "vol_e median", float(np.nanmedian(vol_e)),
              "horizon bars median", float(np.median(nb)))

        res = cl.rate_test(obs, t, available_at=pd.DatetimeIndex(ev["available_at"]),
                           null_fn=null_fn, predictors=ev)
        print({k: res.get(k) for k in ("n", "observed_rate", "null_rate", "diff", "ci_lo",
                                       "ci_hi", "p", "mde", "verdict", "verdict_detail")})
        op = {"rules": RULES_COMMON + [
            "hit = any M1 trade beyond the day's running extreme (closed 1h bars up to the "
            "decision; low for a PDL failure, high for a PDH failure) before 17:00 NY, horizon "
            "in M1 bars",
            "null = same signed distance from the next M1 open in local-volatility units "
            "(distance x vol_random / vol_event, vol = mean M1 high-low over the 240 M1 bars "
            "closed before the moment), same M1-bar horizon, at matched random moments "
            "(sample_times reps 5, +/-30d, NY clock +/-30 min)",
            "claim '+': after a failure to manipulate the day is trending, price continues "
            "beyond the extreme more often than at random"],
            "params": {"tf": TF, "level": "PDL/PDH", "min_day_m1": C.MIN_DAY_M1,
                       "cisd": "series_open, swing 2/2, max_wait 3, min_series 1",
                       "continuation": "first post-break CISD same direction",
                       "session_end": "17:00 NY", "grid4h": "n/a (1h)",
                       "null_vol_bars": VOL_BARS, "null_tod_tol_min": TOD_TOL}}
        src = dict(SRC_COMMON, hit="corpus: wa9m30UHrm0 'we form a continuation, which means lower, "
                   "which means hello, the market is trending'",
                   null_vol_bars="declared-before-run: campaign lesson 3 (rate nulls must match local "
                                 "volatility); 240 M1 bars = 4 trading hours, spans the break-to-CISD sequence",
                   null_tod_tol_min="declared-before-run: trap 9 / campaign lesson 3, PDH/PDL breaks "
                                    "cluster in London/NY hours")
        print(cl.write_result("failure-to-manipulate", "u1007a", res, operationalization=op,
                              params_source=src, script=__file__, probe=probe, notes=NOTES))
    else:
        ev = cl.cache_frame("ftm_u1007b_1h_v1", lambda: detect_b(cl.load_m1()))
        print(len(ev), ev["direction"].value_counts().to_dict())
        probe = cl.probe_lookahead(detect_b, ev, lookback="20D")
        print("probe", probe.get("passed"))
        res = cl.trade_test(ev, max_hold=MAX_HOLD, hold_basis="bars", ctrl_tod_tol_min=30)
        mkt = cl.get_market()
        ep = mkt.o[np.minimum(mkt.pos_at_or_after(pd.DatetimeIndex(ev["decision_time"])), len(mkt.o) - 1)]
        print("stop dist pts median/p10", float(np.median(np.abs(ep - ev["stop_px"]))),
              float(np.percentile(np.abs(ep - ev["stop_px"]), 10)))
        print({k: res.get(k) for k in ("n", "avg_R", "diff", "ci_lo", "ci_hi", "p", "mde",
                                       "verdict", "verdict_detail", "ties", "exposure_bars",
                                       "ctrl_overlap")})
        op = {"rules": RULES_COMMON + [
            "keep only events where the daily previous-candle engine (bias.py §2.3, implied "
            "bias of the previous complete day) agrees with the breakout direction",
            "enter next M1 open after the confirming close, stop = the continuation CISD's "
            "protected swing, target 2R, 10h trading time; control NY clock +/-30 min"],
            "params": {"tf": TF, "level": "PDL/PDH", "min_day_m1": C.MIN_DAY_M1,
                       "cisd": "series_open, swing 2/2, max_wait 3, min_series 1",
                       "continuation": "first post-break CISD same direction",
                       "session_end": "17:00 NY", "bias": "daily previous_candle_state",
                       "rr": RR, "max_hold": MAX_HOLD, "hold_basis": "bars",
                       "ctrl_tod_tol_min": 30}}
        src = dict(SRC_COMMON,
                   bias="corpus: 8yt3jn8L6O4 'You want to blend this with a bias' / 'paired with a daily "
                        "time frame'; mechanised with the campaign's daily previous-candle engine (spec §2.3)",
                   rr="corpus: 8yt3jn8L6O4 'there you go, we hit 2R'",
                   max_hold="phase3: §1.13 10 entry-TF bars",
                   hold_basis="declared-before-run: trading time (trap 7)",
                   ctrl_tod_tol_min="declared-before-run: trap 9, not a timing concept")
        print(cl.write_result("failure-to-manipulate", "u1007b", res, operationalization=op,
                              params_source=src, script=__file__, probe=probe, notes=NOTES))
