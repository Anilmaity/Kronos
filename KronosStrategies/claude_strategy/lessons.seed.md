# Claude Strategy — lessons

Permanent learning file. Read every cycle; post-mortem every closed trade (see CLAUDE.md).

## Scorecard
- Through 2026-10-06: trades 2 · wins 0 · losses 2 · net −$36.00 (operator paper test 10:10 not counted)

## Active rules (≤ 15, each cites its evidence)
1. Enter on the RETEST, never the break bar — chasing from <1 pt above the break close kills R. [10-06 session]
2. A pre-committed trigger that trades through intrabar is missed — do not re-aim at the same level; move to the next structure. [10-06 session]
3. Overlapping delivery is not a fresh FVG — a committed close is necessary but not sufficient without a non-overlapping FVG. [10-06 18:30–19:45 leg]
4. (tentative) Stop must sit beyond the swept extreme with room for noise, not just under the retest zone; if that pushes the SL past ~25 pts, skip rather than tighten. [T1]
5. Broker errors are final for that cycle — log and stop, never retry the order. [10-06 12:45 near-miss]
6. Pre-commit an early-close condition when opening, and honour it — it cut T2 at −$11 five minutes before the −$20.85 stop. [T2]
7. (tentative) Do not fade a day whose 4h structure is still bullish on a 5m rejection alone — T1's long was right on direction (TP touched 11:35), T2's short against it lost while price ran to 4184. Counter-trend needs a 1h CHoCH, not a 5m one. [T1, T2]

## Trade post-mortems
### T1 · 2026-10-06 10:50 BUY 0.09 @4159.24 SL 4156.5 TP 4170 → SL 11:07, −$25
- Thesis: 4158.38 EQH swept 10:35, BOS 10:40, 10:45 retest of 4157.34–4158.38 held; draw PDH 4170.44 (~3.8R).
- What happened: price dipped to 4156.45 — 0.05 pt through the stop — then rallied to 4179.69 by ~12:00, through the TP.
- Mistake or variance? MISTAKE (placement): direction and target were right; the SL was 2.8 pts, inside normal 5m noise and only 0.84 pt under the zone low, so a routine wick took it out.
- Change: rule 4 (tentative until a second trade confirms or contradicts it).

### T2 · 2026-10-06 14:41 SELL 0.03 @4148.55 SL 4155.5 TP 4140 → closed early 14:45, −$11
- Thesis: bearish bias since the 12:45 "kill bar"; 14:35 swept the FVG high 4152.13 and closed back below the FVG low — at-zone rejection, 1.59R to 4140.
- What happened: 14:40 closed 4152.69, back above the FVG (the pre-committed invalidation) → closed at ~4152.65. Price then touched the SL level 4155.5 at 14:50 and rallied to 4184.39 by 19:00; 4140 was never reached.
- Mistake or variance? MISTAKE (bias): the short faded an intraday-bullish day (Asia sweep of 4103 → 4179 rally) on a 5m signal. Management was correct — the early close saved ~$10.
- Change: rule 6 (keep doing it) and rule 7 (tentative).

## Notes (near-misses and one-liners)
- 2026-10-06 12:45 BUY @4172.73 rejected by broker (MetaAPI 504); broker confirmed no fill. Price turned down from there — the error saved ~$25.
