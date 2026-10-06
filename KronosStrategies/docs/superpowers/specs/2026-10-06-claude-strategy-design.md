# Claude Strategy — design

Date: 2026-10-06 · Status: approved in chat, awaiting spec review

## 1. Intent

The operator wants a strategy named **"Claude Strategy"** in which a Claude Code session,
running permanently in a terminal on the second Mac **`reaper`**, reads XAUUSD and trades it
with discretionary ICT/SMC judgement. Per-day limits: **+$100 target, −$100 loss limit**. The
session must start on boot and pick up where it left off after a sudden closure.

Decisions taken with the operator (2026-10-06):

| Question | Answer |
|---|---|
| Account | **Winprofx-Demo** (UserBroker `43e48e58`, MT5 demo, meta acct `3eefc570`) — shared with S93 and both Neymar bots |
| Decision style | **Discretionary ICT read** by Claude each cycle |
| Risk per trade | **$25**, **one open trade at a time** |
| Architecture | **A — Claude decides on reaper, the box executes** via one locked-down SSH command |

Not a goal: proving an edge. There is no backtest for an LLM discretionary trader; this runs on a
demo account and is judged on its live journal.

## 2. Architecture

```
reaper (Mac, launchd at boot)                         kronos-backend box (15.252.166.251)
┌──────────────────────────────────────┐   ssh (forced   ┌───────────────────────────────────────┐
│ tmux "claude-strategy"               │   command,      │ authorized_keys: command="claude-gw"  │
│  run_loop.sh  (every 5 min, Mon-Fri  │   key only for  │   → docker exec kronos-s93_fvg_scalp-1 │
│   07:00-20:00 UTC)                   │   this)         │       python claude_trade.py <args>   │
│   └─ claude -p "<cycle prompt>"      │ ──────────────► │         ├─ guard (±$100, $25, 1 open)  │
│        allowed tools:                │                 │         ├─ place_entry(variation=     │
│          Bash(ssh kronos-claude *)   │ ◄────────────── │         │    "claude_strategy")       │
│          Read/Edit journal.md        │   JSON out      │         └─ close / status / market    │
│   memory: journal.md + DB state      │                 │ position_manager: TP/SL/TIME_EXIT      │
└──────────────────────────────────────┘                 │ strategy_manager: gating, kill-switch  │
                                                         └───────────────────────────────────────┘
```

reaper never holds broker or DB credentials. The only thing it can do on the box is run
`claude_trade.py` with arguments.

## 3. Components

### 3.1 Strategy rows — `strategies/db/deploy_claude_strategy.py`
Idempotent, dry-run by default, `--commit` to write (same pattern as `deploy_manager.py`).
- `apis_strategy` "Claude Strategy" + `apis_userstrategy` on Winprofx-Demo, `deployed=True`,
  `is_active=False` until armed.
- `apis_managedstrategy`: slot `discretionary`, policy `always_on`, `arm_mode` from env
  (default `OFF`), so the manager kill-switch / soft brake / master switch govern it like every
  other strategy.
- `entry_manager._VARIATION_STRATEGY_NAME["claude_strategy"] = "Claude Strategy"`.

### 3.2 Executor — `strategies/claude_trade.py` (runs on the box)
Runs inside the existing strategies image via `docker exec` (no new service). The target
container is a variable in `claude-gw` (default `kronos-s93_fvg_scalp-1`); if S93 is ever
stopped, point it at any running strategies-image container. Process env:
`RISK_PER_TRADE_USD=25` (module-level knob, so it does not affect other strategies) and
`DRY_RUN` inherited from a gateway flag. Every subcommand prints one JSON object.

| Subcommand | Does |
|---|---|
| `status` | today's realized + open P&L for this UserStrategy (USD, UTC day, via `_todays_realized_usd`), open position (side, entry, SL, TP, qty, open P&L), `can_trade` + reason, armed state |
| `market [--tf M1,M5,M15,H1] [--bars N]` | OANDA candles (existing `tsdb_reader` fetch, capped N≤300 per TF) + latest LTP |
| `open --side BUY\|SELL --sl X --tp Y --why "..."` | guard → `place_entry(EntrySignal(...), variation="claude_strategy")`; `why` stored as the signal reason/rationale |
| `close --why "..."` | closes this strategy's open position through the same path position_manager uses (zero position, cancel triggers, MetaAPI close) |

**Guard (the only place limits live; Claude cannot bypass it):**
1. `day_pnl = realized_today + open_pnl`. If `day_pnl >= +100` or `<= −100` → refuse `open`,
   and `status`/any call **closes the open position** and reports `day_locked`. The lock holds
   until 00:00 UTC.
2. At most **1** open position for this UserStrategy (`max_concurrent=1`).
3. SL and TP are mandatory, on the correct side of the entry, SL distance > 0; lot sized by the
   existing `_risk_sized_qty` with the $25 budget (rejects when even the min lot risks > budget).
4. A trade whose SL loss would push `day_pnl` below −100 is refused.
5. Manager gating, news blackout, spread, drift and duplicate gates in `place_entry` all apply
   unchanged.

SL/TP are also attached at the broker (existing `place_order` behaviour), so a dead reaper never
leaves an unprotected trade.

### 3.3 Gateway on the box
- A dedicated SSH key pair; the public key goes into `~ubuntu/.ssh/authorized_keys` with
  `command="/home/ubuntu/bin/claude-gw",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding`.
- `claude-gw` reads `$SSH_ORIGINAL_COMMAND`, allows only the four subcommands with a strict
  argument whitelist (numbers, `BUY|SELL`, quoted `--why` text ≤ 500 chars), then
  `docker exec` with fixed env. Anything else → exit 1 and logged.
- reaper `~/.ssh/config`: `Host kronos-claude` → 15.252.166.251, that key, `IdentitiesOnly yes`.

### 3.4 Session on reaper — `~/claude-strategy/`
- `CLAUDE.md` — the trading brief: role, ICT method (pointers to the vault notes
  [[ICT-SMC Glossary]], [[Entry Gates Reference]]), the cycle procedure, the limits, and "never
  trade without SL/TP; when unsure, skip".
- `journal.md` — Claude's persistent memory: current bias/narrative, levels being watched, open
  trade thesis, and a one-line entry per cycle. Trimmed by Claude to the last ~200 lines; full
  history is in `journal_archive/YYYY-MM-DD.md`.
- `run_loop.sh` — forever: if Mon–Fri 07:00–20:00 UTC, run one cycle, then sleep to the next
  5-minute boundary; outside hours it still calls `status` every 15 min (so a locked/closed day
  and any open trade are visible) but does not invoke Claude.
- One cycle = `claude -p "<cycle prompt>" --allowedTools "Bash(ssh kronos-claude:*)" "Read" "Edit(journal.md)" "Write(journal_archive/*)"`,
  timeout 4 min. The cycle prompt: read journal → `status` → if locked/unarmed stop → `market`
  → decide BUY / SELL / CLOSE / SKIP → act → append the journal line.
- **Crash recovery:** cycles are stateless — each run rebuilds its view from `journal.md` + the
  live `status`. A crash mid-cycle loses at most that cycle; the next one continues. `run_loop.sh`
  also exits non-zero on repeated failures so launchd restarts it.
- **Boot:** `~/Library/LaunchAgents/com.kronos.claude-strategy.plist`
  (`RunAtLoad`, `KeepAlive`) starts `tmux new-session -d -s claude-strategy run_loop.sh` if it
  isn't already running. Watch live: `ssh reaper` → `tmux attach -t claude-strategy`.
  LaunchAgents start at user login, so reaper needs **automatic login** enabled (or the operator
  logs in after a reboot) — flagged as a prerequisite.

## 4. Data flow of one trade

1. Cycle at 10:35 UTC: Claude reads the journal, `status` → flat, day −$12, `can_trade`.
2. `market` → M15 bullish displacement, unfilled FVG at 4131–4133.
3. `open --side BUY --sl 4127.5 --tp 4142 --why "M15 FVG retest after SSL sweep"`.
4. Guard: 1 open? no. SL risk at sized lot ≈ $25, worst-case day −$37 > −100 → pass →
   `place_entry` → Position/Order/Trigger rows + MetaAPI market order with broker SL/TP.
5. position_manager closes it at TP/SL; the dashboard shows it under "Claude Strategy".
6. Next cycles see the result via `status` and record it in the journal.

## 5. Error handling

| Failure | Behaviour |
|---|---|
| reaper asleep / offline / Claude crashes | no new trades; open trade protected by broker SL/TP + position_manager |
| SSH or box unreachable | cycle logs and skips; no retries that could double-place |
| `open` while a position exists | guard refuses (`open_position_cap`) |
| MetaAPI error on entry | existing `place_entry` rollback; signal row REJECTED with the reason |
| Claude asks for something odd (no SL, wrong side, huge size) | guard refuses with a reason Claude reads |
| Day limit reached | position closed, `day_locked` until 00:00 UTC |
| Manager kill-switch / master OFF | `place_entry` gating refuses; `status.armed=false` |

## 6. Testing

- `tests/test_claude_trade_guard.py` (pytest, in `tests/` per `pytest.ini`): ±$100 lock
  boundaries (99.99 / 100 / −100), open-P&L counted, SL-would-breach refusal, SL/TP side
  validation, $25 sizing, one-open cap. Guard is a pure function over (day_pnl, open position,
  request) so it is tested without a DB.
- `claude-gw` whitelist: a small shell test of allowed vs rejected command strings.
- Live: deploy with `arm_mode=PAPER` + gateway `DRY_RUN=true` for one full London+NY session;
  review the journal and signal rows; then the operator arms it LIVE.

## 7. Prerequisites and cost

- Claude Code installed and logged in on reaper (it is **not** on reaper's PATH as of 2026-10-06).
- reaper: keep "prevent sleep" on; enable automatic login for unattended reboots.
- Cost: ~156 cycles per trading day (13 h × 12) of one `claude -p` turn each.

## 8. Rollout

1. Code + tests (box executor, gateway, deploy script, reaper files) — committed in the monorepo
   (`KronosStrategies/strategies/claude_trade.py`, `KronosStrategies/claude_strategy/` for the
   reaper-side files).
2. Box: scp + rebuild the strategies image used for `docker exec`; install `claude-gw` + key.
3. `deploy_claude_strategy.py --commit` with `arm_mode=PAPER`.
4. reaper: install Claude Code, copy `claude_strategy/` to `~/claude-strategy/`, load the
   LaunchAgent, verify a dry-run session.
5. Operator flips to LIVE on the /manager tab. Vault: new note `20 Strategies/Claude Strategy.md`,
   Live Roster + Timeline rows.
