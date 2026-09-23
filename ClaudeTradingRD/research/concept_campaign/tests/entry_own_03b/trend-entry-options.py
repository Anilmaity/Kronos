"""trend-entry-options — TTrades (NgFIza9qsGQ) 'There are four ways I look to enter trend.'

Execution: 'Whichever of the four the price action offers first', with the trend,
toward the marked objective. Tested as ONE book: per aggressive-trend episode, the
first entry offered by
  (1) inducement: a swing high (bearish trend) is raided and the candle closes back
      below it -> enter on that close, stop above the raided high;
  (2) mitigation block: opposing candle, its near extreme later traded through ->
      limit at its OPENING price on the retest, stop at its far extreme;
  (3) cheat code: opposing candle closes -> enter the next candle's open, stop at
      its far extreme;
  (4) 15s/30s model inside the block: needs sub-minute data -> not included.
Target 2R, exit after 150 min. Claim '+' (full entry/stop/target -> trade_test).
The turtle-soup variant is gated on 'if I'm confident' and is not included.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import _batch_common as bc    # noqa: E402
from _batch_common import cl  # noqa: E402

CID = "trend-entry-options"
RR = 2.0
MAX_HOLD = "150min"
BREAK_BARS = 16
LIVE_BARS = 16
COLS = ["decision_time", "available_at", "direction", "stop_px", "rr"]
TD = pd.Timedelta(minutes=bc.TF_MIN)


def detect(m1: pd.DataFrame) -> pd.DataFrame:
    b = bc.bars(m1)
    if len(b) < 50:
        return bc.empty(COLS)
    is_sh, is_sl = bc.swing_arrays(b)
    legs = bc.displacement_legs(b, is_sh, is_sl)
    tdir, tfire, _ = bc.trend_state(b, legs)
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ct = pd.DatetimeIndex(b["close_time"]).tz_convert("UTC")
    n = len(b)
    rows = []           # (decision_time, direction, stop, episode, option)
    # latest confirmed swing high / low known at the close of bar j-1
    last_sh = np.full(n, np.nan)
    last_sl = np.full(n, np.nan)
    ch, cl_ = np.nan, np.nan
    for j in range(n):
        p = j - bc.SW_R - 1
        if p >= 0:
            if is_sh[p]:
                ch = h[p]
            if is_sl[p]:
                cl_ = l[p]
        last_sh[j], last_sl[j] = ch, cl_
    live = tdir != 0
    # (1) inducement
    ind = live & (((tdir == -1) & (h > last_sh) & (c < last_sh)) |
                  ((tdir == 1) & (l < last_sl) & (c > last_sl)))
    for j in np.flatnonzero(ind):
        d = tdir[j]
        rows.append((ct[j], d, h[j] if d == -1 else l[j], tfire[j], 1))
    # (3) cheat code
    opp = ((tdir == -1) & (c > o)) | ((tdir == 1) & (c < o))
    for j in np.flatnonzero(opp):
        d = tdir[j]
        rows.append((ct[j], d, h[j] if d == -1 else l[j], tfire[j], 3))
    # (2) mitigation block, opening-price retest
    mb = []
    for j in np.flatnonzero(opp):
        d = tdir[j]
        end = min(n, j + 1 + BREAK_BARS)
        brk = np.flatnonzero(l[j + 1:end] < l[j]) if d == -1 else \
            np.flatnonzero(h[j + 1:end] > h[j])
        if len(brk) == 0:
            continue
        k = j + 1 + int(brk[0])
        seg = c[j + 1:k + 1]
        if (d == -1 and (seg > h[j]).any()) or (d == 1 and (seg < l[j]).any()):
            continue
        mb.append((k, d, o[j], h[j] if d == -1 else l[j], tfire[j]))
    if mb:
        r = pd.DataFrame(mb, columns=["k", "d", "lvl", "stop", "ep"])
        start = ct[r["k"].to_numpy()]
        hit, dt = bc.touch_sided(m1, start, r["lvl"].to_numpy(), r["d"].to_numpy(),
                                 start + LIVE_BARS * TD)
        for (_, x), t in zip(r[hit].iterrows(), dt[hit]):
            rows.append((t, int(x["d"]), float(x["stop"]), int(x["ep"]), 2))
    if not rows:
        return bc.empty(COLS)
    ev = pd.DataFrame(rows, columns=["decision_time", "direction", "stop_px", "ep", "opt"])
    ev["decision_time"] = pd.DatetimeIndex(ev["decision_time"]).tz_convert("UTC")
    # the first entry the price action offers per trend episode (ties -> option order)
    ev = ev.sort_values(["ep", "direction", "decision_time", "opt"], kind="stable")
    ev = ev.drop_duplicates(["ep", "direction"], keep="first")
    out = pd.DataFrame({"decision_time": ev["decision_time"].to_numpy(),
                        "available_at": ev["decision_time"].to_numpy(),
                        "direction": ev["direction"].to_numpy().astype(int),
                        "stop_px": ev["stop_px"].to_numpy(float), "rr": RR,
                        "option": ev["opt"].to_numpy().astype(int)})
    out["decision_time"] = pd.DatetimeIndex(out["decision_time"]).tz_convert("UTC")
    out["available_at"] = pd.DatetimeIndex(out["available_at"]).tz_convert("UTC")
    return bc.finish(out)


if __name__ == "__main__":
    ev = cl.cache_frame("trend_entry_options_first_per_episode", lambda: detect(cl.load_m1()))
    print("events", len(ev), ev["option"].value_counts().to_dict())
    probe = cl.probe_lookahead(detect, ev, lookback="20D")
    res = cl.trade_test(ev, max_hold=MAX_HOLD)
    for k in ["n", "avg_R", "win_rate", "diff", "ci_lo", "ci_hi", "p", "verdict",
              "verdict_detail", "ties", "exposure_bars", "ctrl_overlap", "dropped"]:
        print(" ", k, res.get(k))
    mix = ev["option"].value_counts(normalize=True).round(3).to_dict()
    op = {"rules": [
        "15m bars; aggressive trend episode = one FIRED displacement (close beyond the latest "
        "2/2 swing + threshold_fits 4-bar magnitude gate), alive 24 bars, dies on a close "
        "beyond the leg origin",
        "option 1 inducement: a candle raids the latest confirmed swing high (bearish trend) "
        "and closes back below it; enter at the next M1 open; stop at that candle's high",
        "option 2 mitigation block: opposing candle whose near extreme is traded through "
        "within 16 bars (no close beyond its far extreme first); limit at its opening price "
        "live 16 bars, filled on the first M1 touch; stop at its far extreme",
        "option 3 cheat code: opposing candle closes; enter at the next open; stop at its "
        "far extreme",
        "per episode take ONLY the earliest entry across options (same minute: option order)",
        "target 2R; exit 150 min; option 4 (15s/30s) omitted - sub-minute data"],
        "params": {"tf": bc.TF, "swing": "2/2", "disp_N": bc.DISP_N, "disp_r": bc.DISP_R,
                   "disp_d": bc.DISP_D, "trend_bars": bc.TREND_BARS, "break_bars": BREAK_BARS,
                   "live_bars": LIVE_BARS, "selection": "first per episode", "rr": RR,
                   "max_hold": MAX_HOLD}}
    src = {"tf": "corpus: trend-entry-options.yaml timeframes htf 4H/1H/15m/5m; phase3 primary entry TF",
           "swing": "phase3: locked 2/2 fractal",
           "disp_N": "threshold_fits: displacement magnitude gate default N=4",
           "disp_r": "threshold_fits: displacement magnitude gate default r=1.5",
           "disp_d": "threshold_fits: displacement magnitude gate default d=0.65",
           "trend_bars": "declared-before-run: aggressive trend lifetime 24 bars",
           "break_bars": "declared-before-run: mitigation break within 16 bars",
           "live_bars": "declared-before-run: retest limit live 16 bars",
           "selection": "corpus: trend-entry-options.yaml execution 'Whichever of the four the price action offers first'",
           "rr": "method_spec: §5.3 2R floor/fixed target stands in for 'the marked objective'",
           "max_hold": "phase3: 10 entry-TF bars (§1.13)"}
    p = cl.write_result(CID, None, res, operationalization=op, params_source=src,
                        script=__file__, probe=probe,
                        notes=f"One trade per trend episode. Option mix of the book: {mix} "
                              "(1=inducement, 2=mitigation block, 3=cheat code). The cheat code "
                              "usually offers first, so this book overlaps cheat-code-entry heavily; "
                              "stops at a just-closed candle's extreme share the stop-geometry "
                              "confound noted there." + " CAVEAT (post-verdict diagnostic, verdict NOT changed): the differential is concentrated in the smallest stops. By stop/ATR96(15m range) quintile the diff was Q1..Q5 +0.212/+0.145/+0.040/+0.092/-0.044R. A pure-noise book (random direction at random 15m closes, stop at the just-closed candle's extreme, 2R, 150 min; n=58,539, n_boot=500, not written) also came back EDGE (+0.026R [+0.013,+0.039]), +0.14R in its smallest-stop quintile: the matched control places the same stop DISTANCE at an arbitrary level, while these books put it at a recent candle extreme, which M1 noise reaches less often. Treat this EDGE as a stop-geometry artefact candidate, not a trend-entry edge.")
    print(p)
