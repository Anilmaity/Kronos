export const meta = {
  name: 'xau-micro-edge',
  description: 'Autonomous loop: design/build/backtest XAU 5s microstructure strategies, adversarially verify survivors, iterate toward the acceptance bar',
  phases: [
    { title: 'Build' },
    { title: 'Verify' },
    { title: 'Synthesize' },
  ],
}

// ---- config (override via args) ----
const ROUNDS = (args && args.rounds) || 3
const K = (args && args.k) || 6
const PYTHON = '.venv/Scripts/python.exe'

// Diverse ICT/microstructure concept lenses. Each build agent owns one.
const CONCEPTS = [
  'Liquidity-sweep reversal: price wicks beyond a recent swing high/low (stop hunt) then closes back inside; fade it. The whole game is FILTERING to high-quality sweeps (session, displacement into the level, equal-highs cluster, volume spike on the wick).',
  'FVG fill in HTF bias: detect a fair-value-gap on a higher TF (M1/M5 via features.resample), only take fills in the direction of an HTF EMA bias; enter on a limit at the gap, target the displacement origin.',
  'Asian-range AMD: build the Asian session range (00-07 UTC), trade the London manipulation — a sweep of the Asian high/low followed by reversion back into the range (classic accumulation->manipulation->distribution).',
  'Volume-spike absorption: a 5s bar with volume >> rolling mean that fails to extend price (absorption) at a liquidity level; fade the exhaustion.',
  'Micro-BOS continuation: a displacement break of micro-structure (close beyond last N-bar extreme by >k*ATR) followed by a shallow retrace; enter continuation on the retest, not the breakout.',
  'Equal-highs/lows raid: cluster of equal highs or lows (within 0.1*ATR) forms a liquidity pool; trade the raid-and-reverse when price sweeps the cluster and rejects.',
]

const BUILD_SCHEMA = {
  type: 'object',
  required: ['path', 'name', 'built_ok', 'runner_json', 'notes'],
  properties: {
    path: { type: 'string', description: 'relative path to the strategy .py written' },
    name: { type: 'string' },
    built_ok: { type: 'boolean', description: 'true if the runner executed and returned metrics' },
    runner_json: { type: 'string', description: 'EXACT stdout JSON line from the runner (empty string if it failed)' },
    notes: { type: 'string', description: 'one-paragraph: the precise rules used + what the metrics say' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['name', 'real_edge', 'look_ahead_suspect', 'plateau_ok', 'verdict', 'evidence'],
  properties: {
    name: { type: 'string' },
    real_edge: { type: 'boolean', description: 'after adversarial checks, is the OOS edge real?' },
    look_ahead_suspect: { type: 'boolean' },
    plateau_ok: { type: 'boolean', description: 'profitable across +/-30% on key params?' },
    verdict: { type: 'string', enum: ['PASS', 'PROMISING', 'REJECT'] },
    evidence: { type: 'string', description: 'numbers from the param sweep + OOS + look-ahead audit' },
  },
}

const CONTRACT = `
You are working in C:\\Projects\\ClaudeProjects\\ClaudeTradingBot (the cwd). Use bash.
Python is ${PYTHON} (numpy only; NO pandas). Real OANDA 5-second XAU bid/ask data is
cached as monthly .npz under reports/s5/ (loaded via bot.oanda_s5.load).

REQUIRED READING before coding (Read these files):
  research/GOAL.md            - the goal, honesty rules, acceptance bar
  research/SCOUT_FINDINGS.md  - measured intel: why naive triggers are dead, where the edge could live
  bot/micro/engine.py         - Bars, Signals, simulate, atr, roll_max/min  (the API)
  bot/micro/features.py       - resample, swings, fvg, sessions, hours_mask, ema
  bot/micro/strat_ref_sweep.py - a WORKING template you copy & edit

THE CONTRACT — your strategy module MUST expose:
  generate(b: Bars) -> Signals     # CAUSAL: only use info up to bar i's close
  SIM  = dict(...)                 # kwargs for engine.simulate (commission=0.07, maxhold, cooldown, trail_pts, be_at_pts)
  NAME = "short_label"
Use absolute imports: from bot.micro.engine import ...

HARD RULES (violating these makes the result worthless):
  - NO LOOK-AHEAD. roll_max/roll_min are already causal (exclude current bar). swings()
    is CENTERED - if you use a swing at index j you may only act at index >= j+k.
    Never index future bars in generate().
  - Spread is REAL (paid via bid/ask in the data). A tiny target cannot beat a 0.66pt
    median spread - your edge must capture a move materially larger than the spread,
    OR use limit (maker) entries (kind=1) that earn the spread.
  - Keep trades/day in roughly 3-25. Thousands of trades = you are trading noise.

RUN IT and capture the JSON:
  ${PYTHON} -m bot.micro.runner <your_strat_path>
The last stdout line is a JSON object with train/oos/oos_stress metrics. Put that EXACT
line in runner_json. If it errors, fix your code and rerun (do not give up after one try).
`

phase('Build')

const allSurvivors = []
const deadEnds = []

for (let r = 1; r <= ROUNDS; r++) {
  log(`=== ROUND ${r}/${ROUNDS} — building ${K} candidates ===`)

  const learn = deadEnds.length
    ? `\nPRIOR DEAD ENDS (do NOT repeat these; go a different direction):\n- ${deadEnds.slice(-12).join('\n- ')}`
    : ''
  const win = allSurvivors.length
    ? `\nWHAT IS WORKING SO FAR (build on / differentiate from these):\n- ${allSurvivors.map(s => s.name + ': ' + (s.note || '')).slice(-6).join('\n- ')}`
    : ''

  // BUILD: each slot a distinct concept (rotate so later rounds revisit with learnings)
  const built = await pipeline(
    Array.from({ length: K }, (_, idx) => ({ idx, concept: CONCEPTS[(idx + r) % CONCEPTS.length] })),
    (item) => agent(
      `${CONTRACT}\n\nYOUR ASSIGNED CONCEPT for this candidate:\n${item.concept}\n${learn}${win}\n` +
      `Design ONE precise, fully-specified variant of this concept, write it to ` +
      `bot/micro/strat_r${r}_${item.idx}.py, run the runner, and report. Iterate on your ` +
      `own filters/params (2-4 internal attempts) to get the best HONEST OOS result you can ` +
      `before reporting. Prioritise: positive OOS net after the 1.5x stress pass, PF>=1.3, ` +
      `trades/day 3-25, and the highest win rate achievable WITHOUT look-ahead.`,
      { label: `build:r${r}.${item.idx}`, phase: 'Build', schema: BUILD_SCHEMA }
    ),
  )

  // TRIAGE (plain code) — parse metrics, keep the promising, record dead ends
  const promising = []
  for (const b of built.filter(Boolean)) {
    let m = null
    try { m = JSON.parse(b.runner_json) } catch (e) { m = null }
    if (!b.built_ok || !m || !m.oos) {
      deadEnds.push(`${b.name || 'unnamed'}: build/parse failed or no OOS`)
      continue
    }
    const o = m.oos, s = m.oos_stress || {}
    const score = (o.pf || 0) * (o.net$ > 0 ? 1 : 0.3)
    const ok = (o.net$ > 0) && (o.pf >= 1.2) && (o.trades >= 60) &&
               (o.trades_per_day >= 2.5) && (o.trades_per_day <= 28) &&
               ((s.net$ === undefined) || s.net$ > 0)
    if (ok) {
      promising.push({ ...b, m, score })
    } else {
      deadEnds.push(`${b.name}: OOS pf=${o.pf} net=${o.net$} t/d=${o.trades_per_day} stress=${s.net$} (below bar)`)
    }
  }
  promising.sort((a, b) => b.score - a.score)
  log(`round ${r}: ${promising.length}/${K} candidates passed triage`)

  // VERIFY (adversarial) — top survivors only
  const top = promising.slice(0, 4)
  const verdicts = await pipeline(
    top,
    (cand) => agent(
      `${CONTRACT}\n\nADVERSARIAL VERIFICATION. A candidate strategy claims an OOS edge:\n` +
      `  file: ${cand.path}\n  name: ${cand.name}\n  reported OOS+stress metrics: ${cand.runner_json}\n\n` +
      `Your job is to BREAK it. Default to REJECT unless it genuinely survives:\n` +
      `1. AUDIT FOR LOOK-AHEAD: read ${cand.path} line by line. Does generate() ever use a swing/level/` +
      `feature whose value is only known in the future? Does it index bars > i? Re-run after fixing any leak.\n` +
      `2. PARAMETER PLATEAU: edit each key param +/-30% (one at a time), re-run the runner each time. Is OOS ` +
      `net still positive across the range, or is it a single fragile spike?\n` +
      `3. OOS HONESTY: confirm the 1.5x-cost stress OOS pass is still net>0.\n` +
      `Report verdict with the actual swept numbers as evidence.`,
      { label: `verify:${cand.name}`, phase: 'Verify', schema: VERIFY_SCHEMA, effort: 'high' }
    ),
  )

  for (let j = 0; j < top.length; j++) {
    const v = verdicts[j]
    if (!v) continue
    if (v.verdict === 'PASS' || (v.verdict === 'PROMISING' && v.real_edge && !v.look_ahead_suspect)) {
      allSurvivors.push({ name: top[j].name, path: top[j].path, runner_json: top[j].runner_json,
                          verdict: v.verdict, evidence: v.evidence, note: top[j].notes })
    } else {
      deadEnds.push(`${top[j].name}: verify=${v.verdict} lookahead=${v.look_ahead_suspect} (${(v.evidence||'').slice(0,120)})`)
    }
  }
  log(`round ${r}: total survivors so far = ${allSurvivors.length}`)
}

// SYNTHESIZE — write the findings report + summarize (agent has fs access)
phase('Synthesize')
const survJson = JSON.stringify(allSurvivors, null, 2)
const summary = await agent(
  `${CONTRACT}\n\nSYNTHESIS. The microstructure research loop finished ${ROUNDS} rounds. ` +
  `Verified survivors (may be empty):\n${survJson}\n\nDead ends this run:\n- ${deadEnds.slice(-30).join('\n- ')}\n\n` +
  `Write research/FINDINGS.md with: (1) the honest verdict — did anything clear the acceptance bar in ` +
  `research/GOAL.md, and how close to the 70-90%WR / 1-2%DD stretch target; (2) a table of survivors with ` +
  `their OOS metrics; (3) what categorically failed and why (tie back to the 0.66pt spread reality); ` +
  `(4) the single most promising direction to pursue next. Keep the best survivor strategy files in place ` +
  `and list their paths. Be truthful — "no robust edge found yet" is a valid, valuable finding. ` +
  `Return a 4-6 sentence executive summary.`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'high' }
)

return {
  rounds: ROUNDS, k_per_round: K,
  survivors: allSurvivors,
  dead_end_count: deadEnds.length,
  summary,
}
