"""Walk-forward backtest harness for the Kronos K-line foundation model on XAUUSD.

The Kronos predictor (a heavy CPU transformer) is INJECTED as `predict_fn`, so the
accounting / signal / FundingPips logic here can be built and unit-tested offline
with a cheap stub. The real model plugs in later via `make_kronos_predict_fn(...)`
WITHOUT touching the harness.

Account economics are calibrated to the user's real FundingPips-SIM1 account
(same constants as bt_account_sim.py):
  1.0 XAU point = $100 per 1.0 lot ($10 per 0.10 lot)
  spread 0.25 pt, commission $4.87 per 1.0 lot round-trip
  gold swap per lot per night: long -93.17, short +21.68
  min lot 0.01, step 0.01
FundingPips rules: start $5,000, target +$500 (=$5,500), overall floor $4,500,
max daily loss -$250.

Design (walk-forward, stride-stepped to bound CPU inferences):
  At each step i (i>=lookback, stepping by `stride`): hand predict_fn the last
  `lookback` OHLC bars + the real future timestamps, get a predicted future OHLC
  frame, derive a directional signal from predicted-close-at-horizon vs last close
  (long/short only if the move exceeds `signal_atr`*ATR, else flat), then simulate
  one trade managed by an ATR stop/target over the next `pred_len` bars
  (pessimistic: stop checked before target intrabar), sized so a stop-out risks
  max(risk_floor, risk_pct*equity).

Core logic uses plain lists + stdlib csv; pandas/numpy are only touched at the
predict_fn boundary (the df in / df out contract that mirrors Kronos).
"""
from __future__ import annotations
import csv, datetime as dt

# ---- account constants (mirror bt_account_sim.py) -------------------------------
USD_PT_PER_LOT = 100.0      # $ per 1.0 point per 1.0 lot
COMM_PER_LOT_RT = 4.87      # round-trip commission per 1.0 lot
SWAP_LONG = -93.17          # per lot per night
SWAP_SHORT = 21.68
SPREAD = 0.25               # points


# ---- indicators (plain lists; same math as bot/challenge_xau.py) ----------------
def atr(h, l, c, n=14):
    trs = [h[0] - l[0]]
    for i in range(1, len(c)):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    out = [trs[0]] * len(c)
    for i in range(1, len(c)):
        out[i] = (out[i - 1] * (n - 1) + trs[i]) / n if i >= n else sum(trs[:i + 1]) / (i + 1)
    return out


# ---- position sizing: reuse bot/challenge_xau.position_size if importable -------
try:                                              # pragma: no cover - import path
    from bot.challenge_xau import position_size as _position_size
except Exception:                                 # replicate the exact formula
    _USD_PER_POINT_PER_0_1_LOT = 10.0

    def _position_size(equity, atr_now, *, risk_pct=0.008, risk_floor=50.0,
                       k_atr=1.0, min_lot=0.01, max_lot=0.50, lot_step=0.01):
        """Lots so a -1R (k_atr*ATR) move risks ~max(risk_floor, risk_pct*equity)."""
        risk_dollars = max(risk_floor, risk_pct * equity)
        risk_points = k_atr * atr_now
        if risk_points <= 0:
            return 0.0, 0.0
        raw_lot = risk_dollars / (risk_points * (_USD_PER_POINT_PER_0_1_LOT / 0.1))
        lot = max(min_lot, min(max_lot, round(raw_lot / lot_step) * lot_step))
        actual_risk = risk_points * (_USD_PER_POINT_PER_0_1_LOT / 0.1) * lot
        return round(lot, 2), round(actual_risk, 2)


# ---- data loading (stdlib only) -------------------------------------------------
def load_bars(csv_path):
    """Return list of (timestamp, o, h, l, c). Columns: time,o,h,l,c,volume (UTC)."""
    bars = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bars.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                         float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return bars


def _max_gap_hours(times, lo, hi):
    """Largest gap (hours) between consecutive bars over the inclusive index span."""
    g = 0.0
    for k in range(lo + 1, hi + 1):
        g = max(g, (times[k] - times[k - 1]).total_seconds() / 3600.0)
    return g


# ---- Kronos adapter: turns predictor.predict into the injected predict_fn --------
def make_kronos_predict_fn(predictor, *, T=1.0, top_p=0.9, sample_count=1):
    """Wrap a live KronosPredictor so it satisfies predict_fn(window_df,x_ts,y_ts,k)."""
    def _predict(window_df, x_ts, y_ts, pred_len):
        return predictor.predict(df=window_df[["open", "high", "low", "close"]],
                                 x_timestamp=x_ts, y_timestamp=y_ts, pred_len=pred_len,
                                 T=T, top_p=top_p, sample_count=sample_count)
    return _predict


# ---- the harness ----------------------------------------------------------------
def walk_forward(bars, predict_fn, *, lookback=256, pred_len=6, stride=6,
                 tp_atr=2.0, sl_atr=1.0, signal_atr=0.25,
                 risk_pct=0.008, risk_floor=50.0,
                 start_equity=5000.0, target=5500.0, floor=4500.0,
                 daily_limit=-250.0, spread=SPREAD, include_swap=True,
                 max_gap_hours=72.0, stop_at_target=False):
    """Walk-forward backtest. `predict_fn(window_df, x_ts, y_ts, pred_len)` -> df with
    open/high/low/close of the predicted future bars. Returns a result dict."""
    import pandas as pd                    # only needed at the predict boundary

    t = [b[0] for b in bars]; o = [b[1] for b in bars]
    h = [b[2] for b in bars]; l = [b[3] for b in bars]; c = [b[4] for b in bars]
    n = len(c)
    a = atr(h, l, c, 14)

    equity = start_equity
    eq_curve = [(t[0], equity)]
    trades = []
    day_start_eq = {}
    breach = None
    hit_target_at = None
    n_signals = n_flat = n_skipped_gap = 0

    i = lookback
    while i <= n - 1 - pred_len:
        # need `lookback` history bars behind i and `pred_len` future bars ahead
        w_lo = i - lookback + 1
        if w_lo < 0:
            i += stride; continue
        # gap robustness: skip windows/horizons spanning data holes
        if max_gap_hours is not None and _max_gap_hours(t, w_lo, i + pred_len) > max_gap_hours:
            n_skipped_gap += 1; i += stride; continue

        A = a[i]
        if A <= 0:
            i += stride; continue

        # --- predict (df in / df out, exactly the Kronos contract) ---
        window_df = pd.DataFrame({"open": o[w_lo:i + 1], "high": h[w_lo:i + 1],
                                  "low": l[w_lo:i + 1], "close": c[w_lo:i + 1]})
        x_ts = pd.Series(t[w_lo:i + 1])
        y_ts = pd.Series(t[i + 1:i + 1 + pred_len])      # real future bar times
        pred_df = predict_fn(window_df, x_ts, y_ts, pred_len)
        pred_close_h = float(pred_df["close"].iloc[-1])

        # --- directional signal ---
        delta = pred_close_h - c[i]
        if delta > signal_atr * A:
            side = "long"
        elif delta < -signal_atr * A:
            side = "short"
        else:
            n_flat += 1; i += stride; continue
        n_signals += 1

        dk = t[i].date()
        day_start_eq.setdefault(dk, equity)

        # --- size from risk (stop distance = sl_atr*ATR) ---
        lot, _ = _position_size(equity, A, risk_pct=risk_pct, risk_floor=risk_floor,
                                k_atr=sl_atr)
        if lot <= 0:
            i += stride; continue

        # --- enter next bar open +/- half spread ---
        entry = o[i + 1] + (spread / 2 if side == "long" else -spread / 2)
        stop = entry - sl_atr * A if side == "long" else entry + sl_atr * A
        tgt = entry + tp_atr * A if side == "long" else entry - tp_atr * A

        # --- manage over next pred_len bars (pessimistic: stop before target) ---
        exit_idx = i + pred_len; exit_px = c[exit_idx]; reason = "horizon"
        for j in range(i + 1, i + pred_len + 1):
            if side == "long":
                if l[j] <= stop:
                    exit_idx, exit_px, reason = j, stop, "stop"; break
                if h[j] >= tgt:
                    exit_idx, exit_px, reason = j, tgt, "target"; break
            else:
                if h[j] >= stop:
                    exit_idx, exit_px, reason = j, stop, "stop"; break
                if l[j] <= tgt:
                    exit_idx, exit_px, reason = j, tgt, "target"; break

        pts = (exit_px - entry) if side == "long" else (entry - exit_px)
        gross = pts * USD_PT_PER_LOT * lot
        comm = COMM_PER_LOT_RT * lot
        nights = max(0, (t[exit_idx].date() - t[i + 1].date()).days)
        swap = ((SWAP_LONG if side == "long" else SWAP_SHORT) * lot * nights) if include_swap else 0.0
        pnl = gross - comm + swap
        equity += pnl
        eq_curve.append((t[exit_idx], equity))
        trades.append({"t_in": t[i + 1], "t_out": t[exit_idx], "side": side, "lot": lot,
                       "pts": pts, "R": pts / (sl_atr * A), "pnl": pnl, "swap": swap,
                       "comm": comm, "equity": equity, "nights": nights, "reason": reason})

        # --- FundingPips rule checks ---
        if equity <= floor and breach is None:
            breach = ("overall", t[exit_idx].date(), equity)
        if equity - day_start_eq[dk] <= daily_limit and breach is None:
            breach = ("daily", dk, equity)
        if equity >= target and hit_target_at is None:
            hit_target_at = (t[exit_idx], len(trades))
            if stop_at_target:
                break

        i += stride

    return {"equity": equity, "curve": eq_curve, "trades": trades, "breach": breach,
            "hit_target": hit_target_at, "start": start_equity,
            "n_signals": n_signals, "n_flat": n_flat, "n_skipped_gap": n_skipped_gap}


# ---- reporting (mirrors bt_account_sim.report) ----------------------------------
def report(res, label="Kronos walk-forward"):
    tr = res["trades"]
    print(f"\n=== {label} ===")
    print(f"  signals {res['n_signals']}  flat {res['n_flat']}  gap-skipped {res['n_skipped_gap']}")
    if not tr:
        print("  no trades"); return
    start = res["start"]; end = res["equity"]
    wins = [x for x in tr if x["pnl"] > 0]
    peak = start; mdd = 0.0; mdd_pct = 0.0
    for x in tr:
        eqs = x["equity"]; peak = max(peak, eqs)
        mdd = min(mdd, eqs - peak); mdd_pct = min(mdd_pct, (eqs - peak) / peak * 100)
    net = end - start
    gw = sum(x["pnl"] for x in wins); gl = sum(x["pnl"] for x in tr if x["pnl"] <= 0)
    pf = gw / abs(gl) if gl else float("inf")
    swap_tot = sum(x["swap"] for x in tr); comm_tot = sum(x["comm"] for x in tr)
    print(f"  period {tr[0]['t_in'].date()} .. {tr[-1]['t_out'].date()}   trades {len(tr)}")
    print(f"  start ${start:,.0f} -> end ${end:,.2f}   net ${net:+,.2f} ({net/start*100:+.1f}%)")
    print(f"  WR {100*len(wins)/len(tr):.0f}%  PF {pf:.2f}  expectancy ${net/len(tr):+,.2f}/trade")
    print(f"  max DD ${mdd:,.0f} ({mdd_pct:.1f}%)")
    print(f"  costs paid: commission ${comm_tot:,.0f}  swap ${swap_tot:,.0f}")
    print(f"  avg lot {sum(x['lot'] for x in tr)/len(tr):.3f}  "
          f"best ${max(x['pnl'] for x in tr):+,.0f}  worst ${min(x['pnl'] for x in tr):+,.0f}")
    exits = {}
    for x in tr:
        exits[x["reason"]] = exits.get(x["reason"], 0) + 1
    print("  exits: " + "  ".join(f"{k}:{v}" for k, v in sorted(exits.items())))
    if res["hit_target"]:
        tt, ntr = res["hit_target"]
        print(f"  FIRST HIT +$500 target on {tt.date()} (after {ntr} trades)")
    else:
        print("  never reached +$500 in one continuous run")
    if res["breach"]:
        kind, when, eq = res["breach"]
        print(f"  *** would BREACH {kind} drawdown limit on {when} (equity ${eq:,.0f}) ***")
    else:
        print("  no FundingPips drawdown-limit breach over the whole run")
    yrs = {}
    for x in tr:
        yrs.setdefault(x["t_out"].year, 0.0); yrs[x["t_out"].year] += x["pnl"]
    print("  by year: " + "  ".join(f"{y}:${v:+,.0f}" for y, v in sorted(yrs.items())))


# ---- stub predictor: naive random-walk forecast (proves the harness end-to-end) -
def make_stub_predict_fn(seed=7):
    """Last-value + recent-momentum random walk. Cheap stand-in for Kronos so the
    accounting can be unit-tested without torch/model inference."""
    import numpy as np, pandas as pd
    rng = np.random.default_rng(seed)

    def stub(window_df, x_ts, y_ts, pred_len):
        closes = window_df["close"].to_numpy(dtype=float)
        last = closes[-1]
        rets = np.diff(closes[-20:]) if closes.size > 1 else np.array([0.0])
        sigma = float(np.std(rets)) or 1.0
        drift = float(np.mean(rets[-5:])) if rets.size else 0.0
        px = last; closes_f = []
        for _ in range(pred_len):
            px = px + drift + rng.normal(0.0, sigma)
            closes_f.append(px)
        closes_f = np.asarray(closes_f)
        opens = np.concatenate([[last], closes_f[:-1]])
        wick = np.abs(rng.normal(0.0, sigma * 0.3, pred_len))
        highs = np.maximum(opens, closes_f) + wick
        lows = np.minimum(opens, closes_f) - wick
        return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes_f})
    return stub


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(here, "reports", "xau_h4_3y.csv")
    bars = load_bars(csv_path)
    print(f"H4 bars {bars[0][0].date()}..{bars[-1][0].date()} ({len(bars)})  "
          f"FundingPips-SIM1, start $5,000  [STUB predictor — no model inference]")
    stub = make_stub_predict_fn(seed=7)
    res = walk_forward(bars, stub, lookback=256, pred_len=6, stride=6,
                       tp_atr=2.0, sl_atr=1.0, signal_atr=0.25, risk_floor=50.0)
    report(res, "STUB random-walk forecast on H4 (real costs+swap, equity-sized)")
