"""LIVE guarded scalper on the FundingPips demo (account 6c7ce166).

Operationalizes bot/scalp.py against the real demo account via MetaApi REST. Each leg is
a BROKER-MANAGED bracket (market order with SL+TP attached) so exits execute server-side
(no fast polling needed). Averaging = a few extra bracketed legs at adverse offsets, CAPPED
(never doubling). Hard daily-loss kill switch. Demo only.

HONEST: backtests show the z-MR scalp is -EV; this runs it small and capped to satisfy the
"implement + use it" directive on demo. Risk per leg ~0.18% (0.01 lot, $9 SL); max ~3 legs.

    .venv/Scripts/python.exe run_scalp_live.py --max-ticks 30 --interval 45
"""
import argparse, csv, os, re, sys, time
from datetime import datetime, timezone
import requests
from bot import data

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(ROOT, ".env")
BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
LOG = os.path.join(ROOT, "journal", "scalp_live.csv")
SYMBOL = "XAUUSD"

ENTRY_Z = 2.0
TP = 3.0
SL = 9.0
ADD_OFFSET = 4.0
MAX_LEGS = 3
LOT = 0.01
DAILY_KILL_PCT = 3.0


def envval(key):
    txt = open(ENV, encoding="utf-8").read()
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def log(row):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts_utc", "event", "side", "z", "price", "lot",
                        "sl", "tp", "order_id", "equity", "note"])
        w.writerow(row)


def zscore(n=50):
    cs = [c for c in data.candles(granularity="M15", count=n + 5) if c["complete"]]
    cl = [c["c"] for c in cs][-n:]
    m = sum(cl) / len(cl)
    sd = (sum((x - m) ** 2 for x in cl) / len(cl)) ** 0.5
    return (cl[-1] - m) / sd if sd else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-ticks", type=int, default=30)
    ap.add_argument("--interval", type=int, default=45)
    a = ap.parse_args()

    acct, token = envval("meta_id"), envval("access_token")
    H = {"auth-token": token, "Content-Type": "application/json"}

    def get(path):
        r = requests.get(f"{BASE}/users/current/accounts/{acct}/{path}", headers=H, timeout=30)
        r.raise_for_status(); return r.json()

    def trade(payload):
        r = requests.post(f"{BASE}/users/current/accounts/{acct}/trade", headers=H,
                          json=payload, timeout=60)
        return r.json()

    start_equity = get("account-information").get("equity", 0.0)
    print(f"[scalp] live start equity ${start_equity:,.2f}  z-entry ±{ENTRY_Z} TP${TP} SL${SL} "
          f"maxlegs {MAX_LEGS}  ticks {a.max_ticks}@{a.interval}s")
    log([datetime.now(timezone.utc).isoformat(), "START", "", "", "", "", "", "",
         "", start_equity, "live guarded scalper"])

    basket_side = None
    legs = []  # list of (positionId, entry_price)

    for tick in range(a.max_ticks):
        try:
            info = get("account-information"); eq = info.get("equity", 0.0)
            if eq <= start_equity * (1 - DAILY_KILL_PCT / 100.0):
                log([datetime.now(timezone.utc).isoformat(), "KILL", "", "", "", "", "", "",
                     "", eq, "daily loss kill switch"]); print("[scalp] KILL switch"); break
            px = get(f"symbols/{SYMBOL}/current-price")
            bid, ask = px["bid"], px["ask"]
            mid = round((bid + ask) / 2, 2)
            z = zscore()
            open_pos = {p["id"] for p in get("positions") if p.get("symbol") == SYMBOL}
            legs = [(pid, e) for (pid, e) in legs if pid in open_pos]  # drop closed (TP/SL hit)
            if not legs:
                basket_side = None

            action = None
            if basket_side is None:
                if z <= -ENTRY_Z:
                    action = ("long", ask)
                elif z >= ENTRY_Z:
                    action = ("short", bid)
            else:  # manage averaging (capped, not doubling)
                last_entry = legs[-1][1]
                if len(legs) < MAX_LEGS:
                    adverse = (mid <= last_entry - ADD_OFFSET) if basket_side == "long" \
                        else (mid >= last_entry + ADD_OFFSET)
                    if adverse:
                        action = (basket_side, ask if basket_side == "long" else bid)

            if action:
                side, ref = action
                if side == "long":
                    sl_px, tp_px = round(ref - SL, 2), round(ref + TP, 2)
                    at = "ORDER_TYPE_BUY"
                else:
                    sl_px, tp_px = round(ref + SL, 2), round(ref - TP, 2)
                    at = "ORDER_TYPE_SELL"
                resp = trade({"actionType": at, "symbol": SYMBOL, "volume": LOT,
                              "stopLoss": sl_px, "takeProfit": tp_px,
                              "comment": "guarded-scalp"})
                oid = resp.get("orderId") or resp.get("positionId") or str(resp.get("stringCode"))
                pid = resp.get("positionId") or oid
                ok = resp.get("stringCode") == "TRADE_RETCODE_DONE"
                if ok:
                    basket_side = side; legs.append((pid, ref))
                ev = "open_leg" if len(legs) == 1 else "add_leg"
                log([datetime.now(timezone.utc).isoformat(), ev if ok else "reject",
                     side, round(z, 2), ref, LOT, sl_px, tp_px, oid, eq,
                     resp.get("stringCode", "")])
                print(f"[scalp] {ev} {side} @{ref} z={z:.2f} -> {resp.get('stringCode')}")
            else:
                if tick % 5 == 0:
                    print(f"[scalp] tick {tick}: mid {mid} z {z:+.2f} legs {len(legs)} eq ${eq:,.2f}")
        except Exception as e:
            print(f"[scalp] tick {tick} error: {e}", file=sys.stderr)
        time.sleep(a.interval)

    end_eq = get("account-information").get("equity", 0.0)
    log([datetime.now(timezone.utc).isoformat(), "END", "", "", "", "", "", "",
         "", end_eq, f"pnl ${end_eq-start_equity:+.2f}"])
    print(f"[scalp] done. equity ${end_eq:,.2f}  session PnL ${end_eq-start_equity:+.2f}")


if __name__ == "__main__":
    main()
