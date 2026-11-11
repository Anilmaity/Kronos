"""Demonstration: the most often ANY strategy with a given profit factor can reach a day target inside a -2.5 % floor.
Each trade wins b x risk with probability p, where p is set so the profit factor is exactly PF.
'Bold' play (risk the whole room every trade) is the known optimum for a losing game; we simulate it and a timid play."""
import numpy as np
rng = np.random.default_rng(7); N = 200_000; FLOOR = 2.5

def day(pf, b, target, risk_frac):                     # risk_frac of the room to the floor, per trade
    p = pf / (pf + b)                                  # p*b / (1-p) = pf
    eq = np.zeros(N); live = np.ones(N, bool)
    for _ in range(400):
        room = eq + FLOOR; risk = np.minimum(room * risk_frac, np.maximum((target - eq) / b, 0))
        win = rng.random(N) < p
        eq = np.where(live, eq + np.where(win, b * risk, -risk), eq)
        live &= (eq < target - 1e-9) & (eq > -FLOOR + 1e-3)
    return (eq >= target - 1e-9).mean() * 100, p * 100

print("PF    payoff(win/loss)  win-rate  play          P(day >= +6%)  P(day >= +20%)")
for pf in (0.70, 0.75, 0.80):
    for b, label in ((1 / 3, "70-80% win-rate scalps"), (2.4, "one big shot to +6%")):
        for frac, play in ((1.0, "bold"), (0.2, "timid")):
            a, p = day(pf, b, 6, frac); c, _ = day(pf, b, 20, frac)
            print(f"{pf:.2f}  {b:>5.2f} {label:<24} {p:5.1f}%   {play:<6} {a:13.1f}% {c:14.1f}%")
