"""smt-divergence-confluence (guests: Finessee_Fx, Ben, $niper, AP, AM Trades) -> gate_test x2.

Contested: WHERE SMT counts. Correlate = XAG_USD H1 (the gold SMT pair the
phase-3 harness used; OANDA feed from 2010). SMT is confluence, never a signal,
so both readings gate a baseline entry book.

Baseline entry: 1h bare CISD, phase-3 locked config (series_open level, 2/2 swing,
max_wait 3, min_series 1), decide at the confirming bar's close, stop at the
protected swing, 2R, 10h hold.

reading a (extremes only - Finessee_Fx weekly/HTF, AP 'only at extremes', $niper
  HTF levels): baseline restricted to CISDs whose extreme bar traded through the
  prior trading day's high (bearish) / low (bullish) on gold. Gate = silver did
  NOT take its own prior-day high/low from the start of that trading day through
  the CISD confirm bar (the correlate failed to make the matching extreme).
reading b (any scale, intra-range - Sniper's 1m/in-candle use, Ben 'in zones'):
  baseline = every 1h CISD. Gate = 1h SMT at the extreme: reference = gold's most
  recent confirmed 2/2 swing low (high) within 20 bars before the extreme bar;
  exactly one of gold / silver traded beyond its own level at that reference
  bar between the reference and the confirm bar.
"""
import sys
sys.path.insert(0, "/Users/anil/Projects/Kronos/ClaudeTradingRD/research/python")
import numpy as np
import pandas as pd
import concept_lab as cl
from detectors.cisd import cisd_events
from detectors.primitives import swing_points

XAG_PATH = "/Users/anil/Projects/Kronos/ClaudeTradingRD/m3_scalper/xag_h1_full.parquet"
LOOKBACK = 20
_XAG = None


def xag_for(m1):
    global _XAG
    if _XAG is None:
        x = pd.read_parquet(XAG_PATH)
        x.index = pd.to_datetime(x.index, utc=True)
        _XAG = x[["open", "high", "low", "close"]].astype(float).sort_index()
    end = pd.DatetimeIndex(m1.index).max() + pd.Timedelta(minutes=1)
    start = pd.DatetimeIndex(m1.index).min()
    x = _XAG
    return x[(x.index >= start.floor("1h")) & (x.index + pd.Timedelta(hours=1) <= end)]


def base(m1):
    b = cl.build_bars(m1, "1h")
    ev = cisd_events(b[["open", "high", "low", "close"]], level_rule="series_open",
                     left=2, right=2, max_wait=3, min_series=1)
    return b, ev


def detect(m1, reading):
    b, ev = base(m1)
    cols = ["decision_time", "available_at", "direction", "stop_px", "rr", "smt"]
    if ev.empty:
        return pd.DataFrame(columns=cols)
    y = xag_for(m1)
    # silver aligned to gold's 1h grid (gold bar starts); missing silver hours -> NaN
    yh = y["high"].reindex(b.index).to_numpy()
    yl = y["low"].reindex(b.index).to_numpy()
    xh, xl = b["high"].to_numpy(), b["low"].to_numpy()
    pos = {t: k for k, t in enumerate(b.index)}
    close = pd.DatetimeIndex(b["close_time"])
    ej = np.array([pos[t] for t in ev["extreme_time"]])
    cj = np.array([pos[t] for t in ev["confirm_time"]])
    bull = (ev["direction"] == "bullish").to_numpy()
    keep = np.ones(len(ev), bool)
    smt = np.zeros(len(ev), bool)
    if reading == "a":
        td = cl.trading_day(b.index)
        tdu = pd.DatetimeIndex(td.unique())
        dmap = {d: k for k, d in enumerate(tdu)}
        dk = np.array([dmap[d] for d in td])
        xs = pd.DataFrame({"d": dk, "xh": xh, "xl": xl, "yh": yh, "yl": yl})
        g = xs.groupby("d")
        dh = g[["xh", "yh"]].max(); dl = g[["xl", "yl"]].min()   # NaN-skipping
        first = g.apply(lambda f: f.index.min(), include_groups=False)
        for i in range(len(ev)):
            j, c, d = ej[i], cj[i], dk[ej[i]]
            if d - 1 not in dh.index:
                keep[i] = False; continue
            s0 = first[d]
            if bull[i]:
                pxl, pyl = dl.loc[d - 1, "xl"], dl.loc[d - 1, "yl"]
                if not (xl[j] < pxl) or np.isnan(pyl):
                    keep[i] = False; continue
                w = yl[s0:c + 1]
                if np.all(np.isnan(w)):
                    keep[i] = False; continue
                smt[i] = np.nanmin(w) >= pyl
            else:
                pxh, pyh = dh.loc[d - 1, "xh"], dh.loc[d - 1, "yh"]
                if not (xh[j] > pxh) or np.isnan(pyh):
                    keep[i] = False; continue
                w = yh[s0:c + 1]
                if np.all(np.isnan(w)):
                    keep[i] = False; continue
                smt[i] = np.nanmax(w) <= pyh
    else:
        sw = swing_points(b[["open", "high", "low", "close"]], left=2, right=2)
        swl = np.flatnonzero(sw["swing_low"].to_numpy())
        swh = np.flatnonzero(sw["swing_high"].to_numpy())
        for i in range(len(ev)):
            j, c = ej[i], cj[i]
            arr = swl if bull[i] else swh
            cand = arr[(arr + 2 <= j - 1) & (arr >= j - LOOKBACK)]   # confirmed before the extreme bar
            if len(cand) == 0:
                continue
            p = cand[-1]
            if bull[i]:
                xb = np.nanmin(xl[p + 1:c + 1]) < xl[p]
                w = yl[p + 1:c + 1]
                if np.isnan(yl[p]) or np.all(np.isnan(w)):
                    continue
                yb = np.nanmin(w) < yl[p]
            else:
                xb = np.nanmax(xh[p + 1:c + 1]) > xh[p]
                w = yh[p + 1:c + 1]
                if np.isnan(yh[p]) or np.all(np.isnan(w)):
                    continue
                yb = np.nanmax(w) > yh[p]
            smt[i] = xb != yb
    dt = close[cj]
    out = pd.DataFrame({"decision_time": dt, "available_at": dt,
                        "direction": np.where(bull, 1, -1),
                        "stop_px": ev["protected_swing"].to_numpy(), "rr": 2.0,
                        "smt": smt})
    return out[keep].reset_index(drop=True)


def run(reading):
    fn = lambda m: detect(m, reading)
    ev = cl.cache_frame(f"smt_conf_1h_cisd_{reading}_lb{LOOKBACK}", lambda: fn(cl.load_m1()))
    print(reading, "events", len(ev), "smt rate", ev["smt"].mean())
    probe = cl.probe_lookahead(fn, ev, lookback="45D")
    res = cl.gate_test(ev, "smt", mask_available_at="decision_time", max_hold="10h", claim="+")
    for k in ("n", "n_gated", "diff", "ci_lo", "ci_hi", "p", "mde", "verdict", "verdict_detail", "ties", "exposure_bars", "ctrl_overlap"):
        print(" ", k, res.get(k))
    common = ["baseline: 1h bare CISD, series_open level, 2/2 swing, max_wait 3, min_series 1; decide at confirm-bar close, enter next M1 open; stop protected swing; 2R; 10h hold",
              "correlate: XAG_USD H1 (OANDA), aligned on gold's 1h bar starts, only silver bars closed by the decision are read"]
    if reading == "a":
        rules = common + ["baseline restricted to CISDs whose extreme bar traded through gold's prior trading-day high (bearish) / low (bullish), 18:00 NY roll",
                          "gate smt = silver did not trade through its own prior-day high/low from the trading-day start to the confirm bar"]
    else:
        rules = common + ["gate smt = reference = gold's latest confirmed 2/2 swing (same side) within 20 bars before the extreme; exactly one of gold/silver traded beyond its own level at that reference bar by the confirm bar"]
    op = {"rules": rules,
          "params": {"tf": "1h", "level_rule": "series_open", "swing": "2/2", "max_wait": 3,
                     "min_series": 1, "rr": 2.0, "max_hold": "10h", "correlate": "XAG_USD H1",
                     "day_open_hour": 18, "smt_lookback_bars": LOOKBACK}}
    src = {k: "phase3: meta/conjunction_preregistration.md §1.8-1.13 (locked config)"
           for k in ("tf", "level_rule", "swing", "max_wait", "min_series", "rr", "max_hold")}
    src["correlate"] = "phase3: backtest_conjunction.load_correlate - XAG is the gold SMT correlate (no DXY in data); yaml says no source rule for choosing the reference"
    src["day_open_hour"] = "session_window_fit: settled 18:00 NY daily roll"
    src["smt_lookback_bars"] = "phase3: detectors/bias.smt_events default lookback=20"
    notes = ("Contested concept, reading %s. Guests used DXY/SPY/ES/YM correlates; gold's only available correlate is XAG." % reading)
    p = cl.write_result("smt-divergence-confluence", reading, res, operationalization=op,
                        params_source=src, script=__file__, probe=probe, notes=notes)
    print(p)


if __name__ == "__main__":
    for r in sys.argv[1:] or ["a", "b"]:
        run(r)
