"""
Live trader for @NeymarGoldTrader signals.

Pipeline:
  Telegram channel  --(Telethon NewMessage)-->  parse_signal()
       |
       v
  Redis  (hft:tg:signal:<id>, hft:tg:open)
       |
       v
  place_order()   <-- stubbed; wire to MetaAPI when ready (DRY_RUN gates it)
       |
       v
  Reply handler   --(typo fix / TP hit / SL hit)-->  modify_order() / close_order()

Run:
  TG_API_ID=... TG_API_HASH=... python live_trader.py
"""

import argparse
import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load MetaAPI / Telegram creds from .env before importing metaapi_orders,
# which reads token/account at import time. Probe a few candidate paths;
# silently skip ones that don't exist (depth varies inside the container).
_HERE = Path(__file__).resolve().parent
_candidates = [_HERE / ".env"]
for n in (1, 2, 3):
    try:
        _candidates.append(_HERE.parents[n - 1] / ".env")
        _candidates.append(_HERE.parents[n - 1] / "Kronos App" / ".env")
    except IndexError:
        break
for _p in _candidates:
    if _p.exists():
        load_dotenv(_p, override=False)

# telethon is imported lazily inside main() so this module can be imported (and
# unit-tested) without the Telegram client dependency installed.
from parse_signals import parse_signal, classify_outcome, looks_like_signal, SL_FIX_RE, clean
from manage_signals import classify_management, resolve_target
import metaapi_orders as mx
import db_persist as db
import apis_persist as apis
from state_store import make_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tg-trader")

API_ID = int(os.getenv("TG_API_ID", "30334024"))
API_HASH = os.getenv("TG_API_HASH", "f7f83460d3bae2e462c02f144dbc114f")
CHANNEL = os.getenv("TG_CHANNEL", "Test_XAU_USD")


def _channel_ref(raw: str):
    """Telethon needs an INT for a numeric channel id, not the string form.

    A private channel has no username, so it can only be addressed by id — the
    VIP source is configured as -1002776523643. Passing that as a string makes
    Telethon treat it as a username and resolve nothing, so the listener starts
    cleanly and then silently receives no messages at all.
    """
    s = (raw or "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else s


CHANNEL_REF = _channel_ref(CHANNEL)
# Telethon session path. Kept under TG_SESSION_DIR so it can be persisted on a
# docker volume: without a saved session every (re)start re-triggers an
# interactive phone/code login, which hangs (then crash-loops) in a headless
# container — i.e. the bot never reaches the message handler and places no trades.
SESSION = str(Path(os.getenv("TG_SESSION_DIR", str(_HERE))) / "kronos_tg")

# Empty REDIS_URL → use in-memory state store. Set to a redis:// URL to enable Redis.
REDIS_URL = os.getenv("REDIS_URL", "").strip() or None
# State-key namespace. A second trader copy (parallel account, same channel) sets
# its own prefix so the two never share :open / :signal:* keys when a real Redis
# backend is configured. (The default in-memory store is already per-process.)
REDIS_PREFIX = os.getenv("TG_REDIS_PREFIX", "hft:tg")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MAX_SIGNAL_AGE_SEC = 120          # ignore signals we receive late (recovery from downtime)
ALLOWED_INSTRUMENTS = {"XAUUSD"}
RISK_PER_TRADE_USD = float(os.getenv("RISK_USD", "100"))

# XAUUSD: $1 PnL per 0.01 price move per 0.01 lot (varies by broker; verify).
# volume_lots = risk_usd / (risk_points * USD_PER_POINT_PER_LOT)
USD_PER_POINT_PER_LOT = float(os.getenv("USD_PER_POINT_PER_LOT", "100"))  # XAUUSD default
MIN_LOT = float(os.getenv("MIN_LOT", "0.01"))

# The Neymar VIP channel ends 309 of its 315 signals with "TP: open" — an
# unbounded runner. When enabled, that leg is placed with a stop and NO
# take-profit, and is closed by a management message or the stale sweep. Default
# OFF, so the free channel keeps placing exactly the numeric TPs it always did.
TP_OPEN_LEG = os.getenv("TG_TP_OPEN_LEG", "false").lower() == "true"

# Act on position-management messages (breakeven / move SL / close / "trade
# failed"). ON for both channels (2026-10-01: the operator wants breakeven ->
# exit 3 keep 2 and "trade failed" -> exit all on Neymar as well as VIP).
ACT_ON_MANAGEMENT = os.getenv("TG_ACT_ON_MANAGEMENT", "true").lower() == "true"

# Drop a signal identical to one already seen within this many seconds. The VIP
# channel reposts 145 of its 315 signals (24%), often the same text twice in the
# same minute. 0 disables it — the default, because on the free channel a
# genuine re-entry at an identical zone is plausible and must not be swallowed.
DEDUP_WINDOW_SEC = float(os.getenv("TG_DEDUP_WINDOW_SEC", "0"))

# A signal is only removed from the :open set on a TP3 / SL reply. If the channel
# announces TP1/TP2 then goes quiet (no TP3, no SL), it would stay "open" forever
# and the no-pyramiding guard below would skip every later signal. Expire — flatten
# remaining broker orders and untrack — any signal open longer than this.
MAX_OPEN_AGE_SEC = float(os.getenv("MAX_OPEN_AGE_HOURS", "12")) * 3600
SWEEP_INTERVAL_SEC = int(os.getenv("SWEEP_INTERVAL_SEC", "1800"))  # background stale-sweep cadence

# Broker reconciliation: poll MetaAPI for the *actual* fate of each tracked
# slice (filled? closed? live PnL?) instead of inferring outcomes only from the
# channel's text replies. A slice that disappears from the broker is confirmed
# terminal only after ABSENT_CONFIRM_POLLS consecutive misses, so a single
# transient empty read can't fake a close.
BROKER_POLL_SEC = int(os.getenv("BROKER_POLL_SEC", "30"))
ABSENT_CONFIRM_POLLS = int(os.getenv("ABSENT_CONFIRM_POLLS", "2"))
_TAG_RE = re.compile(r"tg-(\d+)-tp(\d+)")


def _build_accounts() -> list[dict]:
    """Accounts each signal is mirrored onto (copy trading).

    Primary is always present; a second ('neymar2') is added only when both
    TG2_META_ACCOUNT_ID and TG2_META_API_TOKEN are set — so with no TG2_* creds
    the single-account behaviour is unchanged. Each account carries its own
    MetaApiClient (independent token / trading host / spec cache) and risk size.
    """
    primary = mx.MetaApiClient(
        os.getenv("META_API_TOKEN", ""), os.getenv("META_ACCOUNT_ID", ""),
        dry_run=DRY_RUN, label="primary")
    accounts = [{"label": "primary", "client": primary, "risk_usd": RISK_PER_TRADE_USD,
                 "apis": apis._default_dashboard,  # existing 'Neymar Telegram Copy' strategy
                 "source": "env", "us_id": apis.USER_STRATEGY_ID, "lot": None,
                 "entries": True, "healthy": True}]

    tg2_acct = os.getenv("TG2_META_ACCOUNT_ID", "").strip()
    tg2_tok = os.getenv("TG2_META_API_TOKEN", "").strip()
    if tg2_acct and tg2_tok:
        client2 = mx.MetaApiClient(tg2_tok, tg2_acct, dry_run=DRY_RUN, label="neymar2")
        # Account 2's own platform strategy ('Neymar Telegram Copy (Account 2)').
        # Provisioned by strategies/db/deploy_neymar2_strategy.py; ids overridable.
        dash2 = apis.ApisDashboard(
            os.getenv("APIS2_USER_STRATEGY_ID", "31c5b1cf-8a25-4f5a-983f-2207cceae4b8"),
            os.getenv("APIS2_USER_BROKER_ID", "45b0c6d8-90ed-4996-bbfd-a92a951966bb"),
            apis.CURRENCYPAIR_ID, enabled=apis._ENABLED, label="neymar2",
            strategy_id=os.getenv("APIS2_STRATEGY_ID", "30427449-9705-406c-820d-2b5ff9d8c003"))
        accounts.append({"label": "neymar2", "client": client2,
                         "risk_usd": float(os.getenv("TG2_RISK_USD", str(RISK_PER_TRADE_USD))),
                         "apis": dash2, "source": "env", "us_id": dash2.user_strategy_id,
                         "lot": None, "entries": True, "healthy": True})
    return accounts


ACCOUNTS = _build_accounts()
ACCOUNTS_BY_LABEL = {a["label"]: a["client"] for a in ACCOUNTS}
APIS_BY_LABEL = {a["label"]: a["apis"] for a in ACCOUNTS}

r = None  # state store (RedisStore or MemoryStore) — set in main()

# ── Accounts managed from the dashboard ("Add Data" on the Neymar tabs) ───────
# Besides the env accounts above, every UserStrategy on this bot's Strategy is
# traded too, at its fixed `lot_size` ("Price"). The dashboard rows are re-read
# at every new signal (so Pause/Resume and Price apply to the very next signal)
# and every TG_ACCOUNT_REFRESH_SEC in the background (so a newly added account
# is validated and ready before its first signal). Accounts are never dropped
# from the routing maps once loaded — a paused/removed account just stops taking
# NEW entries, while its already-open slices still close/reconcile normally.
DB_ACCOUNTS = os.getenv("TG_DB_ACCOUNTS", "true").lower() == "true"

# ── VIP priority (Neymar bot only) ──────────────────────────────────────────
# The VIP channel posts ~91% of the free channel's trades, usually 1-2s BEFORE
# it. On an account that is ALSO traded by the VIP bot, the VIP trade wins: the
# Neymar bot skips a trade VIP already posted, and when Neymar posts first it
# waits up to PRIORITY_WAIT_SEC for VIP before trading those shared accounts.
# Accounts only on the Neymar tab always trade instantly. Every bot records its
# signals in the shared kronos_xchan_signals table on arrival.
VIP_CHANNEL_ID = "-1002776523643"
VIP_STRATEGY_ID = "c708a216-5c5f-41b4-a63b-7e13d15ce090"
PRIORITY_CHANNEL = os.getenv(
    "TG_PRIORITY_CHANNEL", VIP_CHANNEL_ID if CHANNEL == "NeymarGoldTrader" else "").strip()
PRIORITY_STRATEGY_ID = os.getenv(
    "TG_PRIORITY_STRATEGY_ID", VIP_STRATEGY_ID if PRIORITY_CHANNEL else "").strip()
PRIORITY_WAIT_SEC = float(os.getenv("TG_PRIORITY_WAIT_SEC", "10"))
PRIORITY_MATCH_SEC = float(os.getenv("TG_PRIORITY_MATCH_SEC", "1800"))
PRIORITY_TOLERANCE = float(os.getenv("TG_PRIORITY_TOLERANCE", "5.0"))
_priority_meta: set[str] = set()      # MetaAPI ids the priority (VIP) bot trades


def _meta_id(acc: dict) -> str:
    return (getattr(acc["client"], "account", "") or "").strip()
ACCOUNT_REFRESH_SEC = int(os.getenv("TG_ACCOUNT_REFRESH_SEC", "60"))
_BAD_ACCOUNT_LOG_SEC = 600
_bad_accounts: dict[str, float] = {}   # user_strategy_id -> last time we logged it unusable


def _decrypt_token(enc: str) -> str:
    """Decrypt a UserBroker.meta_api_token_enc (Fernet, FIELD_ENCRYPTION_KEY —
    the same scheme as Kronos_Backend/apis/crypto.py)."""
    from cryptography.fernet import Fernet
    key = os.getenv("FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set")
    return Fernet(key.encode()).decrypt(enc.encode()).decode()


def _db_label(user_strategy_id: str) -> str:
    return f"us-{user_strategy_id[:8]}"


def _log_bad_account(us_id: str, msg: str, *args) -> None:
    now = datetime.now(timezone.utc).timestamp()
    if now - _bad_accounts.get(us_id, 0) >= _BAD_ACCOUNT_LOG_SEC:
        _bad_accounts[us_id] = now
        log.warning(msg, *args)


def _new_db_account(row: dict) -> dict | None:
    """Build + validate a MetaAPI client for a dashboard-added account. Blocking.
    Returns None (and the account is retried on the next refresh) when its
    creds are missing/undecryptable or MetaAPI can't list its positions — an
    unusable account is never added, so it can't stall the others."""
    us_id = row["user_strategy_id"]
    label = _db_label(us_id)
    acct = (row.get("meta_account_id") or "").strip()
    if not acct or not row.get("token_enc"):
        _log_bad_account(us_id, "[%s] dashboard account has no MetaAPI id/token — not trading it", label)
        return None
    try:
        token = _decrypt_token(row["token_enc"])
    except Exception as e:
        _log_bad_account(us_id, "[%s] cannot decrypt MetaAPI token (%s) — not trading it", label, e)
        return None
    client = mx.MetaApiClient(token, acct, dry_run=DRY_RUN, label=label)
    if client.get_open_positions(next(iter(ALLOWED_INSTRUMENTS))) is None:
        _log_bad_account(us_id, "[%s] MetaAPI account %s not reachable — not trading it yet", label, acct)
        return None
    _bad_accounts.pop(us_id, None)
    dash = apis.ApisDashboard(us_id, row["user_broker_id"], apis.CURRENCYPAIR_ID,
                              enabled=apis._ENABLED, label=label,
                              strategy_id=row["strategy_id"])
    return {"label": label, "client": client, "risk_usd": RISK_PER_TRADE_USD, "apis": dash,
            "source": "db", "us_id": us_id, "meta_account_id": acct,
            "lot": row["lot_size"], "entries": row["entries"], "healthy": True,
            "trade_sl": row.get("trade_sl_usd"), "max_sl": row.get("max_sl_per_trade_usd"),
            "ub_id": row["user_broker_id"]}


async def refresh_accounts(load_new: bool = True) -> bool:
    """Sync every account's lot / Pause-Resume from the dashboard and load newly
    added accounts. Returns False when the DB can't be read (caller fails closed)."""
    loop = asyncio.get_running_loop()
    env_ids = [a["us_id"] for a in ACCOUNTS if a.get("source") == "env" and a.get("us_id")]
    rows = await loop.run_in_executor(
        None, lambda: apis.load_account_rows(apis.STRATEGY_ID, env_ids))
    if rows is None:
        return False
    by_id = {row["user_strategy_id"]: row for row in rows}
    env_meta = {(os.getenv("META_ACCOUNT_ID", "") or "").strip(),
                (os.getenv("TG2_META_ACCOUNT_ID", "") or "").strip()} - {""}

    for acc in ACCOUNTS:
        row = by_id.get(acc.get("us_id") or "")
        if row is None:
            # Row deleted (or env account never provisioned): no NEW entries.
            acc["entries"] = False
            continue
        acc["lot"] = row["lot_size"]
        acc["entries"] = row["entries"]
        acc["trade_sl"] = row.get("trade_sl_usd")
        acc["max_sl"] = row.get("max_sl_per_trade_usd")
        acc["ub_id"] = row.get("user_broker_id")

    # At signal time only the flags/Price/SL are synced (one quick query) —
    # loading + validating new accounts runs in the background refresher, so it
    # never delays an entry.
    if not load_new:
        return True
    if PRIORITY_STRATEGY_ID:
        global _priority_meta
        metas = await loop.run_in_executor(
            None, lambda: apis.load_strategy_meta_accounts(PRIORITY_STRATEGY_ID))
        if metas is not None:
            _priority_meta = metas
    if not DB_ACCOUNTS:
        return True
    known = {a.get("us_id") for a in ACCOUNTS}
    for row in rows:
        us_id = row["user_strategy_id"]
        if us_id in known or row["strategy_id"] != apis.STRATEGY_ID:
            continue
        if (row.get("meta_account_id") or "").strip() in env_meta:
            _log_bad_account(us_id, "[%s] is the same MetaAPI account as an env account "
                             "of this bot — not trading it twice", _db_label(us_id))
            continue
        if not row["entries"]:
            continue  # paused / archived — load it once it is resumed
        acc = await loop.run_in_executor(None, _new_db_account, row)
        if acc is None:
            continue
        ACCOUNTS.append(acc)
        ACCOUNTS_BY_LABEL[acc["label"]] = acc["client"]
        APIS_BY_LABEL[acc["label"]] = acc["apis"]
        log.info("[%s] dashboard account added (MetaAPI %s, lot %s)",
                 acc["label"], acc["meta_account_id"], acc["lot"] or "risk-based")
    return True


def _entry_accounts() -> list[dict]:
    """Accounts that take NEW signals: not paused on the dashboard, broker
    answered at the last check, and not drawdown-blocked for the broker day."""
    return [a for a in ACCOUNTS
            if a.get("entries", True) and a.get("healthy", True) and not _dd_blocked(a)]


# ── Drawdown guard (dashboard "Daily drawdown" / "Max drawdown") ──────────────
# Per MT5 account (UserBroker). Daily / Max drawdown are entered as USD amounts;
# the equity FLOORS are equity - amount (set when first seen, reset every new
# broker day). Every DD_POLL_SEC the guard reads each account's equity:
#   * equity <= a floor        -> close EVERY position + pending order on the
#                                 account (any symbol), no new trades until the
#                                 next broker day
#   * equity <= floor + buffer -> no new trades until the next broker day
#   * new broker day (broker midnight) -> floors reset from that day's starting
#     equity: daily = equity - daily amount, max = equity - max amount
# A floor that is already at/above equity when first seen (a typo) blocks new
# trades but never auto-closes — it closes only after equity was seen above it.
DD_POLL_SEC = float(os.getenv("TG_DD_POLL_SEC", "2"))
DD_BUFFER = float(os.getenv("TG_DD_BUFFER_USD", "10"))
DD_CONFIG_REFRESH_SEC = 10
DD_EQUITY_WRITE_SEC = 3          # equity shown live on the Neymar tabs
DD_CLOSE_RETRY_SEC = 5
DD_BROKER_TIME_REFRESH_SEC = 1800
_dd_state: dict[str, dict] = {}       # user_broker_id -> guard state
_dd_cfg: dict[str, dict] = {}         # user_broker_id -> DB settings (refreshed)
_dd_cfg_at = 0.0


def _dd_blocked(acc: dict) -> bool:
    st = _dd_state.get(acc.get("ub_id") or "")
    return bool(st and st.get("day") and st.get("blocked_day") == st.get("day"))


def _as_date(v):
    if v is None or hasattr(v, "year") and not isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v)).date()


async def _guard_account(loop, ub_id: str, client, cfg: dict) -> None:
    """One guard tick for one MT5 account."""
    now = datetime.now(timezone.utc)
    ts = now.timestamp()
    st = _dd_state.setdefault(ub_id, {"label": client.label})
    # Drawdown is set as USD amounts (daily_dd_offset / max_dd_offset) and the
    # floors are derived: equity - amount. A floor without an amount (set
    # directly) stays fixed.
    has_floor = any(cfg.get(k) is not None for k in
                    ("daily_dd_floor", "max_dd_floor", "daily_dd_offset", "max_dd_offset"))
    if not has_floor and ts - st.get("eq_polled", 0) < DD_EQUITY_WRITE_SEC:
        return                                   # no floors: equity for display only
    st["eq_polled"] = ts
    info = await loop.run_in_executor(None, client.get_account_information)
    if not info:
        return
    eq = float(info["equity"])
    st["equity"] = eq
    writes: dict = {}

    if has_floor:
        # Broker trading day (broker server midnight), offset refreshed half-hourly.
        if st.get("offset") is None or ts - st.get("offset_at", 0) > DD_BROKER_TIME_REFRESH_SEC:
            bt = await loop.run_in_executor(None, client.get_broker_time)
            if bt is not None:
                st["offset"] = bt - now.replace(tzinfo=None)
            st["offset_at"] = ts
        day = (now.replace(tzinfo=None) + (st.get("offset") or timedelta(0))).date()
        st["day"] = day
        daily, mx_ = cfg.get("daily_dd_floor"), cfg.get("max_dd_floor")
        d_amt, m_amt = cfg.get("daily_dd_offset"), cfg.get("max_dd_offset")
        dd_day = _as_date(cfg.get("dd_day"))
        new_day = dd_day is not None and dd_day < day
        if d_amt is not None and (daily is None or new_day):
            daily = round(eq - float(d_amt), 2)
            writes["daily_dd_floor"] = cfg["daily_dd_floor"] = daily
        if m_amt is not None and (mx_ is None or new_day):
            mx_ = round(eq - float(m_amt), 2)
            writes["max_dd_floor"] = cfg["max_dd_floor"] = mx_
        if dd_day is None or new_day:
            writes["dd_day"] = cfg["dd_day"] = day
        if new_day:
            log.warning("[%s] NEW BROKER DAY %s — equity %.2f, daily floor %s, max floor %s",
                        client.label, day, eq, daily, mx_)
        floors = [(n, f) for n, f in (("daily", daily), ("max", mx_)) if f is not None]

        key = tuple(floors)
        if st.get("cfg_key") != key:                         # new / edited floors
            st["cfg_key"] = key
            st["armed"] = all(eq > f for _, f in floors)
            if not st["armed"]:
                log.error("[%s] drawdown floor %s is not below equity %.2f — blocking new "
                          "trades, NOT closing (check the setting)", client.label, floors, eq)
        elif not st.get("armed") and all(eq > f + DD_BUFFER for _, f in floors):
            st["armed"] = True

        blocked_day = _as_date(cfg.get("dd_blocked_day"))
        breached = [n for n, f in floors if eq <= f]
        near = [n for n, f in floors if eq <= f + DD_BUFFER]
        if breached and st["armed"]:
            status = f"breached_{breached[0]}"
            if blocked_day != day or ts - st.get("closed_at", 0) >= DD_CLOSE_RETRY_SEC:
                st["closed_at"] = ts
                res = await loop.run_in_executor(None, client.close_everything)
                if res["positions"] or res["orders"] or blocked_day != day:
                    log.error("[%s] DRAWDOWN BREACH (%s): equity %.2f <= floor %s — closed "
                              "%d position(s), cancelled %d order(s), failed %d, flat=%s",
                              client.label, breached[0], eq, dict(floors)[breached[0]],
                              res["positions"], res["orders"], res["failed"], res["complete"])
        elif breached:
            status = "floor_above_equity"
        elif near:
            status = f"near_{near[0]}"
        elif blocked_day == day:
            status = st.get("status") or "blocked_today"
            status = status if status.startswith(("breached", "near", "floor")) else "blocked_today"
        else:
            status = "ok"
        if (breached or near) and blocked_day != day:
            writes["dd_blocked_day"] = cfg["dd_blocked_day"] = blocked_day = day
            log.warning("[%s] equity %.2f within %.0f of %s floor — no new trades until the "
                        "next broker day", client.label, eq, DD_BUFFER, (breached or near)[0])
        st["blocked_day"] = blocked_day
    else:
        status = ""
        st["blocked_day"] = None                 # floors removed: nothing to block
    if status != st.get("status"):
        st["status"] = writes["dd_status"] = status
    if writes or ts - st.get("eq_written", 0) >= DD_EQUITY_WRITE_SEC:
        st["eq_written"] = ts
        writes["dd_equity"] = round(eq, 2)
        writes["dd_equity_at"] = now
        await loop.run_in_executor(None, lambda: apis.save_drawdown(ub_id, **writes))


async def check_drawdown() -> None:
    """One guard pass over every distinct MT5 account this bot trades."""
    global _dd_cfg, _dd_cfg_at
    loop = asyncio.get_running_loop()
    by_ub: dict[str, object] = {}
    for a in ACCOUNTS:
        if a.get("ub_id") and a["ub_id"] not in by_ub:
            by_ub[a["ub_id"]] = a["client"]
    if not by_ub:
        return
    ts = datetime.now(timezone.utc).timestamp()
    if ts - _dd_cfg_at >= DD_CONFIG_REFRESH_SEC or set(by_ub) - set(_dd_cfg):
        rows = await loop.run_in_executor(None, lambda: apis.load_drawdown_rows(list(by_ub)))
        if rows is not None:
            _dd_cfg, _dd_cfg_at = rows, ts
    items = [(ub, client) for ub, client in by_ub.items() if ub in _dd_cfg]
    results = await asyncio.gather(*(_guard_account(loop, ub, client, _dd_cfg[ub])
                                      for ub, client in items), return_exceptions=True)
    for (ub, client), res in zip(items, results):
        if isinstance(res, Exception):
            log.error("[%s] drawdown guard tick failed: %r", client.label, res)


async def _drawdown_guard() -> None:
    while True:
        await asyncio.sleep(DD_POLL_SEC)
        try:
            await check_drawdown()
        except Exception as e:
            log.exception(f"drawdown guard error: {e}")


async def _account_refresher() -> None:
    while True:
        await asyncio.sleep(ACCOUNT_REFRESH_SEC)
        try:
            await refresh_accounts()
        except Exception as e:
            log.exception(f"account refresher error: {e}")


def is_malformed(sig: dict) -> str | None:
    em = (sig["entry_low"] + sig["entry_high"]) / 2
    if sig["side"] == "buy" and sig["sl"] >= em:
        return "buy SL above entry"
    if sig["side"] == "sell" and sig["sl"] <= em:
        return "sell SL below entry"
    if not sig["tps"]:
        return "no TPs"
    if sig["side"] == "buy" and any(tp <= em for tp in sig["tps"]):
        return "buy TP below entry"
    if sig["side"] == "sell" and any(tp >= em for tp in sig["tps"]):
        return "sell TP above entry"
    return None


def _signal_entry(sig: dict) -> float:
    """The near-edge entry price place_order uses (sell->low, buy->high)."""
    return sig["entry_low"] if sig["side"] == "sell" else sig["entry_high"]


# Every signal is traded as exactly TG_LEG_COUNT legs (default 5): extra TPs are
# dropped, and when the channel gives fewer the LAST TP is repeated (3 TPs ->
# TP1, TP2, TP3, TP3, TP3). 0 = one leg per TP as posted.
LEG_COUNT = int(os.getenv("TG_LEG_COUNT", "5"))
# "Breakeven / zero risk" from the channel: close every open leg except the
# BE_KEEP_LEGS with the farthest TPs, which keep running with their stop moved
# to entry. 0 = old behaviour (stop to entry on every leg, nothing closed).
BE_KEEP_LEGS = int(os.getenv("TG_BE_KEEP_LEGS", "2"))


def order_tps(sig: dict) -> list[float | None]:
    """TP levels to actually place — one broker order per element.

    `sig["tps"]` stays purely numeric: it is persisted to tg_signals and mirrored
    to the dashboard, and a None in there would propagate into both. The
    open-ended runner is appended only here, as a None, so it reaches the broker
    as a stop-only leg without polluting the stored signal.
    """
    tps: list[float | None] = list(sig["tps"])
    if TP_OPEN_LEG and sig.get("tp_open"):
        tps.append(None)
    if LEG_COUNT > 0 and tps:
        tps = tps[:LEG_COUNT]
        tps += [tps[-1]] * (LEG_COUNT - len(tps))
    return tps


def dedup_key(sig: dict) -> str:
    """Identity of a signal for repost detection.

    Deliberately the TRADE, not the text: the channel reposts the same setup with
    incidental wording differences, and two posts naming the same side, zone,
    stop and targets are the same trade whatever the prose around them says.
    """
    return "|".join([
        sig["instrument"], sig["side"],
        f"{sig['entry_low']:.2f}", f"{sig['entry_high']:.2f}", f"{sig['sl']:.2f}",
        ",".join(f"{t:.2f}" for t in sig["tps"]),
    ])


async def _is_repost(sig: dict, signal_ts: float) -> bool:
    """True when this exact trade was already seen inside the dedup window.

    Disabled (always False) when DEDUP_WINDOW_SEC is 0, which is the default and
    what the free channel runs with.

    The timestamp is refreshed even on a hit, so a third repost is measured from
    the second, not the first — a channel that spams the same setup five times
    over twenty minutes is still posting one trade.
    """
    if DEDUP_WINDOW_SEC <= 0:
        return False
    key = f"{REDIS_PREFIX}:dedup:{dedup_key(sig)}"
    prev = await r.get(key)
    await r.set(key, str(signal_ts))
    if prev is None:
        return False
    try:
        return (signal_ts - float(prev)) < DEDUP_WINDOW_SEC
    except (TypeError, ValueError):
        return False


def _record_signals(sig: dict, *, status: str, reason: str = "",
                    rejection_reason: str = "", signal_at=None,
                    only_labels=None, pos_ids: dict | None = None) -> None:
    """Best-effort StrategySignal row per account so the dashboard Signals tab
    shows this telegram signal (one row per platform Strategy, matching the
    per-account positions). Blocking (DB) — call via run_in_executor. Never
    raises: apis.record_signal swallows its own errors."""
    entry = _signal_entry(sig)
    tp = sig["tps"][0] if sig.get("tps") else None
    for acc in ACCOUNTS:
        if only_labels is not None and acc["label"] not in only_labels:
            continue
        if acc.get("source") == "db":
            continue  # same Strategy as the primary — its row already shows the signal
        dash = acc.get("apis")
        if dash is None:
            continue
        dash.record_signal(sig["side"], entry, sig["sl"], tp, status=status,
                           reason=reason, rejection_reason=rejection_reason,
                           signal_at=signal_at,
                           position_id=(pos_ids or {}).get(acc["label"]))


# ── Trade SL ladder (dashboard "Trade SL" / "Max SL per trade") ───────────────
# Trade SL = total USD the account may lose on one signal, split evenly across
# the TP legs. A leg is never stopped for more than Max SL per trade (default
# $90) at once: it enters with that stop, and each time the stop is hit it is
# re-entered at market with the SAME TP and the next chunk of its budget, until
# the budget is spent (e.g. $200/leg -> stops of 90, 90, 20). Re-entries stop
# as soon as the channel ends the signal (it leaves the :open set), its SL is
# managed (breakeven/move), or the account is paused / drawdown-blocked.
DEFAULT_MAX_SL_PER_TRADE = 90.0
LADDER_MIN_CHUNK_USD = 1.0          # a remaining budget below this is not worth a re-entry
LADDER_ATTEMPT_STRIDE = 100         # re-entry k of leg i is tagged tp(i + 100*k)


def _ladder_sl_price(side: str, ref_price: float, loss_usd: float, volume: float,
                     min_d: float | None) -> tuple[float, float]:
    """SL price so that `volume` lots lose `loss_usd` from `ref_price`, never
    closer than the broker's stops level. Returns (sl_price, planned_loss_usd)."""
    dist = loss_usd / (volume * USD_PER_POINT_PER_LOT)
    if min_d and dist < min_d:
        dist = min_d          # broker floor: the planned loss grows slightly
    sl = ref_price - dist if side == "buy" else ref_price + dist
    return round(sl, 2), round(dist * volume * USD_PER_POINT_PER_LOT, 2)


def _leg_cap(acc: dict | None) -> float:
    """Most USD one stop may lose on this account (dashboard Max SL per trade)."""
    return float((acc or {}).get("max_sl") or DEFAULT_MAX_SL_PER_TRADE)


def _ladder_plan(acc: dict, plan: dict | None, side: str, entry: float,
                 total_vol: float, n_legs: int) -> tuple[dict | None, dict[int, dict]]:
    """Account-specific copy of the shared plan with each leg's stop limited to
    the account's Max SL per trade. Returns (plan, {leg index: ladder meta}).

    * Trade SL set: each leg's budget is Trade SL / legs, first stop = min(cap,
      budget) — the channel's SL is not used.
    * No Trade SL: the channel's SL stands unless one leg would lose more than
      the cap there; then that leg stops at the cap and re-enters until the
      channel's SL distance (its budget) is used.
    Legs without meta keep the plan's SL and never re-enter."""
    if plan is None or n_legs <= 0:
        return plan, {}
    vol_each = round(total_vol / n_legs, 2)
    if vol_each <= 0:
        return plan, {}
    cap = _leg_cap(acc)
    ref = plan.get("cur") if plan.get("use_market") and plan.get("cur") else entry
    min_d = plan.get("min_d")
    trade_sl = acc.get("trade_sl")
    levels, metas = [], {}
    for i, (o_sl, tp) in enumerate(plan["levels"], start=1):
        if trade_sl:
            budget = float(trade_sl) / n_legs
        else:
            budget = abs(ref - o_sl) * vol_each * USD_PER_POINT_PER_LOT
            if budget <= cap + 0.01:
                levels.append((o_sl, tp))          # channel SL within the cap
                continue
        sl, planned = _ladder_sl_price(side, ref, min(cap, budget), vol_each, min_d)
        levels.append((sl, tp))
        metas[i] = {"budget": round(budget, 2), "cap": cap, "used": planned,
                    "last": planned, "attempt": 0}
    if not metas:
        return plan, {}
    acc_plan = dict(plan)
    acc_plan["levels"] = levels
    return acc_plan, metas


def _dd_room(acc: dict | None, extra_loss_usd: float) -> bool:
    """True when losing `extra_loss_usd` more would still leave equity above
    every drawdown floor (+ buffer) of the account. True when the account has no
    floors or its equity isn't known yet."""
    ub = (acc or {}).get("ub_id") or ""
    st, cfg = _dd_state.get(ub), _dd_cfg.get(ub)
    if not st or not cfg or st.get("equity") is None:
        return True
    left = float(st["equity"]) - extra_loss_usd
    return all(f is None or left > float(f) + DD_BUFFER
               for f in (cfg.get("daily_dd_floor"), cfg.get("max_dd_floor")))


async def _ladder_reenter(loop, pos: dict, msg_id: int, o: dict, label: str, pnl) -> dict | None:
    """After leg `o` was stopped out, re-enter it at market with the same TP and
    the next chunk of its Trade SL budget. Returns the new slice, or None."""
    lad = o.get("ladder")
    if not lad or lad.get("stopped") or lad.get("reentered"):
        return None
    # Only a real stop-out (a loss of at least half the planned chunk) re-enters
    # — not a breakeven / tiny-loss close.
    if pnl is None or float(pnl) > -0.5 * float(lad.get("last") or lad["used"]):
        return None
    remaining = float(lad["budget"]) - float(lad["used"])
    if remaining < LADDER_MIN_CHUNK_USD:
        return None
    acc = next((a for a in ACCOUNTS if a["label"] == label), None)
    if acc is None or acc not in _entry_accounts():
        return None                      # paused, unreachable or drawdown-blocked
    lad["reentered"] = True              # one re-entry per stopped leg, success or not
    client, side, symbol = acc["client"], pos["side"], pos["instrument"]
    px = await loop.run_in_executor(None, lambda: client.get_symbol_price(symbol))
    if not px:
        log.warning("[%s:%s] TP%s re-entry skipped — no price", msg_id, label, o["tp_index"])
        return None
    min_d = await loop.run_in_executor(None, lambda: client.stops_level_price(symbol))
    ref = px["ask"] if side == "buy" else px["bid"]
    tp = o.get("tp")
    if tp is not None and ((side == "buy" and tp <= ref + min_d) or
                           (side == "sell" and tp >= ref - min_d)):
        log.info("[%s:%s] TP%s re-entry skipped — price already at/through TP %.2f",
                 msg_id, label, o["tp_index"], tp)
        return None
    vol = float(o["volume"])
    chunk = min(float(lad["cap"]), remaining)
    if not _dd_room(acc, chunk):
        log.warning("[%s:%s] TP%s re-entry skipped — a $%.2f stop would reach the drawdown "
                    "limit", msg_id, label, o["tp_index"], chunk)
        return None
    sl, planned = _ladder_sl_price(side, ref, chunk, vol, min_d)
    attempt = int(lad.get("attempt", 0)) + 1
    idx = int(lad["base"]) + LADDER_ATTEMPT_STRIDE * attempt
    tid = await loop.run_in_executor(None, lambda: client.place_market_order_full(
        side, symbol, vol, sl, tp, f"tg-{msg_id}-tp{idx}"))
    if not tid:
        log.error("[%s:%s] TP%s re-entry order FAILED", msg_id, label, o["tp_index"])
        return None
    new = {"tp_index": idx, "tp": tp, "ticket_id": tid, "kind": "market", "volume": vol,
           "entry": ref, "sl": sl, "account": label, "broker_state": "filled",
           # A market fill we just placed: count it as seen so a fast stop-out is
           # still concluded from its absence (never left dangling).
           "observed": True, "miss": 0,
           "ladder": {"budget": lad["budget"], "cap": lad["cap"],
                      "used": round(float(lad["used"]) + planned, 2), "last": planned,
                      "attempt": attempt, "base": lad["base"]}}
    await loop.run_in_executor(None, lambda: db.insert_order(msg_id, new))
    log.warning("[%s:%s] RE-ENTRY %d of leg %s: %s %.2f @ %.2f SL %.2f (-$%.2f) TP %s "
                "— budget used %.2f/%.2f", msg_id, label, attempt, lad["base"], side, vol, ref,
                sl, planned, "open" if tp is None else tp, new["ladder"]["used"], lad["budget"])
    return new


async def place_order(msg_id: int, sig: dict, accounts: list[dict] | None = None) -> dict:
    """Place one MetaAPI order per TP at the NEAR edge of the entry zone, shared SL.

    The near edge is the price the market touches first as it retraces into the
    zone, so a shallower pullback fills us and we participate more often:
      sell -> entry_low  (price rises into the zone, hits the low edge first)
      buy  -> entry_high (price falls into the zone, hits the high edge first)
    Risk/volume, breakeven, and the recorded entry all derive from this price.
    """
    entry_mid = sig["entry_low"] if sig["side"] == "sell" else sig["entry_high"]
    risk_pts = abs(entry_mid - sig["sl"])

    loop = asyncio.get_running_loop()

    # ── Build ONE order plan shared by every account ──────────────────────────
    # Mirrored accounts must place IDENTICAL SL/TP levels (only the fill price may
    # differ, by broker spread). So we decide the plan once — using the STRICTEST
    # stops-floor across all accounts (so it satisfies every broker) and the
    # reference (first/primary) account's price for the market-vs-limit call —
    # instead of letting each account re-decide against its own price/spec, which
    # is what made neymar2 widen a TP differently and miss fills primary caught.
    accounts = _entry_accounts() if accounts is None else accounts
    stops = await asyncio.gather(*(
        loop.run_in_executor(None, lambda c=acc["client"]: c.stops_level_price(sig["instrument"]))
        for acc in accounts), return_exceptions=True)
    min_ds = [s for s in stops if isinstance(s, (int, float))]
    min_d = max(min_ds) if min_ds else None
    ref_client = ACCOUNTS[0]["client"]
    otps = order_tps(sig)   # numeric TPs, plus the open-ended runner as None
    try:
        plan = await loop.run_in_executor(
            None, lambda: ref_client.build_order_plan(
                sig["side"], sig["instrument"], entry_mid, sig["sl"], otps,
                min_distance=min_d))
    except Exception:
        log.exception("[%s] build_order_plan raised — each account will self-plan", msg_id)
        plan = None

    async def _submit_for_account(acc: dict) -> tuple[str, list[dict], float]:
        """Submit one account's slices and tag them. Returns (label, slices,
        account_volume). Swallows its own broker errors so one account failing
        can never abort another whose orders may already be live at the broker."""
        client, label = acc["client"], acc["label"]
        if acc.get("lot"):
            # Fixed "Price" from the dashboard: the TOTAL lot for this signal,
            # split evenly across the TP legs by submit_signal_orders.
            total_vol = float(acc["lot"])
        else:
            total_vol = acc["risk_usd"] / (risk_pts * USD_PER_POINT_PER_LOT)
        total_vol = max(total_vol, MIN_LOT * len(otps))
        acc_plan, ladders = _ladder_plan(acc, plan, sig["side"], entry_mid, total_vol, len(otps))
        try:
            submitted = await loop.run_in_executor(
                None,
                lambda c=client, v=total_vol, pl=acc_plan: c.submit_signal_orders(
                    side=sig["side"],
                    symbol=sig["instrument"],
                    entry=entry_mid,
                    sl=sig["sl"],
                    tps=otps,
                    total_volume=v,
                    msg_id=msg_id,
                    plan=pl,
                ),
            )
        except Exception:
            log.exception("[%s:%s] submit_signal_orders raised", msg_id, label)
            submitted = []
        # Seed per-slice broker bookkeeping the reconciler maintains: a market
        # slice is born "filled", a limit "pending". `observed` flips True once we
        # actually see the slice at the broker, so absence can only conclude a
        # slice we confirmed existed (never a just-placed order not yet listed).
        # Each slice is tagged with its account so modify/close/reconcile route
        # to the right broker.
        for o in submitted:
            o["account"] = label
            o["broker_state"] = "filled" if o.get("kind") == "market" else "pending"
            o["observed"] = False
            o["miss"] = 0
            if o["tp_index"] in ladders:
                o["ladder"] = dict(ladders[o["tp_index"]], base=o["tp_index"])
        if not submitted:
            log.warning("[%s:%s] no orders submitted for this account", msg_id, label)
        acct_vol = (round(sum(float(o["volume"]) for o in submitted), 2)
                    if submitted else total_vol)
        return label, submitted, acct_vol

    # Fan out to every account CONCURRENTLY so each makes its entry decision (price
    # fetch + market-vs-limit) at the same wall-clock instant. Sequential
    # submission made later accounts decide several broker round-trips behind the
    # first, fetching a worse price on a fast retrace — our-side fill divergence.
    results = await asyncio.gather(*(_submit_for_account(acc) for acc in accounts))

    all_orders: list[dict] = []
    primary_vol: float | None = None
    for label, submitted, acct_vol in results:
        all_orders.extend(submitted)
        if label == "primary":
            primary_vol = acct_vol

    return {
        "msg_id": msg_id,
        "instrument": sig["instrument"],
        "side": sig["side"],
        "entry_lo": sig["entry_low"],
        "entry_hi": sig["entry_high"],
        "entry_mid": entry_mid,
        "sl": sig["sl"],
        "tps": sig["tps"],
        # total_volume drives the (primary-only) dashboard + audit row.
        "total_volume": primary_vol if primary_vol is not None else 0.0,
        "risk_pts": risk_pts,
        "orders": all_orders,
        "status": "submitted" if all_orders else "rejected",
        "dry_run": DRY_RUN,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }


async def modify_sl(msg_id: int, new_sl: float, *, managed: bool = True):
    """Move the stop of every leg of a signal.

    managed=True (channel "move SL to X" / typo fix), per account:
      * a leg that would lose more than Max SL per trade at X stops at the cap
        instead and re-enters after that stop until X's loss is used (ladder);
      * a move that ADDS risk is skipped when the worst case (every leg stopped
        + remaining re-entries) would take equity to a drawdown floor.
    managed=False (breakeven): every leg goes to X, re-entries end."""
    key = f"{REDIS_PREFIX}:signal:{msg_id}"
    pos_json = await r.get(key)
    if not pos_json:
        return
    pos = json.loads(pos_json)
    pos["sl"] = new_sl
    pos["sl_history"] = pos.get("sl_history", []) + [{"sl": new_sl, "at": datetime.now(timezone.utc).isoformat()}]
    loop = asyncio.get_running_loop()
    buy = pos["side"] == "buy"
    sign = 1 if buy else -1
    live = [o for o in pos.get("orders", []) if o.get("broker_state") not in ("closed", "cancelled")]

    by_label: dict[str, list[dict]] = {}
    for o in live:
        by_label.setdefault(o.get("account", "primary"), []).append(o)
    for label, legs in by_label.items():
        client = ACCOUNTS_BY_LABEL.get(label)
        if client is None:
            continue
        acc = next((a for a in ACCOUNTS if a["label"] == label), None)
        targets: list[tuple[dict, float, dict | None]] = []
        if managed:
            cap = _leg_cap(acc)
            px = await loop.run_in_executor(None, lambda c=client: c.get_symbol_price(pos["instrument"]))
            cur = (px["bid"] if buy else px["ask"]) if px else None
            new_risk = old_risk = 0.0
            for o in legs:
                v = float(o["volume"])
                e = float(o.get("fill_price") or o.get("entry") or pos["entry_mid"])
                target_loss = max(0.0, (e - new_sl) * sign) * v * USD_PER_POINT_PER_LOT
                if target_loss > cap + 0.01:
                    eff = round(e - sign * cap / (v * USD_PER_POINT_PER_LOT), 2)
                    lad = o.get("ladder") or {}
                    meta = {"budget": round(target_loss, 2), "cap": cap, "used": cap, "last": cap,
                            "attempt": lad.get("attempt", 0), "base": lad.get("base", o["tp_index"])}
                else:
                    eff, meta = new_sl, None
                targets.append((o, eff, meta))
                if cur is not None:
                    new_risk += max(0.0, (cur - eff) * sign) * v * USD_PER_POINT_PER_LOT
                    new_risk += (meta["budget"] - meta["used"]) if meta else 0.0
                    old_sl = float(o.get("sl") or pos["sl"])
                    old_risk += max(0.0, (cur - old_sl) * sign) * v * USD_PER_POINT_PER_LOT
                    old_lad = o.get("ladder") or {}
                    if old_lad and not old_lad.get("stopped"):
                        old_risk += max(0.0, float(old_lad["budget"]) - float(old_lad["used"]))
            if cur is not None and new_risk > old_risk and not _dd_room(acc, new_risk):
                log.warning("[%s:%s] SL move to %.2f SKIPPED — worst-case loss $%.2f would reach "
                            "the drawdown limit; keeping the current stop", msg_id, label,
                            new_sl, new_risk)
                continue
        else:
            targets = [(o, new_sl, None) for o in legs]

        for o, eff, meta in targets:
            # POSITION_MODIFY only applies once filled; pending limits ignore the call.
            await loop.run_in_executor(None, client.modify_position_sl, o["ticket_id"], eff,
                                       o.get("tp"))   # keep the TP (see modify_position_sl)
            o["sl"] = eff
            if meta:
                o["ladder"] = meta                  # re-enter after this capped stop
            elif o.get("ladder"):
                o["ladder"]["stopped"] = True       # stop within the cap: no re-entries
        if managed and any(m for _, _, m in targets):
            log.info("[%s:%s] SL %.2f exceeds $%.0f per trade — legs stopped at the cap and will "
                     "re-enter up to it", msg_id, label, new_sl, _leg_cap(acc))

    await r.set(key, json.dumps(pos))
    await loop.run_in_executor(None, db.update_sl, msg_id, new_sl)
    log.info(f"[{msg_id}] SL modified -> {new_sl} ({'DRY' if DRY_RUN else 'LIVE'})")


async def move_to_breakeven(msg_id: int):
    key = f"{REDIS_PREFIX}:signal:{msg_id}"
    pos_json = await r.get(key)
    if not pos_json:
        return
    pos = json.loads(pos_json)
    await modify_sl(msg_id, pos["entry_mid"], managed=False)


async def apply_management(msg_id: int, text: str, parent_id: int | None) -> dict | None:
    """Act on a position-management instruction. Returns the action taken, or None.

    Off unless TG_ACT_ON_MANAGEMENT is set, so the free channel's copy behaves
    exactly as it always has.

    Order matters: the stop change is applied BEFORE any close, so a close that
    fails at the broker still leaves the position protected at its new stop
    rather than at the original one.
    """
    if not ACT_ON_MANAGEMENT:
        return None
    action = classify_management(text)
    if not action:
        return None

    open_ids = await r.smembers(f"{REDIS_PREFIX}:open")
    target = resolve_target(parent_id, sorted(int(i) for i in open_ids))
    if target is None:
        log.warning("[%s] management %s but no unambiguous target (%d open) — ignored",
                    msg_id, action, len(open_ids))
        return None

    if "move_sl" in action:
        log.info("[%s] management: move SL -> %s (signal %s)", msg_id, action["move_sl"], target)
        await modify_sl(target, action["move_sl"])
    elif action.get("breakeven"):
        log.info("[%s] management: breakeven (signal %s)", msg_id, target)
        if BE_KEEP_LEGS > 0:
            await breakeven_partial(target)
        else:
            await move_to_breakeven(target)

    if action.get("close") == "all":
        log.info("[%s] management: close all (signal %s)", msg_id, target)
        await close_order(target, "channel_close")
    elif action.get("close") == "half":
        # Deliberately NOT implemented. "Close half" appears twice in 13 months
        # of channel history, and a partial close cuts straight through the
        # slice/deal matching that caused the 2026-08-11 P&L corruption. Leaving
        # the position running under its own TPs and (just-moved) stop is the
        # safe failure: it under-closes rather than over-closes. Logged loudly so
        # it is visible if the channel ever starts doing it often.
        log.warning("[%s] management: 'close half' is not supported — position left "
                    "running under its existing TPs/SL (signal %s)", msg_id, target)
    return action


async def _close_slices(loop, msg_id: int, slices: list[dict], reason: str) -> None:
    """Close / cancel these slices at the broker and settle each one."""
    for o in slices:
        client = ACCOUNTS_BY_LABEL.get(o.get("account", "primary"))
        if client is None:
            continue
        was_filled = o.get("broker_state") == "filled" or o["kind"] != "limit"
        if o["kind"] == "limit" and o.get("broker_state") != "filled":
            await loop.run_in_executor(None, client.cancel_order, o["ticket_id"])
        else:
            await loop.run_in_executor(None, client.close_position, o["ticket_id"])
        if o.get("broker_state") in ("closed", "cancelled"):
            continue                    # already settled (reconcile got there first)
        if was_filled:
            # We just closed it, so history-deals may not have settled yet;
            # _slice_realized_pnl falls back to the last live snapshot.
            val = await _slice_realized_pnl(loop, client, o)
            o["broker_state"], o["realized_pnl"] = "closed", val
            await loop.run_in_executor(None, db.record_slice_close,
                                       msg_id, o["tp_index"], o["ticket_id"],
                                       reason, val)
        else:
            o["broker_state"] = "cancelled"
            await loop.run_in_executor(None, db.record_slice_close,
                                       msg_id, o["tp_index"], o["ticket_id"],
                                       "cancelled", None)



async def breakeven_partial(msg_id: int) -> None:
    """Channel said breakeven / zero risk: exit every open leg except the
    BE_KEEP_LEGS with the farthest TPs; those keep running with SL at entry."""
    key = f"{REDIS_PREFIX}:signal:{msg_id}"
    pos_json = await r.get(key)
    if not pos_json:
        return
    pos = json.loads(pos_json)
    for o in pos.get("orders", []):
        if o.get("ladder"):
            o["ladder"]["stopped"] = True     # no more SL re-entries after breakeven
    live = [o for o in pos.get("orders", []) if o.get("broker_state") not in ("closed", "cancelled")]
    buy = pos["side"] == "buy"
    # Farthest TP first; the open-ended runner (tp None) counts as the farthest.
    far = sorted(live, key=lambda o: (o.get("tp") is None,
                                      (o.get("tp") or 0) * (1 if buy else -1),
                                      o["tp_index"]), reverse=True)
    keep, close = far[:BE_KEEP_LEGS], far[BE_KEEP_LEGS:]
    loop = asyncio.get_running_loop()
    if close:
        await _close_slices(loop, msg_id, close, "breakeven_exit")
        for o in close:                       # flatten their dashboard rows now
            if o.get("broker_state") == "closed":
                await _conclude_slice_row(loop, APIS_BY_LABEL.get(o.get("account", "primary")),
                                          pos, o, "breakeven_exit")
    for o in keep:
        client = ACCOUNTS_BY_LABEL.get(o.get("account", "primary"))
        if client is not None and o.get("broker_state") == "filled":
            await loop.run_in_executor(None, client.modify_position_sl, o["ticket_id"],
                                       pos["entry_mid"], o.get("tp"))
        o["sl"] = pos["entry_mid"]
    await r.set(key, json.dumps(pos))
    log.info("[%s] BREAKEVEN: exited %d leg(s), kept %d at entry %.2f (%s)", msg_id,
             len(close), len(keep), pos["entry_mid"], "DRY" if DRY_RUN else "LIVE")


async def close_order(msg_id: int, reason: str):
    key = f"{REDIS_PREFIX}:signal:{msg_id}"
    pos_json = await r.get(key)
    if not pos_json:
        return
    pos = json.loads(pos_json)

    loop = asyncio.get_running_loop()

    # Close at the broker AND settle each leg in the same pass. Ending a signal
    # from a channel reply takes it out of the ':open' set, so reconcile_broker
    # can never revisit it — whatever we fail to record here is lost for good.
    # (Signal 11001, 2026-08-10: legs 2-4 sat 'filled' with NULL realized while
    # the broker had paid +25.24/+25.36/+24.72.)
    await _close_slices(loop, msg_id, pos.get("orders", []), reason)

    pos["status"] = f"closed_{reason}"
    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
    await r.set(key, json.dumps(pos))
    await r.srem(f"{REDIS_PREFIX}:open", str(msg_id))

    # conclude_signal, not close_signal: the latter stamps status only, leaving
    # realized_pnl NULL on every reply-closed signal.
    settled = [o.get("realized_pnl") for o in pos.get("orders", [])
               if o.get("broker_state") == "closed" and o.get("realized_pnl") is not None]
    total = round(sum(settled), 2) if settled else None
    await loop.run_in_executor(None, db.conclude_signal, msg_id, reason, total)

    # Mirror the close into each slice's own dashboard row. The quantity>0 guard
    # in conclude_position makes this a no-op if broker reconciliation already
    # concluded that row, and never-filled legs have no row.
    for acc in ACCOUNTS:
        label, dash = acc["label"], acc.get("apis")
        if dash is None:
            continue
        for o in pos.get("orders", []):
            if o.get("account", "primary") != label:
                continue
            pid = o.get("apis_pos_id")
            if not pid or o.get("broker_state") != "closed":
                continue
            await loop.run_in_executor(
                None, lambda d=dash, p=pid, rl=o.get("realized_pnl"),
                cp=o.get("last_price"), v=float(o["volume"]):
                d.conclude_position(p, rl, cp, pos["side"], v, reason))
    log.info(f"[{msg_id}] CLOSE ({reason}) realized={total}")


async def sweep_stale_open() -> int:
    """Expire signals open longer than MAX_OPEN_AGE_SEC.

    Closes their remaining broker orders and drops them from the :open set so a
    signal the channel never resolves (TP1/TP2 then silence) can't wedge the
    no-pyramiding guard forever. Returns the number expired.
    """
    open_ids = await r.smembers(f"{REDIS_PREFIX}:open")
    now = datetime.now(timezone.utc)
    expired = 0
    for sid in open_ids:
        pos_json = await r.get(f"{REDIS_PREFIX}:signal:{sid}")
        if not pos_json:
            await r.srem(f"{REDIS_PREFIX}:open", sid)  # dangling id, no detail row
            continue
        pos = json.loads(pos_json)
        stamp = pos.get("opened_at") or pos.get("posted_at")
        if not stamp:
            continue
        try:
            age = (now - datetime.fromisoformat(stamp)).total_seconds()
        except ValueError:
            continue
        if age > MAX_OPEN_AGE_SEC:
            log.warning("[%s] open %.1fh > max %.1fh — expiring (flatten + unblock)",
                        sid, age / 3600, MAX_OPEN_AGE_SEC / 3600)
            await close_order(int(sid), "expired")
            expired += 1
    return expired


async def _stale_sweeper() -> None:
    """Periodically expire stale open signals even when no new signal arrives."""
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SEC)
        try:
            n = await sweep_stale_open()
            if n:
                log.info("Background stale-sweep expired %d open signal(s)", n)
        except Exception as e:
            log.exception(f"stale sweeper error: {e}")


async def _slice_realized_pnl(loop, client, o: dict):
    """Best-effort broker-TRUE realized PnL for a filled slice that has left (or
    is leaving) the broker.

    Prefers the settled figure from MetaAPI history deals; falls back to the last
    live `profit` snapshot when the deal lookup is unavailable or the position
    hasn't settled in history yet — so a close is never lost waiting on deals.
    Side effects: stamps o['last_price'] with the real close price and
    o['pnl_source'] ('deal' | 'snapshot') when a settled deal is found. Returns
    the realized PnL (float | None).
    """
    bpid = o.get("broker_position_id")
    deal = None
    if client is not None and bpid:
        deal = await loop.run_in_executor(
            None, lambda c=client, p=bpid: c.get_position_realized_pnl(p))
    if deal and deal.get("closed"):
        if deal.get("close_price") is not None:
            o["last_price"] = deal["close_price"]
        o["pnl_source"] = "deal"
        return deal["realized_pnl"]
    o["pnl_source"] = "snapshot"
    return o.get("last_profit")


def _slice_entry_px(pos: dict, o: dict) -> float:
    """This slice's own broker fill price, falling back to the signal entry."""
    fp = o.get("fill_price")
    return float(fp) if fp is not None else float(pos["entry_mid"])


def _slice_broker_ref(o: dict) -> str | None:
    """The MetaAPI *position* id for this slice — what history-deals keys on,
    and what fill_reconciler matches the dashboard row back to. Falls back to
    the order ticket (they coincide for market fills, differ for limit fills).
    """
    return str(o.get("broker_position_id") or o.get("ticket_id") or "") or None


async def _ensure_slice_row(loop, dash, pos: dict, o: dict) -> str | None:
    """Create this slice's dashboard row once, remembering it on the slice.

    One broker position == one dashboard row, so the Orders tab shows the real
    trades (0.03 x 4) instead of one averaged 0.12 fiction.
    """
    if o.get("apis_pos_id"):
        return o["apis_pos_id"]
    ref = _slice_broker_ref(o)
    # A restart rehydrates slices from tg_orders without their apis_pos_id;
    # re-link to the row that already exists for this broker ref before ever
    # creating one, or every restart doubles the live slices on the dashboard.
    pid = await loop.run_in_executor(
        None, lambda d=dash, t=ref: d.find_position_by_broker_ref(t))
    if not pid:
        pid = await loop.run_in_executor(
            None, lambda d=dash, e=_slice_entry_px(pos, o), v=float(o["volume"]),
            t=ref: d.open_position(pos["side"], e, v, t))
    if pid:
        o["apis_pos_id"] = pid
    return pid


async def _conclude_slice_row(loop, dash, pos: dict, o: dict, reason: str) -> None:
    """Flatten one closed slice's dashboard row with its own realized PnL, once.

    Creates the row first if the broker filled and closed the leg between polls
    (so the trade still shows). `apis_concluded` on the slice makes the call
    idempotent across the per-slice and end-of-signal paths; the DB side is
    guarded by `quantity > 0` as well.
    """
    if dash is None or o.get("apis_concluded"):
        return
    pid = await _ensure_slice_row(loop, dash, pos, o)
    if not pid:
        return
    await loop.run_in_executor(
        None, lambda d=dash, p=pid, rl=o.get("realized_pnl"),
        cp=o.get("last_price"), v=float(o["volume"]):
        d.conclude_position(p, rl, cp, pos["side"], v, reason))
    o["apis_concluded"] = True


def _infer_close_reason(last_price, last_profit, tp, sl) -> str:
    """Best-effort tp/sl call for a filled slice that left the broker.

    Realized PnL/close deals are not exposed over REST on this account, so we
    use the last live snapshot before the position vanished: a positive last
    profit means it ran to target, negative means it was stopped. Falls back to
    whichever of tp/sl the last seen price was nearer when profit is unknown.
    """
    if last_profit is not None:
        return "tp" if last_profit > 0 else "sl"
    if last_price is None:
        return "tp"
    if tp is None:  # "TP: open" runner leg -- only the stop can be recognised
        return "sl" if abs(last_price - sl) <= 1.0 else "tp"
    return "tp" if abs(last_price - tp) <= abs(last_price - sl) else "sl"


async def reconcile_broker() -> None:
    """Reconcile tracked signals against broker positions/orders (broker truth).

    Read-only against MetaAPI. Detects fills (pending limit -> live position),
    snapshots live PnL, and confirms slice closes/cancels. When every slice of a
    signal is terminal it concludes the signal from broker state — recording the
    real outcome + PnL and unblocking the no-pyramiding guard on reality, rather
    than waiting for a channel reply or the 12h stale-sweep.
    """
    open_ids = await r.smembers(f"{REDIS_PREFIX}:open")
    if not open_ids:
        return
    loop = asyncio.get_running_loop()
    symbol = next(iter(ALLOWED_INSTRUMENTS))

    # Build per-account tag maps from each account's own broker truth. Keeping
    # them per-account is the safety-critical bit: a slice is only ever matched
    # against positions/orders from ITS OWN account, never another's. If ANY
    # configured account can't be queried, skip this whole cycle and fail safe.
    acct_maps: dict[str, tuple[dict, dict]] = {}
    for acc in ACCOUNTS:
        client, label = acc["client"], acc["label"]
        positions = await loop.run_in_executor(None, lambda c=client: c.get_open_positions(symbol))
        orders = await loop.run_in_executor(None, lambda c=client: c.get_pending_orders(symbol))
        if positions is None or orders is None:
            if acc.get("source") == "db":
                # Its slices stay untouched (no maps) and it takes no new entries
                # until it answers again; the other accounts reconcile normally.
                acc["healthy"] = False
                log.warning("[%s] broker query failed — skipping this account this cycle", label)
                continue
            return  # could not verify a broker — skip this cycle, fail safe
        acc["healthy"] = True
        pos_by_tag, ord_by_tag = {}, {}
        for p in positions:
            m = _TAG_RE.search(p.get("comment") or "")
            if m:
                pos_by_tag[(int(m.group(1)), int(m.group(2)))] = p
        for o in orders:
            m = _TAG_RE.search(o.get("comment") or "")
            if m:
                ord_by_tag[(int(m.group(1)), int(m.group(2)))] = o
        acct_maps[label] = (pos_by_tag, ord_by_tag)

    for sid in open_ids:
        key = f"{REDIS_PREFIX}:signal:{sid}"
        pos_json = await r.get(key)
        if not pos_json:
            continue
        pos = json.loads(pos_json)
        sid_i = int(sid)
        changed = False
        stopped_legs: list[tuple[dict, str, object]] = []

        for o in pos.get("orders", []):
            label = o.get("account", "primary")
            maps = acct_maps.get(label)
            if maps is None:
                continue  # slice's account isn't configured/polled — leave untouched
            pos_by_tag, ord_by_tag = maps
            idx = o["tp_index"]
            prev = o.get("broker_state") or ("filled" if o.get("kind") == "market" else "pending")
            bpos = pos_by_tag.get((sid_i, idx))
            bord = ord_by_tag.get((sid_i, idx))

            if bpos is not None:                       # slice is a live position
                o["observed"] = True
                o["miss"] = 0
                if prev != "filled":
                    fp = float(bpos.get("openPrice") or o["entry"])
                    o["broker_state"], o["kind"], o["fill_price"] = "filled", "market", fp
                    await loop.run_in_executor(None, db.record_fill, sid_i, idx, o["ticket_id"], fp)
                    log.info("[%s:%s] TP%d FILLED @ %.2f (broker)", sid_i, label, idx, fp)
                elif o.get("fill_price") is None and bpos.get("openPrice") is not None:
                    # Market legs are born "filled": record the broker's real fill
                    # so SL caps / moves are measured from it, not the plan entry.
                    o["fill_price"] = float(bpos["openPrice"])
                # Capture the broker's POSITION id (distinct from our order ticket
                # for limit fills) so we can pull this slice's real close deal from
                # history once it leaves the broker.
                if bpos.get("id") is not None:
                    o["broker_position_id"] = bpos.get("id")
                o["last_profit"] = bpos.get("profit")
                o["last_price"] = bpos.get("currentPrice")
                changed = True
            elif bord is not None:                     # still a pending order
                if not o.get("observed"):
                    o["observed"] = True               # persist so absence can later conclude it
                    changed = True
                o["miss"] = 0
                if prev != "pending":
                    o["broker_state"] = "pending"
                    changed = True
            else:                                      # absent from the broker
                if prev in ("closed", "cancelled") or not o.get("observed"):
                    continue                           # already terminal, or never seen yet
                o["miss"] = o.get("miss", 0) + 1
                changed = True  # persist the counter so it accrues across polls
                if o["miss"] >= ABSENT_CONFIRM_POLLS:
                    if prev == "filled":
                        # Prefer the broker's TRUE realized PnL (history deals)
                        # over the stale last-live snapshot; falls back to the
                        # snapshot if deals aren't available/settled yet.
                        pnl = await _slice_realized_pnl(loop, ACCOUNTS_BY_LABEL.get(label), o)
                        reason = _infer_close_reason(o.get("last_price"), pnl, o["tp"], o["sl"])
                        o["broker_state"], o["realized_pnl"] = "closed", pnl
                        await loop.run_in_executor(None, db.record_slice_close,
                                                   sid_i, idx, o["ticket_id"], reason, pnl)
                        log.info("[%s:%s] TP%d CLOSED (~%s, pnl=%s via %s) (broker)",
                                 sid_i, label, idx, reason, pnl, o.get("pnl_source"))
                        # Flatten THIS slice's dashboard row now. Waiting for the
                        # whole signal to conclude (below) left TP1-3 showing as
                        # open with a frozen mark for as long as the runner leg
                        # lived (2026-09-18: hours behind a breakeven stop).
                        await _conclude_slice_row(loop, APIS_BY_LABEL.get(label), pos, o,
                                                  f"broker_{reason}")
                        if reason == "sl" and o.get("ladder"):
                            stopped_legs.append((o, label, pnl))
                    else:                              # pending -> gone, never filled
                        o["broker_state"] = "cancelled"
                        await loop.run_in_executor(None, db.record_slice_close,
                                                   sid_i, idx, o["ticket_id"], "cancelled", None)
                        log.info("[%s:%s] TP%d CANCELLED unfilled (broker)", sid_i, label, idx)
                    changed = True

        # Trade SL ladder: re-enter stopped legs that still have budget.
        for o, label, pnl in stopped_legs:
            new = await _ladder_reenter(loop, pos, sid_i, o, label, pnl)
            if new:
                pos["orders"].append(new)
            changed = True   # persist the ladder bookkeeping either way

        if changed:
            await r.set(key, json.dumps(pos))

        # ── Dashboard mirror (apis_position) — one row PER BROKER SLICE ───
        # Each TP leg is a separate position at the broker, so it gets its own
        # dashboard row carrying its own volume, fill price, broker position id
        # and PnL. Clubbing the legs into one averaged row hid the real trades
        # and — because the clubbed row referenced only slice 1's ticket — let
        # fill_reconciler restate the whole signal from that one slice.
        # Created lazily on first fill; live PnL refreshed each poll.
        # Best-effort — never blocks reconciliation.
        mirrored = False
        for acc in ACCOUNTS:
            label, dash = acc["label"], acc.get("apis")
            if dash is None:
                continue
            for o in pos.get("orders", []):
                if o.get("account", "primary") != label or o.get("broker_state") != "filled":
                    continue
                had = bool(o.get("apis_pos_id"))
                pid = await _ensure_slice_row(loop, dash, pos, o)
                if not pid:
                    continue
                mirrored = mirrored or not had
                await loop.run_in_executor(
                    None, lambda d=dash, p=pid, lp=o.get("last_price"),
                    pl=o.get("last_profit"): d.update_live(p, lp, pl))
        if mirrored:
            await r.set(key, json.dumps(pos))

        # Conclude the signal once EVERY slice (across all accounts) is terminal.
        states = [o.get("broker_state") for o in pos.get("orders", [])]
        if states and all(s in ("closed", "cancelled") for s in states):
            closed_all = [o for o in pos["orders"] if o.get("broker_state") == "closed"]
            # Aggregate realized PnL across all accounts for the audit row.
            all_pnls = [o.get("realized_pnl") for o in closed_all if o.get("realized_pnl") is not None]
            total = round(sum(all_pnls), 2) if all_pnls else None
            # Outcome (tp vs sl) is a market property; use the primary account's
            # realized sign, falling back to the aggregate.
            primary_closed = [o for o in pos["orders"]
                              if o.get("account", "primary") == "primary" and o.get("broker_state") == "closed"]
            primary_pnls = [o.get("realized_pnl") for o in primary_closed if o.get("realized_pnl") is not None]
            primary_total = round(sum(primary_pnls), 2) if primary_pnls else None
            if closed_all:
                basis = primary_total if primary_total is not None else total
                reason = "broker_tp" if (basis is not None and basis > 0) else "broker_sl"
            else:
                reason = "broker_cancelled"
            pos["status"] = f"closed_{reason}"
            pos["closed_at"] = datetime.now(timezone.utc).isoformat()
            await r.set(key, json.dumps(pos))
            await r.srem(f"{REDIS_PREFIX}:open", str(sid_i))
            await loop.run_in_executor(None, db.conclude_signal, sid_i, reason, total)
            # Flatten EACH slice's own dashboard row with its own realized PnL.
            # If a broker filled then closed a leg entirely between polls we may
            # never have created its row — create it now so the trade still shows.
            # Cancelled legs never traded, so they get no row.
            for acc in ACCOUNTS:
                label, dash = acc["label"], acc.get("apis")
                if dash is None:
                    continue
                for o in pos["orders"]:
                    if o.get("account", "primary") != label or o.get("broker_state") != "closed":
                        continue
                    await _conclude_slice_row(loop, dash, pos, o, reason)
            await r.set(key, json.dumps(pos))
            log.info("[%s] CONCLUDED from broker: %s pnl=%s (all-acct %s)",
                     sid_i, reason, primary_total, total)


async def _position_poller() -> None:
    """Periodically reconcile tracked signals against broker truth."""
    while True:
        await asyncio.sleep(BROKER_POLL_SEC)
        try:
            await reconcile_broker()
        except Exception as e:
            log.exception(f"position poller error: {e}")


async def _classify_open_signals(open_ids) -> tuple[list[str], list[str], bool]:
    """Split currently-open signals into (live, unfilled) by broker truth.

    The channel re-enters the same zone repeatedly, firing a fresh signal while
    a previous one is still an UNFILLED pending limit. Holding one position at a
    time, we want the new signal to take over those unfilled limits — but never
    to cancel a slice that has actually filled into a live market position.

    A signal is "live" if ANY account reports an open position whose comment
    carries its `tg-<msg_id>-` tag; otherwise it is "unfilled" (still pending,
    or already gone) and may be superseded — we never supersede while the signal
    holds a live position on any mirrored account. The bool return is `ok`: False
    means a broker position query failed, so the caller must fail safe and keep
    the no-pyramiding guard rather than cancel anything it could not verify.
    """
    loop = asyncio.get_running_loop()
    symbol = next(iter(ALLOWED_INSTRUMENTS))
    all_positions: list[dict] = []
    # All accounts are queried AT ONCE (this runs before every entry).
    results = await asyncio.gather(*(
        loop.run_in_executor(None, lambda c=acc["client"]: c.get_open_positions(symbol))
        for acc in ACCOUNTS))
    for acc, positions in zip(list(ACCOUNTS), results):
        if positions is None:
            if acc.get("source") == "db":
                acc["healthy"] = False  # excluded from this signal's entries
                log.warning("[%s] broker query failed — not trading this account this signal",
                            acc["label"])
                continue
            return [], [], False  # could not verify an account — caller must not cancel
        all_positions.extend(positions)
    live, unfilled = [], []
    for sid in open_ids:
        if not await r.get(f"{REDIS_PREFIX}:signal:{sid}"):
            unfilled.append(sid)  # dangling id, no detail row — safe to drop
            continue
        needle = f"tg-{sid}-"
        if any(needle in (p.get("comment") or "") for p in all_positions):
            live.append(sid)
        else:
            unfilled.append(sid)
    return live, unfilled, True


async def handle_new_signal(msg) -> None:
    text = clean(msg.text or "")
    sig = parse_signal(text)
    if not sig:
        # Not a signal — but 137 of the VIP channel's 317 management messages
        # arrive as standalone posts with no reply link ("Set breakeven now!!!"),
        # so they land here rather than in handle_reply. Resolve them against the
        # single open signal before writing the message off as chatter.
        if await apply_management(msg.id, text, None):
            return
        # A message that reads like a signal (instrument + side + SL) but the
        # grammar can't parse is an UNHANDLED FORMAT, not chatter — shout so it
        # never again vanishes in silence the way the TP1/TP2/TP3 form did.
        if looks_like_signal(text):
            log.warning("[%s] UNPARSEABLE signal-like message — not traded: %r", msg.id, text)
        return
    age = (datetime.now(timezone.utc) - msg.date.astimezone(timezone.utc)).total_seconds()
    if age > MAX_SIGNAL_AGE_SEC:
        log.warning(f"[{msg.id}] stale signal ({age:.0f}s old) — skip")
        return
    if sig["instrument"] not in ALLOWED_INSTRUMENTS:
        log.info(f"[{msg.id}] instrument {sig['instrument']} not allowed — skip")
        return
    bad = is_malformed(sig)
    if bad:
        log.warning(f"[{msg.id}] malformed signal ({bad}) — skip")
        return
    t_recv = time.monotonic()
    # Tell the other copy-trader about this signal right away (VIP priority).
    asyncio.get_running_loop().run_in_executor(
        None, db.record_channel_signal, CHANNEL, msg.id, sig)
    # Repost guard. The no-pyramiding check below already stops a duplicate from
    # opening a SECOND live position, but it cannot tell a repost from a genuine
    # re-entry: when the first copy is still an unfilled pending limit it
    # *supersedes* it (cancel + replace), churning orders at the broker for no
    # reason. Catching it here also gives the dashboard an accurate reason.
    signal_ts = msg.date.astimezone(timezone.utc).timestamp()
    if await _is_repost(sig, signal_ts):
        log.warning(f"[{msg.id}] duplicate repost within {DEDUP_WINDOW_SEC:.0f}s — skip")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _record_signals(
            sig, status="REJECTED", rejection_reason="duplicate_repost",
            signal_at=msg.date.astimezone(timezone.utc).isoformat()))
        return
    # Pause/Resume gate: each account's UserStrategy row (deployed, active, not
    # archived) decides whether THAT account takes new entries; the rows (and
    # each account's Price) are re-read now so a change applies to this signal.
    # New entries only — replies, closes, sweeps, and broker reconciliation are
    # never gated. DB unreachable -> nothing is entered (fail-closed).
    loop = asyncio.get_running_loop()
    db_ok = await refresh_accounts(load_new=False)
    if not db_ok or not any(a.get("entries", True) for a in ACCOUNTS):
        why = ("manager_gate (strategy paused)" if db_ok
               else "manager_gate (DB unreachable — fail-closed)")
        log.warning(f"[{msg.id}] {why} — skip")
        await loop.run_in_executor(None, lambda: _record_signals(
            sig, status="REJECTED", rejection_reason=why,
            signal_at=msg.date.astimezone(timezone.utc).isoformat()))
        return
    await sweep_stale_open()  # clear any wedged stale opens before the guard
    open_ids = await r.smembers(f"{REDIS_PREFIX}:open")
    if open_ids:
        live, unfilled, ok = await _classify_open_signals(open_ids)
        if not ok:
            log.warning(f"[{msg.id}] {len(open_ids)} open signal(s), broker check failed "
                        f"— skip (no pyramiding, fail-safe)")
            return
        if live:
            log.warning(f"[{msg.id}] {len(live)} live position(s) in market — skip (no pyramiding)")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: _record_signals(
                sig, status="REJECTED",
                rejection_reason="open_position_cap (no pyramiding)",
                signal_at=msg.date.astimezone(timezone.utc).isoformat()))
            return
        # All prior opens are unfilled pending limits (never entered the market).
        # Supersede them so this fresh re-entry can take over the single slot.
        for sid in unfilled:
            log.info(f"[{msg.id}] superseding unfilled signal {sid} (pending limit, not in market)")
            await close_order(int(sid), "superseded")

    log.info(f"[{msg.id}] NEW SIGNAL {sig['side']} {sig['instrument']} "
             f"entry={sig['entry_low']}-{sig['entry_high']} SL={sig['sl']} TPs={sig['tps']}")
    posted_at = msg.date.astimezone(timezone.utc).isoformat()
    accounts = _entry_accounts()
    if PRIORITY_CHANNEL and accounts:
        shared = [a for a in accounts if _meta_id(a) in _priority_meta]
        if shared:
            accounts = [a for a in accounts if a not in shared]
            vip_id = await loop.run_in_executor(None, lambda: db.find_channel_match(
                PRIORITY_CHANNEL, sig, PRIORITY_MATCH_SEC, PRIORITY_TOLERANCE))
            labels = {a["label"] for a in shared}
            if vip_id is not None:
                log.warning(f"[{msg.id}] VIP already posted this trade (msg {vip_id}) — "
                            f"{sorted(labels)} left to the VIP bot")
                await loop.run_in_executor(None, lambda: _record_signals(
                    sig, status="REJECTED", rejection_reason=f"vip_priority (VIP msg {vip_id})",
                    signal_at=posted_at, only_labels=labels))
            else:
                asyncio.create_task(_deferred_priority_entry(msg.id, sig, shared, text, posted_at))
        if not accounts:
            return
    pos = await place_order(msg.id, sig, accounts)
    log.info("[%s] orders sent %.2fs after receipt, %.1fs after the post", msg.id,
             time.monotonic() - t_recv,
             (datetime.now(timezone.utc) - msg.date.astimezone(timezone.utc)).total_seconds())
    pos["raw"] = text
    pos["posted_at"] = posted_at
    # Only track the signal if at least one slice actually hit the broker. A
    # registration when orders=[] wedges the no-pyramiding guard until the 12h
    # stale sweep — costing every subsequent signal of the session.
    if not pos.get("orders"):
        log.warning(f"[{msg.id}] no orders submitted — not tracking (next signal will be eligible)")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _record_signals(
            sig, status="REJECTED",
            rejection_reason="no orders submitted (broker rejection)",
            signal_at=pos.get("posted_at")))
        return
    await r.set(f"{REDIS_PREFIX}:signal:{msg.id}", json.dumps(pos))
    await r.sadd(f"{REDIS_PREFIX}:open", str(msg.id))
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: db.insert_signal(pos, CHANNEL))
    # Surface this signal on the dashboard Signals tab: one row per account that
    # got orders (PLACED), one per account that the broker rejected (REJECTED).
    placed = {o.get("account", "primary") for o in pos["orders"]}
    reject = {a["label"] for a in accounts} - placed
    reason = (f"TG @{CHANNEL} | zone {sig['entry_low']}-{sig['entry_high']} "
              f"| SL {sig['sl']} | TP {sig['tps']}")
    await loop.run_in_executor(None, lambda: _record_signals(
        sig, status="PLACED", reason=reason,
        signal_at=pos.get("posted_at"), only_labels=placed))
    if reject:
        await loop.run_in_executor(None, lambda: _record_signals(
            sig, status="REJECTED", rejection_reason="no orders on this account",
            signal_at=pos.get("posted_at"), only_labels=reject))


async def _deferred_priority_entry(msg_id: int, sig: dict, shared: list[dict],
                                   text: str, posted_at: str) -> None:
    """Neymar posted first: give VIP PRIORITY_WAIT_SEC to post the same trade
    before the accounts shared with the VIP bot take the Neymar one."""
    loop = asyncio.get_running_loop()
    labels = {a["label"] for a in shared}
    try:
        deadline = loop.time() + PRIORITY_WAIT_SEC
        while loop.time() < deadline:
            await asyncio.sleep(0.5)
            vip_id = await loop.run_in_executor(None, lambda: db.find_channel_match(
                PRIORITY_CHANNEL, sig, PRIORITY_MATCH_SEC, PRIORITY_TOLERANCE))
            if vip_id is not None:
                log.warning(f"[{msg_id}] VIP posted the same trade (msg {vip_id}) — "
                            f"{sorted(labels)} left to the VIP bot")
                await loop.run_in_executor(None, lambda: _record_signals(
                    sig, status="REJECTED", rejection_reason=f"vip_priority (VIP msg {vip_id})",
                    signal_at=posted_at, only_labels=labels))
                return
        key = f"{REDIS_PREFIX}:signal:{msg_id}"
        existing = await r.get(key)
        if existing and str(json.loads(existing).get("status", "")).startswith("closed"):
            return                              # the channel already ended this signal
        accounts = [a for a in shared if a in _entry_accounts()]
        if not accounts:
            return
        log.info(f"[{msg_id}] no VIP match within {PRIORITY_WAIT_SEC:.0f}s — "
                 f"trading {sorted(a['label'] for a in accounts)}")
        pos2 = await place_order(msg_id, sig, accounts)
        placed = {o.get("account", "primary") for o in pos2["orders"]}
        if pos2["orders"]:
            existing = await r.get(key)
            if existing:
                pos = json.loads(existing)
                pos["orders"].extend(pos2["orders"])
                await r.set(key, json.dumps(pos))
                for o in pos2["orders"]:
                    await loop.run_in_executor(None, lambda o=o: db.insert_order(msg_id, o))
            else:
                pos2["raw"], pos2["posted_at"] = text, posted_at
                await r.set(key, json.dumps(pos2))
                await r.sadd(f"{REDIS_PREFIX}:open", str(msg_id))
                await loop.run_in_executor(None, lambda: db.insert_signal(pos2, CHANNEL))
            await loop.run_in_executor(None, lambda: _record_signals(
                sig, status="PLACED", reason=f"TG @{CHANNEL} (no VIP match)",
                signal_at=posted_at, only_labels=placed))
        missing = {a["label"] for a in accounts} - placed
        if missing:
            await loop.run_in_executor(None, lambda: _record_signals(
                sig, status="REJECTED", rejection_reason="no orders on this account",
                signal_at=posted_at, only_labels=missing))
    except Exception as e:
        log.exception(f"[{msg_id}] deferred VIP-priority entry failed: {e}")


async def handle_reply(msg) -> None:
    parent_id = msg.reply_to.reply_to_msg_id
    text = clean(msg.text or "")
    if not text:
        return

    sl_fix = SL_FIX_RE.search(text)
    if sl_fix and "typo" in text.lower():
        await modify_sl(parent_id, float(sl_fix.group(1)))
        return

    # Position management (breakeven / move SL / close). Runs before outcome
    # classification because the two overlap and management is the more precise
    # reading: "breakeven hit out of this entries now!" is classified by
    # classify_outcome as breakeven ALONE, which would move the stop and leave
    # the position open when the channel asked to be flat.
    action = await apply_management(msg.id, text, parent_id)
    if action and action.get("close") == "all":
        return  # flattened; nothing left for the outcome path to resolve

    outcome = classify_outcome(text)
    if not outcome:
        return
    if outcome.get("breakeven") and BE_KEEP_LEGS > 0:
        await breakeven_partial(parent_id)          # "set breakeven / zero risk"
    elif outcome.get("tp_hit") == 1 or outcome.get("breakeven"):
        await move_to_breakeven(parent_id)
    if outcome.get("tp_hit") == 3 or "all 3 tps" in text.lower():
        await close_order(parent_id, "tp3")
    if outcome.get("sl_hit"):
        await close_order(parent_id, "sl")


async def hydrate_from_db() -> None:
    """Re-load any open signals from Postgres into the state store.

    Without this, a restart would leave MetaAPI tickets alive but the trader
    blind to subsequent TP/SL/typo replies for those signals. Memory-store
    deployments need this; Redis deployments benefit too when Redis was
    flushed or a different store backend is in use.
    """
    loop = asyncio.get_running_loop()
    positions = await loop.run_in_executor(None, lambda: db.load_open_signals(channel=CHANNEL))
    if not positions:
        return
    restored = 0
    for pos in positions:
        msg_id = pos["msg_id"]
        key = f"{REDIS_PREFIX}:signal:{msg_id}"
        if await r.get(key):  # already present (e.g. Redis still warm) — skip
            continue
        await r.set(key, json.dumps(pos))
        await r.sadd(f"{REDIS_PREFIX}:open", str(msg_id))
        restored += 1
    if restored:
        log.info(f"Hydrated {restored} open signal(s) from DB")


async def reset_state():
    """Drop all hft:tg:* keys so a fresh test run isn't blocked by stale state."""
    keys = []
    async for k in r.scan_iter(match=f"{REDIS_PREFIX}:*"):
        keys.append(k)
    if keys:
        await r.delete(*keys)
    log.info(f"Reset cleared {len(keys)} state key(s) under {REDIS_PREFIX}:*")


async def main(args):
    global r
    from telethon import TelegramClient, events  # runtime-only dependency

    r, kind = await make_store(REDIS_URL)
    log.info(f"State store: {kind}")
    log.info("Fanning out each signal to accounts: %s",
             [a["label"] for a in ACCOUNTS])

    if args.reset:
        await reset_state()

    db.init_schema()
    # Load dashboard accounts BEFORE hydrating, so their open slices route.
    if not await refresh_accounts():
        log.warning("Dashboard accounts not loaded (DB unreachable) — retrying every %ss",
                    ACCOUNT_REFRESH_SEC)
    log.info("Accounts: %s", [(a["label"], a.get("lot") or "risk", a.get("entries"))
                              for a in ACCOUNTS])
    await hydrate_from_db()
    await sweep_stale_open()  # clear opens that already went stale while we were down

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()
    log.info(f"Listening to {CHANNEL} (DRY_RUN={DRY_RUN})")

    @client.on(events.NewMessage(chats=CHANNEL_REF))
    async def _handler(event):
        try:
            if event.message.reply_to:
                await handle_reply(event.message)
            else:
                await handle_new_signal(event.message)
        except Exception as e:
            log.exception(f"handler error: {e}")

    asyncio.create_task(_stale_sweeper())
    asyncio.create_task(_position_poller())
    asyncio.create_task(_account_refresher())
    asyncio.create_task(_drawdown_guard())
    await client.run_until_disconnected()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram -> MetaAPI live trader")
    parser.add_argument("--reset", action="store_true",
                        help="Clear all hft:tg:* Redis keys before starting (fresh test).")
    parser.add_argument("--reset-only", action="store_true",
                        help="Clear Redis state and exit without listening.")
    args = parser.parse_args()

    if args.reset_only:
        async def _just_reset():
            global r
            r, _ = await make_store(REDIS_URL)
            await reset_state()
        asyncio.run(_just_reset())
    else:
        asyncio.run(main(args))
