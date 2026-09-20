"""Deep search: is there a high-WIN-RATE scalp that ALSO makes reproducible profit?

Faithful to the real trader this time: SHORT holds (minutes, not an hour) + a tight
protective stop (models his fast manual bail) + a chop/vol regime gate. Grid-search
on a TRAIN window, then validate survivors OUT-OF-SAMPLE (backtest-expert rule:
seek plateaus, not peaks; OOS-confirm before believing).

Target: WR >= 88% (like his 92.5%) AND positive expectancy AND >=150 trades,
surviving on unseen data after realistic costs.
"""
import csv, sys, datetime as dt, itertools

PT = 10.0  # $ per 1.0 point at 0.1 lot


def load(path):
    b = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                      float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return b


def backtest(bars, closes, eff_arr, vpath_arr, *, lookback, trigger, tp, sl,
             hold_min, max_pos, min_gap, spread, commission, eff_max, vol_min,
             daily_cap):
    n = len(bars); trades = []; open_pos = []; last_i = -10**9
    day_pnl = {}
    for i in range(n):
        t, o, h, l, c = bars[i]; dk = t.date()
        day_pnl.setdefault(dk, 0.0)
        still = []
        for p in open_pos:
            ex = None; rs = None
            if p["side"] == "sell":
                if p["sl_px"] is not None and h >= p["sl_px"]: ex, rs = p["sl_px"], "sl"
                elif l <= p["tp_px"]: ex, rs = p["tp_px"], "tp"
            else:
                if p["sl_px"] is not None and l <= p["sl_px"]: ex, rs = p["sl_px"], "sl"
                elif h >= p["tp_px"]: ex, rs = p["tp_px"], "tp"
            if ex is None and (i - p["i"]) >= hold_min:
                ex = c - spread / 2 if p["side"] == "sell" else c + spread / 2; rs = "time"
            if ex is None:
                still.append(p); continue
            pts = (p["entry"] - ex) if p["side"] == "sell" else (ex - p["entry"])
            pnl = pts * PT - commission
            trades.append({"t": t, "pnl": pnl, "rs": rs}); day_pnl[dk] += pnl
        open_pos = still
        if i < lookback + 1 or len(open_pos) >= max_pos or (i - last_i) < min_gap:
            continue
        if day_pnl[dk] <= -daily_cap:
            continue
        if eff_max < 1.0 and (eff_arr[i] > eff_max or vpath_arr[i] < vol_min):
            continue
        move = closes[i] - closes[i - lookback]
        side = "sell" if move >= trigger else ("buy" if move <= -trigger else None)
        if side is None:
            continue
        entry = c - spread / 2 if side == "sell" else c + spread / 2
        tp_px = entry - tp if side == "sell" else entry + tp
        sl_px = (entry + sl if side == "sell" else entry - sl) if sl else None
        open_pos.append({"side": side, "entry": entry, "tp_px": tp_px, "sl_px": sl_px, "i": i})
        last_i = i
    return trades


def metrics(trades, start=5000.0):
    if len(trades) < 1:
        return None
    n = len(trades); wins = [x for x in trades if x["pnl"] > 0]
    net = sum(x["pnl"] for x in trades)
    eq = start; peak = eq; mdd = 0
    for x in trades:
        eq += x["pnl"]; peak = max(peak, eq); mdd = min(mdd, eq - peak)
    return {"n": n, "wr": 100 * len(wins) / n, "net": net, "exp": net / n,
            "mdd": mdd, "worst": min(x["pnl"] for x in trades)}


def precompute(bars, eff_win=30, vol_win=30):
    closes = [b[4] for b in bars]; n = len(bars)
    eff = [1.0] * n; vp = [0.0] * n
    for i in range(max(eff_win, vol_win), n):
        seg = closes[i - eff_win:i + 1]
        path = sum(abs(seg[j] - seg[j - 1]) for j in range(1, len(seg)))
        net = abs(seg[-1] - seg[0])
        eff[i] = (net / path) if path > 0 else 1.0
        vseg = closes[i - vol_win:i + 1]
        vp[i] = sum(abs(vseg[j] - vseg[j - 1]) for j in range(1, len(vseg)))
    return closes, eff, vp


if __name__ == "__main__":
    bars = load("reports/xau_m1_2026ytd.csv")
    split = dt.datetime(2026, 5, 1)
    train = [b for b in bars if b[0] < split]
    test = [b for b in bars if b[0] >= split]
    print(f"TRAIN {train[0][0].date()}..{train[-1][0].date()} ({len(train)} bars)  "
          f"TEST {test[0][0].date()}..{test[-1][0].date()} ({len(test)} bars)")
    cl_tr, eff_tr, vp_tr = precompute(train)
    cl_te, eff_te, vp_te = precompute(test)

    grid = dict(
        tp=[0.6, 0.8, 1.0, 1.2],
        sl=[0.8, 1.2, 2.0, None],
        hold_min=[2, 3, 5, 10],
        trigger=[0.8, 1.2],
        eff_max=[0.30, 1.0],
    )
    fixed = dict(lookback=3, max_pos=3, min_gap=2, spread=0.25, commission=0.50,
                 vol_min=2.0, daily_cap=150.0)
    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    print(f"Searching {len(combos)} configs on TRAIN...\n")
    survivors = []
    for combo in combos:
        cfg = dict(zip(keys, combo))
        tr = backtest(train, cl_tr, eff_tr, vp_tr, **cfg, **fixed)
        m = metrics(tr)
        if not m:
            continue
        # require: his-like WR, positive expectancy, enough trades
        if m["wr"] >= 88 and m["exp"] > 0 and m["n"] >= 150:
            survivors.append((cfg, m))
    survivors.sort(key=lambda x: -x[1]["exp"])
    print(f"TRAIN survivors (WR>=88%, exp>0, n>=150): {len(survivors)}")
    for cfg, m in survivors[:15]:
        print(f"  tp{cfg['tp']} sl{cfg['sl']} hold{cfg['hold_min']} trig{cfg['trigger']} "
              f"eff{cfg['eff_max']} | n{m['n']} WR{m['wr']:.1f}% exp${m['exp']:+.2f} "
              f"net${m['net']:+.0f} mdd${m['mdd']:+.0f} worst${m['worst']:+.0f}")

    print("\n=== OUT-OF-SAMPLE validation of TRAIN survivors ===")
    held = 0
    for cfg, m in survivors:
        tr2 = backtest(test, cl_te, eff_te, vp_te, **cfg, **fixed)
        m2 = metrics(tr2)
        if not m2:
            continue
        ok = m2["wr"] >= 85 and m2["exp"] > 0 and m2["n"] >= 30
        if ok:
            held += 1
            print(f"  HOLDS: tp{cfg['tp']} sl{cfg['sl']} hold{cfg['hold_min']} trig{cfg['trigger']} "
                  f"eff{cfg['eff_max']} | OOS n{m2['n']} WR{m2['wr']:.1f}% exp${m2['exp']:+.2f} "
                  f"net${m2['net']:+.0f} worst${m2['worst']:+.0f}")
    print(f"\nSurvivors that ALSO hold out-of-sample: {held}/{len(survivors)}")
