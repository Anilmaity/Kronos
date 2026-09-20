"""
s5_volaware_stop.py — Build & walk-forward-compare overshoot-aware stop models.

From diagnosis: loss size ∝ overshoot (stop = 1.5*ov); baseline stop is far wider than
winners need (97.7% of winners survive at 1.5*ov; 93.2% at 1.0*ov). Big overshoots draw
down LESS in ov-units, so they tolerate a tighter multiple.

Models (target stays 0.5*ov maker limit; only the STOP changes):
  base    : stop = 1.50*ov                (current)
  flatXX  : stop = XX*ov                   (flat tighten)
  taper   : stop = SF_big + (SF_small-SF_big)*exp(-ov/SCALE)  (tighter on big ov)
  regime  : stop = 0.75 + 0.75*ratio       (handoff #1 idea — tighten when quiet; test to refute)
"""
import os, numpy as np
import bot.snap_ict_maker as M

USD = 10.0
path = os.path.join(os.path.dirname(__file__), "reports", "xau_m5_3y.csv")
t, o, c, h, l = M.load(path)
bias = M.daily_ict_bias(t, c, h, l)
n = len(c)
hour, mv, sd, rv, thr = M.indicators(t, c, h, l)

def run(stop_mult):
    """stop_mult(ov, ratio) -> multiple of ov for the stop distance. Returns (pnl[], year[])."""
    out = []; yrs = []
    i = M.W + 1
    while i < n - 2:
        ok = (np.isfinite(mv[i]) and np.isfinite(sd[i]) and sd[i] > 0 and M.SESSION(hour[i])
              and np.isfinite(rv[i]) and np.isfinite(thr[i]) and rv[i] < thr[i] and abs(mv[i]) >= M.K*sd[i])
        if not ok: i += 1; continue
        up = mv[i] > 0; side = -1 if up else 1; ov = abs(mv[i])
        if bias[i] == 0 or np.sign(side) != bias[i]: i += 1; continue
        L = c[i] + (M.OFFSET*sd[i] if up else -M.OFFSET*sd[i]); fj = None
        for j in range(i+1, min(i+1+M.FILL_WIN, n)):
            if up and h[j] >= L: fj = j; break
            if (not up) and l[j] <= L: fj = j; break
        if fj is None: i += 1; continue
        entry = L; ratio = rv[i]/thr[i]
        sf = stop_mult(ov, ratio)
        target = entry - M.TARGET_F*ov if up else entry + M.TARGET_F*ov
        stop   = entry + sf*ov         if up else entry - sf*ov
        ex = None; mk = False
        for j in range(fj+1, min(fj+1+M.TIME, n)):
            if up:
                if h[j] >= stop: ex = stop; break
                if l[j] <= target: ex = target; mk = True; break
            else:
                if l[j] <= stop: ex = stop; break
                if h[j] >= target: ex = target; mk = True; break
        if ex is None: ex = c[min(fj+M.TIME, n-1)]
        out.append((ex-entry)*side + M.HALF + (M.HALF if mk else -M.HALF)); yrs.append(t[i][:4])
        i = j + 1
    return np.array(out), np.array(yrs)

def report(name, pnl, yrs):
    line = f"{name:<10}"
    tot = pnl.sum()*USD
    for y in ("2023","2024","2025","2026"):
        p = pnl[yrs==y]
        if len(p): line += f"  {y}:${p.sum()*USD:>+6,.0f}"
    worst = np.sort(pnl)[:3]*USD
    gl=-pnl[pnl<0].sum(); gp=pnl[pnl>0].sum(); pf=gp/gl if gl>0 else 0
    line += f" | ALL ${tot:>+6,.0f} n={len(pnl)} WR{100*(pnl>0).mean():.0f}% PF{pf:.2f} worst{[f'{x:+.0f}' for x in worst]}"
    print(line)

models = {
    "base":   lambda ov, r: 1.50,
    "flat1.25":lambda ov, r: 1.25,
    "flat1.0": lambda ov, r: 1.00,
    "flat0.9": lambda ov, r: 0.90,
    "flat0.8": lambda ov, r: 0.80,
    # taper: small ov -> 1.4, big ov -> 0.9 (decay scale 3pt)
    "taper":  lambda ov, r: 0.90 + 0.50*np.exp(-ov/3.0),
    # regime (handoff #1): tighter when quiet (low ratio). ratio in ~[0.4,1.0]
    "regime": lambda ov, r: 0.75 + 0.75*r,
}
print("=== Overshoot-aware stop walk-forward (0.10 lot) ===")
res = {}
for name, fn in models.items():
    pnl, yrs = run(fn); res[name] = (pnl, yrs); report(name, pnl, yrs)

# focus: per-year positivity check (deploy criterion = positive every year)
print("\nDeploy criterion — positive in ALL of 2023/24/25(OOS)/26(OOS)?")
for name,(pnl,yrs) in res.items():
    yrly = {y: pnl[yrs==y].sum()*USD for y in ("2023","2024","2025","2026")}
    allpos = all(v>0 for v in yrly.values())
    print(f"  {name:<10} {'PASS' if allpos else 'FAIL':<5} {yrly}")
