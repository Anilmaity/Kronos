"""Live end-to-end check of the copy-trader's trading logic on a DEMO MT5 account.

Places REAL 0.01-lot XAUUSD orders through the bot's own code paths and checks
what the broker actually did: 5 legs, the $-per-trade cap, SL moves (+ the
drawdown check), SL re-entry, breakeven (exit 3 / keep 2), "trade failed",
the drawdown guard's close-everything / near-floor block / day reset, the VIP
priority table, and entry speed. Refuses to run on a non-demo account or on an
account that already has open positions/orders (the close-everything step
would flatten them).

Isolated from the live bot: own Redis prefix, own tg tables (e2e_*), no
dashboard rows, message ids 99xxxx. Run on the box with the service's env:

  cd ~/KronosStrategies && sudo docker compose -p kronos run --rm --no-deps \\
    -e TG_REDIS_PREFIX=e2e:tg -e TG_DB_PREFIX=e2e -e APIS_DASHBOARD_SYNC=false \\
    -e TG_DB_ACCOUNTS=false -e DRY_RUN=false \\
    -v "$PWD/Telegram_Bot:/e2e" -w /e2e telegram_trader_vip python e2e_demo_check.py
"""
import asyncio
import json
import os
import sys
import time
from datetime import timedelta

os.environ.setdefault("TG_REDIS_PREFIX", "e2e:tg")
os.environ.setdefault("TG_DB_PREFIX", "e2e")
os.environ.setdefault("APIS_DASHBOARD_SYNC", "false")
os.environ.setdefault("TG_DB_ACCOUNTS", "false")

import db_persist as db          # noqa: E402
import live_trader as lt         # noqa: E402
from state_store import make_store  # noqa: E402

SYMBOL = "XAUUSD"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)
    return bool(ok)


def tagged(client, msg_id: int) -> list[dict]:
    return [p for p in (client.get_open_positions(SYMBOL) or [])
            if (p.get("comment") or "").startswith(f"tg-{msg_id}-")]


def leg_of(p: dict) -> int:
    return int((p.get("comment") or "tp0").rsplit("tp", 1)[1])


def near(a, b, tol=0.02) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def buy_signal(client) -> dict:
    px = client.get_symbol_price(SYMBOL)
    ask = px["ask"]
    return {"side": "buy", "instrument": SYMBOL, "entry_low": round(ask - 1.0, 2),
            "entry_high": round(ask + 0.5, 2), "sl": round(ask - 6.0, 2),
            "tps": [round(ask + 3, 2), round(ask + 5, 2), round(ask + 7, 2)], "tp_open": False}


async def save(pos: dict) -> None:
    db.insert_signal(pos, "e2e")                   # as the live handler does (FK for updates)
    await lt.r.set(f"{lt.REDIS_PREFIX}:signal:{pos['msg_id']}", json.dumps(pos))
    await lt.r.sadd(f"{lt.REDIS_PREFIX}:open", str(pos["msg_id"]))


async def load(msg_id: int) -> dict:
    return json.loads(await lt.r.get(f"{lt.REDIS_PREFIX}:signal:{msg_id}"))


async def flatten_tests(client) -> None:
    for p in client.get_open_positions(SYMBOL) or []:
        if (p.get("comment") or "").startswith("tg-99"):
            client.close_position(str(p["id"]))


async def main() -> int:
    loop = asyncio.get_running_loop()
    from concurrent.futures import ThreadPoolExecutor
    loop.set_default_executor(ThreadPoolExecutor(max_workers=32))   # as the live bot
    lt.r, kind = await make_store(lt.REDIS_URL)
    db.init_schema()
    acc = lt.ACCOUNTS[0]
    client = acc["client"]
    acc.update(lot=0.05, trade_sl=None, max_sl=None, entries=True, healthy=True, ub_id="e2e-ub")
    lt.LEG_COUNT, lt.BE_KEEP_LEGS, lt.ACT_ON_MANAGEMENT = 5, 2, True

    info = client.get_account_information() or {}
    if info.get("type") != "ACCOUNT_TRADE_MODE_DEMO":
        print(f"REFUSING: account type is {info.get('type')!r}, not demo")
        return 2
    if client.get_open_positions() or client.get_pending_orders():
        print("REFUSING: the account has open positions / pending orders")
        return 2
    print(f"demo account, equity {info['equity']}, store {kind}, prefix {lt.REDIS_PREFIX}")

    try:
        # ── 1. five legs, last TP repeated, lot split, speed ──────────────────
        sig = buy_signal(client)
        t0 = time.monotonic()
        pos = await lt.place_order(990101, sig)
        took = time.monotonic() - t0
        pos.update(raw="e2e", posted_at=None)
        await save(pos)
        await lt.reconcile_broker()                           # records the real fills
        pos = await load(990101)
        check("real fill prices recorded for market legs",
              all(o.get("fill_price") for o in pos["orders"]),
              str([o.get("fill_price") for o in pos["orders"]]))
        legs = sorted(tagged(client, 990101), key=leg_of)
        check("5 legs placed at the broker", len(legs) == 5, f"got {len(legs)}")
        check("each leg 0.01 lot (0.05 split over 5)", all(near(p["volume"], 0.01) for p in legs),
              str([p["volume"] for p in legs]))
        tps = [p.get("takeProfit") for p in legs]
        check("legs 4-5 use the last TP (TP3)", len(tps) == 5 and near(tps[3], sig["tps"][2])
              and near(tps[4], sig["tps"][2]) and near(tps[0], sig["tps"][0]), str(tps))
        check("channel SL on every leg (within the $90 cap)",
              all(near(p.get("stopLoss"), sig["sl"], 0.75) for p in legs),
              str({p.get("stopLoss") for p in legs}))
        check("all legs sent in under 3s", took < 3.0, f"{took:.2f}s")

        # ── 2. move SL within the cap ────────────────────────────────────────
        new_sl = round(sig["sl"] - 1.0, 2)
        t0 = time.monotonic()
        await lt.modify_sl(990101, new_sl)
        check("SPEED: SL moved on all 5 legs in under 2s", time.monotonic() - t0 < 2.0,
              f"{time.monotonic() - t0:.2f}s")
        legs = tagged(client, 990101)
        check("move SL within cap: every leg moved", all(near(p.get("stopLoss"), new_sl) for p in legs),
              str({p.get("stopLoss") for p in legs}))
        check("move SL keeps every leg's TP", sorted(p.get("takeProfit") or 0 for p in legs)
              == sorted(tps), str(sorted(p.get("takeProfit") for p in legs)))

        # ── 3. move SL beyond the cap -> stop at the cap + ladder ───────────
        acc["max_sl"] = 3.0                                   # $3 per trade
        far_sl = round(sig["sl"] - 4.0, 2)                    # ~$11 per 0.01 leg
        await lt.modify_sl(990101, far_sl)
        pos = await load(990101)
        legs = {leg_of(p): p for p in tagged(client, 990101)}
        capped = all(near(legs[o["tp_index"]].get("stopLoss"),
                          float(o.get("fill_price") or o["entry"]) - 3.0, 0.05)
                     for o in pos["orders"] if o["tp_index"] in legs)
        check("move SL beyond cap: stops set at the $3 cap", capped,
              str({p.get("stopLoss") for p in legs.values()}))
        lad = pos["orders"][0].get("ladder") or {}
        check("capped SL move keeps every leg's TP",
              sorted(p.get("takeProfit") or 0 for p in legs.values()) == sorted(tps))
        check("ladder budget = loss at the channel's SL", lad.get("used") == 3.0
              and lad.get("budget", 0) > 3.0, str(lad))

        # ── 4. a risk-adding SL move is skipped near a drawdown floor ────────
        eq = (client.get_account_information() or {})["equity"]
        lt._dd_state["e2e-ub"] = {"equity": eq}
        lt._dd_cfg = {"e2e-ub": {"daily_dd_floor": eq - 5.0, "max_dd_floor": None}}
        before = {leg_of(p): p.get("stopLoss") for p in tagged(client, 990101)}
        await lt.modify_sl(990101, round(sig["sl"] - 15.0, 2))
        after = {leg_of(p): p.get("stopLoss") for p in tagged(client, 990101)}
        check("SL move skipped when it would reach the daily floor", before == after,
              f"{before} -> {after}")
        lt._dd_state.clear()
        lt._dd_cfg = {}

        # ── 5. SL re-entry (ladder) ──────────────────────────────────────────
        pos = await load(990101)
        leg1 = next(o for o in pos["orders"] if o["tp_index"] == 1)
        client.close_position(leg1["ticket_id"])              # stand-in for its stop
        leg1["broker_state"] = "closed"
        new = await lt._ladder_reenter(loop, pos, 990101, leg1, acc["label"],
                                       -float(leg1["ladder"]["last"]))
        if check("stopped leg re-entered", new is not None, str(new and new["tp_index"])):
            pos["orders"].append(new)
            await lt.r.set(f"{lt.REDIS_PREFIX}:signal:990101", json.dumps(pos))
            p101 = [p for p in tagged(client, 990101) if leg_of(p) == 101]
            check("re-entry is a live position tagged tp101 with the same TP",
                  len(p101) == 1 and near(p101[0].get("takeProfit"), leg1["tp"]),
                  str(p101 and (p101[0].get("takeProfit"), leg1["tp"])))
            check("re-entry stop = next $3 chunk",
                  p101 and near(p101[0].get("stopLoss"), float(new["entry"]) - 3.0, 0.05),
                  str(p101 and (p101[0].get("stopLoss"), new["entry"])))

        # ── 6. breakeven: exit 3, keep 2 farthest at entry ───────────────────
        pos = await load(990101)
        bid = client.get_symbol_price(SYMBOL)["bid"]
        be = round(min(pos["entry_mid"], bid - 1.5), 2)       # a level the broker accepts now
        pos["entry_mid"] = be
        await lt.r.set(f"{lt.REDIS_PREFIX}:signal:990101", json.dumps(pos))
        live_before = len(tagged(client, 990101))
        t0 = time.monotonic()
        await lt.breakeven_partial(990101)
        check("SPEED: breakeven (exit 3 + move 2) in under 3s", time.monotonic() - t0 < 3.0,
              f"{time.monotonic() - t0:.2f}s")
        legs = tagged(client, 990101)
        check("breakeven: only 2 legs left", len(legs) == 2,
              f"{live_before} -> {len(legs)} {[leg_of(p) for p in legs]}")
        check("breakeven: kept legs are the farthest TP", all(near(p.get("takeProfit"), sig["tps"][2])
                                                              for p in legs))
        check("breakeven: kept legs' SL at entry", all(near(p.get("stopLoss"), be) for p in legs),
              str([p.get("stopLoss") for p in legs]))

        # ── 7. "Trade failed" -> exit all ───────────────────────────────────
        t0 = time.monotonic()
        action = await lt.apply_management(990199, "Trade failed", 990101)
        check("SPEED: 'Trade failed' exit done in under 3s", time.monotonic() - t0 < 3.0,
              f"{time.monotonic() - t0:.2f}s")
        check("'Trade failed' read as close-all", (action or {}).get("close") == "all", str(action))
        check("'Trade failed': no legs left", tagged(client, 990101) == [])
        check("signal no longer open", "990101" not in await lt.r.smembers(f"{lt.REDIS_PREFIX}:open"))

        # ── 7b. full 5-leg channel close timing ────────────────────────────
        pos3 = await lt.place_order(990103, buy_signal(client))
        pos3.update(raw="e2e", posted_at=None)
        await save(pos3)
        t0 = time.monotonic()
        await lt.close_order(990103, "channel_close")
        took = time.monotonic() - t0
        check("SPEED: all 5 legs closed by a channel exit in under 3s",
              took < 3.0 and tagged(client, 990103) == [], f"{took:.2f}s")

        # ── 7c. stop-out noticed by reconciliation within ~10s ───────────────
        pos4 = await lt.place_order(990104, buy_signal(client))
        pos4.update(raw="e2e", posted_at=None)
        await save(pos4)
        await lt.reconcile_broker()                           # observe the legs
        for p in tagged(client, 990104):
            client.close_position(str(p["id"]))               # as if stopped at the broker
        t0 = time.monotonic()
        delay = lt.BROKER_POLL_SEC                            # same cadence as the live poller
        while time.monotonic() - t0 < 25:
            await asyncio.sleep(delay)
            delay = lt.CONFIRM_RECHECK_SEC if await lt.reconcile_broker() else lt.BROKER_POLL_SEC
            if "990104" not in await lt.r.smembers(f"{lt.REDIS_PREFIX}:open"):
                break
        took = time.monotonic() - t0
        check("SPEED: broker-side close confirmed and concluded within ~10s",
              "990104" not in await lt.r.smembers(f"{lt.REDIS_PREFIX}:open") and took <= 10.0,
              f"{took:.1f}s (poll {lt.BROKER_POLL_SEC}s, second look {lt.CONFIRM_RECHECK_SEC}s)")

        # ── 8. drawdown guard: close everything, near-floor block, day reset ─
        pos2 = await lt.place_order(990102, buy_signal(client))
        check("guard test position opened", len(tagged(client, 990102)) == 5)
        saved: list[dict] = []
        lt.apis.save_drawdown = lambda ub, **f: saved.append(f) or True
        eq = (client.get_account_information() or {})["equity"]
        day = (client.get_broker_time()).date()
        cfg = {"daily_dd_floor": round(eq - 50, 2), "max_dd_floor": None, "daily_dd_offset": 230.0,
               "max_dd_offset": 500.0, "dd_day": day, "dd_blocked_day": None}
        await lt._guard_account(loop, "e2e-ub", client, cfg)
        check("guard: armed and ok above the floor", saved[-1].get("dd_status") == "ok", str(saved[-1]))
        real_info = client.get_account_information
        client.get_account_information = lambda: dict(real_info(), equity=cfg["daily_dd_floor"] - 1)
        t0 = time.monotonic()
        await lt._guard_account(loop, "e2e-ub", client, cfg)
        took = time.monotonic() - t0
        client.get_account_information = real_info
        check("guard breach: account flat (all positions closed)", client.get_open_positions() == [],
              f"closed in {took:.2f}s")
        check("guard breach: status breached_daily", saved[-1].get("dd_status") == "breached_daily")
        check("guard breach: no new entries today", acc not in lt._entry_accounts())
        lt._dd_state.clear()
        cfg2 = dict(cfg, daily_dd_floor=round(eq - 50, 2), dd_blocked_day=None)
        await lt._guard_account(loop, "e2e-ub", client, cfg2)        # arm
        client.get_account_information = lambda: dict(real_info(), equity=cfg2["daily_dd_floor"] + 5)
        await lt._guard_account(loop, "e2e-ub", client, cfg2)
        client.get_account_information = real_info
        check("guard near floor (+$5): blocked, nothing closed",
              saved[-1].get("dd_status") == "near_daily" and acc not in lt._entry_accounts())
        lt._dd_state.clear()
        cfg3 = dict(cfg, dd_day=day - timedelta(days=1), dd_blocked_day=day - timedelta(days=1),
                    max_dd_floor=1.0)
        saved.clear()
        await lt._guard_account(loop, "e2e-ub", client, cfg3)
        eq_now = saved[0].get("dd_equity") if saved else None
        check("new broker day: floors = equity - 230 / - 500",
              saved and near(saved[0].get("daily_dd_floor"), eq_now - 230, 1.0)
              and near(saved[0].get("max_dd_floor"), eq_now - 500, 1.0), str(saved[:1]))
        check("new broker day: yesterday's block cleared", acc in lt._entry_accounts())
        lt._dd_state.clear()

        # ── 9. VIP priority table ────────────────────────────────────────────
        s = buy_signal(client)
        db.record_channel_signal("e2e-vip", 990301, s)
        check("VIP priority: same trade found", db.find_channel_match("e2e-vip", s, 60, 5.0) == 990301)
        check("VIP priority: opposite side not matched",
              db.find_channel_match("e2e-vip", dict(s, side="sell"), 60, 5.0) is None)
        far = dict(s, entry_low=s["entry_low"] + 50, entry_high=s["entry_high"] + 50)
        check("VIP priority: different zone not matched",
              db.find_channel_match("e2e-vip", far, 60, 5.0) is None)
    finally:
        await flatten_tests(client)
        try:
            with db._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM kronos_xchan_signals WHERE channel LIKE 'e2e%%'")
                for t in ("e2e_signal_updates", "e2e_orders", "e2e_signals"):
                    cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        except Exception as e:
            print("cleanup:", e)
        keys = [k async for k in lt.r.scan_iter(match=f"{lt.REDIS_PREFIX}:*")]
        if keys:
            await lt.r.delete(*keys)
        left = client.get_open_positions() or []
        print(f"cleanup: {len(left)} position(s) left on the account")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
