"""
s9x_bt_s96_m5_exit_variants.py
------------------------------
Exit-shape experiment for the rewritten S96 M5 EMA9/21 crossover (entries
UNCHANGED, real module signals): does a FIXED SL + TRAILING TP save the edge?

Motivation: the 2026-07-03 re-validation (REPORT-s96-m5-ema-cross-validation.md)
failed with the production chandelier exit (trail dist = 1.5xATR = initial SL).
User proposal: fixed hard SL + a profit-side trailing exit. That shape needs an
arming threshold (a trail active from entry with dist < SL simply IS the stop),
so the grid is (SL mult, trail mult, arm mult) in ATR(14,M5) units:

  fixed SL   : entry -/+ SL*ATR, never moves
  trailing TP: once price has moved arm*ATR in favour (hwm/lwm basis), a
               chandelier trail with distance trail*ATR activates and ratchets;
               exit on pullback to it. Until armed, only fixed SL + TIME apply.
  TIME       : 480-min backstop (unchanged)

Also includes two fixed-RR baselines (fixed SL + static TP) for context, and
the production chandelier as reference. Entries, costs, data, split identical
to s9x_bt_s96_m5_ema_cross.py. Ungated only (the gate made things worse).

Everything here is an OFFLINE experiment — none of these exit shapes exist in
position_monitor yet; building one is conditional on a positive result.
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

DATA = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\xau_m5_3y.csv"
OUT_JSON = r"C:\Projects\ClaudeProjects\ClaudeTradingBot\reports\s96_m5_exit_variants_results.json"

LOT = 0.10
USD_PER_PT = 10.0
SPREAD_PTS = 0.20
COMMISSION = 4.90 * LOT
SL_SLIP = 0.05

WIN_5M = 160
COOLDOWN_NS = 300 * 10**9
EPS_GAP = 0.01
MIN5_NS = 300_000_000_000
MAX_HOLD_MIN = 480

TRAIN = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))
TEST = (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC"))
H4_WINDOW_DAYS = 90   # keep the same warm-up as the base run for comparability


def load_m5() -> pd.DataFrame:
    df = pd.read_csv(DATA, parse_dates=["time"])
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df["time"] = df["time"].dt.tz_localize("UTC")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    return df[["time", "open", "high", "low", "close"]]


def find_candidates(m5: pd.DataFrame, fast: int, slow: int) -> np.ndarray:
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


# ── exit shapes (all conservative same-bar SL-first, SL slippage on stops) ───
def exit_fixed_trail(t5, o5, h5, l5, c5, i0, side, entry, atr,
                     sl_mult, trail_mult, arm_mult, expiry_ns):
    """Fixed SL at entry -/+ sl_mult*ATR; trailing TP (dist trail_mult*ATR)
    arms once favourable excursion reaches arm_mult*ATR, then ratchets off the
    hwm/lwm; TIME exit at expiry. Conservative ordering per bar:
    fixed SL -> trail (pre-update level) -> then update watermark/arming."""
    sl = entry - sl_mult * atr if side == "BUY" else entry + sl_mult * atr
    hwm = entry
    armed = False
    trail = None
    n = len(t5)
    for i in range(i0, n):
        if t5[i] >= expiry_ns:
            return i, float(o5[i]), "TIME"
        if side == "BUY":
            if l5[i] <= sl:
                return i, min(sl, float(o5[i])) - SL_SLIP, "SL"
            if armed and l5[i] <= trail:
                return i, min(trail, float(o5[i])) - SL_SLIP, "TRAIL_TP"
            hwm = max(hwm, float(h5[i]))
            if not armed and hwm >= entry + arm_mult * atr:
                armed = True
                trail = hwm - trail_mult * atr
            elif armed:
                trail = max(trail, hwm - trail_mult * atr)
        else:
            if h5[i] >= sl:
                return i, max(sl, float(o5[i])) + SL_SLIP, "SL"
            if armed and h5[i] >= trail:
                return i, max(trail, float(o5[i])) + SL_SLIP, "TRAIL_TP"
            hwm = min(hwm, float(l5[i]))
            if not armed and hwm <= entry - arm_mult * atr:
                armed = True
                trail = hwm + trail_mult * atr
            elif armed:
                trail = min(trail, hwm + trail_mult * atr)
    return n - 1, float(c5[n - 1]), "EOD"


def exit_fixed_rr(t5, o5, h5, l5, c5, i0, side, entry, atr,
                  sl_mult, tp_mult, expiry_ns):
    """Fixed SL + static TP (baseline for context)."""
    sl = entry - sl_mult * atr if side == "BUY" else entry + sl_mult * atr
    tp = entry + tp_mult * atr if side == "BUY" else entry - tp_mult * atr
    n = len(t5)
    for i in range(i0, n):
        if t5[i] >= expiry_ns:
            return i, float(o5[i]), "TIME"
        if side == "BUY":
            if l5[i] <= sl:
                return i, min(sl, float(o5[i])) - SL_SLIP, "SL"
            if h5[i] >= tp:
                return i, tp, "TP"
        else:
            if h5[i] >= sl:
                return i, max(sl, float(o5[i])) + SL_SLIP, "SL"
            if l5[i] <= tp:
                return i, tp, "TP"
    return n - 1, float(c5[n - 1]), "EOD"


def exit_chandelier(t5, o5, h5, l5, c5, i0, side, stop0, dist, tp, expiry_ns):
    """Production reference (verbatim from the validation harness)."""
    stop = stop0
    n = len(t5)
    for i in range(i0, n):
        if t5[i] >= expiry_ns:
            return i, float(o5[i]), "TIME"
        if side == "BUY":
            if l5[i] <= stop:
                return i, min(stop, float(o5[i])) - SL_SLIP, "TRAIL"
            if h5[i] >= tp:
                return i, tp, "TP"
            stop = max(stop, float(h5[i]) - dist)
        else:
            if h5[i] >= stop:
                return i, max(stop, float(o5[i])) + SL_SLIP, "TRAIL"
            if l5[i] <= tp:
                return i, tp, "TP"
            stop = min(stop, float(l5[i]) + dist)
    return n - 1, float(c5[n - 1]), "EOD"


def run_variant(signals: dict, m5: pd.DataFrame, warmup_ns: int, exit_fn):
    """exit_fn(t5,o5,h5,l5,c5,i0,side,entry,atr,expiry) -> (ie, px, reason).
    Flat-only + 300s cooldown, entry at next M5 open — same as validation."""
    t5 = m5["time"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    o5 = m5["open"].to_numpy(); h5 = m5["high"].to_numpy()
    l5 = m5["low"].to_numpy(); c5 = m5["close"].to_numpy()
    trades = []
    flat_from = -1
    last_entry_ns = -10**18
    for j in sorted(signals):
        sig = signals[j]
        tau = int(t5[j]) + MIN5_NS
        if tau < warmup_ns:
            continue
        if tau < flat_from or tau - last_entry_ns < COOLDOWN_NS:
            continue
        i0 = j + 1
        if i0 >= len(t5):
            continue
        entry_mid = float(o5[i0])
        atr = abs(float(sig.entry_price) - float(sig.stop_loss)) / 1.5  # module K_ATR
        expiry = tau + MAX_HOLD_MIN * 60 * 10**9
        ie, exit_mid, reason = exit_fn(t5, o5, h5, l5, c5, i0, sig.side,
                                       entry_mid, atr, expiry)
        d = 1.0 if sig.side == "BUY" else -1.0
        pnl_pts = d * (exit_mid - entry_mid) - SPREAD_PTS
        pnl_usd = pnl_pts * USD_PER_PT - COMMISSION
        trades.append({"entry_time": str(pd.Timestamp(tau, tz="UTC")),
                       "reason": reason, "pnl_usd": round(pnl_usd, 2)})
        last_entry_ns = tau
        flat_from = int(t5[ie]) + MIN5_NS
    return trades


def metrics(trades, lo, hi):
    tr = [t for t in trades if lo <= pd.Timestamp(t["entry_time"]) < hi]
    n = len(tr)
    if n == 0:
        return {"trades": 0}
    pnl = np.array([t["pnl_usd"] for t in tr])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gw, gl = wins.sum(), -losses.sum()
    eq = np.cumsum(pnl)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return {"trades": n, "net_usd": round(float(pnl.sum()), 2),
            "expectancy_usd": round(float(pnl.mean()), 2),
            "profit_factor": round(float(gw / gl), 3) if gl > 0 else float("inf"),
            "win_rate": round(float(len(wins)) / n, 3),
            "max_dd_usd": round(dd, 2)}


def main():
    m5 = load_m5()
    warmup_ns = int((m5["time"].iloc[0] + timedelta(days=H4_WINDOW_DAYS + 1)).value)

    cand = find_candidates(m5, s96._EMA_FAST, s96._EMA_SLOW)
    signals = confirm_signals(m5, cand)
    print(f"signals={len(signals)}", flush=True)

    def split(tr):
        return {"train": metrics(tr, *TRAIN), "test": metrics(tr, *TEST)}

    results = {"entries": "real s96 module @35d44c8, EMA9/21 cross, unchanged",
               "n_signals": len(signals), "variants": {}}

    # Production chandelier reference (should reproduce the validation run)
    ref = run_variant(signals, m5, warmup_ns,
                      lambda t5, o5, h5, l5, c5, i0, side, entry, atr, exp:
                      exit_chandelier(t5, o5, h5, l5, c5, i0, side,
                                      entry - 1.5 * atr if side == "BUY" else entry + 1.5 * atr,
                                      1.5 * atr,
                                      entry + 30 * atr if side == "BUY" else entry - 30 * atr,
                                      exp))
    results["variants"]["REF chandelier 1.5ATR (production)"] = split(ref)
    print("ref done", flush=True)

    # Fixed SL + trailing TP grid
    for sl in (1.5, 2.0):
        for trail in (0.5, 0.75, 1.0):
            for arm in (0.5, 1.0, 1.5):
                lbl = f"fixedSL={sl} trail={trail} arm={arm}"
                tr = run_variant(signals, m5, warmup_ns,
                                 lambda t5, o5, h5, l5, c5, i0, side, entry, atr, exp,
                                        _sl=sl, _t=trail, _a=arm:
                                 exit_fixed_trail(t5, o5, h5, l5, c5, i0, side,
                                                  entry, atr, _sl, _t, _a, exp))
                results["variants"][lbl] = split(tr)
                print(lbl, "done", flush=True)

    # Fixed-RR baselines
    for sl, tp in ((1.5, 1.5), (1.5, 3.0)):
        lbl = f"fixedSL={sl} staticTP={tp}"
        tr = run_variant(signals, m5, warmup_ns,
                         lambda t5, o5, h5, l5, c5, i0, side, entry, atr, exp,
                                _sl=sl, _tp=tp:
                         exit_fixed_rr(t5, o5, h5, l5, c5, i0, side,
                                       entry, atr, _sl, _tp, exp))
        results["variants"][lbl] = split(tr)
        print(lbl, "done", flush=True)

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=1)

    # Compact table
    print(f"\n{'variant':38s} {'TR net':>9s} {'TR PF':>6s} {'TE net':>9s} {'TE PF':>6s} {'TE n':>5s}")
    for lbl, d in results["variants"].items():
        tr, te = d["train"], d["test"]
        print(f"{lbl:38s} {tr.get('net_usd', 0):>9.0f} {tr.get('profit_factor', 0):>6.3f} "
              f"{te.get('net_usd', 0):>9.0f} {te.get('profit_factor', 0):>6.3f} {te.get('trades', 0):>5d}")


if __name__ == "__main__":
    main()
