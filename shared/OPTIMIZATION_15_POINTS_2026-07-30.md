# Kronos — 15 Optimization Points (Technology · Strategy · Market Analysis)

Research date: 2026-07-30. Sources: full code survey of KronosStrategies (live strategy
modules, execution layer, regime layer) + the KronosVault evidence base (fidelity audit
Jul 7–23, manager sim, July drawdown RCA, M3 forensics). All file:line cites verified
against the working tree on this date.

**Strategy inventory loaded** — Live (5): S93 FVG Scalp, S94 Sweep Reversal, S99 MSS+FVG,
S100 M3 Combo, Neymar Telegram Copy (all `always_on`, Winprofx-Demo). Retired: S95, S97,
CHALLENGE_XAU, kronos_combined_v2, session_breakout. Rejected in validation: S98, S96-EMA,
S93 variants (STRICT/H4/5pt-cap/M3/OB/split-entry), M3-family rejects. Research library:
s03/s04/s10/s11/s12/s14 + archived s01–s09 + s90_* xauusd family (10 modules) +
c03 + legacy kronos_s* modules.

---

## A. TECHNOLOGY / PLATFORM

### 1. Cut signal-path latency: 20s candle-cache TTL + 5s poll → bar-boundary invalidation or a streaming feed
The 1m frame feeding `get_signal` can be up to 20s stale (`tsdb_reader.py:45,164-167`
`_CANDLE_TTL=20`) plus up to 5s poll granularity (`research_runner.py:40`), plus ~10
sequential DB round-trips and an uncached OANDA drift call in `place_entry` before the
MetaAPI POST. Net: bar-close → order ≈ 20–25s on strategies that enter at market. This is
the mechanism behind the documented "entered 1 M5 bar late" behavior and feeds the
entry_drift gate (34 of 81 rejections in the Jul audit). Fix order: (a) invalidate the 1m
cache on minute rollover (cheap, immediate), (b) longer term subscribe one OANDA
pricing-stream (or MetaAPI streaming) writer that all services read. Everything today is
REST polling — zero streaming anywhere in the stack.

### 2. Centralize market data into one fetcher; decommission the dead tick-collector stack
Five processes (4 runners + strategy_manager) independently fetch identical XAU_USD
candles into private per-process caches. The manager refetches ~4,600 candles across 6
OANDA calls every 60s tick — and its 20s cache TTL is shorter than its own loop, so the
cache never hits (`regime_engine.py:271-283`). Meanwhile the 3 always-on
`tick_data_collector` containers write an `ltp` hypertable that **no live-path code
reads** — `fetch_latest_ltp` hits OANDA S5 directly (`tsdb_reader.py:194-204`); only
offline backfill/validate scripts read `ltp`. (This also means the CLAUDE.md/vault claim
"position_manager reads TimescaleDB" is stale — correct the docs.) One shared data
service (or even a Redis mid-price key) reclaims 3+ container footprints on the 2GB box
and removes 4× duplicate OANDA load.

### 3. Fix DB access patterns: N+1 queries, write amplification, session churn, oversized pool, missing indexes
Per 1s monitor tick: one SELECT per open position for PENDING triggers (N+1,
`position_monitor.py:202-206`), plus `pos.ltp`/`profit_loss` UPDATEs for every open
position every second and an unconditional CurrencyPair SELECT+UPDATE
(`position_monitor.py:159-171,192-199`). `place_entry` opens ~10 fresh `Session()`s
sequentially. Pool config is `pool_size=60, max_overflow=10` **per process** × ~8
single-threaded processes ≈ 560 potential connections against one managed Postgres
(`models.py:34`). No non-PK indexes exist anywhere; hot filters `Trigger(position_id,
status)`, `Position(symbol, quantity)`, `Order(condition, created_at)`,
`Order(broker_order_id)` are unindexed (Django owns the schema — add there). Fix: one
scoped session per loop/entry, batch the trigger query, throttle P&L writes, pool_size≈5
with `pool_pre_ping`, add the four indexes via a Django migration.

### 4. Close the reliability gaps: retries, fail-open drift gate, healthchecks, alerting, resource limits
The good `urllib3 Retry` config exists only in the tick collector
(`oanda_tick_lib/_client.py:130-136`); the actual trading fetch path has none — a single
429/5xx degrades to stale-or-None silently. MetaAPI entry placement is single-attempt: a
transient 504 permanently drops the signal (`entry_manager.py:595-599`) — S94's audit
showed missing signals means missing the rare big winners. `_entry_drift_exceeded` fails
OPEN on missing price (`entry_manager.py:126`) while other gates fail closed. The
"RECONCILE MANUALLY" flatten (position left open at broker) is log-only
(`position_monitor.py:137-145`). No compose healthchecks, no memory limits on a 2GB box
(one pandas spike can OOM-cascade; `restart: always` then crash-loops), and the only
heartbeat is a log line. Add: retry adapter on `tsdb_reader._session`, bounded retry on
`place_market_order`, make drift-gate fail-closed (or explicit), compose `healthcheck:` +
`mem_limit` per service, and push critical events (reconcile-manually, kill-switch trip,
API outage) to Telegram/email. Also reclaim the idle leftover containers
(`s97_snap_scalper`, `session_breakout`).

### 5. Add real observability: slippage, signal→fill latency, API health as metrics
Today the only execution-quality measurement is the 300s `fill_reconciler` and per-trade
log lines. No metrics system exists (confirmed: no prometheus/statsd/OTel anywhere).
Given the fidelity audit proved friction assumptions decide everything (rejected-set
replay flips from +$134 at 0.25pt to −$383 at 0.75pt), measure it live: per-trade
slippage (signal price vs broker fill — both already in the DB), bar-close→fill latency,
OANDA/MetaAPI error rates and call latency, loop-tick duration, and blocking time (active
close can block the 1s exit loop up to 15s — move broker calls off the hot loop). A tiny
Prometheus+Grafana or even a Django dashboard page over existing tables would do; the
data is already being written.

---

## B. STRATEGY

### 6. Ship the validated-but-unshipped S93 SOFT structure veto + 1.5×ATR gap cap
Validated 2026-07-23 and sitting idle awaiting direction: SOFT M15 swing-structure veto
(veto only counter-structure FVGs; ranging stays tradeable) + gap ≤1.5×ATR cap. Test
n=388 PF 1.31 vs base 1.26, avg +1.16pt vs +0.99pt, stress-0.80pt PF 1.20 vs 1.16, flat
parameter plateau, removes ~27% of trades that were net-negative (the Jul-10-style
counter-structure spikes). S93 is the only live strategy that tracks its backtest, so
live capture of this edge is credible. This is the highest-confidence, lowest-effort P&L
improvement on the table.

### 7. Rework exits: all four live modules are static SL/TP while the evidence says trail
Every live module uses static SL + fixed-R TP + wall-clock time backstop;
`Signal.trailing` exists in the contract (`base.py:40`) but nothing sets it. The M3
12-month forensics found TIME-backstop exits are 64% winners ("trail, don't cut") and 74%
of losing SLs die within 9 minutes. S94's edge is tail-carried (WR ~29%, P&L in a few big
winners) — exactly the profile that benefits from trailing/partial-TP structures.
Candidates to validate offline first (per house doctrine — no breakeven, it truncates
winners): chandelier trail on S94/S100 after 1R, and replacing the S100 flat TIME exit
with a trail-out. The chandelier variant already validated on CHALLENGE_XAU (PF 1.83,
`feat/challenge-xau-trailing`).

### 8. Consolidate duplicated strategy code and kill the window-default landmines
`_atr` is byte-identical in s93/s99/s100 (a vectorized `atr()` already exists in
`_kronos_indicators.py:42-46`); the FVG geometry test is triplicated; the
retrace/phantom-guard `_touch` state machine is near-duplicated ×4; the tz-localize idiom
repeats ~8×; and the entire regime/ict/market_timing tree exists as TWO hand-synced
copies (`strategy_manager/*` vs `strategies/*`) that have **already drifted**
(`EntrySignal.from_signal` exists in one). Factor one shared indicators + pending-retrace
engine and one importable regime package. Separately: runner defaults silently starve
strategies — S94 needs ≥298 M5 bars vs default `WIN_5M=80`; S100 needs ≥642 M1 bars vs
default `WIN_1M=60` (`research_runner.py:41-43`). Only compose env overrides save live
today (the exact defect class that killed CHALLENGE_XAU). Add a startup assert: each
module declares `MIN_BARS`, runner refuses to start undersized. Minor: wall-clock
`expires_at` (all four) should use bar time; standardize tick-rounding/epsilon on price
touches; fix the s99 hours comment drift.

### 9. Manage cross-strategy correlation explicitly — three of four modules fire on the same geometry
S93, S99, and S100's FVG leg all enter on FVG-proximal-edge retrace with overlapping
hours; the only defenses are entry_manager's crude same-side proximity dedup (15min/2pt)
and the global max_concurrent=3. Add a signal-level correlation budget: skip (or
half-size) a new entry when an open position from a sibling strategy is within X points
and same side, and log the overlap rate. At portfolio level, act on the 12-month sim
verdict (book net negative in every mode; S94 its biggest loser at PF 0.84 −$1,103 with a
harness-sensitive "+623R" own-claim): re-validate S94 in the unified harness and demote
it to PAPER if it fails there — demo mode right now makes this free to do.

### 10. Fix S94's live-capture and level-fidelity gap — its edge dies in the details
The audit showed S94's WR matches sim but P&L flips (PF 0.75 live vs 1.23 sim) because
live captures ~half the signals and the missed ones contain the rare big winners. Three
concrete mechanical fixes: (a) level-universe parity — `_LEVEL_TTL=1440` M5 bars (~5
days) vs deployed window `WIN_5M=1500` gives near-zero margin; the module's own comment
(`s94:83-85`) concedes shorter windows see fewer levels than backtest — feed it the full
TTL depth; (b) the O(n·levels) full-rebuild `_detect` python loop each M5 bar
(`s94:121-179`) is the latency-heaviest detection in the roster — vectorize or make
incremental so detection lands earlier in the bar; (c) single-attempt order placement
(point 4) drops exactly the signals it can least afford. Success metric already exists:
signal-capture ratio vs sim in `StrategySignal`.

---

## C. MARKET ANALYSIS

### 11. The regime engine gates nothing — wire it into entries or stop paying for it
Everything the regime engine computes (D1/H4 ICT bias, ATR-percentile vol, Kaufman ER
trend, session) currently influences **zero live decisions**: all five roster strategies
are `always_on`, four of five policies are unreachable, `snap.session` and the whole
`details{}` blob are never read, and the only live-effective manager output is
`market_closed` — a clock function (`policies.py`, `deploy_manager.py:112-162`). The
evidence (manager sim: gating = robust ~40–50% DD cut, not a return edge) says the right
integration is not strategy-pausing but passing the RegimeSnapshot into
`entry_manager.place_entry` as entry-quality context — starting with a trend-persistence
(ER) gate for S100, whose only losing period (2023H2) is exactly the regime the ER read
identifies, using infrastructure the manager already computes.

### 12. Add the counter-HTF-bias entry filter — the July drawdown's named fix, still unbuilt
The July 2026 drawdown RCA concluded: S94/S99 repeatedly bought against a bearish D1/H4;
trend-pausing made things worse; the promising untested direction is **direction-aware
(counter-HTF-bias) signal filtering** at entry time. The building blocks all exist and
all sit unused: `base.htf_bias` (`base.py:63-79`), `_kronos_indicators.htf_bias_from_window`,
`ict_engine.check_entry(…, bias)` — no live runner consumes any of them, and every live
module ignores its `w15m` parameter (fetched every tick, wasted). Validate offline per
strategy (S12/S14 in the research library are literally this experiment shape for
M90/OB_MIT), then wire: veto (or half-size) entries whose side opposes an aligned D1+H4
bias. This is the single most evidence-backed *strategy-return* idea available, and it
reuses the S93 SOFT-veto validation harness.

### 13. Replace the static news blackout with the event-gate calendar the repo already has
The live news defense is one hardcoded window: `NEWS_BLACKOUT_UTC="12:25-12:45"`
(`entry_manager.py:59`). Meanwhile `strategies/shared/event_gate.py` (hand-coded
2025–2026 FOMC/CPI/NFP/PCE/GDP/ECB calendar, ±2h, fail-open) and
`strategies/research/news_filter.py` (ForexFactory CSV) exist and are proven in the
kronos_s* research strategies — but neither reaches the manager, the regime, or
entry_manager. Promote `event_window_open` to a manager guard / RegimeSnapshot field +
entry gate, add a periodic ForexFactory refresh so the calendar doesn't rot after 2026,
and log a `news_gate` rejection reason so its cost is auditable like every other gate.
The 52pt news gap that motivated S93's gap cap is the reminder of what an unguarded
release does to an FVG book.

### 14. Add spread/execution-cost awareness — the decisive variable nobody measures
Every price in the system is OANDA **mid** (`"price":"M"`, `tsdb_reader.py:132,195`);
bid/ask is never fetched, so live spread is invisible — yet the fidelity audit's entire
conclusion pivots on friction (rejected-set: +$134 at 0.25pt vs −$383 at 0.75pt), the M3
spec's dead zone (9–12 UTC) and S99's dropped Asia hours are hardcoded proxies for
spread, and sub-0.5×ATR stops were shown to be "cost fodder". Fetch bid/ask (one extra
param on the existing OANDA calls), then: (a) live spread gate — reject entries when
spread > X% of stop distance; (b) per-hour spread stats to replace hardcoded hour
exclusions with measured ones; (c) spread-at-entry recorded on Position for
per-strategy net-cost attribution. This directly hardens every scalping-slot strategy
whose edge is ~1pt/trade.

### 15. Make the regime loop cheap and extend it with the missing market context
Efficiency: stop fetching the M5/M1 frames (~2,300 of 4,600 candles/tick feed
display-only `details` fields), reuse the D1/H4 swing computations (each computed twice
per tick), and memoize on last-closed-bar timestamps as `manager_sim_engine.py:451-479`
already does — D1 structure is currently recomputed 1,440×/day for one new bar. Coverage:
the regime knows nothing about session-relative levels (Asian range, prior-day H/L — S94
builds its own privately; nothing shares them), volume (fetched into every frame, never
read), or cross-asset context (the TNX z-score gate in `macro_gate.py` exists, is proven
in research strategies, and is unwired — DXY would follow the same pattern). Publishing
PDH/PDL/Asian-range + a spread/vol/news-aware RegimeSnapshot turns the manager into an
actual market-analysis service that strategies and the /manager tab can trust — today the
tab renders a rich regime that causally affects nothing.

---

## Suggested sequencing

Quick wins, this week: #6 (ship S93 veto — validated), #4 partial (retry adapter +
MetaAPI entry retry + fail-closed drift), #2 partial (stop tick collectors, fix doc),
#15 partial (drop M5/M1 frames), #8 partial (MIN_BARS assert).
Medium: #1, #3, #5, #13, #14.
Research-gated (validate offline first, demo account makes it free): #7, #9, #10, #11, #12.
