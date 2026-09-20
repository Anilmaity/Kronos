"""Scouting: after a liquidity sweep of the prior-N high/low, what is the
post-event favorable vs adverse excursion? Tells us whether a FADE has any
expectancy once the ~0.66pt spread is paid, and the achievable RR/WR frontier.

For each sweep event (in active sessions), measure over the next H bars:
  MFE = max favorable move (in the fade direction) from the close
  MAE = max adverse move
Then grid: for target T and stop S, fraction of events where T is hit before S
(a proxy win rate for a fade with those brackets), net of a 0.66pt round-trip.
"""
import numpy as np
from bot.oanda_s5 import load, S5_DIR
import os
from bot.micro.engine import Bars, atr, roll_max, roll_min
from bot.micro.features import hours_mask

months = sorted(f[len("xau_s5_"):-4] for f in os.listdir(S5_DIR) if f.endswith(".npz"))
a, z = months[0], months[-2] if len(months) > 1 else months[-1]  # skip the lone future month
b = Bars(load(a, z))
print(f"scouting {a}..{z}  {b.n:,} bars")

A = atr(b, 14)
N = 30
rmax = roll_max(b.mid, N); rmin = roll_min(b.mid, N)
sess = hours_mask(b, (7, 8, 9, 12, 13, 14, 15))
volok = (A >= 0.3) & (A <= 1.5)
MINREV = 0.3

sweep_up = (b.ah > rmax) & (b.bc < rmax - MINREV) & np.isfinite(rmax) & sess & volok
sweep_dn = (b.al < rmin) & (b.bc > rmin + MINREV) & np.isfinite(rmin) & sess & volok

H = 180  # ~15 min horizon
def excursions(idx, side):
    # side=-1 fade a sweep-up (we short): favorable = price down; +1 fade sweep-dn (long)
    mfe = np.zeros(len(idx)); mae = np.zeros(len(idx))
    for k, i in enumerate(idx):
        j0 = i + 1; j1 = min(i + 1 + H, b.n)
        if j1 <= j0:
            mfe[k] = mae[k] = 0; continue
        entry = b.ac[i] if side > 0 else b.bc[i]  # market fill cost side
        if side > 0:  # long: favorable = bid_high up, adverse = bid_low down
            fav = b.bh[j0:j1].max() - entry
            adv = entry - b.bl[j0:j1].min()
        else:         # short: favorable = ask_low down, adverse = ask_high up
            fav = entry - b.al[j0:j1].min()
            adv = b.ah[j0:j1].max() - entry
        mfe[k] = fav; mae[k] = adv
    return mfe, mae

iu = np.where(sweep_up)[0]; il = np.where(sweep_dn)[0]
mfe_u, mae_u = excursions(iu, -1)
mfe_l, mae_l = excursions(il, +1)
mfe = np.concatenate([mfe_u, mfe_l]); mae = np.concatenate([mae_u, mae_l])
print(f"sweep events: {len(mfe):,}  (up {len(iu):,}, dn {len(il):,})")
print(f"MFE pts: med {np.median(mfe):.2f} p75 {np.percentile(mfe,75):.2f} p90 {np.percentile(mfe,90):.2f}")
print(f"MAE pts: med {np.median(mae):.2f} p75 {np.percentile(mae,75):.2f} p90 {np.percentile(mae,90):.2f}")

print("\nFade bracket grid (win = target hit before stop, using MFE/MAE proxy):")
print("  target/stop ->  approx WR   (need WR*T > (1-WR)*S + 0.66 spread to profit)")
for T in (1.0, 1.5, 2.0, 3.0):
    row = []
    for S in (1.0, 1.5, 2.0, 3.0):
        win = (mfe >= T) & (mae < S)   # target reached, stop not (within horizon, optimistic on ordering)
        # also count clear losses: stop reached and target not
        wr = win.mean()
        ev = wr * T - (1 - wr) * S - 0.66  # crude EV per trade in pts
        row.append(f"T{T}/S{S}:WR{wr*100:4.0f}% EV{ev:+.2f}")
    print("  " + "  ".join(row))
