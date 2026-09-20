"""Build-test-repeat search for a profitable scalp at 5-SECOND resolution.

Uses the KronosStrategies S5 cache. Each 5s bar carries a 4-point intra-bar path
(open->low->high->close on up bars; open->high->low->close on down bars), so stop/TP
fills are resolved in true intra-bar order — the fidelity the coarser M1/M5 tests lacked.

Realistic costs: spread filled on entry (buy@ask, sell@bid) + commission per lot.
Decision cadence = every 5s. Search families: mean-reversion fade (trader's style) and
micro-momentum. Train/test split + parameter sweep; we keep only configs that are
positive on BOTH halves (no curve-fit peaks).
"""
import json, glob, datetime as dt

CACHE = "C:/Projects/PycharmProjects/personal/KronosStrategies/tick_data_collector/Tick_Data_Generator/cache_data/XAU_USD"
USD_PT_PER_0_1_LOT = 10.0


def load_bars(files):
    """[(t, o, h, l, c, path[4])] sorted, path = intra-bar 4-point sequence."""
    bars = []
    for fp in files:
        for g in json.load(open(fp, encoding="utf-8")):
            t = dt.datetime.fromisoformat(g[0]["time"])
            path = [float(p["price"]) for p in g]
            o, c = path[0], path[-1]
            bars.append((t, o, max(path), min(path), c, path))
    bars.sort(key=lambda x: x[0])
    return bars


def backtest(bars, *, family="fade", lookback=6, trigger=0.4, tp=0.5, sl=1.0,
             hold_s=60, spread=0.25, commission=0.05, max_pos=1, min_gap_s=5,
             lot=0.1):
    """family 'fade' = mean-reversion; 'mom' = momentum continuation.
       trigger/tp/sl in points; hold_s/min_gap_s in seconds."""
    closes = [b[4] for b in bars]; times = [b[0] for b in bars]
    n = len(bars); trades = []; pos = None; last_t = None
    mult = USD_PT_PER_0_1_LOT * (lot / 0.1)
    hold_bars = max(1, hold_s // 5)
    for i in range(lookback, n):
        t = times[i]
        # manage open position via intra-bar 4-point path (true fill order)
        if pos is not None:
            ex = None; rs = None
            slpx = pos["sl_px"]
            for px in bars[i][5]:           # walk the 4 sub-points in order
                if pos["side"] == "buy":
                    if slpx is not None and px <= slpx: ex, rs = slpx, "sl"; break
                    if px >= pos["tp_px"]: ex, rs = pos["tp_px"], "tp"; break
                else:
                    if slpx is not None and px >= slpx: ex, rs = slpx, "sl"; break
                    if px <= pos["tp_px"]: ex, rs = pos["tp_px"], "tp"; break
            if ex is None and (i - pos["i"]) >= hold_bars:
                c = closes[i]
                ex = c - spread / 2 if pos["side"] == "buy" else c + spread / 2
                rs = "time"
            if ex is not None:
                pts = (ex - pos["entry"]) if pos["side"] == "buy" else (pos["entry"] - ex)
                trades.append({"t": t, "pnl": pts * mult - commission, "rs": rs})
                pos = None
        if pos is not None:
            continue
        # gaps: skip if previous bar far away (session break)
        if (times[i] - times[i - 1]).total_seconds() > 30:
            continue
        if last_t and (times[i] - last_t).total_seconds() < min_gap_s:
            continue
        move = closes[i] - closes[i - lookback]
        if family == "fade":
            side = "sell" if move >= trigger else ("buy" if move <= -trigger else None)
        else:  # momentum
            side = "buy" if move >= trigger else ("sell" if move <= -trigger else None)
        if side is None:
            continue
        c = closes[i]
        entry = c + spread / 2 if side == "buy" else c - spread / 2
        if side == "buy":
            tp_px = entry + tp; sl_px = (entry - sl) if sl else None
        else:
            tp_px = entry - tp; sl_px = (entry + sl) if sl else None
        pos = {"side": side, "entry": entry, "tp_px": tp_px, "sl_px": sl_px, "i": i}
        last_t = times[i]
    return trades


def stats(trades):
    if not trades:
        return None
    n = len(trades); wins = [x for x in trades if x["pnl"] > 0]
    net = sum(x["pnl"] for x in trades)
    gl = sum(x["pnl"] for x in trades if x["pnl"] <= 0)
    gw = sum(x["pnl"] for x in wins)
    return {"n": n, "wr": 100 * len(wins) / n, "net": net, "exp": net / n,
            "pf": (gw / abs(gl) if gl else float("inf")),
            "worst": min(x["pnl"] for x in trades)}


if __name__ == "__main__":
    import itertools, sys
    files = sorted(glob.glob(CACHE + "/*.json"))
    bars = load_bars(files)
    split_time = bars[len(bars) // 2][0]
    print(f"S5 bars {len(bars)}  {bars[0][0]} .. {bars[-1][0]}  split @ {split_time}", flush=True)

    grid = dict(family=["fade", "mom"], lookback=[2, 6, 12, 24],
                trigger=[0.3, 0.5, 0.8, 1.2], tp=[0.4, 0.6, 1.0],
                sl=[0.6, 1.0, 2.0, None], hold_s=[30, 60, 120])
    keys = list(grid)
    combos = list(itertools.product(*[grid[k] for k in keys]))
    print(f"Searching {len(combos)} configs, single-pass, commission $0.05 spread 0.25\n", flush=True)

    survivors = []; best_full = []
    for idx, combo in enumerate(combos):
        cfg = dict(zip(keys, combo))
        trades = backtest(bars, **cfg)          # ONE pass over full data
        if len(trades) < 120:
            continue
        tr = [x for x in trades if x["t"] < split_time]
        te = [x for x in trades if x["t"] >= split_time]
        mfull = stats(trades); mtr = stats(tr); mte = stats(te)
        best_full.append((cfg, mfull))
        if mtr and mte and mtr["n"] >= 60 and mte["n"] >= 60 and mtr["exp"] > 0 and mte["exp"] > 0:
            survivors.append((cfg, mtr, mte, mfull))
        if (idx + 1) % 200 == 0:
            print(f"  ...{idx+1}/{len(combos)} done, survivors so far: {len(survivors)}", flush=True)

    survivors.sort(key=lambda x: -(x[1]["exp"] + x[2]["exp"]))
    print(f"\n=== Configs positive on BOTH train AND test (no curve-fit): {len(survivors)} ===", flush=True)
    for cfg, mtr, mte, mf in survivors[:15]:
        print(f"  {cfg['family']} lb{cfg['lookback']} trig{cfg['trigger']} tp{cfg['tp']} "
              f"sl{cfg['sl']} hold{cfg['hold_s']}s | TRAIN ${mtr['exp']:+.3f} ({mtr['n']}) | "
              f"TEST ${mte['exp']:+.3f} ({mte['n']}) | FULL ${mf['exp']:+.3f} WR{mf['wr']:.0f}% PF{mf['pf']:.2f}",
              flush=True)

    best_full.sort(key=lambda x: -x[1]["exp"])
    print("\n=== Best expectancy over ALL data (in-sample ceiling, may be curve-fit) ===", flush=True)
    for cfg, m in best_full[:6]:
        print(f"  {cfg['family']} lb{cfg['lookback']} trig{cfg['trigger']} tp{cfg['tp']} sl{cfg['sl']} "
              f"hold{cfg['hold_s']}s | exp${m['exp']:+.3f} WR{m['wr']:.0f}% PF{m['pf']:.2f} n{m['n']} "
              f"net${m['net']:+.0f}", flush=True)
    print(f"\nProfitable-on-full configs: {sum(1 for _,m in best_full if m['exp']>0)}/{len(best_full)}", flush=True)
