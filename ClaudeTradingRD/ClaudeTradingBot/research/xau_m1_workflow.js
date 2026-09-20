export const meta = {
  name: 'xau-m1-edge',
  description: 'Hunt a real intraday XAU edge on M1/M5 bars (5-20/day natural) that holds in BOTH train and OOS at realistic 0.25 taker spread; adversarially verify regime-robustness',
  phases: [
    { title: 'Build' },
    { title: 'Verify' },
    { title: 'Synthesize' },
  ],
}

const ROUNDS = (args && args.rounds) || 3
const K = (args && args.k) || 6
const PYTHON = '.venv/Scripts/python.exe'

// Pattern families that need M1+ resolution (5s noise floor suppressed these).
const CONCEPTS = [
  'Mean-reversion z-score / Bollinger fade (improve bot/micro/strat_m1_ref.py): the edge is SELECTIVITY — fade an over-extension only at a session/structure liquidity extreme, ideally COUNTER to a short burst but WITH the higher-TF (M5/M15) mean, with a structure stop and a mean-revert target. Naive all-bar z-fade loses; find the context filter that makes it pay at 0.25 taker.',
  'Opening-range breakout (London 07:00 UTC, NY 12:30-13:30 UTC): define the OR over the first X minutes, trade a decisive break of OR high/low WITH a higher-TF bias filter, stop at OR mid/opposite, target a measured move. This is taker-compatible by nature (market on break) and is the known session-breakout family — quantify it properly on M1.',
  'M1 FVG fill in M5/M15 bias: detect a fair-value-gap on M1 (or M5), only take fills in the higher-TF EMA-bias direction, enter a limit at the gap, target the displacement origin. Bigger M1 gaps clear the spread the 5s ones could not.',
  'M1 liquidity sweep reversal: sweep of a SESSION high/low or an equal-highs/lows cluster (real resting liquidity, not a rolling extreme), then a displacement reversal back through it; enter the reversal, stop beyond the sweep, target the range interior. M1 bars (~2pt) give the reversal room to clear cost.',
  'Session VWAP deviation reversion: build a session-anchored VWAP from M1 (price*vol), fade extensions beyond k*sigma bands back toward VWAP, only in-session, only when higher-TF is balanced (not trending hard). Standard, robust, naturally 5-20/day.',
  'Order-block / breaker retest continuation on M1/M5: detect an OB (last opposite candle before an M5 displacement BOS), enter the retest continuation, stop beyond the OB, 2R target. Higher TF than the dead 5s micro-BOS so each setup spans a real move.',
]

const BUILD_SCHEMA = {
  type: 'object',
  required: ['path', 'name', 'tf', 'built_ok', 'runner_json', 'oos_trades', 'train_pf_025t', 'oos_pf_025t', 'notes'],
  properties: {
    path: { type: 'string' }, name: { type: 'string' },
    tf: { type: 'number', description: 'execution timeframe in seconds (60=M1, 300=M5)' },
    built_ok: { type: 'boolean' },
    runner_json: { type: 'string', description: 'EXACT runner JSON (has oos + oos_spread_grid + train_spread_grid)' },
    oos_trades: { type: 'number' },
    train_pf_025t: { type: 'number', description: 'TRAIN taker PF at ~0.25 spread (avg of 0.20/0.30 taker from train_spread_grid)' },
    oos_pf_025t: { type: 'number', description: 'OOS taker PF at ~0.25 spread' },
    notes: { type: 'string' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['name', 'real_edge', 'look_ahead_suspect', 'plateau_ok', 'regime_robust', 'verdict', 'evidence'],
  properties: {
    name: { type: 'string' },
    real_edge: { type: 'boolean' },
    look_ahead_suspect: { type: 'boolean' },
    plateau_ok: { type: 'boolean' },
    regime_robust: { type: 'boolean', description: 'positive at 0.25 taker in BOTH train and OOS, and majority of individual years?' },
    verdict: { type: 'string', enum: ['PASS', 'PROMISING', 'REJECT'] },
    evidence: { type: 'string' },
  },
}

const CONTRACT = `
cwd = C:\\Projects\\ClaudeProjects\\ClaudeTradingBot. Python = ${PYTHON} (numpy only). Use bash.
Real OANDA 5s XAU bid/ask cached under reports/s5/ (30 months, 2024-01..2026-06).

REQUIRED READING:
  research/GOAL.md, research/SCOUT_FINDINGS.md, research/FINDINGS.md (why 5s failed)
  bot/micro/strat_m1_ref.py  - M1 TEMPLATE: set TF=60 (M1) or 300 (M5); the runner resamples
                               the S5 bid/ask data to that timeframe automatically.
  bot/micro/engine.py, bot/micro/features.py  - API. NOTE: features.resample(b, seconds) and
                               resample_bars build higher-TF views; ema/atr/swings/fvg/hours_mask.

WHY M1/M5: at M1 the bar range median ~2.06pt vs the 0.66 spread (ratio ~3.1), where 5s was 0.26
(ratio 0.4). There is finally room for a real edge, and 5-20 trades/day is natural.

THE BAR (this run is STRICTER than before to avoid regime artifacts):
A candidate must be POSITIVE AT 0.25 TAKER IN BOTH TRAIN AND OOS — the runner now prints
train_spread_grid AND oos_spread_grid. The prior 5s "winner" was train-NEGATIVE / OOS-positive
(regime fit) and is REJECTED. Targets: OOS trades >= 100 (3-20/day), taker PF >= 1.3 @0.25 in
OOS AND >= 1.15 @0.25 in TRAIN, positive @0.30 taker, parameter plateau, no look-ahead.

HARD RULES: NO LOOK-AHEAD (roll_max/min causal; centered swings act only at >= j+k; any higher-TF
feature must align to the LAST COMPLETED bar; never index future bars). Absolute imports.
generate(b)->Signals, SIM=dict(), NAME, and TF=<seconds>.

RUN: ${PYTHON} -m bot.micro.runner <strat_path>   (last stdout line = JSON). Iterate 3-5 times.
`

phase('Build')
const survivors = []
const deadEnds = []

for (let r = 1; r <= ROUNDS; r++) {
  log(`=== M1 round ${r}/${ROUNDS} ===`)
  const learn = deadEnds.length ? `\nDEAD ENDS (don't repeat):\n- ${deadEnds.slice(-10).join('\n- ')}` : ''
  const win = survivors.length ? `\nWORKING (push further):\n- ${survivors.map(s => s.name + ': ' + (s.note || '')).slice(-5).join('\n- ')}` : ''

  const built = await pipeline(
    Array.from({ length: K }, (_, idx) => ({ idx, concept: CONCEPTS[(idx + r) % CONCEPTS.length] })),
    (item) => agent(
      `${CONTRACT}\n\nYOUR CONCEPT:\n${item.concept}\n${learn}${win}\n` +
      `Write bot/micro/strat_m1_r${r}_${item.idx}.py (set TF), run the runner, iterate to get the ` +
      `highest HONEST result that is positive at 0.25 taker in BOTH train and OOS. Report the EXACT ` +
      `runner JSON, OOS trade count, and the ~0.25-taker PF for BOTH train and OOS.`,
      { label: `build:r${r}.${item.idx}`, phase: 'Build', schema: BUILD_SCHEMA }
    ),
  )

  const promising = []
  for (const b of built.filter(Boolean)) {
    let m = null
    try { m = JSON.parse(b.runner_json) } catch (e) {}
    if (!b.built_ok || !m || !m.oos_spread_grid || !m.train_spread_grid) {
      deadEnds.push(`${b.name || 'unnamed'}: build/parse failed`); continue
    }
    const ot = ((m.oos_spread_grid['0.20'] || {}).taker || {}).pf || 0
    const ot30 = ((m.oos_spread_grid['0.30'] || {}).taker || {}).pf || 0
    const tt = ((m.train_spread_grid['0.20'] || {}).taker || {}).pf || 0
    const freq = m.oos.trades
    const tpd = m.oos.trades_per_day
    const edge = (ot >= 1.3) && (ot30 >= 1.0) && (tt >= 1.15)   // BOTH train & oos
    const freqOk = freq >= 100 && tpd >= 2.5 && tpd <= 25
    if (edge && freqOk) promising.push({ ...b, m, score: Math.min(ot, tt) * Math.min(freq, 600) })
    else deadEnds.push(`${b.name}: oos20t=${ot} oos30t=${ot30} train20t=${tt} N=${freq} t/d=${tpd} (edge=${edge} freq=${freqOk})`)
  }
  promising.sort((a, b) => b.score - a.score)
  log(`round ${r}: ${promising.length}/${K} passed triage (train+oos edge @0.25t, freq>=100)`)

  const verdicts = await pipeline(
    promising.slice(0, 4),
    (cand) => agent(
      `${CONTRACT}\n\nADVERSARIAL VERIFICATION — BREAK it (default REJECT):\n` +
      `  file: ${cand.path}\n  reported: ${cand.runner_json}\n\n` +
      `1. LOOK-AHEAD AUDIT line by line (future indexing? centered swing used early? higher-TF feature ` +
      `not aligned to last completed bar?). Fix & rerun if found.\n` +
      `2. REGIME ROBUSTNESS: this is the key test. Confirm taker PF@0.25 is positive in BOTH train AND ` +
      `oos. Then run it per-year (--train 2024-01:2024-12, then 2025, then 2026-01:2026-06) and confirm ` +
      `it is profitable at 0.25 taker in the MAJORITY of years, not just one regime.\n` +
      `3. PLATEAU: vary each key param +/-30%; PF@0.25t stable (not a spike)? Trade count stable?\n` +
      `4. Not driven by 1-2 outlier trades.\n` +
      `Report verdict; regime_robust=true ONLY if train+oos+majority-years all positive.`,
      { label: `verify:${cand.name}`, phase: 'Verify', schema: VERIFY_SCHEMA, effort: 'high' }
    ),
  )
  const top = promising.slice(0, 4)
  for (let j = 0; j < top.length; j++) {
    const v = verdicts[j]; if (!v) continue
    if ((v.verdict === 'PASS') || (v.verdict === 'PROMISING' && v.real_edge && !v.look_ahead_suspect && v.regime_robust)) {
      survivors.push({ name: top[j].name, path: top[j].path, runner_json: top[j].runner_json,
                       verdict: v.verdict, evidence: v.evidence, note: top[j].notes })
    } else {
      deadEnds.push(`${top[j].name}: verify=${v.verdict} la=${v.look_ahead_suspect} regime=${v.regime_robust}`)
    }
  }
  log(`round ${r}: survivors so far = ${survivors.length}`)
}

phase('Synthesize')
const summary = await agent(
  `${CONTRACT}\n\nSYNTHESIS. The M1/M5 loop ran ${ROUNDS} rounds. Verified survivors:\n` +
  `${JSON.stringify(survivors, null, 2)}\n\nDead ends:\n- ${deadEnds.slice(-30).join('\n- ')}\n\n` +
  `Append "Round 3 — M1/M5" to research/FINDINGS.md: (1) did any family produce a REGIME-ROBUST edge ` +
  `(positive at 0.25 taker in train AND oos AND majority of years) at 3-20/day? (2) a survivors table ` +
  `with train+oos+per-year PF at 0.25 taker, frequency, WR, maxDD; (3) which family carried the edge and ` +
  `why M1 worked where 5s did not; (4) the honest call on the user's 5-20/day + real-edge goal at M1, and ` +
  `the required live spread. If a regime-robust survivor exists, promote the best to ` +
  `bot/micro/EDGE_m1.py with a header documenting train/oos/per-year numbers, required live spread, the ` +
  `taker-deployability on FundingPips, and the deploy caveat (measure real spread first). Be truthful — ` +
  `a regime-robust 3-8/day real edge is a genuine WIN even if below 20/day and below 70% WR. Return a 6-8 sentence summary.`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'high' }
)

return { rounds: ROUNDS, k_per_round: K, survivors, dead_end_count: deadEnds.length, summary }
