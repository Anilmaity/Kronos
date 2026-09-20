# Kronos Codebase Audit — 2026-07-12

Full-codebase audit of all three repos (KronosStrategies, Kronos_Backend, kronos_frontend),
focused on **logic-preserving** improvements: performance, modularity, testability,
debuggability, coding standards. Every finding was verified at file:line by reading the code.

Legend — Risk: **LOW** = mechanical, no behavior change possible · **MED** = behavior-preserving but touches hot/auth/money paths · **HIGH** = needs careful verification before touching.

Status tags added during the same session: `[FIXED]` = implemented and verified green · `[REPORTED]` = intentionally NOT fixed (behavior change or needs on-box verification — user decision required).

**Verification after all changes (2026-07-12):**
- KronosStrategies: `pytest tests/` → **580 passed** (565 baseline + 15 new trigger-logic tests); all changed files byte-compile.
- Kronos_Backend: `manage.py test` → **81 passed** (73 baseline + 2 schema-surface + 6 relocated PnL tests); `manage.py check` clean; new schema smoke test proves the GraphQL surface is byte-identical.
- kronos_frontend: `npm run lint` clean, `npm test` → **34 passed** (new vitest suite), `npm run build` green (19 routes); dead-code removal alone cut first-load JS: /admin 303→172 kB, /dashboard 353→222 kB.
- **Nothing committed or pushed** — all changes sit in each repo's working tree for review. Frontend especially: pushing main ships to production.

---

## Repo 1: KronosStrategies (live trading engine)

Baseline: 523 tests green (`pytest tests/ -q`).

### Performance
1. **[PERF] `strategies/shared/tsdb_reader.py:189-201` + `position_manager/position_monitor.py:275`** — `fetch_latest_ltp()` = one uncached OANDA HTTP call per second (~86k/day) though the S5 candle changes every 5s. Fix: 1–2s TTL cache mirroring `_candle_cache`. Risk MED (hot exit path). Impact high. `[REPORTED — exit-latency tradeoff is an operator decision]`
2. **[PERF] `position_monitor.py:91-103`** — commits a `CurrencyPair.ltp` write every second even when price unchanged (2 sessions + up to 2 commits/sec). Fix: skip write when unchanged. Risk MED (modified_at semantics). `[REPORTED]`
3. **[PERF] `position_monitor.py:131-136`** — N+1: one Trigger query per open position per second. Fix: single `IN` query grouped in Python. Risk MED. `[REPORTED — do together with #25 extraction]`
4. **[PERF] `strategies/micro_scalper.py:94-103`** — `_today_realized_pnl_points` loads every closed Position ever, filters by date in Python; unbounded growth. Fix: SQL-side date filter. Risk LOW. `[FIXED]`
5. **[PERF] `strategies/research_runner.py:140-145`** — 5m/15m fetched before the new-1m-bar check; wasted fetches on idle ticks (×3 runner services). Fix: fetch 1m first, early-continue. Risk LOW. `[FIXED]`
6. **[PERF] `entry_manager.py:500-613`** — `place_entry` opens ~8 separate SQLAlchemy sessions per signal. Fix: one session passed through. Risk MED (order path). `[REPORTED]`
7. **[PERF] `strategies/shared/models.py:23`** — `create_engine(pool_size=60, max_overflow=10)` in every service × 3 shared copies against a micro Postgres; no `pool_pre_ping`. Fix: pool_size=5, overflow=5, pre_ping. Risk MED. `[REPORTED — verify no service needs 60]`
8. **[PERF] `ict_engine.py:58-72,124-145,168-193`** — `_swing_points`/`detect_fvgs`/`detect_order_blocks` are per-row Python loops, vectorizable with shift()/rolling(). Risk LOW with parity test. `[REPORTED — needs parity fixture first]`
9. **[PERF] `s90_killzone_ote.py:487`, `s90_killzone_ote_tuned.py:191`** — `iterrows()` in signal path; S93/S94/S99 show the numpy pattern. Risk LOW. `[REPORTED]`
10. **[PERF] `strategy_manager/manager.py:165-168` / `entry_manager.py:190-193`** — daily-P&L helper fetches ALL of today's non-ENTRY order position_ids DB-wide then IN-filters. Fix: joined aggregate. Risk MED (kill-switch input). `[REPORTED]`

### Modularity
11. **[MOD] `position_manager/shared/` + `strategy_manager/shared/` are hand-copied forks of `strategies/shared/` with live drift** — `position_manager/shared/models.py` is missing `StrategySignal` + `UserStrategy.archived`; its `metaapi_client.py` is an older module-level-only version; `market_timing.py` lacks injectable-now. Fix: one canonical shared package in the build pipeline. Risk MED (build change). Impact **high** — this drift is how the next live incident happens. `[REPORTED — needs deploy coordination]`
12. **[MOD] `metaapi_client.py:62-150` vs `:175-242`** — ~90 duplicated lines between module-level functions and `MetaApiClient` methods. Fix: delegate to a lazy default client (pattern already in `Telegram_Bot/metaapi_orders.py:553-589`). Risk MED. `[REPORTED]`
13. **[MOD] Contract factor ×100 defined in 5+ places** (`entry_manager.py:44,178`, `manager.py:150`, `fill_reconciler.py:54`, `position_monitor.py:118`, `live_trader.py:80`) — a unit mismatch here already caused a live 100× sizing error once. Fix: one shared constants module. `[PARTIALLY FIXED — position_monitor magic ×100 now a named constant; full cross-service consolidation blocked by #11]`
14. **[MOD] Duplicated strategy helpers** — `_atr` byte-identical in s93/s99; `_touch` triplicated (s93/s94/s99); `_in_session` copied into 4 s90 modules though `base.in_session` exists. Fix: move to `_kronos_indicators.py`. Risk LOW for _atr, MED for _touch (live parity — defer). `[REPORTED — s94 is LIVE; do not touch its copy]`
15. **[MOD] `manager.py:153-179` vs `entry_manager.py:181-202`** — same exit-keyed daily-P&L logic maintained twice; gates kill-switch AND soft brake; must stay in sync. `[REPORTED — blocked by #11]`
16. **[MOD] 52 `sys.path.insert` hacks** across runners/scripts. Fix: pyproject + editable install or PYTHONPATH in Dockerfiles. Risk MED (build change). `[REPORTED]`
17. **[MOD] `entry_manager.py:474-758`** — `place_entry` is a 285-line god-function (6 gates + sizing + broker + persistence). Fix: extract `_run_entry_gates` / `_persist_entry`. Risk MED-HIGH (kill-switch gates shipped 2026-07-11 live here). `[REPORTED — only with full gate suite green]`
18. **[MOD] `base.Signal` vs `EntrySignal`** — near-duplicate dataclasses manually field-copied in both runners; new fields can be silently dropped. Fix: `EntrySignal.from_signal()`. Risk LOW. `[FIXED]`
19. **[MOD] `entry_manager.py:284-344`** — `_VARIATION_STRATEGY_NAME` 60-line hardcoded registry. Risk MED (deploy-critical). `[REPORTED]`

### Testability
20. **[TEST] `strategies/shared/models.py:21-24`** — engine + Session created at import time from env; forces path-hacks in tests. Fix: lazy creation via module `__getattr__` (PEP 562), `from shared.models import Session` keeps working. Risk MED. `[FIXED — all 3 shared copies, identical edit]`
21. **[TEST] Wall-clock buried in money logic** — `entry_manager.py:142,188,520`, `position_monitor.py:159`. Fix: optional `now` param defaulting to wall clock (pattern exists in `market_timing.py`). Risk LOW. `[REPORTED — do together with #17/#25 extractions]`
22. **[TEST] Module-level mutable runner state with no reset hook** — `research_runner.py:63-65`, `micro_scalper.py:53-54`, `xauusd_runner.py:69-71` (S9x modules ship `reset_state()`; runners don't). Risk LOW. `[FIXED]`
23. **[TEST] `db_utils.py:80,108`** — `sys.exit()` inside library functions. Fix: raise. Risk LOW (offline path). `[REPORTED]`
24. **[TEST] `Telegram_Bot/live_trader.py:131-133`** — real `MetaApiClient`s built at import time. Fix: build in `main()`. Risk MED (deploy only via skill). `[REPORTED]`
25. **[TEST] Zero coverage of `position_monitor._check_triggers`** — the sole enforcer of TIME_EXIT, trail-fire, sibling-cancel, one-close-per-tick. Fix: extract pure decision function + tests. Risk MED (mechanical extraction only). Impact **high**. `[FIXED — new position_manager/trigger_logic.py (pure, DB-free) + 15 unit tests covering TIME_EXIT epoch guard, trail ratchet/rounding/fire, SL/TP directionality; the DB/broker shell in _check_triggers applies decisions with identical writes and log lines]`

### Debuggability
26. **[DEBUG] `tick_data_collector/main.py:34`** — **prints the OANDA API key** to container logs on every start (×3 instances). `[FIXED — line deleted]`
27. **[DEBUG] `strategies/shared/db_utils.py:69`** — **prints the DB password**. `[FIXED]`
28. **[DEBUG] `tsdb_reader.py:169,200` (+2 copies)** — live-feed errors go to `print()`, invisible to log filtering. Fix: module logger. `[FIXED — all 3 copies]`
29. **[DEBUG][HIGH] `position_monitor.py:205` + `position_manager/shared/metaapi_client.py:225`** — active close (TIME_EXIT/TRAIL) posts to the **env-configured** account, but entries open via per-broker `client_for_broker` (S94 → broker 4dbc…). If env account ≠ position account: close 404s, DB flattens, real position rides to backstop SL/TP. **Verify on-box env before anything else; S94's 1200-min time exit depends on this.** `[REPORTED — needs on-box verification, highest-priority follow-up]`
30. **[DEBUG][HIGH] `xauusd_runner.py:70,158`** — `_open_local` set True after first trade, never reset → S4 runner silently stops trading until restart. Might be intentional one-shot throttle. `[REPORTED — confirm intent]`
31. **[DEBUG] `tick_data_collector/main.py:89`** — "Market Live -" logged every 5s ≈ 17k lines/day/instance. `[FIXED — demoted to debug]`
32. **[DEBUG] Inconsistent logging setup per service** (formats differ; live_trader omits `%(name)s`). Fix: shared `logging_setup.py`. `[REPORTED — cross-service, blocked by #11]`
33. **[DEBUG] `backtest_concepts.py:109,111`, `backtest_all_cache_mp.py:102,104`** — bare `except:` swallows KeyboardInterrupt. `[FIXED]`
34. **[STD] `shared/models.py:86`** — `api_key` default `str(uuid.uuid4())` evaluated **once at import** → every SQLAlchemy-inserted UserBroker gets the same key (unique-violation landmine). Fix: `default=lambda: ...`. `[FIXED — all three shared copies]`
35. **[STD] `live_trader.py:57-58`** — real Telegram API_ID/API_HASH committed as env fallbacks. Fix: remove defaults, fail fast. `[REPORTED — verify box env first; removing blind could kill the live copytrader]`
36. **[STD] Unpinned requirements** (`pandas`, `numpy`, `requests`, `psycopg2-binary` unversioned in strategies + position_manager) — any rebuild can bump a pandas major under a LIVE bot. Fix: pin from the *deployed image's* `pip freeze`. `[REPORTED — must be pinned from the box image, not local]`
37. **[STD] Dead code/imports** — `entry_manager._has_open_position` (0 callers), unused imports in xauusd_runner, tick collector, fill_reconciler, micro_scalper. `[FIXED]`
38. **[STD] `position_monitor.py:118`** — magic `*100` contract factor; unrealized P&L stored in USD but realized in points×lots two screens apart. Fix: named constant + units docstring. `[FIXED]`
39. **[STD] `models.py:245-254`** — `Action.TRIGGER_TYPE` is a set literal (nondeterministic Enum order). Fix: tuple. `[FIXED]`
40. **[STD] TIME_EXIT smuggles a UNIX epoch through the `trigger_price` price column** — convention lives only in comments on both sides. Fix short-term: shared `is_time_exit()` predicate. `[FIXED — predicate added in the new pure decision module]`

**Do NOT touch (live-critical):** `s94_sweep_reversal.py` internals (LIVE since 07-07, window re-walk is deliberate parity), entry_manager gate logic lines 51-132/500-560 (kill-switch fix live 07-11), `strategy_manager/` semantics, position_monitor TIME_EXIT/TRAIL comments, `research_runner._is_new_1m` closed-bar convention (fixed the ORB stale-fill losses — do NOT harmonize with micro_scalper's different convention), `Telegram_Bot/` live path (deploy only via skill), compose.yml `-p kronos` rule.

**Test-coverage gaps:** `_check_triggers` (now covered via extraction), `place_entry` persistence body, cross-account close routing (#29), `tsdb_reader` paging/TTL/stale-fallback, tick collector insert/reconnect, micro_scalper daily-cap math.

---

## Repo 2: Kronos_Backend (Django 5 + GraphQL)

Baseline: 73 tests green (`manage.py test`, SQLite). Repo had **zero** `import logging` anywhere in app code.

### Performance
- **F1 [LOW/HIGH]** `types/user_strategy_type.py:20-27` + `position_type.py:30,42,46` — dashboard's hottest path is N+1: per-position `currencypair` fetch in `resolve_ltp`/`resolve_profit_loss`/`resolve_profit_loss_percentage`/`resolve_total_profit_loss`. Fix: `select_related("currencypair")` in `_positions_qs` & co. `[FIXED]`
- **F2 [LOW/HIGH]** `user_type.py:122`, `user_broker_type.py:149-153` — +2 queries per strategy row (`strategy.name`, `user_broker`). Fix: `select_related("strategy","user_broker")`. `[FIXED]`
- **F3 [LOW/MED]** `query/strategy_manager_state.py:34-37` — `ManagedStrategy.objects.all()` + per-row `user_strategy.strategy` walk. Fix: `select_related("user_strategy__strategy")`. `[FIXED]`
- **F4 [LOW/MED]** `managed_strategy_type.py:28-39` — Python-side sum of full Position rows → `aggregate(Sum(...))`. `[FIXED]`
- **F5 [LOW/MED]** `query/get_heat_map.py` — triple-nested loops load every position ever; O(n²) grouping. (Also broken — see F22.) `[REPORTED — fix together with F22 repair]`
- **F6 [MED]** `user_type.py:100-125` `resolve_reports_positions` — O(n²) grouping that mutates ORM instances; line 112 adds a *buy* price into `avg_sell_price` (probable bug). `[REPORTED]`
- **F7 [LOW]** `user_strategy_type.py:85-108`, `user_broker_type.py:126-152` — query-per-date loops (also broken via `Position.date` — F23). `[REPORTED]`
- **F8 [LOW]** `query/all_indicator.py:22-89` — full `ta` introspection per request; input static. Fix: compute at import. `[FIXED]`
- **F9 [LOW]** `mutation/admin/update_strategy_action.py:21-22` — same `.get(id=id)` executed twice. `[FIXED]`
- **F10 [MED]** `mutation/user/exit_strategy.py:22-30` — sequential blocking `requests.post` per position inside the request cycle. `[REPORTED — live money exit path]`

### Modularity
- **F11 [MED/HIGH]** owner-or-superuser fetch copy-pasted in ~10 mutations. Fix: one `get_owned()` helper. `[REPORTED — auth scoping, needs dedicated tests]`
- **F12 [LOW/HIGH]** auto-discovery importlib loop copy-pasted 5×, silently drops modules whose class name mismatches. Fix: one `discover_classes()` that **warns on missing class**. `[FIXED — now logs a warning; immediately surfaces F20-class bugs]`
- **F13 [MED/HIGH]** hardcoded endpoints/secrets: `exit_strategy.py:10` Lambda URL, `generate_back_test_report.py:53` Lambda URL, `verify_account.py:21` JWT secret literal `"algoacharya"`. `[REPORTED — secret rotation + env coordination needed]`
- **F14 [LOW]** `kolkata = timezone("Asia/Kolkata")` re-declared in 6 files. Fix: `apis/constants.py` with `KOLKATA_TZ` + `today_ist()`. `[FIXED]`
- **F15 [MED]** four different mutation payload shapes (`Response`/`success`/`Success`/`Ok`). Fix: additive `ok`+`message` on all. `[REPORTED — frontend contract]`
- **F16 [LOW]** aggregation business logic embedded in GraphQL type files (vs the exemplary pure+tested `types/pnl.py`). `[REPORTED — extract when fixing F5-F7]`

### Testability
- **F17 [LOW]** `datetime.now(tz=kolkata)` at 10 call sites → untestable "today" logic. Fix: shared `today_ist()`. `[FIXED — call sites now route through apis/constants.today_ist]`
- **F18 [LOW]** `utils/models.py:22-24` — SQLAlchemy engine + session opened at import time. `[REPORTED — module is dead code, see F31]`
- **F19 [LOW]** `types/test_pnl.py` — real regression tests never collected by `manage.py test` (wrong location + sys.path hack). `[FIXED — now discovered and passing]`
- **F20 [MED/HIGH]** discovery silently drops `getUserPositions`/`getUserStrategies` (both files define `class GetUserPosition`); one resolver also lacks auth + has broken pagination. `[REPORTED — re-adding schema fields = API surface change; the new discovery warning now makes it visible at startup]`
- **F21 [LOW/HIGH]** no endpoint-level GraphQL execution test — field-registration bugs invisible. Fix: `graphene.test.Client` smoke test pinning the schema surface. `[FIXED — schema smoke test added]`

### Debuggability (latently broken code — flagged, NOT silently "fixed")
- **F22 [MED/HIGH]** dropped `broker` FK still queried in 4 places (`all_user_brokers.py:16-18`, `get_heat_map.py:15`, `user_type.py:95,138`) → FieldError as generic GraphQL error. `[REPORTED]`
- **F23 [MED/HIGH]** nonexistent `Position.date` referenced in 4 resolvers → errors at query time. Fix: `created_at__date` (align bucketing with position_manager first). `[REPORTED]`
- **F24 [MED]** `get_user_strategy.py` — resolver never binds (name mismatch), field always null; no ownership check. `[REPORTED]`
- **F25 [LOW]** resolvers over fields dropped from models (currency_pair `exchange`/`segment`, strategy `interval`/`monthlyReturn`/`drawdown`, user_broker `userbrokerposition_set`/`client_code`). `[REPORTED — deletions need frontend query cross-check]`
- **F26 [MED/HIGH]** four admin mutations broken at runtime (create_strategy passes nonexistent fields; pause_strategy catches wrong DoesNotExist; update_strategy_action arg/return bugs; delete_strategy_action contains a dead duplicate class that no-ops and reports success). `[REPORTED]`
- **F27 [MED/HIGH]** silent no-op user mutations (toggle_risk_profile / toggle_trailing_stoploss touch nonexistent fields; update_user writes phantom attrs AND is an IDOR — looks up target by email argument). `[REPORTED — security]`
- **F28 [MED/HIGH]** `change_password.py` — unauthenticated, takes arbitrary email (password change for any account given old password + user enumeration). `[REPORTED — security]`
- **F29 [LOW-MED/HIGH]** swallowed exceptions everywhere, zero loggers in repo; `verify_token` falls through with no return; `get_candles` leaks raw DB error text to client; backtest report `Success` semantics inverted. `[PARTIALLY FIXED — loggers added at every except site; the two behavior slips (Success flag, verify_token return) REPORTED as they change API responses]`
- **F30 [LOW]** `all_indicator.py:69` print; list mutated while iterating; missing auth decorators. `[PARTIALLY FIXED — print removed; the mutate-while-iterating loop was left VERBATIM (fixing it would change the returned indicator list) and the auth-decorator addition is REPORTED (behavior change)]`

### Standards / dead code
- **F31 [MED]** `utils/models.py` dead AND wrong (`APP_PREFIX="api"` vs real `apis_*` tables; models the dropped Broker table). `[REPORTED — possible external lambda consumers]`
- **F32 [LOW]** Celery is scaffolding only — no `CELERY_*` settings, no tasks anywhere; repo CLAUDE.md claim is aspirational. `[REPORTED — delete-or-configure decision]`
- **F33 [LOW]** 13 empty schema placeholder files + empty `utils/auth.py` + boilerplate `views.py`. `[FIXED — deleted; CLAUDE.md auth.py reference corrected]`
- **F34 [LOW]** unused imports across ~15 files (`ruff --select F401` class). `[FIXED]`
- **F35 [MED/HIGH]** settings hygiene: `DEBUG=True` hardcoded on the box serving production GraphQL; insecure SECRET_KEY fallback; default DB password in code; dead `STATIC_DIRS`; dead CHANNEL_LAYERS/ASGI. `[REPORTED — DEBUG flip needs deploy coordination]`
- **F36 [MED]** `models.py:95` `default=str(uuid.uuid4)` evaluated once at class load (worked around in add_account). `[REPORTED — Django-side default change touches migration state]`
- **F37 [LOW-MED]** dead statements (position_type discarded queryset, signal_type strftime roundtrip); requirements: dotenv duplicated, `requests==2.25.1` (2020, CVEs), 3 redis clients, DRF with zero REST views; Dockerfile runs dev `runserver` in prod. `[PARTIALLY FIXED — dead statements + duplicate dotenv line removed; dep upgrades REPORTED (need smoke test)]`
- **F38 [MED]** `schema/__init__.py:11` mounts graphql_auth's relay `users(...)` query over the full User table. `[REPORTED — verify frontend usage, privacy]`
- **F39 [LOW]** `multiplyer` DB column typo — keep column (shared with SQLAlchemy consumers); GraphQL alias possible. `[REPORTED]`

**Do NOT touch:** `apis/migrations/*`, model field definitions (shared tables), `settings.py` DATABASES/USE_TZ/TIME_ZONE, `types/pnl.py` (recently fixed money math), `encrypt_decrypt.py`/`decrypt_env.py` (possible lambda consumers).

**Coverage gaps:** entire auth surface, update_user, exit_strategy.mutate, generate_back_test_report, ALL admin mutations (why 4 are broken), most non-manager queries.

---

## Repo 3: kronos_frontend (Next.js 14, Netlify — push to main SHIPS LIVE)

Baseline metrics: 37/37 Apollo calls `no-cache` + imperative `client.query` (zero hooks); 17 files with inline `gql`; 0 tests; 0 error boundaries; 39 raw `localStorage` accesses; 13 file-wide `eslint-disable react-hooks/exhaustive-deps`.

### Performance
- **F1 [LOW/HIGH]** `admin/_components/main.tsx:127-131` — polls the entire allUserBrokers tree every **1 second** with `no-cache`. `[REPORTED — poll cadence is an operator decision]`
- **F2 [MED/HIGH]** `StrategyTable.tsx:169-178` — 15s deep poll; effect deps tear down + refire on every row expand. `[REPORTED]`
- **F3 [LOW]** `UserBrokerPositionTable.tsx:77-81` — 4s poll, market-hours guard deleted (dead `now` computation remains); component appears unmounted. `[REPORTED]`
- **F4 [LOW/HIGH]** `crypto.randomUUID()` as React key (`StrategyBox.tsx:448`, `admin/main.tsx:174`) → full subtree remount every render (admin remounts rows every 1s). `[FIXED — stable keys]`
- **F5 [LOW/MED]** dead ~900-iteration date-array loops on every render, twice (`dashboard/main.tsx:43-58`, `StrategyBox.tsx:86-105`) — result never used. `[FIXED — deleted]`
- **F6 [MED]** zero Apollo cache use — even static-ish data is `no-cache`. `[REPORTED — stale-data semantics decision]`
- **F7 [MED]** no pagination: signals fetches 500 rows unvirtualized, backtests unbounded, admin everything. `[REPORTED]`
- **F8 [LOW/MED]** never-imported heavy deps in package.json: apexcharts, react-apexcharts, recharts, chart.js, chartjs-adapter-moment, react-gauge-chart, moment, lodash, crypto-js, @nextui-org/react, country-state-city, query-string. `[FIXED — removed from package.json; build verified]`
- **F9 [LOW]** whole-store destructuring of Zustand stores instead of selectors. `[REPORTED — minor]`
- **F10 [LOW/MED]** ~1.6 MB stray screenshots at repo root + `*.tmp.*` files under `app/` that match Next's tsx glob and can break builds. `[PARTIALLY FIXED — `*.tmp.*` added to .gitignore; files left in place (untracked, user's)]`

### Modularity
- **F11 [MED/HIGH]** 4 mutation handlers (~110 lines) copy-pasted verbatim between `StrategyBox.tsx:122-229` and `StrategyTableRow.tsx:78-187` — they call real broker actions (ExitStrategy/Delete). Fix: `useStrategyActions()` hook. `[REPORTED — refactor behind identical signatures, test in DRY conditions]`
- **F12 [LOW/HIGH]** 17 components define GraphQL inline instead of `GraphQL/*Controls.ts` (incl. the dashboard's core query). `[REPORTED — pure relocation, large diff; do per-page with build checks]`
- **F13 [LOW]** `formatCapital` tripled in `utils/FormatCapital.ts`. `[FIXED — one core fn + thin wrappers, output-identical]`
- **F14 [LOW/MED]** fmtNum/fmtTime/fmtDateTime/pnlColor re-declared per page (signals, backtests, manager, PositionRows). `[FIXED — consolidated into utils/format.ts; pages import]`
- **F15 [LOW/HIGH]** magic strings for localStorage keys + routes in 10+ files. `[FIXED — lib/storage.ts typed constants; call sites updated mechanically]`
- **F16 [LOW/HIGH]** dead code: entire legacy landing (`app/components/`, 15 files, sole framer-motion consumer), `components/Box/`, 4 dead Zustand stores, `client2`/`baseUrl2`, `utils/decrypt.ts` + 4 empty imports of it, `website/` static HTML. `[FIXED — deleted after grep + build verification]`
- **F17 [MED]** `manager/_components/main.tsx` = 916 lines (types + helpers + 4 panels). `[REPORTED — manager page is the live control panel; split later]`

### Testability
- **F18** zero test infrastructure. `[FIXED — vitest + @testing-library/react configured; `npm test` runs]`
- **F19 [LOW/HIGH]** pure logic locked in components (sorting comparator, OTP timer restore, killSwitchTripped, P&L summation). `[PARTIALLY FIXED — formatters extracted + unit-tested; component-embedded logic REPORTED]`
- **F20 [LOW/HIGH]** module-scope `localStorage` in `useUserToken`/`useAuthStep` — SSR landmine; build survives only via two accidental CSR bailouts. `[FIXED — lazy init with typeof window guard; build verified]`

### Debuggability
- **F21 [LOW/HIGH]** zero error boundaries — render crash white-screens the trading dashboard. `[FIXED — app/error.tsx + app/(main)/error.tsx with retry]`
- **F22 [LOW-MED]** swallowed errors: `.catch(console.log(...))` (invoked, not passed!), unconditional success toast in DataTable, silent localStorage.clear on login verify, expired-token path doesn't redirect. `[REPORTED — behavior changes]`
- **F23 [LOW]** 11 console.log/error sites in prod paths. `[FIXED — the pure-noise duplicate removed; the 9 console.error sites were KEPT deliberately: each is the only record of its caught error (don't blind errors)]`
- **F24 [LOW/MED]** **admin "Algo Positions" columns swapped** — LTP renders under "Avg Buy Price" and vice versa (`admin/main.tsx:165-187`); Exit button's onClick fully commented out. `[REPORTED — it shows WRONG PRICES to the operator; 2-line fix awaiting go-ahead since it changes displayed data]`
- **F25 [LOW]** `PositionRows.tsx:157` keys by `trigger.id` but the query never selects `id` → undefined keys. `[FIXED — id added to selection]`
- **F26 [LOW]** ChangePassword validation checks field names that don't exist in the form. `[REPORTED — fixing enables validation = behavior change]`

### Standards / security-adjacent
- **F27 [MED/HIGH]** GraphQL documents built by string interpolation — **password interpolated into the query text** (login/otp/ChangePassword); a `"` in a password breaks login. `[REPORTED — convert to variables; needs backend arg-type verification + deploy-preview test]`
- **F28 [HIGH]** plaintext password persisted in localStorage for the OTP flow. `[REPORTED — auth-flow redesign, coordinate with backend]`
- **F29 [MED/HIGH]** auth state lives in 4 places; two `localStorage.clear()` sites nuke unrelated prefs. `[PARTIALLY FIXED — keys centralized in lib/storage.ts; clearSession-style consolidation REPORTED]`
- **F30 [LOW]** stale metadata ("CryptoBot" title), dead Metadata import on a client page. `[FIXED]`
- **F31 [LOW/MED]** unused imports/vars pile-up in dashboard main + dead IST computations in two tables. `[FIXED]`
- **F32 [LOW/MED]** hardcoded old-palette colors bypassing the `--tv-*`/`--my*` token system (signals, backtests, manager). `[REPORTED — visual no-op only if mapped exactly; needs eyeball check]`
- **F33 [LOW]** 13 file-wide `eslint-disable react-hooks/exhaustive-deps`. `[REPORTED — narrowing can surface real missing deps = behavior risk]`
- **F34 [LOW]** `tsconfig.tsbuildinfo` committed, tool droppings. `[PARTIALLY FIXED — gitignore additions]`

**Do NOT touch without deploy preview:** auth flow files (otpForm/loginForm/clientOnly/middleware), polling cadences (operator may rely on 1s/4s during live trades), StrategyBox/StrategyTableRow mutation handlers (real broker actions), manager page's deliberate no-cache.

---

## Highest-priority follow-ups (need user decision / on-box verification)

1. **KS #29 — cross-account close routing** (position_monitor closes on env account, entries open per-broker): verify `META_ACCOUNT_ID` on the box vs broker `4dbc…`. If they differ, S94's TIME_EXIT is silently broken. **Check this first.**
2. **Backend F28/F27 — change_password unauthenticated + update_user IDOR** — real security holes on the production GraphQL endpoint.
3. **Frontend F24 — admin panel shows swapped LTP/AvgBuyPrice** — 2-line fix, awaiting go-ahead (changes displayed data).
4. **Backend F35 — `DEBUG=True` in production** — flip needs a coordinated deploy.
5. **KS #11 — three drifting copies of `shared/`** — the structural fix (single canonical package in the build) prevents the next drift incident; needs a careful box deploy.
6. **KS #36 — pin requirements from the deployed image's pip freeze** (must be done on-box).
7. **Frontend F27/F28 — password in GraphQL string / plaintext password in localStorage** — auth hardening batch, via Netlify deploy preview.
