"""ROUND 3: where does the bias-filtered breakout edge actually live?
Scan each session-open hour 0..23 (single-session bias ORB), rank by edge.
Then build a MULTI-SESSION portfolio from only the positive hours and measure
trades/day + weekly consistency. Goal: reach 2-3/day while keeping the edge.
"""
import datetime as dt

from s5_intraday_research import load, evaluate, COST_PT
from s5_intraday_research2 import strat_orb_biased, combine


def scan_hours(bars):
    print("per-hour single-session bias-ORB (cost-adjusted):")
    print(f"{'hr':>3} {'n':>5} {'t/d':>4} {'WR':>4} {'PF':>5} {'exp':>7} {'net$':>9} {'green%':>6}")
    results = {}
    for hr in range(24):
        tr = strat_orb_biased(bars, sessions=((hr, hr, 30),))
        if not tr:
            continue
        net = [x["gross"] - COST_PT for x in tr]
        n = len(net); tot = sum(net)
        days = len({x["t"].date() for x in tr}); tpd = n / days if days else 0
        wins = sum(1 for p in net if p > 0)
        gl = sum(p for p in net if p <= 0); gw = sum(p for p in net if p > 0)
        pf = gw / abs(gl) if gl else 9.99
        wk = {}
        for x in tr:
            k = x["t"].isocalendar()[:2]; wk[k] = wk.get(k, 0) + (x["gross"] - COST_PT)
        green = 100 * sum(1 for v in wk.values() if v > 0) / len(wk) if wk else 0
        results[hr] = {"exp": tot / n, "pf": pf, "net": tot, "tpd": tpd, "green": green}
        flag = "  <<" if tot / n > 0.2 and pf > 1.1 else ""
        print(f"{hr:>3} {n:>5} {tpd:>4.1f} {100*wins/n:>3.0f}% {pf:>5.2f} "
              f"{tot/n:>+7.3f} {tot*10:>+9,.0f} {green:>5.0f}%{flag}")
    return results


if __name__ == "__main__":
    bars = load()
    print(f"loaded {len(bars)} M5 bars\n")
    res = scan_hours(bars)

    # pick hours with positive edge (exp>0.2pt, pf>1.1)
    good = sorted([hr for hr, r in res.items() if r["exp"] > 0.2 and r["pf"] > 1.1])
    print(f"\npositive-edge session hours: {good}")

    print(f"\n{'PORTFOLIO':<40} {'stats':<66} weekly-consistency")
    print("-" * 130)
    for label, hrs in [("top-2 hours", good[:2] if len(good) >= 2 else good),
                       ("all positive hours", good)]:
        if not hrs:
            continue
        sess = tuple((h, h, 30) for h in hrs)
        tr = strat_orb_biased(bars, sessions=sess)
        evaluate(tr, f"multi-session ORB: {label} {hrs}")
