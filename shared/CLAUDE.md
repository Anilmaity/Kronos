# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Kronos is an algorithmic trading platform for **XAUUSD (gold)** — also XAG (silver) and BTC —
built around **ICT/SMC** (Inner Circle Trader / Smart Money Concepts) strategies. Since
**2026-09-20 the whole workspace is one git monorepo** — remote GitHub `Anilmaity/Kronos`
(private), branch `main`, `.git` at the workspace root. The three product folders plus the
research sandbox are plain subdirectories of it, each still with its own `.venv`/`node_modules`,
its own `.gitignore` (nested ignore files stay in force) and its own `CLAUDE.md`.

```
<workspace root>/            # git monorepo → github.com/Anilmaity/Kronos
├── KronosStrategies/   # Python live trading engine + backtester  (the "brain")
├── Kronos_Backend/     # Django 5 + GraphQL API                   (the "control plane")
├── kronos_frontend/    # Next.js 14 dashboard                     (the "cockpit")
├── ClaudeTradingRD/    # research sandbox (corpus studies, lab harnesses)
├── shared/             # this CLAUDE.md, audit docs, reports, chart PNGs
├── kb/                 # local Chroma semantic index over lab reports + vault (chroma/ store is ignored)
└── .claude/            # workspace-level Claude Code settings + skills
```

> **History before the monorepo.** Until 2026-09-20 these were four independent repos
> (KronosStrategies → GitHub `Anilmaity/KronosStrategies` + Bitbucket `jegnus/kronosstrategies`;
> Kronos_Backend → GitHub `Anilmaity/Kronos_Backend`; kronos_frontend → Bitbucket
> `jegnus/algomaya-frontend`; ClaudeTradingRD → the Mac over Tailscale). Those remotes are now
> **frozen** — they are not updated from the monorepo. Their full local histories, including
> branches that were never pushed, are kept in `~/Kronos_git_backups/20260920-160317/<repo>.git`
> on the Mac. Workspace root on the Mac is `/Users/anil/Projects/Kronos`; on the Windows box it
> was `E:/Projects/Kronos`.

### Product naming (one product, several names)
- **Kronos** — the product/app name (page title: *"Kronos — ICT/SMC XAUUSD Algorithmic Trading Bot"*).
- **Algorobos** — the current brand / design system (`ALGOROBOS_DESIGN.md`), live domain `app.algorobos.com`.
- **Algomaya** — legacy branding; appears in the frontend README and the bitbucket remote `algomaya-frontend`. Treat as historical.

### How the three repos fit together (the key integration fact)
All three share **one managed PostgreSQL database**. This is the seam:
- **Kronos_Backend** owns the schema via the Django ORM (app `apis`) and migrations.
- **KronosStrategies** reads/writes the *same* tables through its own **SQLAlchemy** mirror
  (`strategies/shared/models.py`). Django migrations manage the schema; the strategy engine just
  connects directly. Kronos_Backend *also* carries a second SQLAlchemy mirror (`utils/models.py`)
  for non-Django consumers.
- **kronos_frontend** never touches the DB directly — it talks only to the backend's GraphQL endpoint.

There are two candidate Postgres hosts — **TigerData Cloud** (per `compose.yml`) and a **Lightsail-managed
`kronos-strategies-db`** — and the live one for any service is whatever its on-box `.env` sets; see the
Deployment section. A separate **TimescaleDB hypertable (`ltp`)** is written by `tick_data_collector`;
`position_manager` does **not** read it — it pulls latest LTP live via OANDA REST S5
(`shared/tsdb_reader.fetch_latest_ltp`). The `ltp` hypertable is read only by offline backfill/validation
scripts. As of opt15, the `tick_data_collector` services sit behind the `data-archive`
compose profile — `docker compose up -d` no longer starts them by default; this profile
change shipped to the `algorobos` box in the 2026-07-31 opt15 deploy (compose merged
additively). A profile change does not auto-stop containers already running from before
the deploy, so whether the collectors are currently running on the box is not established
by this fact alone — start them explicitly with `docker compose --profile data-archive up -d`
when the archive is wanted.

Data/control flow end to end:
```
OANDA REST (candles) ─► KronosStrategies runners ─► get_signal() ─► entry_manager
                                                                        │ writes Position/Order/Trigger (SQLAlchemy)
                                                                        ▼
                                          Postgres (managed cloud) ◄──────────────► Kronos_Backend (Django ORM / GraphQL)
                                                                        ▲                         ▲
OANDA REST S5 (latest LTP) ─► position_manager (1s loop, TP/SL/TIME_EXIT)                        │ GraphQL over JWT
                                                                                          kronos_frontend (Apollo)
tick_data_collector ─► TimescaleDB ltp ─► offline backfill/validation scripts only (data-archive profile)
Broker side: strategies & Telegram_Bot ─► MetaAPI REST ─► MT4/MT5
```

> The two per-repo `CLAUDE.md` files (`Kronos_Backend/CLAUDE.md`, and the stale pointer note in
> `KronosStrategies/Claude.md`) are authoritative for their own repo's detail. The path constants
> inside `KronosStrategies/Claude.md` and `info` (`C:\Projects\PycharmProjects\...`) are **outdated** —
> the real workspace is the monorepo root (`/Users/anil/Projects/Kronos` on the Mac).

---

## 1. KronosStrategies — Python trading engine

Subdirectory of the monorepo (see above). Pre-monorepo it lived on branch `feat/strategy-manager`;
the frozen remotes were GitHub `Anilmaity/KronosStrategies` + Bitbucket `jegnus/kronosstrategies`.

This is a **Docker Compose stack** (`compose.yml`, project name `kronos`) of long-running services
plus a library of strategy modules and an offline backtester. No web server.

### Layout
- `strategies/` — the engine. Subdirs:
  - `strategy/` — **pure functions, no DB**: `ict_engine.py` (market structure, FVGs, order blocks,
    liquidity, `check_entry` → `EntrySignal`), `liquidity_engine.py`, `scalper_engine.py`.
  - `strategy/entry_manager.py` — the bridge: turns an `EntrySignal` into `Position`/`Order`/`Trigger`
    rows (SQLAlchemy) and places the MetaAPI order. Registers strategy variation tags.
  - `backtest_strategies/` — research strategies `sNN_*.py`; each exports `NAME`, `CONFIG`
    (`StrategyConfig`), and `get_signal(w1m, w5m, w15m, now_utc) -> Signal | None`. Contract in
    `backtest_strategies/base.py`.
  - `concept_strategies/` (`cNN_*.py`), `xauusd_strategies/` (`s04_breaker`, `s90_*`).
  - `shared/` — DB + broker layer: `models.py` (SQLAlchemy ORM mirror), `metaapi_client.py`
    (`place_order`, `close_position_by_id`), `tsdb_reader.py` (OANDA candle fetch, 20s TTL cache;
    `fetch_latest_ltp` pulls latest LTP live via OANDA REST S5 — TimescaleDB `ltp` reads happen
    only in offline backfill/validation scripts).
  - `backtest/` — walk-forward replay simulator (offline, no live trading).
  - `db/` — schema migrations + strategy deploy/retire scripts (e.g. `deploy_combined_v2.py`).
- `position_manager/position_monitor.py` — **1s loop**: pulls latest LTP, evaluates each open
  position's PENDING triggers — TARGET (`price >= tp`), STOPLOSS (`price <= sl`), and TIME_EXIT
  (wall-clock `max_hold_min`) — realizes P&L, zeroes the position, cancels remaining triggers, and
  actively closes the MetaAPI position. SL/TP are also attached at the broker as a backstop; **TIME_EXIT
  is only enforced here**.
- `tick_data_collector/` — polls OANDA S5/M1 candles → batch-inserts mid-price ticks into the shared
  TimescaleDB `ltp` hypertable. Three compose instances (XAU_USD, XAG_USD, BTC_USD), distinguished by
  the `symbol` column. `backfill_ltp.py` loads deep history.
- `Telegram_Bot/` — copy-trader for the `@NeymarGoldTrader` Telegram channel: `parse_signals.py` →
  `metaapi_orders.py`. See its dedicated skill `deploying-telegram-copytrader` (in
  `.claude/skills/`) before redeploying it to the AWS box.
- `btc_research/`, `ConceptStrategies/` (docs), `tests/`, `docs/` (deployment plans), `_scratch/` (retired local-DB helpers).

### Runners (live entry points — dispatched by env var)
```bash
RESEARCH_STRATEGY=s03_ob_mitigation python strategies/research_runner.py   # any sNN_/cNN_ strategy
XAUUSD_STRATEGY=S4 python strategies/xauusd_runner.py                      # xauusd_strategies
python strategies/micro_scalper.py                                        # 1m liquidity scalper (VAR3)
python position_manager/position_monitor.py                               # exit monitor (must run for SL/TP/TIME_EXIT)
python strategies/trial_all_strategies.py                                 # one-shot DRY_RUN trial fire
```
`DRY_RUN` gates real broker calls — DRY mode runs the full pipeline (DB rows, audit) but places no order.

### Commands
```bash
# Bring up / rebuild the stack (run from KronosStrategies/)
docker compose up -d --build <service>          # e.g. tick_data_collector position_manager
docker compose logs -f <service>
docker compose stop <service>                   # kill switch for a strategy

# Tests (pytest is scoped to tests/ via pytest.ini — keep new strategy tests there)
pytest tests/ -q
pytest tests/test_s90_winrate.py -q             # single module
pytest tests/test_s90_winrate.py::test_name -q  # single test

# Offline parity backtest (needs TSDB access)
python -m backtest.backtest_combined_v2 --days 540   # run from strategies/
```
Dependencies are **per-service** (`strategies/`, `position_manager/`, `tick_data_collector/`,
`Telegram_Bot/` each have their own `requirements.txt`); `requirements-dev.txt` at the root is just `pytest`.
Python 3.12 in `.venv`.

### Strategy & deploy concepts
- A **deployed strategy** = a `Strategy` row + a `UserStrategy` row (`deployed=True`, `is_active=True`)
  seeded by an idempotent `db/deploy_*.py` script (dry-run by default; `--commit` to write). Sizing is
  per-leg lots via `UserStrategy.multiplyer`.
- The heavy live strategies (`kronos_combined_v2`, etc.) were **decommissioned 2026-06-24** and their
  rows deleted; they are recreatable from git history + the deploy scripts. See `COMBINED_V2_DEPLOYMENT.md`
  for the runbook and the important **fidelity** caveats (live ≠ backtest).
- Strategy-design and validation are backed by Skills — prefer `/backtest-expert`,
  `ict-smc-strategy-design`, `crt-strategy-design`, `quant-strategy-design`, etc. when building or
  stress-testing a strategy rather than improvising.

---

## 2. Kronos_Backend — Django 5 + GraphQL API

Subdirectory of the monorepo. Pre-monorepo it lived on branch `feat/strategy-manager` (the
`fix/pnl-short-positions` note was stale); frozen remote GitHub `Anilmaity/Kronos_Backend`.
**This repo has its own detailed `CLAUDE.md` — read it for specifics.** Essentials:

- Django app dir is **`apis/`** (registered as `"apis"`; all imports `apis.*`). Project package /
  settings / Celery live in `Kronos_Backend/`. `utils/` holds the SQLAlchemy mirror + encryption.
- **The entire API is GraphQL at `/graphql/`** — there are no REST views. Schema assembled in
  `apis/schema/__init__.py`; **both queries and mutations are auto-discovered** by `importlib` —
  drop a `.py` whose class is the CamelCase of the filename into `apis/schema/query/`, or into
  `apis/schema/mutation/{admin,broker,user}/` (split by role). (Note: it's `apis/`, not `api/` — the
  backend's own CLAUDE.md says `api/`, which is stale.)
- **Auth**: `django-graphql-jwt`, header `Authorization: JWT <token>`, 6h expiry, no refresh
  (`settings.py`: `JWT_EXPIRATION_DELTA=6h`, `JWT_REUSE_REFRESH_TOKENS=False`). Decorators
  `@user_authenticate` / `@admin_authenticate` live in `apis/schema/utils/__init__.py` (the
  `auth.py` path in the backend CLAUDE.md is wrong — that file is empty). Tests run against an
  in-memory SQLite DB to avoid touching the TigerData Postgres.
- **Models** (`apis/models.py`) all inherit `BaseModel` (UUID PK, `created_at`, `modified_at`):
  `User` (email is `USERNAME_FIELD`), `Strategy → UserStrategy → Position → Order/Trigger`,
  `CurrencyPair`, `Signal`, `UserBroker`, `Action`. These are the same tables the strategy engine writes.
- **Celery**: Redis broker (`redis://redis:6379`), results in Django DB, `DatabaseScheduler` beat.

```bash
python manage.py runserver           # dev server (port 8000)
python manage.py migrate
python manage.py makemigrations
python manage.py test                # all tests
python manage.py test apis.tests     # single module
celery -A Kronos_Backend worker --loglevel=info
celery -A Kronos_Backend beat  --loglevel=info
docker compose up                    # web service on :8000
```
Env via `.env` (`python-dotenv`): `SECRET_KEY`, and `NAME/USER/PASSWORD/HOST/PORT` for Postgres.

---

## 3. kronos_frontend — Next.js 14 dashboard

Subdirectory of the monorepo; frozen pre-monorepo remote Bitbucket `jegnus/algomaya-frontend`.
Deployed on **Netlify** (`netlify.toml`, `@netlify/plugin-nextjs`) — since 2026-09-29 the site
**`algorobos-kronos`** in the *new* Netlify account (see Deployment → Frontend). It is **not linked
to any git repo**: pushing the monorepo never deploys the frontend; deploy with the Netlify CLI.

- **Next.js 14 App Router** with route groups: `(auth)` (`/login` + OTP), `(main)` protected
  (`/dashboard`, `/accounts`, `/backtests`, `/chart`, `/marketplace`, `/signals`, `/admin`,
  `/accountprofile`, `/settings`), `(minimal)` (`/forget-password`, `/reset-password/[token]`,
  `/verify-account`). Root layout `app/layout.tsx`; protected shell `app/(main)/layout.tsx`.
- **GraphQL via Apollo Client** → endpoint `https://app.algorobos.com/graphql/` (set in `GraphQL/url.ts`,
  re-exported by `constants.ts`). Operations are grouped by domain in `GraphQL/*Controls.ts`
  (account / strategy / marketplace). Apollo middleware (`GraphQL/client.ts`) attaches
  `Authorization: "JWT " + localStorage.token`; `GraphQL/middleware.ts` catches expired/failed auth and
  redirects to `/login`.
- **Auth**: JWT from the `Login` mutation stored in `localStorage` (`token`, `userEmail`, `AUTH_STEP`).
  No httpOnly cookie — token lives in localStorage.
- **State**: Zustand stores in `hooks/` (`useUserData`, `useUserToken`, `useUserBroker`,
  `useRiskProfiles`, `useSidebar`, change-trigger stores for broker/strategy refetch). Server state is
  Apollo's cache.
- **UI**: shadcn/ui + Radix primitives in `components/ui/`; feature components in `components/Box`,
  `components/inputs`. Tables via TanStack Table; charts via ApexCharts / Recharts / lightweight-charts.
- **Design**: Tailwind (`tailwind.config.ts`) + the *Algorobos / "Alchemist's Codex"* dark-academic
  system in `ALGOROBOS_DESIGN.md` — burnished-gold accents, serif display/body fonts (Cormorant
  Garamond, Libre Baskerville), OKLCH tokens. Shared types in `types.ts`.

```bash
npm run dev        # next dev
npm run build      # next build
npm run start      # next start -p 3000
npm run lint       # next lint
```

---

## Cross-cutting notes
- **Secrets** live in per-repo `.env` files and are gitignored (`.env`, `.env_aws`, `account*.txt`,
  `*.pem`). Never commit broker/OANDA/MetaAPI/DB credentials.
- The old local `db`/`tsdb` containers were retired; Postgres + TimescaleDB are now managed cloud
  services (TigerData Cloud and/or the Lightsail-managed DB — see Deployment). Anything needing live data
  (backtests, runners, the position monitor) requires network access to whichever host the active `.env` targets.
- **One repo, one history** (since 2026-09-20). Branch and commit at the workspace root; a change
  that touches backend + frontend together is one commit. Prefix commit scopes with the folder
  (`feat(backend): …`, `fix(frontend): …`, `lab(research_s5): …`) since the diff no longer says which
  project it belongs to. Never `git init` inside a subfolder again.
- Root `.gitignore` covers the cross-cutting exclusions (all `.env*`, `*.pem`, `*.session`,
  `account*.txt`, `.venv/`, `node_modules/`, `.next/`, `__pycache__/`, `kb/chroma/`, `.idea/`); the
  per-folder `.gitignore` files still apply inside their folders.
- **opt15 (2026-07-30/31)** platform-hardening + strategy-gate change log: source report
  `shared/OPTIMIZATION_15_POINTS_2026-07-30.md`, plan + outcome ledger
  `KronosStrategies/docs/superpowers/plans/2026-07-30-optimization-15-plan.md`.

---

## Deployment & infrastructure (AWS + Netlify)

> **Migrated 2026-09-28.** Production moved from AWS account `086769945463` (the "old" account,
> local profile `jegnus`) into account **`948806325684`** (IAM user `anilmaity`, region
> **ap-south-1**). The new account's IAM keys are in the workspace-root `.env`
> (gitignored, `Access key ID : …` format — never echo them). `aws` CLI v1.40 is installed locally.

### Lightsail (production — account 948806325684)
- **`kronos-backend`** — `ubuntu@15.252.166.251` (static IP `kronos-backend-ip`), Ubuntu 22.04,
  `micro_3_1` (**1 GB + 2 GB swap** — the account refused `small_3_1`; resize via snapshot once AWS
  raises the plan limit). **This is the live production box** despite its name: the whole
  `KronosStrategies` Compose stack (`-p kronos`) *and* the Django backend (`-p kronos_backend`, host
  nginx :443 → :8000, Let's Encrypt cert for `app.algorobos.com`, certbot timer). Checkouts
  `/home/ubuntu/KronosStrategies` and `/home/ubuntu/Kronos_Backend` are **not git repos** — deploy by
  `scp` + `docker compose build`, not `git pull`. **Compose project name must be `-p kronos`**
  (omitting it spawns a duplicate stack → double trading). SSH: key `~/.ssh/algobet-ssh.pem`,
  always `ssh -F /dev/null` (Lightsail's own key `kronos-backend-key` is not on the Mac). Service code
  is **baked into images at build time** (not bind-mounted) → a restart alone does not pick up code
  changes; you must rebuild. For the Telegram copy-trader specifically, use the
  `KronosStrategies:deploying-telegram-copytrader` skill (its IP/host references predate the migration).
- `Kronos_Backend/deploy/deploy.sh` (the old standalone-env tool) is **retired** — it would overwrite
  production; it now exits unless `I_KNOW_THIS_IS_PRODUCTION=yes`. The standalone checkout is kept
  at `~/standalone_backup/` on the box; snapshot `kronos-backend-pre-prod-20260928` is its rollback.

### Databases
- **`kronos-db`** — Lightsail managed PostgreSQL 18.6 (`micro_2_0`), **private** (reachable only from
  Lightsail in account 948806325684), endpoint
  `ls-31e814d812c0b37f746fa7ce799f5d6d1c0f0700.c3c6eykyy22v.ap-south-1.rds.amazonaws.com:5432`,
  master user `dbmasteruser`. Production data lives in database **`tsdb`** (same name as before).
  Scripts on the Mac cannot reach it unless public access is enabled.
- The on-box `.env` files are the only real config; the local `.env` files in the three product
  folders are **empty (0 bytes)**. Never scp a local `.env`/`*.session` to the box, and never read the
  running container's env (it leaks live broker/Redis/Telegram secrets).

### Old account 086769945463 (pre-migration — do not trade from it)
- **`algorobos`** (`13.126.204.82`) — the former production box. All Kronos containers **stopped with
  `--restart=no`** at the 2026-09-28 cutover; its nginx only relays `app.algorobos.com` to the new box
  until Cloudflare DNS is repointed. **`kronos-strategies-db`** (PostgreSQL 18.4, public) holds the
  frozen pre-cutover copy. Both kept for rollback until the operator retires them.
- `mailcow`, `jegnus-backend`, `algobet-backend`, the Lightsail DB **`onvya_database`** (plus the
  `delidr` database) and the `jegnus-*` S3 buckets belong to *other, unrelated projects* — leave them alone.
- DNS for `algorobos.com` is on **Cloudflare** (proxied), not AWS.

### Frontend
- **Netlify site `algorobos-kronos`** (id `41e6aaa0-25ae-4acd-969f-685cf3039d35`, team "algo" in the
  new Netlify account, migrated 2026-09-29) serves **`algorobos.com`** (+ alias `www.algorobos.com`,
  force-SSL, Netlify Let's Encrypt cert carried over). Build: `netlify.toml` (`npm run build`, publish
  `.next`, `@netlify/plugin-nextjs`); no env vars; Netlify login protection on non-production deploys
  only. The SPA calls `https://app.algorobos.com/graphql/` (API-only), answered by the Django backend on
  the production box (`kronos-backend`).
- **Not git-linked** — deploy from `kronos_frontend/` with the CLI, token = the `new_netlify : …` line
  of the workspace-root `.env` (never echo it):
  `NETLIFY_AUTH_TOKEN=<new_netlify> NETLIFY_SITE_ID=41e6aaa0-25ae-4acd-969f-685cf3039d35 npx -y netlify-cli deploy --prod --build`.
- The old site `algorobos` (`492b58d0…`, old account = the `netlify : …` token, which also hosts
  unrelated jegnus/delidr/matru sites) no longer has the domain; kept only for rollback.
