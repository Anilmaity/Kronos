"""
s9x_bt_s96_m5_ema_cross.py
--------------------------
Frozen-parameter re-validation backtest of the REWRITTEN kronos s96 module
(pure M5 EMA9/21 crossover, imported from
KronosStrategies/strategies/backtest_strategies/s96_h1_momentum.py @ 35d44c8),
ungated vs gated by the Strategy Manager 'trending' policy (regime_engine math
replicated causally, same replication as the 2026-07-02 H1-Donchian run:
ER(H1,24)>0.35 AND ER(M15,30)>0.35 AND get_htf_bias(H4,H1) != neutral).

Data   : reports/xau_m5_3y.csv (M5 mid OHLC, 2023-01 .. 2026-06-24). Native TF.
Costs  : 0.20-pt RT spread + $4.90/lot RT commission at 0.10 lot ($10/pt),
         SL slippage 0.05 — identical to the prior S96 validation.
Split  : TRAIN 2023-01..2024-12, TEST 2025-01..2026-06 (frozen params; test read once).

Live-timing fidelity notes (from reading the rewritten code + runner):
 * s96 now uses ONLY w5m. research_runner supplies w5m = complete M5 candles
   (forming bar dropped) .tail(RESEARCH_WIN_5M=160) — so the module is called
   here on exactly the trailing 160 CLOSED M5 bars ending at each signal bar.
 * A cross EVENT on the M5 bar closing at t is first actionable seconds after
   t (5s poll). Entry fill = open of the next M5 bar (~= close of the signal
   bar). The event exists only while that bar is the last closed bar, so a
   signal skipped because a position is open is gone for good.
 * cooldown_s=300 between placements; max_concurrent_positions=1 (flat-only).
 * Exit = position_monitor chandelier: stop ratchets to hi/lo-watermark -/+
   dist (= |signal.entry_price - signal.stop_loss| = 1.5xATR(14,M5)), initial
   level = signal.stop_loss; far TP (30 ATR) broker backstop; TIME_EXIT 480m.

Signal pass: candidate cross bars are pre-located with a vectorised full-series
EMA9/21 gap sign-flip detector (with a +/-0.01-pt near-zero tolerance band to
absorb windowed-vs-full EMA drift), then EVERY candidate is confirmed by
calling the REAL s96.get_signal on the exact 160-bar live window — the module
is ground truth. A 400-bar random non-candidate sample verifies the detector
misses nothing (expected: all None).
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
OUT_JSON = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\s96_m5_ema_cross_bt_results.json"

# Costs / sizing — identical to the 2026-07-02 S96 H1-Donchian validation.
LOT = 0.10
USD_PER_PT = 10.0          # 0.10 lot XAUUSD
SPREAD_PTS = 0.20          # round-trip, mid data
COMMISSION = 4.90 * LOT    # $ per round trip
SL_SLIP = 0.05             # extra points against us on stop exits

WIN_5M = 160               # live RESEARCH_WIN_5M (compose) — rows per get_signal call
COOLDOWN_NS = 300 * 10**9  # cfg.cooldown_s
EPS_GAP = 0.01             # near-zero EMA-gap tolerance band for candidates (pts)

TRAIN = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))
TEST = (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC"))

# Regime-engine constants (replicated from strategies/regime/regime_engine.py)
ER_H1_BARS, ER_M15_BARS, ER_TRENDING = 24, 30, 0.35
H4_WINDOW_DAYS, H1_WINDOW_DAYS = 90, 30

MIN5_NS = 300_000_000_000


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


# ── regime math (replicated causally — verbatim from the prior harness) ──────
def er_series(closes: np.ndarray, n: int) -> np.ndarray:
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
        if j - s + 1 < 9:
            continue
        p = np.searchsorted(hi_idx, j - 3, side="right")
        q = np.searchsorted(lo_idx, j - 3, side="right")
        if p < 2 or q < 2:
            continue
        i1, i2 = hi_idx[p - 1], hi_idx[p - 2]
        k1, k2 = lo_idx[q - 1], lo_idx[q - 2]
        if i2 < s + 3 or k2 < s + 3:
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
def find_candidates(m5: pd.DataFrame, fast: int, slow: int) -> np.ndarray:
    """Vectorised full-series EMA cross candidates: gap sign flip between
    consecutive bars, widened by an EPS_GAP tolerance band so that windowed
    (160-bar) EMA drift cannot hide a real module signal."""
    c = m5["close"].astype(float)
    gap = (c.ewm(span=fast, adjust=False).mean()
           - c.ewm(span=slow, adjust=False).mean()).to_numpy()
    g_prev = np.roll(gap, 1)
    g_prev[0] = np.nan
    up = (g_prev <= 0) & (gap > 0)
    dn = (g_prev >= 0) & (gap < 0)
    near = (np.abs(gap) < EPS_GAP) | (np.abs(g_prev) < EPS_GAP)
    cand = np.flatnonzero(up | dn | near)
    return cand[cand >= WIN_5M - 1]


def confirm_signals(m5: pd.DataFrame, cand: np.ndarray) -> dict:
    """Call the REAL s96.get_signal on the exact live window for every
    candidate bar. Returns {bar_index: Signal} for confirmed events."""
    t_end = (m5["time"] + timedelta(minutes=5)).dt.to_pydatetime()
    out = {}
    for j in cand:
        w5m = m5.iloc[j - WIN_5M + 1: j + 1]
        try:
            sig = s96.get_signal(None, w5m, None, t_end[j])
        except Exception:
            sig = None
        if sig is not None:
            out[int(j)] = sig
    return out


def validate_detector(m5: pd.DataFrame, cand: np.ndarray, n_sample: int = 400) -> int:
    """Real-module calls on random NON-candidate bars: any Signal returned is
    a detector miss. Returns the miss count (expected 0)."""
    rng = np.random.default_rng(7)
    non = np.setdiff1d(np.arange(WIN_5M - 1, len(m5)), cand)
    sample = rng.choice(non, size=min(n_sample, len(non)), replace=False)
    t_end = (m5["time"] + timedelta(minutes=5)).dt.to_pydatetime()
    miss = 0
    for j in sample:
        w5m = m5.iloc[j - WIN_5M + 1: j + 1]
        if s96.get_signal(None, w5m, None, t_end[j]) is not None:
            miss += 1
    return miss


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
def run_variant(signals: dict, gate_at, m5: pd.DataFrame, warmup_ns: int):
    """signals: {bar j: Signal}. Actionable at bar-j end; entry at open of
    bar j+1; flat-only (one position); 300s cooldown; event lost if not flat."""
    t5 = m5["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    o5 = m5["open"].to_numpy(); h5 = m5["high"].to_numpy()
    l5 = m5["low"].to_numpy(); c5 = m5["close"].to_numpy()
    trades = []
    flat_from = -1
    last_entry_ns = -10**18
    for j in sorted(signals):
        sig = signals[j]
        tau = int(t5[j]) + MIN5_NS                  # signal bar close = actionable
        if tau < warmup_ns:
            continue
        if tau < flat_from or tau - last_entry_ns < COOLDOWN_NS:
            continue
        if gate_at is not None and not gate_at(tau):
            continue
        i0 = j + 1
        if i0 >= len(t5):
            continue
        entry_mid = float(o5[i0])
        dist = abs(float(sig.entry_price) - float(sig.stop_loss))
        expiry = tau + int(sig.max_hold_min) * 60 * 10**9
        ie, exit_mid, reason = simulate_exit(t5, o5, h5, l5, c5, i0, sig.side,
                                             float(sig.stop_loss), dist,
                                             float(sig.take_profit), expiry)
        d = 1.0 if sig.side == "BUY" else -1.0
        pnl_pts = d * (exit_mid - entry_mid) - SPREAD_PTS
        pnl_usd = pnl_pts * USD_PER_PT - COMMISSION
        trades.append({
            "entry_time": str(pd.Timestamp(tau, tz="UTC")),
            "exit_time": str(pd.Timestamp(int(t5[ie]) + MIN5_NS, tz="UTC")),
            "side": sig.side, "entry": round(entry_mid, 2), "exit": round(exit_mid, 2),
            "reason": reason, "pnl_usd": round(pnl_usd, 2),
            "hold_hours": round((int(t5[ie]) + MIN5_NS - tau) / 3.6e12, 1),
        })
        last_entry_ns = tau
        flat_from = int(t5[ie]) + MIN5_NS
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

    m15_start = m15["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    m15_end = m15_start + 15 * 60 * 10**9
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

    def gate_at(tau: int) -> bool:
        j15 = int(np.searchsorted(m15_end, tau, side="right")) - 1
        j1 = int(np.searchsorted(h1_end, tau, side="right")) - 1
        j4 = int(np.searchsorted(h4_end, tau, side="right")) - 1
        if j15 < 0 or j1 < 0 or j4 < 0:
            return False
        e1, e15 = er_h1[j1], er_m15[j15]
        if not (np.isfinite(e1) and np.isfinite(e15)):
            return False
        return (e1 > ER_TRENDING and e15 > ER_TRENDING
                and combine_bias(int(s4h[j4]), int(s1h[j1])) != "neutral")

    warmup_ns = int((m5["time"].iloc[0] + timedelta(days=H4_WINDOW_DAYS + 1)).value)

    # Base signal pass: candidates -> real-module confirmation + detector audit
    cand = find_candidates(m5, s96._EMA_FAST, s96._EMA_SLOW)
    signals = confirm_signals(m5, cand)
    misses = validate_detector(m5, cand)
    print(f"candidates={len(cand)} confirmed={len(signals)} detector_misses={misses}",
          flush=True)

    ungated = run_variant(signals, None, m5, warmup_ns)
    gated = run_variant(signals, gate_at, m5, warmup_ns)

    def split(trades):
        return {"train": metrics(trades, *TRAIN), "test": metrics(trades, *TEST)}

    # Gate duty cycle over post-warmup M15 closes (comparable to prior report)
    post = m15_end[m15_end >= warmup_ns]
    gate_pct = float(np.mean([gate_at(int(t)) for t in post[::4]]))  # hourly sample

    results = {
        "strategy": "kronos_s96 M5 EMA9/21 crossover (real rewritten module @35d44c8, frozen params)",
        "data": "xau_m5_3y.csv M5 mid 2023-01-02..2026-06-24 (native TF; w1m/w15m=None)",
        "costs": {"spread_pts_rt": SPREAD_PTS, "commission_usd_rt": COMMISSION,
                  "sl_slippage_pts": SL_SLIP, "lot": LOT, "usd_per_pt": USD_PER_PT},
        "timing": "cross event on M5 close t actionable seconds later (5s poll); entry at next M5 open; event lost if not flat; cooldown 300s",
        "signal_pass": {"candidates": int(len(cand)), "confirmed": int(len(signals)),
                        "detector_miss_sample_400": int(misses)},
        "struct_replica_match_vs_ict_engine": round(struct_match, 3),
        "gate_pct_of_bars_hourly_sample": round(gate_pct, 4),
        "ungated": split(ungated),
        "gated": split(gated),
        "ungated_trades": ungated,
        "gated_trades": gated,
    }

    # ── robustness (reported separately, ungated; ±20% on K_ATR and EMA pair) ─
    rob = {}
    base = dict(K_ATR=s96._K_ATR, F=s96._EMA_FAST, S=s96._EMA_SLOW)
    for label, patch in [("K_ATR=1.2", {"_K_ATR": 1.2}),
                         ("K_ATR=1.8", {"_K_ATR": 1.8}),
                         ("EMA=7/17", {"_EMA_FAST": 7, "_EMA_SLOW": 17}),
                         ("EMA=11/25", {"_EMA_FAST": 11, "_EMA_SLOW": 25})]:
        s96._K_ATR = patch.get("_K_ATR", base["K_ATR"])
        s96._EMA_FAST = patch.get("_EMA_FAST", base["F"])
        s96._EMA_SLOW = patch.get("_EMA_SLOW", base["S"])
        ck = find_candidates(m5, s96._EMA_FAST, s96._EMA_SLOW)
        sg = confirm_signals(m5, ck)
        tr = run_variant(sg, None, m5, warmup_ns)
        rob[label] = {p: {kk: vv for kk, vv in d.items() if kk != "monthly_net"}
                      for p, d in split(tr).items()}
        print(f"robustness {label}: done ({len(sg)} signals)", flush=True)
    s96._K_ATR, s96._EMA_FAST, s96._EMA_SLOW = base["K_ATR"], base["F"], base["S"]
    results["robustness_ungated"] = rob

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1)
    print(json.dumps({k: v for k, v in results.items()
                      if k not in ("ungated_trades", "gated_trades")}, indent=1))


if __name__ == "__main__":
    main()
