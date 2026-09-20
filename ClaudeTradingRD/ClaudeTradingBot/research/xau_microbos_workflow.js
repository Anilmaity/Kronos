export const meta = {
  name: 'xau-microbos-frequency',
  description: 'Deepen the proven micro-BOS continuation edge: raise frequency to >=100 OOS trades while holding PF>=1.3 at 0.25 taker spread; adversarially verify',
  phases: [
    { title: 'Build' },
    { title: 'Verify' },
    { title: 'Synthesize' },
  ],
}

const ROUNDS = (args && args.rounds) || 3
const K = (args && args.k) || 6
const PYTHON = '.venv/Scripts/python.exe'

// Frequency-expansion levers — each build slot attacks the ~1/day ceiling a different way,
// WITHOUT killing the edge. The base signal (bot/micro/strat_r3_1.py) is proven; broaden it.
const LEVERS = [
  'MULTI-SCALE structure: run the micro-BOS detector at several LOOKBACKs at once (e.g. 40/80/160 S5 bars) and/or on M1 AND M5 resampled bars, unioning the signals. More independent break contexts -> more trades, same logic.',
  'RE-ARM within a leg: the base takes only the FRESH break edge (one signal per leg). Allow a new continuation entry on each further displacement extension or each fresh higher-low (long) while the leg and EMA-bias persist, with cooldown to avoid clustering.',
  'LOOSEN the gate, keep the edge: sweep K_DISP down (1.2-1.8), RETR (0.15-0.45), ATR band and session width; find the LOOSEST gate that still holds PF>=1.3 at 0.25 taker. Map the frequency<->PF frontier explicitly.',
  'BOTH-SIDES symmetry: ensure the short-continuation side is as productive as the long side across the 2025-26 chop/down legs (round-1 triggers were trend-skewed). Balance long/short so range regimes also produce trades.',
  'RETEST family: vary the entry mechanic — limit at retest (base), limit at the broken level itself (breaker retest), or a second-chance limit deeper in the leg — and combine the most productive that keep PF>=1.3 at 0.25 taker.',
  'SESSION-localised stacking: treat London-open and NY-open as separate engines with their own params; a continuation that fires in BOTH sessions roughly doubles daily count. Add the late-US/Asian momentum window only if it holds the edge.',
]

const BUILD_SCHEMA = {
  type: 'object',
  required: ['path', 'name', 'built_ok', 'runner_json', 'oos_trades', 'pf_025_taker', 'notes'],
  properties: {
    path: { type: 'string' },
    name: { type: 'string' },
    built_ok: { type: 'boolean' },
    runner_json: { type: 'string', description: 'EXACT stdout JSON from the runner (has oos + oos_spread_grid)' },
    oos_trades: { type: 'number', description: 'OOS trade count' },
    pf_025_taker: { type: 'number', description: 'interpolated/closest PF at ~0.25 spread, taker mode, from the spread grid' },
    notes: { type: 'string', description: 'what lever you applied, the frequency<->edge tradeoff you found' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['name', 'real_edge', 'look_ahead_suspect', 'plateau_ok', 'freq_ok', 'verdict', 'evidence'],
  properties: {
    name: { type: 'string' },
    real_edge: { type: 'boolean' },
    look_ahead_suspect: { type: 'boolean' },
    plateau_ok: { type: 'boolean' },
    freq_ok: { type: 'boolean', description: 'OOS trades >= 100 and 3-25/day?' },
    verdict: { type: 'string', enum: ['PASS', 'PROMISING', 'REJECT'] },
    evidence: { type: 'string' },
  },
}

const CONTRACT = `
cwd = C:\\Projects\\ClaudeProjects\\ClaudeTradingBot. Python = ${PYTHON} (numpy only).
Real OANDA 5s XAU bid/ask cached under reports/s5/ (30 months). Use bash.

REQUIRED READING:
  research/GOAL.md            - esp. the "UPDATE (post round-1)" section + round-2 acceptance
  research/SCOUT_FINDINGS.md  - the cost floor + where asymmetry lives
  bot/micro/strat_r3_1.py     - THE PROVEN BASE you start from (micro-BOS continuation,
                                clean/no-look-ahead, PF 1.85 cost-free, PF 1.33 taker @0.20,
                                but only ~1.1 trades/day). COPY it and broaden it.
  bot/micro/engine.py, bot/micro/features.py - the API (Bars, Signals, simulate, resample, ema, atr, roll_max/min)

THE MISSION: keep the micro-BOS continuation EDGE while RAISING FREQUENCY from ~1/day to
the 3-25/day band (OOS trades >= 100). Edge is judged at REALISTIC spread, not 0.66:
the runner now prints "oos_spread_grid" with maker & taker PF/net at 0.20 and 0.30. Your
target: PF >= 1.3 at 0.25 taker (read 0.20 & 0.30 taker and judge ~0.25), positive at 0.30
taker, and OOS trades >= 100. Frequency that DESTROYS the edge is failure; report the
honest frequency<->PF frontier you find.

HARD RULES (unchanged): NO LOOK-AHEAD (roll_max/min causal; swings centered -> act only at
>= j+k; M1/M5 features must align to the LAST COMPLETED bar like _m1_atr_aligned does;
never index future bars). Absolute imports. generate(b)->Signals, SIM=dict(), NAME.

RUN IT: ${PYTHON} -m bot.micro.runner <your_strat_path>   (last stdout line = JSON).
Iterate 3-5 internal attempts to push frequency up while holding PF>=1.3 @0.25 taker.
`

phase('Build')
const survivors = []
const deadEnds = []

for (let r = 1; r <= ROUNDS; r++) {
  log(`=== micro-BOS round ${r}/${ROUNDS} ===`)
  const learn = deadEnds.length
    ? `\nPRIOR DEAD ENDS (don't repeat):\n- ${deadEnds.slice(-10).join('\n- ')}` : ''
  const win = survivors.length
    ? `\nWORKING SO FAR (push further / combine):\n- ${survivors.map(s => s.name + ': ' + (s.note || '')).slice(-5).join('\n- ')}` : ''

  const built = await pipeline(
    Array.from({ length: K }, (_, idx) => ({ idx, lever: LEVERS[(idx + r) % LEVERS.length] })),
    (item) => agent(
      `${CONTRACT}\n\nYOUR FREQUENCY LEVER for this candidate:\n${item.lever}\n${learn}${win}\n` +
      `Write bot/micro/strat_mb_r${r}_${item.idx}.py, run the runner, iterate to maximise OOS ` +
      `trade count SUBJECT TO PF>=1.3 at 0.25 taker and positive at 0.30 taker. Report the EXACT ` +
      `runner JSON, the OOS trade count, and the ~0.25 taker PF.`,
      { label: `build:r${r}.${item.idx}`, phase: 'Build', schema: BUILD_SCHEMA }
    ),
  )

  const promising = []
  for (const b of built.filter(Boolean)) {
    let m = null
    try { m = JSON.parse(b.runner_json) } catch (e) {}
    if (!b.built_ok || !m || !m.oos_spread_grid) {
      deadEnds.push(`${b.name || 'unnamed'}: build/parse failed`)
      continue
    }
    const g = m.oos_spread_grid
    const t20 = (g['0.20'] && g['0.20'].taker) || {}
    const t30 = (g['0.30'] && g['0.30'].taker) || {}
    const freq = m.oos.trades
    const edge = (t20.pf >= 1.3) && (t30.pf >= 1.0)
    const freqOk = freq >= 80 && m.oos.trades_per_day >= 2.5 && m.oos.trades_per_day <= 28
    if (edge && freqOk) {
      promising.push({ ...b, m, score: (t30.pf || 0) * Math.min(freq, 400) })
    } else {
      deadEnds.push(`${b.name}: t20pf=${t20.pf} t30pf=${t30.pf} oosN=${freq} t/d=${m.oos.trades_per_day} (edge=${edge} freq=${freqOk})`)
    }
  }
  promising.sort((a, b) => b.score - a.score)
  log(`round ${r}: ${promising.length}/${K} passed triage (edge@0.25taker + freq>=80)`)

  const verdicts = await pipeline(
    promising.slice(0, 4),
    (cand) => agent(
      `${CONTRACT}\n\nADVERSARIAL VERIFICATION — try to BREAK this candidate (default REJECT):\n` +
      `  file: ${cand.path}\n  name: ${cand.name}\n  reported: ${cand.runner_json}\n\n` +
      `1. LOOK-AHEAD AUDIT: read ${cand.path} line by line. Any future-indexing? Any centered swing used ` +
      `before +k? Any M1/M5 feature not aligned to the last COMPLETED bar? Fix & rerun if found.\n` +
      `2. PLATEAU: vary each key param +/-30% one at a time, rerun the runner; is PF@0.25-taker stable ` +
      `(>=1.2 across the range) or a fragile spike? Is OOS trade count stable >=80?\n` +
      `3. EDGE@REALISTIC SPREAD: confirm oos_spread_grid taker PF>=1.3 @0.20 and >=1.0 @0.30, and that ` +
      `it degrades gracefully (not a cliff). Confirm it is not driven by 1-2 outlier trades.\n` +
      `Report verdict with the swept numbers.`,
      { label: `verify:${cand.name}`, phase: 'Verify', schema: VERIFY_SCHEMA, effort: 'high' }
    ),
  )
  const top = promising.slice(0, 4)
  for (let j = 0; j < top.length; j++) {
    const v = verdicts[j]; if (!v) continue
    if ((v.verdict === 'PASS') || (v.verdict === 'PROMISING' && v.real_edge && !v.look_ahead_suspect && v.freq_ok)) {
      survivors.push({ name: top[j].name, path: top[j].path, runner_json: top[j].runner_json,
                       verdict: v.verdict, evidence: v.evidence, note: top[j].notes })
    } else {
      deadEnds.push(`${top[j].name}: verify=${v.verdict} la=${v.look_ahead_suspect} plateau=${v.plateau_ok} freq=${v.freq_ok}`)
    }
  }
  log(`round ${r}: survivors so far = ${survivors.length}`)
}

phase('Synthesize')
const summary = await agent(
  `${CONTRACT}\n\nSYNTHESIS. The micro-BOS frequency-expansion loop ran ${ROUNDS} rounds. ` +
  `Verified survivors:\n${JSON.stringify(survivors, null, 2)}\n\nDead ends:\n- ${deadEnds.slice(-30).join('\n- ')}\n\n` +
  `Append a "Round 2 — micro-BOS frequency" section to research/FINDINGS.md covering: (1) did any ` +
  `variant reach >=100 OOS trades / 3-25 per day while holding PF>=1.3 at 0.25 taker? (2) the explicit ` +
  `frequency<->PF frontier (how PF@0.25taker fell as trade count rose); (3) the single best deployable-` +
  `candidate file + its full spread grid + the live-spread it REQUIRES to be profitable; (4) honest call ` +
  `on whether the user's 5-20/day goal is reachable with a real edge, or whether ~1-5/day is the true ` +
  `ceiling. If the best survivor is taker-positive at <=0.25 spread, promote it to bot/micro/EDGE_microbos.py ` +
  `with a header documenting the required live spread + the deploy caveat. Return a 5-7 sentence summary.`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'high' }
)

return { rounds: ROUNDS, k_per_round: K, survivors, dead_end_count: deadEnds.length, summary }
