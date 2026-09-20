"""Backtest a SYSTEMATIC replica of the manual mobile-scalp style seen on account
5216074f (Prijen B), to test whether the 92.5% win rate is a real edge or a
no-stop artifact of a mean-reverting regime.

Style (reverse-engineered from 67 real trades):
  - XAUUSD only, fixed 0.1 lot, market in/out (no bracket orders)
  - mean-reversion entries: fade a short-term move
  - tiny fixed take-profit (~1 point = $10 at 0.1 lot)
  - human used NO stop loss; exits were manual -> we model TP + time-stop
  - <=3 positions stacked, median hold ~60s

We run two variants on identical signals:
  V1 NO-STOP  (faithful to the human): TP or time-stop only
  V2 GUARDED  (challenge-safe):        TP + a real hard stop

Contract: 1.0 price point of XAUUSD = $10 P&L per 0.1 lot.
Costs: half-spread paid on entry and on time-stop exits (TP/SL are resting prices,
       so we model the spread by filling entries at mid +/- spread/2). Commission
       per round trip added explicitly.
"""
import csv
import sys
import datetime as dt

PT = 10.0  # $ per 1.0 XAU point at 0.1 lot


def load(path):
    bars = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bars.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                         float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return bars


def backtest(bars, *, lookback=3, trigger=1.2, tp=1.0, sl=None, time_stop=60,
             max_pos=3, min_gap=1, spread=0.25, commission=0.50,
             session_filter=None):
    """Returns list of trade dicts. sl=None -> no stop (V1). session_filter: fn(dt)->bool."""
    trades = []
    open_pos = []  # dicts: side, entry, tp_px, sl_px, opened_i, opened_t
    last_entry_i = -10**9
    n = len(bars)
    closes = [b[4] for b in bars]
    for i in range(n):
        t, o, h, l, c = bars[i]

        # ---- manage open positions on THIS bar (pessimistic: SL before TP) ----
        still = []
        for p in open_pos:
            exit_px = None; reason = None
            if p["side"] == "sell":
                if p["sl_px"] is not None and h >= p["sl_px"]:
                    exit_px, reason = p["sl_px"], "sl"
                elif l <= p["tp_px"]:
                    exit_px, reason = p["tp_px"], "tp"
            else:  # buy
                if p["sl_px"] is not None and l <= p["sl_px"]:
                    exit_px, reason = p["sl_px"], "sl"
                elif h >= p["tp_px"]:
                    exit_px, reason = p["tp_px"], "tp"
            # time stop
            if exit_px is None and (i - p["opened_i"]) >= time_stop:
                # exit at close, pay half-spread against us
                exit_px = c - spread / 2 if p["side"] == "sell" else c + spread / 2
                reason = "time"
            if exit_px is None:
                still.append(p); continue
            pnl_pts = (p["entry"] - exit_px) if p["side"] == "sell" else (exit_px - p["entry"])
            trades.append({"t_in": p["opened_t"], "t_out": t, "side": p["side"],
                           "entry": p["entry"], "exit": exit_px,
                           "pnl": pnl_pts * PT - commission, "reason": reason,
                           "bars_held": i - p["opened_i"]})
        open_pos = still

        # ---- entry signal (mean reversion) ----
        if session_filter and not session_filter(t):
            continue
        if i < lookback or len(open_pos) >= max_pos or (i - last_entry_i) < min_gap:
            continue
        move = closes[i] - closes[i - lookback]
        side = None
        if move >= trigger:
            side = "sell"
        elif move <= -trigger:
            side = "buy"
        if side is None:
            continue
        # fill at mid +/- half spread (buy at ask, sell at bid)
        entry = c - spread / 2 if side == "sell" else c + spread / 2
        if side == "sell":
            tp_px = entry - tp
            sl_px = (entry + sl) if sl else None
        else:
            tp_px = entry + tp
            sl_px = (entry - sl) if sl else None
        open_pos.append({"side": side, "entry": entry, "tp_px": tp_px, "sl_px": sl_px,
                         "opened_i": i, "opened_t": t})
        last_entry_i = i
    return trades


def stats(trades, label, start_equity=5000.0):
    if not trades:
        print(f"{label}: no trades"); return None
    n = len(trades); wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    net = sum(t["pnl"] for t in trades)
    gw = sum(t["pnl"] for t in wins); gl = sum(t["pnl"] for t in losses)
    wr = 100 * len(wins) / n
    pf = gw / abs(gl) if gl else float("inf")
    # equity curve + max drawdown
    eq = start_equity; peak = eq; maxdd = 0.0
    for t in sorted(trades, key=lambda x: x["t_out"]):
        eq += t["pnl"]; peak = max(peak, eq); maxdd = min(maxdd, eq - peak)
    worst = min(t["pnl"] for t in trades); best = max(t["pnl"] for t in trades)
    avg_w = gw / len(wins) if wins else 0; avg_l = gl / len(losses) if losses else 0
    exp = net / n
    reasons = {}
    for t in trades:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    print(f"\n=== {label} ===")
    print(f"  trades {n}  WR {wr:.1f}%  PF {pf:.2f}  net ${net:+.2f}  expectancy ${exp:+.3f}/trade")
    print(f"  avg win ${avg_w:+.2f}  avg loss ${avg_l:+.2f}  best ${best:+.2f}  worst ${worst:+.2f}")
    print(f"  max drawdown ${maxdd:+.2f}  final equity ${eq:.2f}  exits {reasons}")
    return {"n": n, "wr": wr, "pf": pf, "net": net, "exp": exp, "maxdd": maxdd,
            "worst": worst, "best": best, "final": eq, "avg_w": avg_w, "avg_l": avg_l}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "reports/xau_m1_2026ytd.csv"
    bars = load(path)
    print(f"Loaded {len(bars)} M1 bars  {bars[0][0]} .. {bars[-1][0]}")
    base = dict(lookback=3, trigger=1.2, tp=1.0, time_stop=60, max_pos=3,
                min_gap=1, spread=0.25, commission=0.50)
    v1 = backtest(bars, sl=None, **base)
    stats(v1, "V1 NO-STOP (human replica)")
    v2 = backtest(bars, sl=2.5, **base)
    stats(v2, "V2 GUARDED (stop 2.5pt)")
