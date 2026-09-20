# Codebase Restructure — Design Spec

**Date:** 2026-06-16
**Status:** Approved (design), pending spec review
**Scope:** Structural reorganization of the ClaudeTradingBot codebase. No behavior changes.

## 1. Problem

The project works but is structurally fragile:

- **27 loose `.py` files at the repo root** with no separation between operational
  CLIs, one-off diagnostics, exploratory research, and tests. Research scripts sit
  next to production entry points, so it is easy to confuse "throwaway" with "load
  bearing" — which is exactly how a mis-measured research result (last-trade pricing,
  optimistic paper settlement) leaked into how the project was reasoned about.
- **Everything assumes `cwd == repo root`.** Imports work only because root is on
  `sys.path`; scripts read relative paths like `journal/` and
  `dashboard/live5m.json`. Run anything from another directory and it breaks.
- **No version control.** A bad move cannot be undone.

## 2. Goals / Non-Goals

**Goals**
- A logical folder/package layout: production package, operational scripts,
  diagnostics, research, and tests each in their own place.
- Research code is physically isolated and **cannot** be imported by production code.
- Imports resolve from any working directory (editable install).
- File I/O resolves against an absolute project root, not `cwd`.
- A research-methodology document so results are produced correctly going forward.
- A final report summarizing the new structure and where the project landed.
- **Zero behavior change** — every entry point runs exactly as before.

**Non-Goals**
- No logic changes to trading, execution, gate, or strategy code.
- No change to the `dashboard/` internal layout (Electron references files by path).
- No change to `.env*` / `cert.pem` / `mt5algo.ini` locations or to `journal/`.
- No new features. This is purely structural.

## 3. Decisions (locked with user)

1. **Packaging:** editable install via `pyproject.toml` + `pip install -e .`, with a
   `src/` layout (`src/bot/`).
2. **Package depth:** regroup `bot/` into subpackages, preserving all existing import
   call sites via a back-compat layer (§5).
3. **Safety net:** `git init` + baseline commit before any file moves.
4. **Logs:** research and dashboard outputs keep writing into `journal/` (lowest risk;
   the live feed and dashboard reads are unchanged).

## 4. Target Layout

```
ClaudeTradingBot/
├── pyproject.toml          # NEW — editable install, deps, project metadata
├── README.md               # NEW — what this is + how to run each entry point
├── .gitignore              # NEW
├── src/
│   └── bot/
│       ├── __init__.py     # back-compat re-export + alias layer (§5)
│       ├── core/           # paths (NEW), arb_gate, secrets
│       ├── data/           # <former data.py>, data_mt5, analysis, orders_log
│       ├── brokers/        # base, mt5_native, metaapi, broker (existing subpkg)
│       ├── markets/        # kalshi, polymarket, funding, arbitrage
│       ├── execution/      # exec_kalshi, exec_polymarket
│       └── strategies/     # live_strategy, pm_strategy, paper_pm
├── scripts/                # operational entry points
│   ├── trade.py  status.py  monitor.py  analyze.py  analyze_symbol.py
│   ├── arb.py  bets.py  pmpaper.py  livearb.py  livearb_once.py
│   └── diagnostics/        # check.py  check_apis.py  check_broker.py
│       │                     check_meta.py  check_meta_sdk.py
├── research/               # exploratory ONLY — never imported by production
│   ├── research_forward_edge.py   research_kalshi_depth.py
│   ├── research_static_arb.py     research_xvenue_threshold.py
│   ├── validate_arb.py            poly_test_order.py
│   └── README.md           # points at docs/RESEARCH_PROTOCOL.md
├── tests/
│   ├── test_arb_gate.py  test_never_naked.py  test_arb_oneshot.py
│   ├── test_edge_0.py  test_edge_1.py  test_edge_2.py  test_edge_3.py
│   ├── test_import_compat.py   # NEW — asserts every legacy import form resolves
│   └── test_research_isolation.py  # NEW — asserts bot/ + scripts/ never import research/
├── dashboard/              # UNCHANGED internal layout
├── journal/                # runtime state + logs (dir kept; contents gitignored)
├── docs/
│   ├── superpowers/specs|plans/...
│   ├── RESEARCH_PROTOCOL.md    # the "plot.md" methodology doc (§7)
│   └── RESTRUCTURE_REPORT.md   # final report (§8)
├── assets/                 # img.png, img_1.png, dashboard screenshots (moved from root)
└── .env  .env.bets  cert.pem  mt5algo.ini   # configs stay at root
```

## 5. Back-Compat Contract (the critical part)

The import scan (`from|import bot`) shows three call-site styles in use:

- `from bot import X` — the vast majority (e.g. `from bot import kalshi, polymarket`).
- `import bot.X as y` — `import bot.kalshi as kalshi`, `import bot.polymarket as pm`
  (in `test_edge_1.py`, `test_edge_3.py`).
- `from bot.X import Y` — `from bot.arb_gate import MIN_NET, MAX_GROSS`
  (in `live_strategy.py`), `from bot.brokers import get_broker`.

To keep **all** external call sites unchanged, the rules are:

**(a) Internal package imports use canonical subpackage paths.**
Inside `src/bot/`, modules import siblings by their new path, never via
`from bot import X`. This removes module-level circular dependence on `bot/__init__`.
Concrete edits:
- `core/arb_gate.py`: `from bot.strategies import paper_pm`
- `strategies/pm_strategy.py`: `from bot.strategies import paper_pm` +
  `from bot.core import arb_gate` + `from bot.markets import kalshi, polymarket`
- `strategies/live_strategy.py`: `from bot.execution import exec_kalshi, exec_polymarket`
  + `from bot.core.arb_gate import MIN_NET, MAX_GROSS`
- `execution/exec_kalshi.py`, `execution/exec_polymarket.py`: `from bot.core import secrets`
  (+ deferred `from bot.markets import kalshi` where already function-local)
- `markets/arbitrage.py`: deferred (function-local) `from bot.markets import polymarket, kalshi`
  + `from bot.data import data_mt5` — unchanged structure, new paths.
- `brokers/broker.py`: `from bot.brokers import get_broker` (already correct).

**(b) `bot/__init__.py` rebinds legacy names + aliases dotted paths.**
For every non-colliding former top-level module
(`kalshi, polymarket, funding, arbitrage, arb_gate, secrets, analysis, data_mt5,
orders_log, exec_kalshi, exec_polymarket, live_strategy, pm_strategy, paper_pm, broker`):
```python
import sys
from bot.markets import kalshi, polymarket, funding, arbitrage
from bot.core import arb_gate, secrets
from bot.data import data_mt5, analysis, orders_log
from bot.execution import exec_kalshi, exec_polymarket
from bot.strategies import live_strategy, pm_strategy, paper_pm
from bot.brokers import broker
for _n, _m in {
    "kalshi": kalshi, "polymarket": polymarket, "funding": funding,
    "arbitrage": arbitrage, "arb_gate": arb_gate, "secrets": secrets,
    "data_mt5": data_mt5, "analysis": analysis, "orders_log": orders_log,
    "exec_kalshi": exec_kalshi, "exec_polymarket": exec_polymarket,
    "live_strategy": live_strategy, "pm_strategy": pm_strategy,
    "paper_pm": paper_pm, "broker": broker,
}.items():
    sys.modules[f"bot.{_n}"] = _m   # makes `import bot.kalshi` + `from bot.kalshi import Y` resolve
```
This single mechanism satisfies all three call-site styles: the name becomes an
attribute of `bot` (covers `from bot import X`) and a registered dotted module
(covers `import bot.X` and `from bot.X import Y`).

**(c) The `data` name collision is handled by the subpackage `__init__`.**
`bot.data` is now a *package*, not the former `data.py` module. The former
`data.py` body moves to `src/bot/data/<feed>.py` (concrete filename chosen at
implementation time from the module's actual content, e.g. `oanda.py`), and
`src/bot/data/__init__.py` re-exports its public API so `from bot import data`
followed by `data.<fn>()` resolves exactly as before. All observed `data` call
sites use `from bot import data` (attribute) — none use `from bot.data import Y` —
so the package re-export is sufficient.

**(d) `bot.brokers` is unchanged** (already a real subpackage), so
`from bot.brokers import get_broker` stays native.

## 6. Path Resolution (root-cause fix)

Add `src/bot/core/paths.py`:
```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[3]   # src/bot/core/paths.py -> repo root
JOURNAL_DIR    = PROJECT_ROOT / "journal"
DASHBOARD_DIR  = PROJECT_ROOT / "dashboard"
ENV_FILE       = PROJECT_ROOT / ".env"
ENV_BETS_FILE  = PROJECT_ROOT / ".env.bets"
```
Modules and scripts that currently open relative paths (`journal/...`,
`dashboard/*.json`, `.env.bets`) are updated to resolve via `paths`. This makes
"run from any directory" actually true. `secrets.py` reads `ENV_BETS_FILE`.
Behavior (which files, what content) is identical; only path resolution hardens.

## 7. Research Isolation

- `research/` may import `bot`; **nothing in `bot/` or `scripts/` may import `research`.**
- `tests/test_research_isolation.py` greps `src/bot/` and `scripts/` for
  `import research` / `from research` and fails if found — a permanent guard.
- Research scripts keep their read-only / DRY-RUN posture; outputs land in `journal/`.

## 8. The Methodology Doc ("plot.md") — `docs/RESEARCH_PROTOCOL.md`

User-requested document on "how to not produce results like this again." Encodes the
hard-won lessons from the arbitrage work as a repeatable protocol:

- **Price at the executable book ask, never last-trade / midpoint.** The phantom arb
  existed only because edges were measured on last-trade prices.
- **Pre-register before running:** hypothesis, the price source, sample size
  (e.g. ~300 windows), and a kill-criterion. No open-ended "let it run and hope."
- **Model all costs:** taker fees, bid-ask spread crossed on entry *and* exit, and the
  basis-risk tail (different settlement references can make both legs lose).
- **Settle paper on real per-venue outcomes**, never an optimistic "one leg always wins"
  assumption — that fiction hid a −$17 break behind a fake +$702 track record.
- **Separate research from production**; a research result is a hypothesis until it
  survives executable-price validation over the pre-registered sample.
- An **"is this edge real?"** checklist (executable price? fees modeled? tail modeled?
  sample size met? out-of-sample? settlement reference matched?).

## 9. Final Report — `docs/RESTRUCTURE_REPORT.md`

Generated at the end: a file-by-file move map (old → new), the new architecture and
each subpackage's responsibility, how to run every entry point post-restructure, the
test results, and a concise recap of the arbitrage research verdict — so the report is
a single meaningful summary of where the project stands.

## 10. Verification Strategy

The restructure is "done" only when all of the following pass:

1. `pip install -e .` succeeds in the existing `.venv`.
2. `tests/test_import_compat.py` — imports every legacy name in all three styles — green.
3. `tests/test_arb_gate.py` (36 checks) and `tests/test_never_naked.py` (32 checks) green.
4. `tests/test_research_isolation.py` green.
5. Smoke test: `python dashboard/refresh_live5m.py` and `dashboard/refresh_data.py`
   import cleanly and write their JSON (read-only data paths; no live orders;
   `journal/STOP` remains in place).
6. A representative CLI (`python scripts/status.py` or `scripts/bets.py`) runs.

If any check fails, fix before proceeding; never declare success on partial results.

## 11. Risks & Mitigations

- **Circular imports during `bot/__init__`** → removed by rule 5(a) (canonical internal
  paths, no module-level `from bot import sibling`).
- **`data` collision** → handled by 5(c) (package re-export).
- **Dashboard breakage** → dashboard internal layout untouched; only import resolution
  (via editable install) and any relative path it owns are verified by the §10 smoke test.
- **Irreversible move** → git baseline commit first; each phase is a separate commit.
- **Hidden path assumptions** → §6 paths module + the §10 CLI/feed smoke tests.
