# Deployment plan

The bot is broker-agnostic: every script goes through `bot/broker.py`, which
delegates to the backend chosen by the `BROKER` env var in `.env`:

| `BROKER`  | Backend                            | OS requirement | Needs                                   |
|-----------|------------------------------------|----------------|------------------------------------------|
| `mt5`     | Native MetaTrader5 terminal (IPC)  | Windows only   | MT5 terminal installed + logged into Winprofx demo |
| `metaapi` | MetaApi cloud REST (london region) | Any            | `META_ACCOUNT_ID` + `META_API_TOKEN`      |

Switching backends is a one-line `.env` change. No code changes.

## Phase 1 — local (now)

Windows 11, `BROKER=mt5`. One-time setup: open the MT5 terminal, log into the
Winprofx-Live demo account, tick **Save password**. After that the bot attaches
to the terminal automatically (no credentials in `.env` needed). Alternatively
set `MT5_LOGIN` / `MT5_PASSWORD` / `MT5_SERVER` in `.env` and the bot will
launch + log in the terminal itself.

Known broker quirk (applies to BOTH backends): Winprofx demo server drops
connections during daily rollover ~21:55–22:55 UTC. Retry with backoff; do not
treat it as an outage.

## Phase 2 — AWS

### Option A (recommended): Windows EC2, keep `BROKER=mt5`

- Instance: `t3.medium` (2 vCPU / 4 GB — MT5 terminal + Python need ~2 GB+),
  Windows Server 2022 AMI. `t3.small` is too tight for the terminal UI.
- Install Python 3.14, clone repo, `pip install -r requirements.txt`, and the
  **WinproFX-branded MT5** — NOT vanilla MetaQuotes MT5. WinproFX is not in the
  MetaQuotes broker directory, so vanilla MT5 cannot find the Winprofx-Live
  server and `initialize()` hangs in IPC timeouts. Installer:
  `https://download.mql5.com/cdn/web/winprofx.limited/mt5/winprofx5setup.exe`
  (silent: `winprofx5setup.exe /auto`; installs to
  `C:\Program Files\Winprofx MT5 Terminal\` — keep `MT5_TERMINAL_PATH` on that).
- Log the terminal into the Winprofx demo once with Save password (RDP in).
- Make sure only ONE terminal64.exe runs — a second MT5 instance hijacks the
  Python package's IPC attach.
- Run the bot via **Task Scheduler** ("At startup", restart on failure) or NSSM
  so it survives reboots. Keep the terminal in the autostart too.
- Patching: enable AWS Systems Manager for updates instead of leaving RDP open.

### Option B: Linux (EC2 / ECS / Fargate), `BROKER=metaapi`

- Same codebase; `MetaTrader5` is skipped by the platform marker in
  requirements.txt. Set `BROKER=metaapi` in the task/instance env.
- Cheaper and simpler infra, but re-inherits MetaApi's reliability issues
  (london-region 504s, DNS flaps on `*.agiliumtrade.ai`).
- Good as a warm fallback even if Option A is primary.

### Secrets (both options) — do this, not `.env` files on disk

- **Rotate the access key currently sitting in `.env_aws` before deploying** —
  it is a long-lived IAM user key in plaintext. Delete `.env_aws` after.
- Attach an **IAM role** to the instance/task instead of static AWS keys.
- Store `OANDA_API_KEY`, `META_API_TOKEN`, `MT5_PASSWORD` in **SSM Parameter
  Store (SecureString)** or Secrets Manager; load them into env at startup,
  e.g. a small bootstrap that exports them before launching the bot.
- Never bake secrets into an AMI or commit any `.env*` file.

### Cost sketch

- Option A: t3.medium Windows ≈ $34/mo on-demand (~$22/mo with a savings plan).
- Option B: t3.micro Linux ≈ $8/mo + MetaApi subscription.
