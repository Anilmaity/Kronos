"""Backtest the H4 trend-follow ON the FundingPips account (5216074f / FundingPips-SIM1).

Calibrated to the account's REAL specs (fetched live from MetaApi):
  contractSize 100, tickValue $1/lot  -> $10 per 1.0 point at 0.10 lot
  spread ~0.25 pt, commission ~$4.87/lot round-trip (from his actual fills $0.49 @0.1)
  swapLong -93.17 / swapShort +21.68 per lot per night (gold carry)
  minVolume 0.01, step 0.01, leverage 100

Strategy: bot/challenge_xau (H4 Donchian-20 breakout, EMA20/50 bias, 3xATR trail),
sized each trade from equity via challenge_xau.position_size (risk = max($40, 0.8%)).

Applies FundingPips-style evaluation rules (TYPICAL — confirm yours):
  start $5,000, profit target +$500 (=$5,500), max overall loss 10% (floor $4,500),
  max daily loss 5% ($250 from each day's starting equity).
"""
import csv, datetime as dt
from bot import challenge_xau as CX

USD_PT_PER_LOT = 100.0          # $ per 1.0 point per 1.0 lot (contractSize*tickValue/tickSize*... = 100*1/... )
COMM_PER_LOT_RT = 4.87          # round-trip commission per 1.0 lot (his $0.49 @0.10 lot)
SWAP_LONG = -93.17              # per lot per night
SWAP_SHORT = 21.68
SPREAD = 0.25                   # points


def load(path):
    b = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            b.append((dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S"),
                      float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    return b


def simulate(bars, *, N=20, k_atr=3.0, ema_fast=20, ema_slow=50,
             start_equity=5000.0, risk_pct=0.008, risk_floor=40.0,
             target=5500.0, floor=4500.0, daily_limit=-250.0,
             include_swap=True, stop_at_target=False):
    o = [b[1] for b in bars]; h = [b[2] for b in bars]
    l = [b[3] for b in bars]; c = [b[4] for b in bars]; t = [b[0] for b in bars]
    n = len(c)
    ef, es = CX.ema(c, ema_fast), CX.ema(c, ema_slow); a = CX.atr(h, l, c, 14)

    equity = start_equity
    eq_curve = [(t[0], equity)]
    trades = []
    day_start_eq = {}            # date -> equity at first bar of that day
    breach = None                # ('overall'|'daily', date, equity)
    hit_target_at = None
    i = max(N, ema_slow) + 1
    while i < n - 1:
        dk = t[i].date()
        day_start_eq.setdefault(dk, equity)
        donch_hi = max(h[i - N:i]); donch_lo = min(l[i - N:i]); up = ef[i] > es[i]
        side = "long" if (c[i] > donch_hi and up) else ("short" if (c[i] < donch_lo and not up) else None)
        if side is None:
            i += 1; continue
        A = a[i]
        if A <= 0:
            i += 1; continue
        lot, _ = CX.position_size(equity, A, risk_pct=risk_pct, risk_floor=risk_floor, k_atr=k_atr)
        entry = o[i + 1] + (SPREAD / 2 if side == "long" else -SPREAD / 2)
        risk = k_atr * A
        j = i + 1; exit_px = None
        if side == "long":
            trail = entry - risk; hh = entry
            while j < n:
                hh = max(hh, h[j]); trail = max(trail, hh - risk)
                if l[j] <= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            pts = exit_px - entry
        else:
            trail = entry + risk; ll = entry
            while j < n:
                ll = min(ll, l[j]); trail = min(trail, ll + risk)
                if h[j] >= trail:
                    exit_px = trail; break
                j += 1
            if exit_px is None:
                exit_px = c[-1]; j = n - 1
            pts = entry - exit_px

        gross = pts * USD_PT_PER_LOT * lot
        comm = COMM_PER_LOT_RT * lot
        nights = max(0, (t[j].date() - t[i].date()).days)
        swap = ((SWAP_LONG if side == "long" else SWAP_SHORT) * lot * nights) if include_swap else 0.0
        pnl = gross - comm + swap
        equity += pnl
        eq_curve.append((t[j], equity))
        trades.append({"t_in": t[i], "t_out": t[j], "side": side, "lot": lot,
                       "pts": pts, "pnl": pnl, "swap": swap, "comm": comm, "equity": equity,
                       "nights": nights})

        # FundingPips rule checks
        if equity <= floor and breach is None:
            breach = ("overall", t[j].date(), equity)
        if equity - day_start_eq[dk] <= daily_limit and breach is None:
            breach = ("daily", dk, equity)
        if equity >= target and hit_target_at is None:
            hit_target_at = (t[j], len(trades))
            if stop_at_target:
                break
        i = j + 1
    return {"equity": equity, "curve": eq_curve, "trades": trades,
            "breach": breach, "hit_target": hit_target_at, "start": start_equity}


def report(res, label):
    tr = res["trades"]
    if not tr:
        print(f"{label}: no trades"); return
    start = res["start"]; end = res["equity"]
    wins = [x for x in tr if x["pnl"] > 0]
    peak = start; mdd = 0; mdd_pct = 0
    eqs = start
    for x in tr:
        eqs = x["equity"]; peak = max(peak, eqs); mdd = min(mdd, eqs - peak)
        mdd_pct = min(mdd_pct, (eqs - peak) / peak * 100)
    net = end - start
    gw = sum(x["pnl"] for x in wins); gl = sum(x["pnl"] for x in tr if x["pnl"] <= 0)
    pf = gw / abs(gl) if gl else float("inf")
    swap_tot = sum(x["swap"] for x in tr); comm_tot = sum(x["comm"] for x in tr)
    print(f"\n=== {label} ===")
    print(f"  period {tr[0]['t_in'].date()} .. {tr[-1]['t_out'].date()}   trades {len(tr)}")
    print(f"  start ${start:,.0f} -> end ${end:,.2f}   net ${net:+,.2f} ({net/start*100:+.1f}%)")
    print(f"  WR {100*len(wins)/len(tr):.0f}%  PF {pf:.2f}  max DD ${mdd:,.0f} ({mdd_pct:.1f}%)")
    print(f"  costs paid: commission ${comm_tot:,.0f}  swap ${swap_tot:,.0f}")
    print(f"  avg lot {sum(x['lot'] for x in tr)/len(tr):.3f}  best ${max(x['pnl'] for x in tr):+,.0f}  worst ${min(x['pnl'] for x in tr):+,.0f}")
    if res["hit_target"]:
        tt, ntr = res["hit_target"]
        print(f"  FIRST HIT +$500 target on {tt.date()} (after {ntr} trades)")
    else:
        print(f"  never reached +$500 in one continuous run")
    if res["breach"]:
        kind, when, eq = res["breach"]
        print(f"  *** would BREACH {kind} drawdown limit on {when} (equity ${eq:,.0f}) ***")
    else:
        print(f"  no FundingPips drawdown-limit breach over the whole run")
    yrs = {}
    for x in tr:
        yrs.setdefault(x["t_out"].year, 0.0); yrs[x["t_out"].year] += x["pnl"]
    print("  by year: " + "  ".join(f"{y}:${v:+,.0f}" for y, v in sorted(yrs.items())))


if __name__ == "__main__":
    bars = load("reports/xau_h4_3y.csv")
    print(f"H4 bars {bars[0][0].date()}..{bars[-1][0].date()} ({len(bars)})  "
          f"account FundingPips-SIM1, start $5,000")
    report(simulate(bars), "H4 trend-follow on the account (real costs+swap, equity-sized)")
    report(simulate(bars, include_swap=False),
           "  same, EXCLUDING swap (to isolate carry drag)")
    report(simulate(bars, stop_at_target=True),
           "  challenge mode: stop the moment +$500 is hit")
