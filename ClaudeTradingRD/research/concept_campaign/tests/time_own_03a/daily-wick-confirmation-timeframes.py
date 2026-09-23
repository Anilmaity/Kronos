"""daily-wick-confirmation-timeframes — Confirming the day's high/low: which timeframe, by
session (TTrades own voice, contested).

Claim ('+'): "you can mechanically confirm the wick high or wick low of the day" with a
session-dependent instrument; the execution is to trade AWAY from the confirmed wick
(continuation), stop beyond the confirmed extreme, target the previous day's high/low.
The concept carries two confirmation METHODS, which are the two readings:

  a  METHOD 1 — CISD, session map of the definition (Mo9QMtotQyo): extreme formed in
     ASIA -> 1h CISD; LONDON -> 15m or 30m CISD; NEW YORK -> 5m or 15m CISD. "A higher-
     timeframe CISD is always acceptable" (the map is a floor): allowed TFs are
     Asia {1h}, London {1h,30m,15m}, NY {1h,30m,15m,5m}.
  b  METHOD 2 — candle closure (Mo9QMtotQyo whiteboard): a 4-hour closure (any session)
     or, in New York only, a 1-hour closure ("I don't trust an hourly closure this early"
     in Asia/London); "never a timeframe below 1-hour"; the closure must be a C2 closure
     (spec §3.2 test) — its sweep of the previous candle is the point of interest.

Common to both:
  * the confirmed extreme must be a candidate for the day's high/low: it equals the
    trading day's running extreme (all closed M1 bars) at the decision time, and lies in
    the same trading day;
  * "only one CISD per day" (spec §2.4): first qualifying confirmation per trading day;
  * decide at the confirming bar's close, enter next M1 open, direction away from the
    wick, stop = the confirmed extreme, target = previous day's opposite extreme
    (execution.targets first item); rows whose target is not beyond the confirming close
    are dropped (no room — the concept's own 'sanity check before dropping down');
    time exit at 17:00 NY of that trading day.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (cl, np, pd, OHLC, daily, day_end_utc, ny_session,  # noqa: E402
                     running_extremes_at, cisd_frame, show, MIN_DAY_M1)

CID = "daily-wick-confirmation-timeframes"
READ = sys.argv[1] if len(sys.argv) > 1 else "a"
COLS = ["decision_time", "available_at", "direction", "stop_px", "target_px", "max_hold",
        "tf", "session"]

ALLOWED_A = {"asia": {"1h"}, "london": {"1h", "30min", "15min"},
             "ny": {"1h", "30min", "15min", "5min"}}
ALLOWED_B = {"asia": {"4h"}, "london": {"4h"}, "ny": {"4h", "1h"}}


def _finish(m1, cand: pd.DataFrame) -> pd.DataFrame:
    """cand: decision_time, direction (+1/-1), xp (extreme), x_time (extreme bar start),
    ref_close (confirming close), tf. Applies the shared filters and trade geometry."""
    if cand.empty:
        return pd.DataFrame(columns=COLS)
    # deterministic tie order when two TFs confirm at the same close: higher TF first
    rank = {"4h": 0, "1h": 1, "30min": 2, "15min": 3, "5min": 4}
    cand = (cand.assign(_r=cand["tf"].map(rank))
            .sort_values(["decision_time", "_r"], kind="stable")
            .drop(columns="_r").reset_index(drop=True))
    dec = pd.DatetimeIndex(cand["decision_time"])
    bull = cand["direction"].to_numpy() > 0
    xp = cand["xp"].to_numpy(float)
    rlo, rhi, rtd = running_extremes_at(m1, dec)
    td_x = cl.trading_day(pd.DatetimeIndex(cand["x_time"]))
    is_ext = np.where(bull, np.isclose(xp, rlo, rtol=0, atol=1e-6),
                      np.isclose(xp, rhi, rtol=0, atol=1e-6))
    same_day = np.asarray(pd.DatetimeIndex(rtd) == pd.DatetimeIndex(td_x))
    d = daily(m1)
    prev = cl.asof(d[OHLC + ["close_time", "trading_day"]], dec)
    gap = (pd.DatetimeIndex(rtd) - pd.DatetimeIndex(prev["trading_day"])).days
    prev_ok = np.asarray((gap >= 1) & (gap <= 4))
    tgt = np.where(bull, prev["high"].to_numpy(float), prev["low"].to_numpy(float))
    ref = cand["ref_close"].to_numpy(float)
    room = np.where(bull, tgt > ref, tgt < ref)
    hold = day_end_utc(pd.DatetimeIndex(rtd)) - dec
    ok = is_ext & same_day & prev_ok & room & np.asarray(hold > pd.Timedelta(0))
    out = pd.DataFrame({
        "decision_time": dec, "available_at": dec,
        "direction": np.where(bull, 1, -1),
        "stop_px": xp, "target_px": tgt, "max_hold": hold,
        "tf": cand["tf"].to_numpy(), "session": cand["session"].to_numpy(),
        "tday": pd.DatetimeIndex(rtd),
    })[ok]
    out = out.drop_duplicates("tday", keep="first")
    return out[COLS].reset_index(drop=True)


def detect_a(m1: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for tf in ("1h", "30min", "15min", "5min"):
        ev = cisd_frame(m1, tf)
        if ev.empty:
            continue
        sess = ny_session(pd.DatetimeIndex(ev["extreme_time"]))
        keep = np.array([tf in ALLOWED_A[s] for s in sess], dtype=bool)
        e = ev[keep]
        parts.append(pd.DataFrame({
            "decision_time": pd.DatetimeIndex(e["decision_time"]),
            "direction": np.where(e["direction"] == "bullish", 1, -1),
            "xp": e["extreme_price"].to_numpy(float),
            "x_time": pd.DatetimeIndex(e["extreme_time"]),
            "ref_close": e["confirm_close"].to_numpy(float),
            "tf": tf, "session": sess[keep]}))
    cand = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return _finish(m1, cand)


def detect_b(m1: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for tf in ("4h", "1h"):
        b = cl.build_bars(m1, tf)
        pl, ph = b["low"].shift(1), b["high"].shift(1)
        bull = ((b["low"] < pl) & (b["close"] > pl)).fillna(False).to_numpy()
        bear = ((b["high"] > ph) & (b["close"] < ph)).fillna(False).to_numpy()
        one = bull ^ bear                                   # two-sided C2 -> skip
        sess = ny_session(b.index if tf == "1h" else b.index)
        if tf == "4h":
            sess_ok = np.ones(len(b), bool)                 # 4h closure allowed everywhere
            sess = ny_session(pd.DatetimeIndex(b["close_time"]) - pd.Timedelta(minutes=1))
        else:
            sess_ok = np.array([tf in ALLOWED_B[s] for s in sess], dtype=bool)
        k = one & sess_ok
        e = b[k]
        bu = bull[k]
        parts.append(pd.DataFrame({
            "decision_time": pd.DatetimeIndex(e["close_time"]),
            "direction": np.where(bu, 1, -1),
            "xp": np.where(bu, e["low"], e["high"]).astype(float),
            # the C2 bar's own last minute: its extreme lies inside this bar, which
            # belongs to the trading day of its close (a forex-grid 17:00 bar holds the
            # new day's 18:00-21:00 data)
            "x_time": pd.DatetimeIndex(e["close_time"]) - pd.Timedelta(minutes=1),
            "ref_close": e["close"].to_numpy(float),
            "tf": tf, "session": sess[k]}))
    cand = pd.concat(parts, ignore_index=True)
    return _finish(m1, cand)


if READ == "a":
    detect, key = detect_a, "dwct_a_cisd_map_v2"
    OP = {"rules": [
        "CISD (detectors.cisd: close through the OPEN of the first candle of the opposing run "
        "into a 2/2 swing, within 3 bars) on 1h, 30m, 15m and 5m bars",
        "session of the extreme bar's start (NY): Asia [18:00,02:00), London [02:00,07:00), "
        "NY [07:00,17:00); allowed TFs Asia {1h}, London {1h,30m,15m}, NY {1h,30m,15m,5m} "
        "(definition map as a floor; higher TF always counts)",
        "the CISD extreme equals the trading day's running extreme at the confirm close "
        "(candidate daily wick), same trading day",
        "first qualifying CISD per trading day; decide at the confirming bar close",
        "direction away from the wick; stop = the extreme; target = previous (non-stub) "
        "day's opposite extreme, rows with no room dropped; exit 17:00 NY"],
        "params": {"tfs": "1h,30min,15min,5min", "session_bounds": "18-02/02-07/07-17 NY",
                   "map": "asia:1h; london:1h,30m,15m; ny:1h,30m,15m,5m",
                   "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                   "min_series": 1, "one_per_day": True,
                   "target": "previous day opposite extreme", "max_hold": "to 17:00 NY",
                   "stub_filter_min_m1": MIN_DAY_M1, "ctrl_tod_tol_min": 30}}
else:
    detect, key = detect_b, "dwct_b_closure_map_v2"
    OP = {"rules": [
        "C2 closure (spec §3.2: sweep the previous candle's extreme, close back inside; "
        "two-sided skipped) on 4h (forex grid 17/21/01/05/09/13 NY) or 1h bars",
        "4h closure allowed in every session; 1h closure only when the 1h C2 bar starts in "
        "NY [07:00,17:00) ('I don't trust an hourly closure this early'); nothing below 1h",
        "the C2's extreme equals the trading day's running extreme at the C2 close "
        "(candidate daily wick), same trading day",
        "first qualifying closure per trading day; decide at the C2 close",
        "direction away from the wick; stop = the C2 extreme; target = previous (non-stub) "
        "day's opposite extreme, rows with no room dropped; exit 17:00 NY"],
        "params": {"tfs": "4h,1h", "grid4h": "forex", "session_bounds": "18-02/02-07/07-17 NY",
                   "map": "asia:4h; london:4h; ny:4h,1h", "one_per_day": True,
                   "target": "previous day opposite extreme", "max_hold": "to 17:00 NY",
                   "stub_filter_min_m1": MIN_DAY_M1, "ctrl_tod_tol_min": 30}}

SRC = {"tfs": "corpus: Mo9QMtotQyo 'in Asia, I want to use an hourly change in the state of "
              "delivery' / 'In London, I'd want to use that M15 or M30 CISD' / 4-hour or 1-hour "
              "closure, never below",
       "session_bounds": "declared-before-run: partition at killzone starts (London 02:00, "
                         "forex NY AM 07:00; session_window_fit killzones.yaml) and the "
                         "18:00 NY day open",
       "map": "corpus: Mo9QMtotQyo session map (method_spec §2.4 table); 'a higher-timeframe "
              "CISD always counts' -> floor",
       "level_rule": "phase3: locked CISD level rule (first-candle open), method_spec §4.2",
       "swing": "phase3: locked swing fractal left=2,right=2",
       "max_wait": "phase3: locked max_wait=3 (v-shape-reversal-speed '1, 2, maybe three')",
       "min_series": "phase3: locked min_series=1",
       "grid4h": "method_spec: §1.4 forex grid for gold",
       "one_per_day": "method_spec: §2.4 'There is only one CISD per day'",
       "target": "corpus: execution.targets 'previous day high / low' (first listed)",
       "max_hold": "declared-before-run: the wick confirmation is for the current day",
       "stub_filter_min_m1": "declared-before-run: README trap 6 stub sessions (n_m1>=600)",
       "ctrl_tod_tol_min": "declared-before-run: confirmations cluster by session clock and "
                           "the concept is about the confirming instrument, not the hour "
                           "(README trap 9)"}
SRC = {k: v for k, v in SRC.items() if k in OP["params"]}

FIX_NOTE = ("Rerun once after a bug fix: when two timeframes confirmed at the same close the "
            "candidate order was an unstable sort; now the higher timeframe wins deterministically "
            "(found when reading b's probe failed on exactly such a tie)." if READ == "a" else
            "Same-close ties between timeframes resolved higher-TF-first (deterministic).")

if __name__ == "__main__":
    ev = cl.cache_frame(key, lambda: detect(cl.load_m1()))
    print(READ, len(ev), ev["direction"].value_counts().to_dict(),
          ev.groupby(["session", "tf"]).size().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="10D")
    print("probe", probe.get("passed"))
    res = cl.trade_test(ev, ctrl_tod_tol_min=30)
    show(res)
    p = cl.write_result(CID, READ, res, operationalization=OP, params_source=SRC,
                        script=__file__, probe=probe,
                        notes="Daily-bias precondition not applied: the test isolates the "
                              "confirmation instrument (direction = away from the confirmed "
                              "wick). Hold per row = to 17:00 NY (max_hold column, wall clock, "
                              "no halt inside the trading day). " + FIX_NOTE)
    print(p)
