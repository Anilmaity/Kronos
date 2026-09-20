"""ROUND 5: STRESS the 5-session bias-ORB candidate (hours 1,7,12,13,14).
(1) cost sensitivity 0.35/0.45/0.60pt  (2) parameter plateau or_min/tp_mult/n_long
(3) weekly P&L distribution: worst week, median red week, longest red streak.
"""
import datetime as dt
import statistics as st
from s5_intraday_research import load, COST_PT
from s5_intraday_research2 import strat_orb_biased

HOURS = [1, 7, 12, 13, 14]
SESS = tuple((h, h, 30) for h in HOURS)


def weekly(trades, cost):
    wk = {}
    for x in trades:
        k = x["t"].isocalendar()[:2]
        wk[k] = wk.get(k, 0.0) + (x["gross"] - cost)
    keys = sorted(wk)
    return [wk[k] for k in keys]


def stats(trades, cost):
    net = [x["gross"] - cost for x in trades]
    n = len(net); tot = sum(net)
    gl = sum(p for p in net if p <= 0); gw = sum(p for p in net if p > 0)
    pf = gw / abs(gl) if gl else 9.99
    w = weekly(trades, cost)
    green = 100 * sum(1 for v in w if v > 0) / len(w)
    return n, tot, pf, tot / n, green, w


if __name__ == "__main__":
    bars = load()
    base = strat_orb_biased(bars, sessions=SESS)
    days = len({x["t"].date() for x in base})

    print("=== (1) COST SENSITIVITY (taker round-trip pts) ===")
    print(f"{'cost':>5} {'exp':>8} {'pf':>5} {'net$':>10} {'green%':>7}")
    for cost in (0.35, 0.45, 0.60, 0.80):
        n, tot, pf, exp, green, _ = stats(base, cost)
        print(f"{cost:>5.2f} {exp:>+8.3f} {pf:>5.2f} {tot*10:>+10,.0f} {green:>6.0f}%")

    print(f"\n=== (2) PARAMETER PLATEAU (cost 0.45) ===  (trades/day={len(base)/days:.1f})")
    print(f"{'param':>16} {'exp':>8} {'pf':>5} {'green%':>7} {'t/d':>5}")
    for orm in (20, 30, 40):
        tr = strat_orb_biased(bars, sessions=SESS, or_min=orm)
        n, tot, pf, exp, green, _ = stats(tr, 0.45)
        d = len({x["t"].date() for x in tr})
        print(f"   or_min={orm:<6} {exp:>+8.3f} {pf:>5.2f} {green:>6.0f}% {n/d:>5.1f}")
    for tpm in (1.0, 1.5, 2.0, 2.5):
        tr = strat_orb_biased(bars, sessions=SESS, tp_mult=tpm)
        n, tot, pf, exp, green, _ = stats(tr, 0.45)
        d = len({x["t"].date() for x in tr})
        print(f"  tp_mult={tpm:<5} {exp:>+8.3f} {pf:>5.2f} {green:>6.0f}% {n/d:>5.1f}")
    for nl in (180, 240, 360, 480):
        tr = strat_orb_biased(bars, sessions=SESS, n_long=nl)
        n, tot, pf, exp, green, _ = stats(tr, 0.45)
        d = len({x["t"].date() for x in tr})
        print(f"   n_long={nl:<6} {exp:>+8.3f} {pf:>5.2f} {green:>6.0f}% {n/d:>5.1f}")

    print("\n=== (3) WEEKLY P&L DISTRIBUTION (cost 0.45, $ @0.1lot) ===")
    _, _, _, _, green, w = stats(base, 0.45)
    wd = [x * 10 for x in w]
    reds = [x for x in wd if x <= 0]; greens = [x for x in wd if x > 0]
    # longest consecutive red streak
    streak = mx = 0
    for x in wd:
        streak = streak + 1 if x <= 0 else 0
        mx = max(mx, streak)
    print(f"weeks: {len(wd)}  green {len(greens)} ({green:.0f}%)  red {len(reds)}")
    print(f"median green week: ${st.median(greens):+,.0f}   median red week: ${st.median(reds):+,.0f}")
    print(f"worst week: ${min(wd):+,.0f}   best week: ${max(wd):+,.0f}")
    print(f"longest consecutive red-week streak: {mx} weeks")
    print(f"mean weekly: ${st.mean(wd):+,.0f}   stdev weekly: ${st.pstdev(wd):,.0f}")
