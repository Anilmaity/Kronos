# Claude Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Claude Code session on `reaper` trades XAUUSD on Winprofx-Demo as the strategy "Claude Strategy", with the ±$100/day, $25/trade, one-open limits enforced on the production box.

**Architecture:** Claude decides on reaper (a `claude -p` cycle every 5 min inside tmux, started by launchd, memory in `journal.md`). It reaches the box only through an SSH key whose forced command (`claude-gw`) allows four `claude_trade.py` subcommands. `claude_trade.py` runs inside the existing strategies container, checks the pure `claude_guard` limits, and trades through the existing `entry_manager.place_entry`, so manager gating, position_manager exits and the dashboard all work unchanged.

**Tech Stack:** Python 3.12, SQLAlchemy mirror (`shared.models`), pytest, bash, launchd, tmux, Claude Code CLI.

**Spec:** `KronosStrategies/docs/superpowers/specs/2026-10-06-claude-strategy-design.md`

## Global Constraints

- Strategy name `Claude Strategy`, variation tag `claude_strategy`, account Winprofx-Demo (meta acct `3eefc570…`), symbol `XAU_USD`.
- Day target **+$100**, day loss limit **−$100** (realized + open, UTC day), risk **$25** per trade, **one** open trade.
- SL and TP mandatory on every trade; a trade whose stop would take the day below −$100 is refused.
- Session cadence: every 5 min, Mon–Fri 07:00–20:00 UTC.
- Compose project name **`-p kronos`** on the box, always. Box code is baked into images → rebuild.
- reaper never holds broker/DB credentials; its key can only run `claude-gw`.
- `arm_mode=PAPER` ⇒ `DRY_RUN=true` for the executor; first rollout is PAPER.

## Review Focus

1. Unquoted multi-word `--why` from `ssh kronos-claude open … --why M15 FVG retest` — must arrive as one reason, not fail. (Task 3 test `test_why_takes_rest_of_line`.)
2. Day P&L exactly at the edges (−100.00 / +100.00 / 99.99) — lock exactly at the limit. (Task 1 tests.)
3. A stop so tight the lot would explode, or so wide even 0.01 lot risks > $25 — refused. (Task 1 tests.)
4. Lot rounding: 25/(dist·100) landing on x.999… must not floor one step low. (Task 1 `test_size_lots_float_edge`.)
5. Shell metacharacters in the command (`; rm`, `$(…)`, backticks) — rejected or passed as inert text, never executed. (Task 3 test `test_injection_is_inert`.)

---

### Task 1: Pure risk guard

**Files:**
- Create: `KronosStrategies/strategies/claude_guard.py`
- Test: `KronosStrategies/tests/test_claude_guard.py`

**Interfaces:**
- Produces: `day_lock(day_pnl_usd: float) -> str | None`; `size_lots(sl_dist_pts: float, max_lot: float) -> float | None`; `check_open(side, entry, sl, tp, day_pnl_usd, has_open, max_lot) -> tuple[float | None, str]`; constants `DAY_TARGET_USD`, `DAY_LOSS_USD`, `RISK_PER_TRADE_USD`, `MIN_SL_PTS`.

- [ ] **Step 1: Write the failing tests**

```python
"""Claude Strategy guard — the limits the Claude session trades under."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "strategies"))

import pytest

import claude_guard as g


@pytest.mark.parametrize("pnl,want", [
    (0.0, None), (99.99, None), (100.0, "target_hit"), (250.0, "target_hit"),
    (-99.99, None), (-100.0, "loss_limit_hit"), (-180.0, "loss_limit_hit"),
])
def test_day_lock_edges(pnl, want):
    assert g.day_lock(pnl) == want


def test_size_lots_risks_at_most_budget():
    assert g.size_lots(5.0, 0.10) == 0.05            # 0.05 * 5 * 100 = 25
    assert g.size_lots(2.0, 0.10) == 0.10            # 0.125 capped by MAX_LOT
    assert g.size_lots(30.0, 0.10) is None           # 0.01 lot risks 30 > 25


def test_size_lots_float_edge():
    # 25 / (25/29 * 100) = 0.29 exactly in theory; float gives 0.2899999…
    assert g.size_lots(25 / 29, 1.0) == 0.29


def test_check_open_ok_buy_and_sell():
    lots, why = g.check_open("BUY", 4130.0, 4125.0, 4140.0, 0.0, False, 0.10)
    assert lots == 0.05 and why.startswith("ok")
    lots, _ = g.check_open("SELL", 4130.0, 4135.0, 4120.0, -40.0, False, 0.10)
    assert lots == 0.05


@pytest.mark.parametrize("side,sl,tp,reason", [
    ("BUY", 4135.0, 4140.0, "bad_levels"),      # SL above entry on a buy
    ("BUY", 4125.0, 4132.0, "ok"),              # small RR is allowed
    ("SELL", 4125.0, 4120.0, "bad_levels"),     # SL below entry on a sell
    ("HOLD", 4125.0, 4140.0, "bad_side"),
    ("BUY", 4129.5, 4140.0, "sl_too_tight"),
    ("BUY", 4095.0, 4200.0, "sl_too_wide"),
])
def test_check_open_level_validation(side, sl, tp, reason):
    lots, why = g.check_open(side, 4130.0, sl, tp, 0.0, False, 0.10)
    assert why.startswith(reason)
    assert (lots is None) == (reason != "ok")


def test_check_open_one_trade_and_day_lock():
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, 0.0, True, 0.10)[1].startswith("open_position_cap")
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, 100.0, False, 0.10)[1] == "day_locked:target_hit"
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -100.0, False, 0.10)[1] == "day_locked:loss_limit_hit"


def test_check_open_refuses_breaching_the_loss_limit():
    # day -80, $25 at risk -> worst -105 -> refused; day -75 -> worst exactly -100 -> allowed
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -80.0, False, 0.10)[1].startswith("would_breach")
    assert g.check_open("BUY", 4130.0, 4125.0, 4140.0, -75.0, False, 0.10)[0] == 0.05
```

- [ ] **Step 2: Run to verify failure** — `cd KronosStrategies && .venv/bin/python -m pytest tests/test_claude_guard.py -q` → FAIL `ModuleNotFoundError: claude_guard`.

- [ ] **Step 3: Implement**

```python
"""Claude Strategy risk guard — pure functions, no DB, no broker.

Every limit the Claude session trades under lives here; claude_trade.py calls
check_open() before any order and day_lock() on every call. The session on
reaper cannot change these — they run on the box.
Spec: docs/superpowers/specs/2026-10-06-claude-strategy-design.md §3.2
"""
from __future__ import annotations

DAY_TARGET_USD = 100.0
DAY_LOSS_USD = 100.0
RISK_PER_TRADE_USD = 25.0
MIN_SL_PTS = 1.0            # tighter than this is spread noise on gold
USD_PER_PT_PER_LOT = 100.0  # XAU_USD: $1 move x 1 lot = $100
MIN_LOT = 0.01


def day_lock(day_pnl_usd: float) -> str | None:
    """'target_hit' / 'loss_limit_hit' once the UTC day is done, else None."""
    if day_pnl_usd >= DAY_TARGET_USD:
        return "target_hit"
    if day_pnl_usd <= -DAY_LOSS_USD:
        return "loss_limit_hit"
    return None


def size_lots(sl_dist_pts: float, max_lot: float) -> float | None:
    """Lots risking at most RISK_PER_TRADE_USD at the stop; None if even MIN_LOT risks more."""
    raw = RISK_PER_TRADE_USD / (sl_dist_pts * USD_PER_PT_PER_LOT)
    steps = int(round(raw / MIN_LOT, 6))   # round first: 0.29/0.01 is 28.999…
    if steps < 1:
        return None
    return round(min(max_lot, steps * MIN_LOT), 2)


def check_open(side: str, entry: float, sl: float, tp: float,
               day_pnl_usd: float, has_open: bool, max_lot: float) -> tuple[float | None, str]:
    """(lots, reason) for a requested market entry; lots=None means refuse."""
    lock = day_lock(day_pnl_usd)
    if lock:
        return None, f"day_locked:{lock}"
    if has_open:
        return None, "open_position_cap: one trade at a time"
    side = side.upper()
    if side == "BUY":
        levels_ok = sl < entry < tp
    elif side == "SELL":
        levels_ok = tp < entry < sl
    else:
        return None, f"bad_side: {side}"
    if not levels_ok:
        return None, f"bad_levels: {side} needs SL and TP on opposite sides of entry {entry:.2f}"
    dist = abs(entry - sl)
    if dist < MIN_SL_PTS:
        return None, f"sl_too_tight: {dist:.2f} pts < {MIN_SL_PTS}"
    lots = size_lots(dist, max_lot)
    if lots is None:
        return None, (f"sl_too_wide: {MIN_LOT} lot risks "
                      f"{MIN_LOT * dist * USD_PER_PT_PER_LOT:.2f} USD > {RISK_PER_TRADE_USD:.0f}")
    risk = lots * dist * USD_PER_PT_PER_LOT
    worst = day_pnl_usd - risk
    if worst < -DAY_LOSS_USD:
        return None, f"would_breach_loss_limit: worst case day {worst:.2f} USD"
    return lots, f"ok: {lots} lots, risk {risk:.2f} USD"
```

- [ ] **Step 4: Run tests** → all PASS.
- [ ] **Step 5: Commit** `feat(strategies): Claude Strategy risk guard`.

### Task 2: Executor `claude_trade.py` + variation tag + deploy script

**Files:**
- Create: `KronosStrategies/strategies/claude_trade.py`
- Create: `KronosStrategies/strategies/db/deploy_claude_strategy.py`
- Modify: `KronosStrategies/strategies/strategy/entry_manager.py` (`_VARIATION_STRATEGY_NAME`: add `"claude_strategy": "Claude Strategy"`)
- Test: `KronosStrategies/tests/test_claude_trade_cli.py`

**Interfaces:**
- Consumes: `claude_guard.check_open/day_lock/RISK_PER_TRADE_USD`; `entry_manager.place_entry(signal, symbol, variation, max_concurrent)`, `entry_manager._todays_realized_usd(sess, us_ids)`, `entry_manager.MAX_LOT`; `shared.tsdb_reader.fetch_candles(tf, days, symbol)` (DataFrame `time,open,high,low,close,volume`), `fetch_latest_ltp(symbol)`; `deploy_manager._ensure_strategy/_ensure_user_strategy/_ensure_managed`.
- Produces: CLI `python claude_trade.py status|market|open|close …` → one JSON object on stdout; `build_parser()` for tests.

Executor behaviour (code written in the task):
- Reads the Claude Strategy UserStrategy + ManagedStrategy arm_mode first; PAPER sets `DRY_RUN=true`; always sets `RISK_PER_TRADE_USD=25`; only then imports `entry_manager` (whose broker client reads `DRY_RUN` at import).
- `status`: realized today + open P&L, open position (side/entry/lots/SL/TP), `day_locked`, `armed`, `can_trade`. If locked with a position open → requests a close.
- `market`: `--tf` (default `5m,15m,1h`), `--bars` (default 120, max 300) → `[[iso_time, o, h, l, c], …]` per TF + `ltp`.
- `open`: refuses when not armed; guard on `entry = fetch_latest_ltp()`; `place_entry(EntrySignal(..., reason="CLAUDE: "+why[:190]), variation="claude_strategy", max_concurrent=1)`; reports the StrategySignal status / rejection reason and the position.
- `close`: adds a `CUSTOM`/`TIME_EXIT` trigger with an already-expired epoch → position_manager closes it through its normal path within ~1 s; waits up to 20 s for `quantity == 0`.

- [ ] Step 1: test `build_parser()` accepts the four subcommands and rejects a bad side (`SystemExit`).
- [ ] Step 2: run → FAIL (module missing).
- [ ] Step 3: implement `claude_trade.py`, add the variation tag, write `deploy_claude_strategy.py` (reuses `deploy_manager` helpers; binds to the UserBroker whose `meta_account_id` starts with `3eefc570`; slot `discretionary`, policy `always_on`; arm from `MANAGER_ARM_MODE`, dry-run unless `--commit`).
- [ ] Step 4: full suite `pytest tests -q` passes.
- [ ] Step 5: commit `feat(strategies): Claude Strategy executor + deploy script`.

### Task 3: SSH gateway `claude-gw`

**Files:**
- Create: `KronosStrategies/claude_strategy/claude_gw.py` (installed on the box as `/home/ubuntu/bin/claude-gw`)
- Test: `KronosStrategies/tests/test_claude_gw.py`

**Interfaces:**
- Produces: `parse(raw: str) -> list[str]` (raises `ValueError`); `main()` execs `docker exec <container> python claude_trade.py <argv>` (list form, no shell).

Rules: subcommands `status`, `market [--tf T[,T]] [--bars N≤300]`, `open --side BUY|SELL --sl NUM --tp NUM --why TEXT`, `close --why TEXT`. Everything after ` --why ` is the reason (≤500 chars, outer quotes stripped). Container from `CLAUDE_GW_CONTAINER` (default `kronos-s93_fvg_scalp-1`). Every call logged to `~/claude-gw.log` as ALLOW/DENY.

- [ ] Step 1: tests — allowed forms; `test_why_takes_rest_of_line` (`open --side BUY --sl 4125 --tp 4140 --why M15 FVG retest` → why `"M15 FVG retest"`); `test_injection_is_inert` (`status; rm -rf /`, `market --tf $(id)`, `` open --side `id` … `` → ValueError; `--why "x; rm -rf /"` → accepted as text only); unknown subcommand / duplicate flag / missing `--side` on open → ValueError.
- [ ] Step 2–4: implement, run, pass.
- [ ] Step 5: commit `feat(strategies): claude-gw forced-command gateway`.

### Task 4: reaper session files

**Files (all in `KronosStrategies/claude_strategy/`):**
- `CLAUDE.md` — trading brief: tools, limits, cycle procedure, ICT method, journal format.
- `cycle_prompt.md` — the per-cycle prompt (`{{NOW}}` replaced with UTC time).
- `run_loop.sh` — the 5-minute loop (in hours: one `claude -p` cycle with a 240 s perl-alarm timeout; out of hours: `status` only); exits after 5 consecutive failed cycles.
- `start.sh` — creates tmux session `claude-strategy` running `run_loop.sh` if absent, then blocks while it lives (so launchd `KeepAlive` restarts it when it dies).
- `com.kronos.claude-strategy.plist` — LaunchAgent: `RunAtLoad`, `KeepAlive`, `ThrottleInterval 60`, runs `start.sh` under a login shell.
- `install.sh` — idempotent: copies files to `~/claude-strategy`, seeds `journal.md` if missing, adds the `Host kronos-claude` block to `~/.ssh/config`, installs + (re)loads the LaunchAgent.

`claude -p` allowed tools: `Bash(ssh kronos-claude:*)`, `Read`, `Edit(journal.md)`, `Write(journal.md)`, `Write(journal_archive/**)`.

- [ ] Step 1: `bash -n` on all scripts; `plutil -lint` on the plist.
- [ ] Step 2: commit `feat(strategies): Claude Strategy reaper session (launchd + tmux loop)`.

### Task 5: Deploy (box)

- [ ] Confirm the box copies of `entry_manager.py` (and `db/deploy_manager.py`) equal `main` before overwriting (no box drift).
- [ ] scp `claude_guard.py`, `claude_trade.py`, `strategy/entry_manager.py`, `db/deploy_claude_strategy.py` to `/home/ubuntu/KronosStrategies/strategies/…`.
- [ ] `docker compose -p kronos build s93_fvg_scalp && docker compose -p kronos up -d --no-deps s93_fvg_scalp`; container count unchanged; S93 healthy.
- [ ] `docker exec -e MANAGER_ARM_MODE=PAPER kronos-s93_fvg_scalp-1 python -m db.deploy_claude_strategy` → review → `--commit`.
- [ ] Install `claude-gw` to `~/bin/claude-gw`; back up `~/.ssh/authorized_keys`; append reaper's new public key with `command="/home/ubuntu/bin/claude-gw",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding`.

### Task 6: Deploy (reaper) + verify

- [ ] `brew install tmux`; `ssh-keygen -t ed25519 -f ~/.ssh/kronos-claude -N ""` (key never leaves reaper; only the .pub goes to the box).
- [ ] Copy `claude_strategy/` to reaper, run `install.sh`.
- [ ] From reaper: `ssh kronos-claude status` → JSON, `armed`=PAPER; `ssh kronos-claude 'ls'` → denied; `ssh kronos-claude market` → candles.
- [ ] Wait for a cycle (or run one by hand in hours): journal line written, `logs/` shows the Claude turn, gw log ALLOW lines.
- [ ] PAPER `open` + `close` round trip once by hand (DRY_RUN): StrategySignal PLACED, position closed, no broker order.
- [ ] Vault: `20 Strategies/Claude Strategy.md`, Live Roster + Timeline + Home; sync vault to reaper.
- [ ] Operator flips arm_mode to LIVE on /manager after reviewing a PAPER session.
