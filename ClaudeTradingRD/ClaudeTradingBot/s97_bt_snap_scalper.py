"""
s97_bt_snap_scalper.py — validation backtest of the REAL s97_snap_scalper_m5
strategy module (KronosStrategies/strategies/backtest_strategies/s97_snap_scalper_m5.py).

- Imports the real module and drives its get_signal(w1m, w5m, w15m, now_utc)
  causally, replaying rolling windows that match the live compose env:
      RESEARCH_WIN_5M=120, RESEARCH_WIN_15M=400  (compose.yml s97 service)
- w1m is passed as None: the strategy never touches w1m (verified by reading
  the code); the live runner only length-checks it before calling.
- Evaluation cadence: once per closed M5 bar (live evaluates each new M1 close,
  but the signal state only changes when a new M5 bar closes, so this is
  equivalent up to ~1 min of entry-timing jitter).
- Fill model (honest/conservative):
    entry  : market at the NEXT M5 bar's open (mid) — live places a market
             order ~1 min after the M5 close; TP/SL keep the strategy's
             absolute prices (computed from the signal-bar close, as live).
    exits  : trigger detection on mid OHLC (position_monitor triggers on mid
             LTP). Same-bar TP+SL ambiguity -> SL FIRST (conservative).
             Gap-open beyond SL -> filled at the open, not the SL.
    costs  : 0.20 pt spread ($2.00 at 0.10 lot, $10/pt) + $4.90/lot RT
             commission => $0.49 at 0.10 lot => $2.49 per round trip.
             SL exits pay an extra 0.05 pt slippage ($0.50).
    time   : max_hold_min=30 -> exit at the open of the first bar whose open
             time >= entry_time + 30 min (position_monitor wall-clock).
- Constraints replicated from the runner: cooldown_s=600 from entry,
  max_concurrent_positions=1, session gate inside get_signal (03-09 UTC).
- Manager 'quiet_fade' gate variant: entries additionally require
  vol_regime(H1 ATR14 pctile vs trailing 30d) in {LOW, NORMAL} and
  d1_bias (ict_engine.get_market_structure on trailing 120 closed UTC-day
  candles) directional — same math as strategies/regime/regime_engine.py
  (D1 here is UTC-day resampled from M5 mid, vs OANDA NY-close daily live).
- Train 2023-01..2024-12; TEST 2025-01..2026-06 read once, params frozen.
"""
from __future__ import annotations

import json
import sys
import time as _time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

STRAT_DIR = r"E:\Projects\Kronos\KronosStrategies\strategies"
sys.path.insert(0, STRAT_DIR)

import backtest_strategies.s97_snap_scalper_m5 as s97  # noqa: E402
from strategy.ict_engine import get_market_structure  # noqa: E402

CSV = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\xau_m5_3y.csv"
OUT_JSON = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\s97_snap_scalper_bt_2026-07-02.json"

WIN_5M, WIN_15M = 120, 400           # live compose env for the s97 service
LOT = 0.10
USD_PER_PT = 10.0                    # at 0.10 lot
SPREAD_PT = 0.20
COMMISSION_USD = 4.90 * LOT          # $0.49 RT
SL_SLIP_PT = 0.05
COOLDOWN_S = 600
MAX_HOLD = timedelta(minutes=30)

TRAIN = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))
TEST = (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC"))


# ── data ──────────────────────────────────────────────────────────────────────
def naive64(s: pd.Series) -> np.ndarray:
    """tz-aware UTC Series -> naive-UTC datetime64[ns] numpy array."""
    return s.dt.tz_localize(None).to_numpy()


def load():
    df = pd.read_csv(CSV)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    return df[["time", "open", "high", "low", "close"]]


def resample(df, rule):
    x = df.set_index("time").resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    return x.reset_index()


# ── regime pieces for the quiet_fade gate (same math as regime_engine) ───────
def atr_series(c, n=14):
    h, l, cl = c["high"], c["low"], c["close"]
    pc = cl.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def vol_regime_per_h1(h1):
    """LOW/NORMAL/HIGH/EXTREME per closed H1 bar (mid-rank pctile vs trailing 30d)."""
    atr = atr_series(h1).to_numpy()
    t = naive64(h1["time"])
    out = np.array(["NORMAL"] * len(h1), dtype=object)
    for k in range(len(h1)):
        v = atr[k]
        if np.isnan(v):
            continue
        lo = np.searchsorted(t, t[k] - np.timedelta64(30, "D"))
        w = atr[lo : k + 1]
        w = w[~np.isnan(w)]
        if len(w) == 0:
            continue
        pct = 100.0 * (float((w < v).sum()) + 0.5 * float((w == v).sum())) / len(w)
        out[k] = ("EXTREME" if pct > 95 else "HIGH" if pct > 75
                  else "LOW" if pct < 25 else "NORMAL")
    return out


def d1_bias_per_day(d1):
    """'bullish'|'bearish'|'ranging' per day, from trailing 120 CLOSED daily bars
    up to and including that day (bias used the NEXT day)."""
    out = {}
    for k in range(len(d1)):
        w = d1.iloc[max(0, k - 119) : k + 1].reset_index(drop=True)
        out[d1["time"].iloc[k]] = get_market_structure(w)
    return out


# ── trade simulation ─────────────────────────────────────────────────────────
def simulate_exit(df5, entry_idx, side, sl, tp):
    """Returns (exit_idx, exit_price_mid, reason). Conservative SL-first."""
    n = len(df5)
    t = naive64(df5["time"])
    o = df5["open"].to_numpy(); h = df5["high"].to_numpy(); l = df5["low"].to_numpy()
    entry_time = t[entry_idx]
    deadline = entry_time + np.timedelta64(30, "m")
    j = entry_idx
    while j < n:
        if j > entry_idx and t[j] >= deadline:
            return j, float(o[j]), "TIME"
        if side == "SELL":
            if o[j] >= sl:
                return j, float(o[j]) + SL_SLIP_PT, "SL_GAP"
            if h[j] >= sl:
                return j, sl + SL_SLIP_PT, "SL"
            if l[j] <= tp:
                return j, tp, "TP"
        else:
            if o[j] <= sl:
                return j, float(o[j]) - SL_SLIP_PT, "SL_GAP"
            if l[j] <= sl:
                return j, sl - SL_SLIP_PT, "SL"
            if h[j] >= tp:
                return j, tp, "TP"
        j += 1
    return n - 1, float(df5["close"].iloc[-1]), "EOD"


def run_variant(df5, m15, *, label, session=(3, 9), gate=None,
                ov_mult=1.2, tp_frac=0.5, start=None, end=None, verbose=True):
    """gate: None or callable(now_ts, i5) -> bool (manager quiet_fade)."""
    # patch the real module's knobs (restored by caller)
    s97._SESSION_START_H, s97._SESSION_END_H = session
    s97._OV_MULT = ov_mult
    s97._TP_FRAC = tp_frac

    t5 = df5["time"]
    close_t = naive64(t5 + pd.Timedelta(minutes=5))       # bar close = eval time
    c = df5["close"].astype(float)
    d2 = c.diff(2)
    sigma = d2.shift(1).rolling(60, min_periods=60).std()
    cand = (d2.abs() > ov_mult * sigma) & (sigma > 0)

    hours = pd.DatetimeIndex(close_t).hour
    in_sess = (hours >= session[0]) & (hours < session[1])

    lo = np.searchsorted(close_t, np.datetime64(start.to_datetime64())) if start else 0
    hi = np.searchsorted(close_t, np.datetime64(end.to_datetime64())) if end else len(df5)

    # closed m15 bars per m5 close time: m15 close = open+15m
    m15_close = naive64(m15["time"] + pd.Timedelta(minutes=15))

    idxs = np.nonzero(cand.to_numpy() & in_sess)[0]
    idxs = idxs[(idxs >= max(lo, WIN_5M)) & (idxs < hi - 1)]

    trades = []
    busy_until = np.datetime64("1970-01-01")   # position open OR cooldown
    n_calls = 0
    t0 = _time.time()
    for i in idxs:
        now = close_t[i]
        if now < busy_until:
            continue
        now_utc = pd.Timestamp(now).to_pydatetime().replace(tzinfo=timezone.utc)
        if gate is not None and not gate(pd.Timestamp(now), i):
            continue
        w5m = df5.iloc[i - WIN_5M + 1 : i + 1].reset_index(drop=True)
        k15 = np.searchsorted(m15_close, now, side="right")
        w15m = m15.iloc[max(0, k15 - WIN_15M) : k15].reset_index(drop=True)
        n_calls += 1
        sig = s97.get_signal(None, w5m, w15m, now_utc)
        if sig is None:
            continue
        entry_idx = i + 1
        # market-closed guard: stale signal across a session gap
        if (df5["time"].iloc[entry_idx] - pd.Timestamp(now, tz="UTC")) > pd.Timedelta(minutes=30):
            continue
        entry_fill = float(df5["open"].iloc[entry_idx])
        exit_idx, exit_px, reason = simulate_exit(df5, entry_idx, sig.side,
                                                  sig.stop_loss, sig.take_profit)
        direction = 1.0 if sig.side == "BUY" else -1.0
        pts = direction * (exit_px - entry_fill)
        usd = pts * USD_PER_PT - SPREAD_PT * USD_PER_PT - COMMISSION_USD
        entry_time = df5["time"].iloc[entry_idx]
        exit_time = df5["time"].iloc[exit_idx]
        trades.append(dict(
            signal_time=str(pd.Timestamp(now)), side=sig.side, reason=reason,
            entry=entry_fill, exit=round(exit_px, 3),
            sl=sig.stop_loss, tp=sig.take_profit,
            entry_time=str(entry_time), exit_time=str(exit_time),
            pts=round(pts, 3), usd=round(usd, 2),
        ))
        busy_until = max(
            exit_time.to_datetime64(),
            entry_time.to_datetime64() + np.timedelta64(COOLDOWN_S, "s"),
        )
    if verbose:
        print(f"[{label}] candidates={len(idxs)} get_signal_calls={n_calls} "
              f"trades={len(trades)} ({_time.time()-t0:.0f}s)", flush=True)
    return trades


def metrics(trades):
    if not trades:
        return dict(trades=0, net_usd=0.0, pf=None, win_rate=None,
                    expectancy_usd=None, max_dd_usd=0.0, monthly={},
                    worst_month_share=None, tp=0, sl=0, time_exit=0)
    df = pd.DataFrame(trades)
    usd = df["usd"]
    wins = usd[usd > 0].sum()
    losses = -usd[usd <= 0].sum()
    eq = usd.cumsum()
    dd = float((eq - eq.cummax()).min())
    month = pd.to_datetime(df["entry_time"]).dt.strftime("%Y-%m")
    monthly = usd.groupby(month).sum().round(2).to_dict()
    net = float(usd.sum())
    wshare = (max(monthly.values()) / net) if net > 0 else None
    return dict(
        trades=len(df),
        net_usd=round(net, 2),
        pf=round(wins / losses, 3) if losses > 0 else None,
        win_rate=round(float((usd > 0).mean()), 3),
        expectancy_usd=round(float(usd.mean()), 3),
        avg_pts=round(float(df["pts"].mean()), 3),
        max_dd_usd=round(dd, 2),
        monthly=monthly,
        worst_month_share=round(wshare, 3) if wshare is not None else None,
        tp=int((df["reason"] == "TP").sum()),
        sl=int(df["reason"].isin(["SL", "SL_GAP"]).sum()),
        time_exit=int((df["reason"] == "TIME").sum()),
        buys=int((df["side"] == "BUY").sum()),
        sells=int((df["side"] == "SELL").sum()),
    )


def main():
    df5 = load()
    print(f"M5 bars: {len(df5)}  {df5['time'].iloc[0]} .. {df5['time'].iloc[-1]}", flush=True)
    m15 = resample(df5, "15min")
    h1 = resample(df5, "1h")
    d1 = resample(df5, "1D")

    print("precomputing regime (vol_regime H1, d1_bias)...", flush=True)
    volreg = vol_regime_per_h1(h1)
    h1_close = naive64(h1["time"] + pd.Timedelta(hours=1))
    d1_bias = d1_bias_per_day(d1)
    d1_days = naive64(d1["time"])

    def quiet_fade_gate(now_ts, i5):
        # vol_regime of the last CLOSED H1 bar
        k = np.searchsorted(h1_close, now_ts.to_datetime64(), side="right") - 1
        if k < 0 or volreg[k] not in ("LOW", "NORMAL"):
            return False
        # d1_bias from the last CLOSED UTC day (strictly before today)
        day = now_ts.normalize().to_datetime64()
        kd = np.searchsorted(d1_days, day) - 1
        if kd < 0:
            return False
        bias = d1_bias[d1["time"].iloc[kd]]
        return bias not in ("ranging", "neutral", None, "")

    # sanity: pre-filter consistency — random non-candidate in-session bars must be None
    rng = np.random.default_rng(7)
    c = df5["close"].astype(float)
    d2 = c.diff(2); sig_ = d2.shift(1).rolling(60, min_periods=60).std()
    noncand = np.nonzero((~((d2.abs() > 1.2 * sig_) & (sig_ > 0))).to_numpy())[0]
    noncand = noncand[(noncand > 5000) & (noncand < len(df5) - 10)]
    m15_close = naive64(m15["time"] + pd.Timedelta(minutes=15))
    checked = 0
    for i in rng.choice(noncand, 200, replace=False):
        now = (df5["time"].iloc[int(i)] + pd.Timedelta(minutes=5))
        if not (3 <= now.hour < 9):
            continue
        w5m = df5.iloc[int(i) - WIN_5M + 1 : int(i) + 1].reset_index(drop=True)
        k15 = np.searchsorted(m15_close, now.to_datetime64(), side="right")
        w15m = m15.iloc[max(0, k15 - WIN_15M) : k15].reset_index(drop=True)
        assert s97.get_signal(None, w5m, w15m, now.to_pydatetime()) is None
        checked += 1
    print(f"pre-filter sanity: {checked} non-candidate in-session bars all None [OK]", flush=True)

    results = {"meta": dict(
        strategy="s97_snap_scalper_m5 (kronos_s97_snap_scalper_m5)",
        data=CSV, run_date="2026-07-02",
        windows=dict(win_5m=WIN_5M, win_15m=WIN_15M),
        costs=dict(spread_pt=SPREAD_PT, commission_usd_rt=COMMISSION_USD,
                   sl_slip_pt=SL_SLIP_PT, lot=LOT, usd_per_pt=USD_PER_PT),
        fill_model="entry next-M5-open mid; SL-first same-bar; TP/SL trigger on mid; "
                   "gap-open SL at open; TIME exit at first bar-open >= entry+30min",
        notes=[
            "w1m passed as None — the strategy code never reads it (verified).",
            "evaluated once per closed M5 bar (live: each M1 close; signal state "
            "only changes per M5 close).",
            "quiet_fade d1_bias uses UTC-day candles resampled from M5 mid "
            "(live uses OANDA NY-close daily) — minor divergence.",
            "gate applied to ENTRIES only (manager pauses activation; open "
            "position handling on deactivate not modeled).",
        ],
    )}

    trade_logs = {}

    def both_periods(key, **kw):
        tr = run_variant(df5, m15, label=f"{key}/train", start=TRAIN[0], end=TRAIN[1], **kw)
        te = run_variant(df5, m15, label=f"{key}/test", start=TEST[0], end=TEST[1], **kw)
        results[key] = {"train": metrics(tr), "test": metrics(te)}
        trade_logs[key] = {"train": tr, "test": te}
        # restore frozen knobs
        s97._SESSION_START_H, s97._SESSION_END_H = 3, 9
        s97._OV_MULT, s97._TP_FRAC = 1.2, 0.5

    # A) primary: strategy exactly as coded (paper baseline, no manager gate)
    both_periods("baseline_as_coded")
    # B) + manager quiet_fade gate
    both_periods("gated_quiet_fade", gate=quiet_fade_gate)
    # C) ungated all-hours (session gate removed)
    both_periods("ungated_all_hours", session=(0, 24))

    # robustness (TEST, reported separately): ±20% on _OV_MULT and _TP_FRAC
    rb = {}
    for mult in (0.96, 1.44):
        tr = run_variant(df5, m15, label=f"rb ov_mult={mult}/test",
                         ov_mult=mult, start=TEST[0], end=TEST[1])
        rb[f"ov_mult_{mult}"] = metrics(tr)
        s97._OV_MULT = 1.2
    for tpf in (0.4, 0.6):
        tr = run_variant(df5, m15, label=f"rb tp_frac={tpf}/test",
                         tp_frac=tpf, start=TEST[0], end=TEST[1])
        rb[f"tp_frac_{tpf}"] = metrics(tr)
        s97._TP_FRAC = 0.5
    results["robustness_test_pm20"] = rb

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(OUT_JSON.replace(".json", "_trades.json"), "w") as f:
        json.dump(trade_logs, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in results.items() if k != "meta"}, indent=2, default=str))
    print(f"saved -> {OUT_JSON}")


if __name__ == "__main__":
    main()
