"""Test the LEARNED pattern from his 67 real trades: fade a meaningful short-term
extension, but ONLY in the quiet sessions he actually traded.

Learned signature (from s5 feature-mining):
  - FADE: sell after an up-move, buy after a down-move (41/67 of his entries)
  - require a real extension: |move over 5min| >= EXT (his winners faded ~+1pt; losers ~0)
  - session: he concentrated 46% of trades at 22:00-23:00 UTC, plus 08:00 & 12-13:00 UTC
  - small fixed TP, fast exit, no/loose stop

We test whether session-gating the fade (the piece my earlier grid lacked) creates an edge,
with realistic costs and an honest stop. Data: KronosStrategies S5 (~2 weeks, multi-session).
"""
import json, glob, datetime as dt
import s5_search as S   # reuse load_bars + stats

CACHE = "C:/Projects/PycharmProjects/personal/KronosStrategies/tick_data_collector/Tick_Data_Generator/cache_data/XAU_USD"
USD = 10.0  # $/pt at 0.1 lot


def backtest(bars, *, hours=None, ext_5min=1.0, tp=0.8, sl=2.0, hold_s=90,
             spread=0.25, commission=0.05, min_gap_s=15, lot=0.1,
             require_15m=False):
    times = [b[0] for b in bars]; closes = [b[4] for b in bars]; n = len(bars)
    # index helpers: 5min = 60 bars, 15min = 180 bars (5s bars)
    L5, L15 = 60, 180
    mult = USD * (lot / 0.1); hold_bars = max(1, hold_s // 5)
    trades = []; pos = None; last_i = -10**9
    for i in range(L15, n):
        t = times[i]
        if pos is not None:
            ex = None; rs = None; slpx = pos["sl_px"]
            for px in bars[i][5]:
                if pos["side"] == "buy":
                    if slpx is not None and px <= slpx: ex, rs = slpx, "sl"; break
                    if px >= pos["tp_px"]: ex, rs = pos["tp_px"], "tp"; break
                else:
                    if slpx is not None and px >= slpx: ex, rs = slpx, "sl"; break
                    if px <= pos["tp_px"]: ex, rs = pos["tp_px"], "tp"; break
            if ex is None and (i - pos["i"]) >= hold_bars:
                c = closes[i]; ex = c - spread/2 if pos["side"] == "buy" else c + spread/2; rs = "time"
            if ex is not None:
                pts = (ex - pos["entry"]) if pos["side"] == "buy" else (pos["entry"] - ex)
                trades.append({"t": t, "pnl": pts*mult - commission, "rs": rs}); pos = None
        if pos is not None: continue
        if (times[i] - times[i-1]).total_seconds() > 30: continue
        if hours is not None and t.hour not in hours: continue
        if (i - last_i) < (min_gap_s // 5): continue
        m5 = closes[i] - closes[i - L5]
        m15 = closes[i] - closes[i - L15]
        if abs(m5) < ext_5min: continue
        # FADE: counter the 5-min move
        side = "sell" if m5 > 0 else "buy"
        if require_15m and ((side == "sell" and m15 <= 0) or (side == "buy" and m15 >= 0)):
            continue   # require the longer extension to agree (a real stretched move)
        c = closes[i]
        entry = c + spread/2 if side == "buy" else c - spread/2
        if side == "buy": tp_px, sl_px = entry + tp, (entry - sl if sl else None)
        else: tp_px, sl_px = entry - tp, (entry + sl if sl else None)
        pos = {"side": side, "entry": entry, "tp_px": tp_px, "sl_px": sl_px, "i": i}
        last_i = i
    return trades


def show(label, trades):
    m = S.stats(trades)
    if not m:
        print(f"{label}: no trades"); return
    print(f"{label}: n={m['n']:5d}  WR={m['wr']:4.0f}%  PF={m['pf']:.2f}  "
          f"exp=${m['exp']:+.3f}  net=${m['net']:+.0f}  worst=${m['worst']:+.0f}")


if __name__ == "__main__":
    bars = S.load_bars(sorted(glob.glob(CACHE + "/*.json")))
    print(f"S5 bars {len(bars)}  {bars[0][0]} .. {bars[-1][0]}\n")
    HIS_PRIME = {22, 23}
    HIS_ALL = {0, 5, 6, 7, 8, 9, 10, 12, 13, 19, 22, 23}

    print("--- baseline fade (all hours), the piece my grid already showed loses ---")
    show("  all-hours fade ext1.0 tp0.8 sl2.0", backtest(bars, hours=None))
    print("\n--- LEARNED: session-gated fade (his prime quiet hours 22-23 UTC) ---")
    show("  22-23h fade ext1.0 tp0.8 sl2.0   ", backtest(bars, hours=HIS_PRIME))
    show("  22-23h fade ext1.0 tp0.8 sl2.0 +15m", backtest(bars, hours=HIS_PRIME, require_15m=True))
    show("  his-all-hours fade ext1.0        ", backtest(bars, hours=HIS_ALL))
    print("\n--- extension sensitivity in his prime session (plateau check) ---")
    for ext in (0.6, 0.8, 1.0, 1.5, 2.0):
        show(f"  22-23h ext{ext} tp0.8 sl2.0       ", backtest(bars, hours=HIS_PRIME, ext_5min=ext))
    print("\n--- TP/SL sensitivity in prime session ---")
    for tp, sl in ((0.6,1.5),(0.8,2.0),(1.0,2.5),(0.8,None),(1.2,3.0)):
        show(f"  22-23h tp{tp} sl{sl}            ", backtest(bars, hours=HIS_PRIME, tp=tp, sl=sl))
