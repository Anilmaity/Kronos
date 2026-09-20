"""
s9x_bt_s96_h1_momentum.py
-------------------------
Frozen-parameter validation backtest of the REAL kronos_s96_h1_momentum module
(imported from KronosStrategies/strategies/backtest_strategies/s96_h1_momentum.py),
ungated vs gated by the Strategy Manager 'trending' policy
(regime_engine math replicated causally: ER(H1,24)>0.35 AND ER(M15,30)>0.35
AND get_htf_bias(H4,H1) != neutral).

Data   : reports/xau_m5_3y.csv (M5 mid OHLC, 2023-01 .. 2026-06-24), resampled.
Costs  : 0.20-pt RT spread + $4.90/lot RT commission at 0.10 lot ($10/pt).
Fills  : conservative same-bar SL-first, SL slippage 0.05.
Split  : TRAIN 2023-01..2024-12, TEST 2025-01..2026-06 (frozen params; test read once).

Live-timing fidelity notes (from reading the real code):
 * s96 uses ONLY w15m (w1m/w5m are ignored by the module) -> passed as None.
 * tsdb_reader returns only COMPLETE candles and s96._resample_h1 always drops
   the last H1 bucket, so the H1 bar closing at t is first actionable at t+15m
   (when the first M15 bar of the next hour closes). Entry fill = M5 open there.
   The same (retained-last) H1 signal stays live at t+30m/t+45m/t+60m, which is
   when a manager gate that flips ON mid-hour can still admit the entry.
 * Exit = position_monitor chandelier: stop ratchets to hi/lo-watermark -/+
   dist (= |signal.entry_price - signal.stop_loss|), initial level =
   signal.stop_loss; far TP (30 ATR) broker backstop; TIME_EXIT at 2880 min.
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

KS_STRATEGIES = r"E:\Projects\Kronos\KronosStrategies\strategies"
sys.path.insert(0, KS_STRATEGIES)

import backtest_strategies.s96_h1_momentum as s96  # noqa: E402
from strategy.ict_engine import get_market_structure  # noqa: E402  (validation only)

DATA = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\xau_m5_3y.csv"
OUT_JSON = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\s96_h1_momentum_bt_results.json"
OUT_MD = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\REPORT-s96-h1-momentum-validation.md"

# Costs / sizing
LOT = 0.10
USD_PER_PT = 10.0          # 0.10 lot XAUUSD
SPREAD_PTS = 0.20          # round-trip, mid data
COMMISSION = 4.90 * LOT    # $ per round trip
SL_SLIP = 0.05             # extra points against us on stop exits

W15_WIN = 400              # M5->M15 window rows passed to get_signal (100 H1 bars)

TRAIN = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))
TEST = (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC"))

# Regime-engine constants (replicated from strategies/regime/regime_engine.py)
ER_H1_BARS, ER_M15_BARS, ER_TRENDING = 24, 30, 0.35
H4_WINDOW_DAYS, H1_WINDOW_DAYS = 90, 30   # FRAME_SPEC '4h': 90, '1h': 30


# ── data ─────────────────────────────────────────────────────────────────────
def load_m5() -> pd.DataFrame:
    df = pd.read_csv(DATA, parse_dates=["time"])
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df["time"] = df["time"].dt.tz_localize("UTC")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    return df[["time", "open", "high", "low", "close"]]


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    o = df.set_index("time")
    r = (o.resample(rule, label="left", closed="left")
           .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
           .dropna().reset_index())
    return r


# ── regime math (replicated causally) ────────────────────────────────────────
def er_series(closes: np.ndarray, n: int) -> np.ndarray:
    """Kaufman ER over the last n moves, as of each bar close (regime_engine
    _efficiency_ratio on the trailing n+1 closes)."""
    c = closes.astype(float)
    d = np.abs(np.diff(c, prepend=np.nan))
    path = pd.Series(d).rolling(n, min_periods=n).sum().to_numpy()
    net = np.abs(c - np.roll(c, n))
    net[:n] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        er = net / path
    er[~np.isfinite(er)] = np.nan
    return er


def structure_per_bar(high: np.ndarray, low: np.ndarray,
                      start_ns: np.ndarray, end_ns: np.ndarray,
                      window_days: int) -> np.ndarray:
    """Vectorised replica of ict_engine.get_market_structure(frame, lookback=3)
    evaluated on the frame of the trailing `window_days` ending at each bar.
    Returns int8: 1 bullish / -1 bearish / 0 ranging."""
    n = len(high)
    hs = pd.Series(high)
    ls = pd.Series(low)
    flag_hi = (high == hs.rolling(7, center=True, min_periods=7).max().to_numpy())
    flag_lo = (low == ls.rolling(7, center=True, min_periods=7).min().to_numpy())
    hi_idx = np.flatnonzero(flag_hi)
    lo_idx = np.flatnonzero(flag_lo)
    win_ns = np.int64(window_days) * 86_400_000_000_000
    s_arr = np.searchsorted(start_ns, end_ns - win_ns, side="left")
    out = np.zeros(n, dtype=np.int8)
    for j in range(n):
        s = s_arr[j]
        if j - s + 1 < 9:            # len < lookback*2+3 -> ranging
            continue
        p = np.searchsorted(hi_idx, j - 3, side="right")
        q = np.searchsorted(lo_idx, j - 3, side="right")
        if p < 2 or q < 2:
            continue
        i1, i2 = hi_idx[p - 1], hi_idx[p - 2]
        k1, k2 = lo_idx[q - 1], lo_idx[q - 2]
        if i2 < s + 3 or k2 < s + 3:  # <2 qualifying swings inside the window
            continue
        hh, hl = high[i1] > high[i2], low[k1] > low[k2]
        lh, ll = high[i1] < high[i2], low[k1] < low[k2]
        if hh and hl:
            out[j] = 1
        elif lh and ll:
            out[j] = -1
    return out


def combine_bias(s4: int, s1: int) -> str:
    if s4 == 1 and s1 >= 0:
        return "long"
    if s4 == -1 and s1 <= 0:
        return "short"
    return "neutral"


# ── signal pass ──────────────────────────────────────────────────────────────
def compute_signals(m15: pd.DataFrame, h1_start_ns: np.ndarray):
    """One causal pass: for each M15 close time tau, identify the retained-last
    H1 bar (the one s96 will signal on) and compute the real get_signal once per
    unique signal bar, at its earliest live evaluation time."""
    m15_end = (m15["time"] + timedelta(minutes=15)).to_numpy().astype("datetime64[ns]").astype(np.int64)
    m15_start_ns = m15["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    HOUR = 3_600_000_000_000
    dropped_bucket = (m15_start_ns // HOUR) * HOUR          # floor1h(window-last-bar start)
    sig_bar_pos = np.searchsorted(h1_start_ns, dropped_bucket, side="left") - 1

    signals = {}          # h1 bar pos -> (Signal|None, first_eval_k)
    sig_at_k = np.full(len(m15), -1, dtype=np.int64)        # which signal bar is live at k
    for k in range(W15_WIN, len(m15)):
        b = sig_bar_pos[k]
        if b < 0:
            continue
        sig_at_k[k] = b
        if b not in signals:
            w15 = m15.iloc[k - W15_WIN + 1: k + 1]
            now = pd.Timestamp(m15_end[k], tz="UTC")
            try:
                sig = s96.get_signal(None, None, w15, now.to_pydatetime())
            except Exception:
                sig = None
            signals[b] = sig
    return m15_end, sig_at_k, signals


# ── exit simulation (position_monitor chandelier replica, conservative) ──────
def simulate_exit(t5: np.ndarray, o5, h5, l5, c5, i0: int, side: str,
                  stop0: float, dist: float, tp: float, expiry_ns: int):
    stop = stop0
    n = len(t5)
    for i in range(i0, n):
        if t5[i] >= expiry_ns:
            return i, float(o5[i]), "TIME"
        if side == "BUY":
            if l5[i] <= stop:                       # conservative: SL first, pre-ratchet stop
                px = min(stop, float(o5[i])) - SL_SLIP
                return i, px, "TRAIL"
            if h5[i] >= tp:
                return i, tp, "TP"
            stop = max(stop, float(h5[i]) - dist)   # ratchet after the check
        else:
            if h5[i] >= stop:
                px = max(stop, float(o5[i])) + SL_SLIP
                return i, px, "TRAIL"
            if l5[i] <= tp:
                return i, tp, "TP"
            stop = min(stop, float(l5[i]) + dist)
    return n - 1, float(c5[n - 1]), "EOD"


# ── run one variant ──────────────────────────────────────────────────────────
def run_variant(m15_end, sig_at_k, signals, gate, m5, warmup_ns):
    t5 = m5["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    o5 = m5["open"].to_numpy(); h5 = m5["high"].to_numpy()
    l5 = m5["low"].to_numpy(); c5 = m5["close"].to_numpy()
    MIN5 = 60_000_000_000
    trades = []
    flat_from = -1            # ns time we are flat again
    last_entry_ns = -10**18
    entered_bars = set()
    for k in range(len(m15_end)):
        tau = m15_end[k]
        if tau < warmup_ns:
            continue
        b = sig_at_k[k]
        if b < 0 or b in entered_bars:
            continue
        if tau < flat_from or tau - last_entry_ns < 3600 * 10**9:
            continue
        if gate is not None and not gate[k]:
            continue
        sig = signals.get(b)
        if sig is None:
            entered_bars.add(b)   # no signal on this bar: never will be
            continue
        i0 = int(np.searchsorted(t5, tau, side="left"))
        if i0 >= len(t5):
            continue
        entry_mid = float(o5[i0])
        dist = abs(float(sig.entry_price) - float(sig.stop_loss))
        expiry = tau + int(sig.max_hold_min) * MIN5
        ie, exit_mid, reason = simulate_exit(t5, o5, h5, l5, c5, i0, sig.side,
                                             float(sig.stop_loss), dist,
                                             float(sig.take_profit), expiry)
        d = 1.0 if sig.side == "BUY" else -1.0
        pnl_pts = d * (exit_mid - entry_mid) - SPREAD_PTS
        pnl_usd = pnl_pts * USD_PER_PT - COMMISSION
        trades.append({
            "entry_time": str(pd.Timestamp(tau, tz="UTC")),
            "exit_time": str(pd.Timestamp(int(t5[ie]) + 5 * MIN5, tz="UTC")),
            "side": sig.side, "entry": round(entry_mid, 2), "exit": round(exit_mid, 2),
            "reason": reason, "pnl_usd": round(pnl_usd, 2),
            "hold_hours": round((int(t5[ie]) + 5 * MIN5 - tau) / 3.6e12, 1),
        })
        entered_bars.add(b)
        last_entry_ns = tau
        flat_from = int(t5[ie]) + 5 * MIN5
    return trades


# ── metrics ──────────────────────────────────────────────────────────────────
def metrics(trades, lo: pd.Timestamp, hi: pd.Timestamp):
    tr = [t for t in trades if lo <= pd.Timestamp(t["entry_time"]) < hi]
    n = len(tr)
    if n == 0:
        return {"trades": 0}
    pnl = np.array([t["pnl_usd"] for t in tr])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gw, gl = wins.sum(), -losses.sum()
    eq = np.cumsum(pnl)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    months = pd.Series(pnl, index=pd.to_datetime([t["entry_time"] for t in tr], utc=True))
    mo = months.resample("ME").sum()
    mo = mo[mo != 0]
    net = float(pnl.sum())
    top_share = float(mo.max() / net) if net > 0 and len(mo) else None
    return {
        "trades": n,
        "net_usd": round(net, 2),
        "expectancy_usd": round(net / n, 2),
        "profit_factor": round(float(gw / gl), 3) if gl > 0 else float("inf"),
        "win_rate": round(float(len(wins)) / n, 3),
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "max_dd_usd": round(dd, 2),
        "top_month_share_of_net": round(top_share, 3) if top_share is not None else None,
        "monthly_net": {str(k.date())[:7]: round(float(v), 2) for k, v in mo.items()},
    }


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    m5 = load_m5()
    m15 = resample(m5, "15min")
    h1 = resample(m5, "1h")
    h4 = resample(m5, "4h")

    h1_start = h1["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    h1_end = h1_start + 3_600_000_000_000
    h4_start = h4["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    h4_end = h4_start + 4 * 3_600_000_000_000

    # Regime pieces (all as-of bar close, causal)
    er_h1 = er_series(h1["close"].to_numpy(), ER_H1_BARS)
    er_m15 = er_series(m15["close"].to_numpy(), ER_M15_BARS)
    s1h = structure_per_bar(h1["high"].to_numpy(), h1["low"].to_numpy(),
                            h1_start, h1_end, H1_WINDOW_DAYS)
    s4h = structure_per_bar(h4["high"].to_numpy(), h4["low"].to_numpy(),
                            h4_start, h4_end, H4_WINDOW_DAYS)

    # Validate the vectorised structure replica against the real ict_engine
    rng = np.random.default_rng(7)
    match = 0; tot = 0
    lab = {1: "bullish", -1: "bearish", 0: "ranging"}
    for j in rng.choice(np.arange(600, len(h4)), size=150, replace=False):
        end_t = pd.Timestamp(int(h4_end[j]), tz="UTC")
        win = h4[(h4["time"] >= end_t - timedelta(days=H4_WINDOW_DAYS)) & (h4["time"] < end_t)]
        real = get_market_structure(win.reset_index(drop=True))
        tot += 1; match += int(real == lab[int(s4h[j])])
    struct_match = match / tot

    m15_end, sig_at_k, signals = compute_signals(m15, h1_start)

    # gate[k]: regime at tau = m15_end[k] using last COMPLETE bars only
    j1 = np.searchsorted(h1_end, m15_end, side="right") - 1
    j4 = np.searchsorted(h4_end, m15_end, side="right") - 1
    ok = (j1 >= 0) & (j4 >= 0)
    gate = np.zeros(len(m15_end), dtype=bool)
    e1 = np.where(ok, er_h1[np.clip(j1, 0, None)], np.nan)
    e15 = er_m15
    bias_ok = np.zeros(len(m15_end), dtype=bool)
    for k in np.flatnonzero(ok):
        bias_ok[k] = combine_bias(int(s4h[j4[k]]), int(s1h[j1[k]])) != "neutral"
    gate = ok & (e1 > ER_TRENDING) & (e15 > ER_TRENDING) & bias_ok

    warmup_ns = int((m5["time"].iloc[0] + timedelta(days=H4_WINDOW_DAYS + 1))
                    .value)

    ungated = run_variant(m15_end, sig_at_k, signals, None, m5, warmup_ns)
    gated = run_variant(m15_end, sig_at_k, signals, gate, m5, warmup_ns)

    def split(trades):
        return {"train": metrics(trades, *TRAIN), "test": metrics(trades, *TEST)}

    results = {
        "strategy": "kronos_s96_h1_momentum (real module, frozen params)",
        "data": "xau_m5_3y.csv M5 mid 2023-01-02..2026-06-24 (M1 not used by s96; w1m/w5m=None)",
        "costs": {"spread_pts_rt": SPREAD_PTS, "commission_usd_rt": COMMISSION,
                  "sl_slippage_pts": SL_SLIP, "lot": LOT, "usd_per_pt": USD_PER_PT},
        "timing": "signal on H1 close t actionable at t+15m (complete-candle fetch + drop-last-H1); entry at M5 open there; gate re-checked each M15 while the signal bar is live",
        "struct_replica_match_vs_ict_engine": round(struct_match, 3),
        "gate_pct_of_m15_bars": round(float(gate[m15_end >= warmup_ns].mean()), 4),
        "ungated": split(ungated),
        "gated": split(gated),
        "ungated_trades": ungated,
        "gated_trades": gated,
    }

    # ── robustness (reported separately, ungated, ±20% on K_ATR and DONCH) ──
    rob = {}
    base = dict(K_ATR=s96._K_ATR, DONCH=s96._DONCH, MIN_H1=s96._MIN_H1)
    for label, patch in [("K_ATR=1.2", {"_K_ATR": 1.2}), ("K_ATR=1.8", {"_K_ATR": 1.8}),
                         ("DONCH=19", {"_DONCH": 19}), ("DONCH=29", {"_DONCH": 29})]:
        s96._K_ATR = patch.get("_K_ATR", base["K_ATR"])
        s96._DONCH = patch.get("_DONCH", base["DONCH"])
        s96._MIN_H1 = s96._EMA_SLOW + s96._DONCH + 2
        _, sk, sg = compute_signals(m15, h1_start)
        tr = run_variant(m15_end, sk, sg, None, m5, warmup_ns)
        rob[label] = split(tr)
        rob[label] = {p: {kk: vv for kk, vv in d.items() if kk != "monthly_net"}
                      for p, d in rob[label].items()}
    s96._K_ATR, s96._DONCH, s96._MIN_H1 = base["K_ATR"], base["DONCH"], base["MIN_H1"]
    results["robustness_ungated"] = rob

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1)
    print(json.dumps({k: v for k, v in results.items()
                      if k not in ("ungated_trades", "gated_trades")}, indent=1))


if __name__ == "__main__":
    main()
