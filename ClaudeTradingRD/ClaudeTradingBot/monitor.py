"""XAUUSD trigger monitor (gold-only) — exits when a watched level/time breaks,
which re-invokes the agent to assess and act.

Levels re-set 2026-06-17 18:02 UTC. Account flat $1003.96 (commingled w/ copier),
0W/3L on bot trades. **FOMC PRINTED HAWKISH at 18:00 UTC.** Sustained liquidation: 4382 -> 4270 (~112pt),
the 4305 bounce failed and rolled to lower lows. Now ~4274, INSIDE the H4 bull FVG
4235-4285 (HTF discount), still falling. STAND ASIDE on the post-print spike: every
entry is either a chase or un-sizable at 1% (0.01 min lot = $1/pt; a structural stop
is ~30-38pt = ~3% risk). Re-engage only at a real decision LEVEL or once volatility
compresses enough for a 1%-fittable located entry. OANDA feed fresh; MT5 = UTC+3.

Update 00:31 UTC (Jun 18, Asia): flat (limit cancelled). Gold recovered to ~4304 —
broke the 4285 PDL + 4300, clean continuation (HL 4268->4294->4299), now ~64% retrace
of the whole FOMC drop (4382->4219). +85pt off the low = EXTENDED; NO chase at 4304 in
thin Asia. The proper continuation-long = a pullback to the broken 4285 PDL (new
support), and the real read is the London KZ ~07:00 UTC. OANDA fresh; MT5 = UTC+3.

Armed wide for genuine engagement only (no Asia-grind churn):
  - LONDON_KZ Thu >=07:00 UTC (Jun 18) : primary reassessment with real liquidity.
  - GOLD_LOWER < 4286 : pullback to the 4285 PDL retest (new support) → assess a SIZED
                        continuation LONG toward 4332/4369 on an M5 bullish reaction.
  - GOLD_UPPER > 4333 : broke the 4332 post-print bounce high → momentum continuation →
                        reassess (don't chase; wait for a pullback entry).
12h max-age guard prevents a stale process.
"""
import sys
import time
from datetime import datetime, timezone

from bot import data

GOLD_UPPER = 4333.0
GOLD_LOWER = 4286.0
FOMC_PRINT = (2026, 6, 18, 7, 0)   # Y, M, D, hour, minute UTC — London KZ primary reassessment
POLL_SECONDS = 60
MAX_AGE_HOURS = 12

start = time.time()
fomc_flagged = False
while True:
    now = datetime.now(timezone.utc)
    if time.time() - start > MAX_AGE_HOURS * 3600:
        print(f"EXIT: MAX_AGE at {now.isoformat()} - relaunch with fresh levels")
        sys.exit(0)

    # Post-FOMC reaction read (once), Wed >= 18:05 UTC.
    if (not fomc_flagged and (now.year, now.month, now.day) == FOMC_PRINT[:3]
            and (now.hour, now.minute) >= FOMC_PRINT[3:]):
        fomc_flagged = True
        print(f"EXIT: LONDON_KZ at {now.isoformat()} - London open, real liquidity. "
              "Re-read the post-FOMC structure (did the 4382->4219 drop fully recover or "
              "stall?); map DOL + FVGs and take only a clean, properly-sized setup.")
        sys.exit(0)

    line = [now.strftime("%H:%M:%S") + "Z"]
    try:
        q = data.current_price("XAU_USD")
        g = q["mid"]
        line.append(f"XAU={g}")
        if g > GOLD_UPPER:
            print(f"EXIT: GOLD_UPPER {g} > {GOLD_UPPER} - broke the 4332 bounce high; "
                  "momentum continuation, reassess but wait for a pullback entry (no chase)")
            sys.exit(0)
        if g < GOLD_LOWER:
            print(f"EXIT: GOLD_LOWER {g} < {GOLD_LOWER} - pulled back to the 4285 PDL retest "
                  "(new support); assess a SIZED continuation LONG toward 4332/4369 on M5 bullish reaction")
            sys.exit(0)
    except Exception as e:
        line.append(f"XAU err: {e}")
    print(" ".join(line), flush=True)
    time.sleep(POLL_SECONDS)
