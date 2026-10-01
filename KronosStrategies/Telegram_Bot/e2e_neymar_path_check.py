"""Live check of the Neymar bot's message path on a DEMO account (isolated state).

Feeds Neymar-format messages through the bot's real handlers: VIP-priority skip
(VIP posted before / during the wait), trade after the wait with the account's
Price + Trade SL, breakeven (exit 3, keep 2 at entry with TP) and "Trade failed"
(exit all). Refuses a non-demo or non-flat account. Run on the box:

  cd ~/KronosStrategies && sudo docker compose -p kronos run --rm --no-deps -T \
    -e DRY_RUN=false -v "$PWD/Telegram_Bot:/e2e" -w /e2e --entrypoint python \
    telegram_trader e2e_neymar_path_check.py
"""
import asyncio
import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("TG_REDIS_PREFIX", "e2e:ney")
os.environ.setdefault("TG_DB_PREFIX", "e2e")
os.environ.setdefault("APIS_DASHBOARD_SYNC", "false")
os.environ.setdefault("TG_DB_ACCOUNTS", "false")

import db_persist as db          # noqa: E402
import live_trader as lt         # noqa: E402
from state_store import make_store  # noqa: E402

R = []
VIP = lt.VIP_CHANNEL_ID


def check(n, ok, d=""):
    R.append(bool(ok))
    print("PASS" if ok else "FAIL", n, d, flush=True)


def msg(mid, text, reply_to=None):
    return SimpleNamespace(id=mid, text=text, date=datetime.now(timezone.utc),
                           reply_to=SimpleNamespace(reply_to_msg_id=reply_to) if reply_to else None)


def tagged(c, mid):
    return [p for p in (c.get_open_positions("XAUUSD") or []) if (p.get("comment") or "").startswith(f"tg-{mid}-")]


def signal_text(c, offset=0.0):
    ask = c.get_symbol_price("XAUUSD")["ask"] + offset
    hi, lo = round(ask + 0.5, 2), round(ask - 1.0, 2)
    return (f"Gold buy now {hi} - {lo} SL: {round(ask - 6, 2)} TP: {round(ask + 3, 2)} "
            f"TP: {round(ask + 5, 2)} TP: {round(ask + 7, 2)}"), (lo, hi)


def vip_row(mid, lo, hi):
    db.record_channel_signal(VIP, mid, {"side": "buy", "entry_low": lo, "entry_high": hi})


async def main():
    lt.r, _ = await make_store(lt.REDIS_URL)
    db.init_schema()
    lt.ACT_ON_MANAGEMENT = True                      # new default for both channels
    await lt.refresh_accounts()                      # loads _priority_meta (VIP accounts)
    acc = lt.ACCOUNTS[0]
    c = acc["client"]
    info = c.get_account_information() or c.get_account_information() or {}
    if info.get("type") != "ACCOUNT_TRADE_MODE_DEMO" or c.get_open_positions():
        print("REFUSE: not demo or not flat")
        return
    check("Neymar bot sees Winprofx as shared with VIP", lt._meta_id(acc) in lt._priority_meta,
          f"channel={lt.CHANNEL} priority={lt.PRIORITY_CHANNEL}")
    check("bot uses your Neymar-tab settings", acc.get("lot") == 0.2 and acc.get("trade_sl") == 200.0,
          f"lot={acc.get('lot')} tradeSL={acc.get('trade_sl')}")
    try:
        # A. VIP already posted the same trade -> skip
        text, (lo, hi) = signal_text(c)
        vip_row(990701, lo, hi)
        await lt.handle_new_signal(msg(990801, text))
        await asyncio.sleep(2)
        check("A: VIP already posted -> Neymar does not trade", tagged(c, 990801) == [])
        db_del()

        # B. VIP posts during the 10s wait -> skip
        text, (lo, hi) = signal_text(c)
        await lt.handle_new_signal(msg(990802, text))
        await asyncio.sleep(3)
        vip_row(990702, lo, hi)
        await asyncio.sleep(lt.PRIORITY_WAIT_SEC + 1)
        check("B: VIP posts within 10s -> Neymar does not trade", tagged(c, 990802) == [])
        db_del()

        # C. VIP never posts -> trade after the wait, with your settings
        text, _ = signal_text(c)
        t0 = time.monotonic()
        await lt.handle_new_signal(msg(990803, text))
        await asyncio.sleep(lt.PRIORITY_WAIT_SEC + 4)
        legs = tagged(c, 990803)
        check("C: no VIP match -> Neymar trades after the 10s wait", len(legs) == 5,
              f"{len(legs)} legs, {time.monotonic() - t0:.1f}s after the message")
        check("C: 5 x 0.04 lot", all(abs(p["volume"] - 0.04) < 1e-9 for p in legs), str([p["volume"] for p in legs]))
        dists = [round(p["openPrice"] - p["stopLoss"], 2) for p in legs]
        check("C: stop $40 per trade (~10.00)", legs and all(abs(d - 10) <= 0.6 for d in dists), str(dists))

        # D. breakeven reply -> exit 3, keep 2 at entry (with TP kept)
        import json
        key = f"{lt.REDIS_PREFIX}:signal:990803"
        pos = json.loads(await lt.r.get(key))
        pos["entry_mid"] = round(min(pos["entry_mid"], c.get_symbol_price("XAUUSD")["bid"] - 1.5), 2)
        await lt.r.set(key, json.dumps(pos))
        await lt.handle_reply(msg(990804, "Set breakeven now", reply_to=990803))
        await asyncio.sleep(1.5)
        legs = tagged(c, 990803)
        check("D: breakeven -> 2 trades left", len(legs) == 2, str([p["comment"] for p in legs]))
        check("D: kept trades at entry with their TP", legs and all(abs(p["stopLoss"] - pos["entry_mid"]) < 0.02
                                                                    and p.get("takeProfit") for p in legs),
              str([(p["stopLoss"], p.get("takeProfit")) for p in legs]))
        await lt.handle_reply(msg(990805, "Trade failed", reply_to=990803))
        await asyncio.sleep(1.5)
        check("D: 'Trade failed' -> all trades closed", tagged(c, 990803) == [])
    finally:
        db_del()
        for p in c.get_open_positions("XAUUSD") or []:
            if (p.get("comment") or "").startswith("tg-99"):
                c.close_position(str(p["id"]))
        with db._connect() as conn, conn.cursor() as cur:
            for t in ("e2e_signal_updates", "e2e_orders", "e2e_signals"):
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        keys = [k async for k in lt.r.scan_iter(match=f"{lt.REDIS_PREFIX}:*")]
        if keys:
            await lt.r.delete(*keys)
        print("info", f"cleanup: {len(c.get_open_positions() or [])} position(s) left")
    print("info", f"{sum(R)}/{len(R)} checks passed")


def db_del():
    with db._connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM kronos_xchan_signals WHERE msg_id BETWEEN 990000 AND 999999")


asyncio.run(main())
