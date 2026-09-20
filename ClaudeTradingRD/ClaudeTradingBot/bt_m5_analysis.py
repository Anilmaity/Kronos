"""Full M5 trend-follow analysis on the FundingPips account, multi-regime 2023-2026.
Mirrors the H4 account-calibrated test so the two timeframes are directly comparable.
"""
import collections
import datetime as dt
from bot import challenge_xau as CX
import bt_account_sim as A

bars = A.load("reports/xau_m5_3y.csv")
print(f"M5 bars {bars[0][0].date()}..{bars[-1][0].date()} ({len(bars)})  account FundingPips-SIM1\n")

print("=== Continuous $5k run, several trend-follow configs (real costs+swap, equity-sized) ===")
for N, k in ((20, 3.0), (40, 3.0), (60, 3.0), (40, 4.0), (80, 4.0)):
    A.report(A.simulate(bars, N=N, k_atr=k), f"M5 Donchian({N}) {k}xATR")

# Build trade universe for the best-looking config for rolling windows + by-year edge check.
def trade_universe(bars, N=40, k=3.0):
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; t = [b[0] for b in bars]; n = len(c)
    ef, es = CX.ema(c, 20), CX.ema(c, 50); atr = CX.atr(h, l, c, 14)
    trades = []; i = max(N, 50) + 1
    while i < n - 1:
        dh = max(h[i - N:i]); dl = min(l[i - N:i]); up = ef[i] > es[i]
        side = "long" if (c[i] > dh and up) else ("short" if (c[i] < dl and not up) else None)
        if side is None: i += 1; continue
        Aa = atr[i]
        if Aa <= 0: i += 1; continue
        entry = o[i + 1] + (A.SPREAD / 2 if side == "long" else -A.SPREAD / 2); risk = k * Aa
        j = i + 1; ex = None
        if side == "long":
            trail = entry - risk; hh = entry
            while j < n:
                hh = max(hh, h[j]); trail = max(trail, hh - risk)
                if l[j] <= trail: ex = trail; break
                j += 1
            if ex is None: ex = c[-1]; j = n - 1
            pts = ex - entry
        else:
            trail = entry + risk; ll = entry
            while j < n:
                ll = min(ll, l[j]); trail = min(trail, ll + risk)
                if h[j] >= trail: ex = trail; break
                j += 1
            if ex is None: ex = c[-1]; j = n - 1
            pts = entry - ex
        trades.append(dict(atr=Aa, side=side, pts=pts, t_in=t[i], t_out=t[j],
                           nights=max(0, (t[j].date() - t[i].date()).days)))
        i = j + 1
    return trades

def run_challenge(trades, start_idx, risk_dollars, k, max_days=60, target=500, floor=-500, daily=-250):
    eq = 5000.0; sd = trades[start_idx]['t_in'].date(); day_anchor = {}
    for tr in trades[start_idx:]:
        if (tr['t_in'].date() - sd).days > max_days: return "timeout"
        lot, _ = CX.position_size(eq, tr['atr'], risk_floor=risk_dollars, risk_pct=0, k_atr=k)
        p = tr['pts'] * A.USD_PT_PER_LOT * lot - A.COMM_PER_LOT_RT * lot \
            + (A.SWAP_LONG if tr['side'] == "long" else A.SWAP_SHORT) * lot * tr['nights']
        eq += p; dk = tr['t_out'].date(); day_anchor.setdefault(dk, eq - p)
        if eq - 5000 <= floor: return "fail_overall"
        if eq - day_anchor[dk] <= daily: return "fail_daily"
        if eq - 5000 >= target: return "pass"
    return "timeout"

BN, BK = 40, 3.0
trades = trade_universe(bars, N=BN, k=BK)
print(f"\n=== Edge check, Donchian({BN}) {BK}xATR: {len(trades)} trades ===")
yrs = collections.defaultdict(lambda: [0, 0.0])
Rs = []
for tr in trades:
    R = tr['pts'] / (BK * tr['atr']); Rs.append(R)
    yrs[tr['t_out'].year][0] += 1; yrs[tr['t_out'].year][1] += R
print("  by year (totR): " + "  ".join(f"{y}:{v[1]:+.0f}R({v[0]})" for y, v in sorted(yrs.items())))
import statistics
print(f"  meanR {statistics.mean(Rs):+.3f}  winR% {100*sum(1 for r in Rs if r>0)/len(Rs):.0f}  "
      f"worstR {min(Rs):+.2f}  bestR {max(Rs):+.2f}")

print("\n=== Rolling fresh-$5k challenges, real sequence (start every 5th trade) ===")
starts = list(range(0, len(trades) - 5, 5))
for horizon in (60, 180):
    print(f"  {horizon}-day window:")
    for rd in (40, 75, 150, 250):
        res = collections.Counter(run_challenge(trades, s, rd, BK, max_days=horizon) for s in starts)
        tot = len(starts); fail = res['fail_overall'] + res['fail_daily']
        print(f"    risk ${rd:3d}: pass {100*res['pass']/tot:.0f}%  fail {100*fail/tot:.0f}%  timeout {100*res['timeout']/tot:.0f}%")
