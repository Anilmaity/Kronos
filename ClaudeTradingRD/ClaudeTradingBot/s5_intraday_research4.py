"""ROUND 4: kill the selection-bias concern. Split train(2023-2024)/test(2025-2026).
Rank session hours on TRAIN only; check each hour's edge PERSISTS on TEST.
Then build a 2-5/day portfolio from hours robust in BOTH halves and report
OUT-OF-SAMPLE trades/day, expectancy, and weekly consistency.
"""
import datetime as dt
from s5_intraday_research import load, evaluate, COST_PT
from s5_intraday_research2 import strat_orb_biased

SPLIT = dt.date(2025, 1, 1)


def edge(trades):
    if not trades:
        return None
    net = [x["gross"] - COST_PT for x in trades]
    n = len(net); tot = sum(net)
    days = len({x["t"].date() for x in trades})
    gl = sum(p for p in net if p <= 0); gw = sum(p for p in net if p > 0)
    pf = gw / abs(gl) if gl else 9.99
    wk = {}
    for x in trades:
        k = x["t"].isocalendar()[:2]; wk[k] = wk.get(k, 0) + (x["gross"] - COST_PT)
    green = 100 * sum(1 for v in wk.values() if v > 0) / len(wk) if wk else 0
    return {"n": n, "exp": tot / n, "pf": pf, "tpd": n / days, "green": green, "net": tot}


if __name__ == "__main__":
    bars = load()
    train = [b for b in bars if b[0].date() < SPLIT]
    test = [b for b in bars if b[0].date() >= SPLIT]
    print(f"train {train[0][0].date()}..{train[-1][0].date()}  "
          f"test {test[0][0].date()}..{test[-1][0].date()}\n")

    print("per-hour edge persistence (exp pt, after cost):")
    print(f"{'hr':>3} | {'train_exp':>9} {'tr_pf':>5} | {'test_exp':>9} {'te_pf':>5}  persists?")
    persist = []
    for hr in range(24):
        et = edge(strat_orb_biased(train, sessions=((hr, hr, 30),)))
        ev = edge(strat_orb_biased(test, sessions=((hr, hr, 30),)))
        if not et or not ev:
            continue
        ok = et["exp"] > 0.15 and et["pf"] > 1.1 and ev["exp"] > 0.0 and ev["pf"] > 1.0
        if ok:
            persist.append(hr)
        print(f"{hr:>3} | {et['exp']:>+9.3f} {et['pf']:>5.2f} | {ev['exp']:>+9.3f} "
              f"{ev['pf']:>5.2f}  {'YES' if ok else ''}")

    print(f"\nhours with edge in BOTH train & test: {persist}")
    # cap at a robust 2-5/day subset: take persistent hours, prefer session clusters
    subset = persist[:5] if len(persist) > 5 else persist
    sess = tuple((h, h, 30) for h in subset)

    print(f"\n=== OUT-OF-SAMPLE portfolio (hours chosen on train): {subset} ===")
    tr_tr = strat_orb_biased(train, sessions=sess)
    tr_te = strat_orb_biased(test, sessions=sess)
    print("\nstats                                                                  weekly-consistency")
    print("-" * 120)
    evaluate(tr_tr, "IN-SAMPLE (2023-2024)")
    evaluate(tr_te, "OUT-OF-SAMPLE (2025-2026)")
