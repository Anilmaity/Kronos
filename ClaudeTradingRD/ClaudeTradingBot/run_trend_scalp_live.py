"""TREND-ALIGNED HIGH-WIN-RATE scalper on the FundingPips demo (account 6c7ce166).

Goal: small profits, very high win rate, but only WITH the trend (so the WR is real,
not just the negative-skew illusion of fading everything).

  * Bias: M15 EMA50 vs EMA200. Trade ONLY in the bias direction.
  * Entry (pullback fade in trend dir): downtrend -> SHORT a minor bounce (z >= +ENTRY_Z);
    uptrend -> LONG a minor dip (z <= -ENTRY_Z). z = (close-SMA50)/std50 on M15.
  * Small TP (high win rate) + wider SL: TP $2.5 / SL $8. Honest tradeoff -> high WR,
    but a loss = ~3 wins, so the daily kill switch + trend filter cap the damage.
  * Averaging = PYRAMID INTO WINNERS only (add as price moves in our favour), capped.
  * Hard daily-loss kill switch. Demo only; risk per leg ~0.16% (0.01 lot, $8 SL).

    .venv/Scripts/python.exe run_trend_scalp_live.py --max-ticks 1200 --interval 45
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

SMA_N = 50             # z-score basis (M15)
ENTRY_Z = 1.0         # pullback size to fade WITH the trend (small => frequent, high WR)
TP_D = 2.5            # small profit  -> high win rate
SL_D = 8.0           # wider stop     -> protects the win rate (accepts negative skew)
PYRAMID_D = 3.0      # add a leg after price moves this far IN OUR FAVOUR
MAX_LEGS = 3
LOT = 0.01
DAILY_KILL_PCT = 3.0
REENTRY_GAP = 60     # seconds to wait after a basket closes before re-entering


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


def ema(v, n):
    k = 2 / (n + 1); out = [v[0]]
    for x in v[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def market():
    """Return (bias, z) from completed M15 bars."""
    cs = [c for c in data.candles(granularity="M15", count=260) if c["complete"]]
    cl = [c["c"] for c in cs]
    e50, e200 = ema(cl, 50), ema(cl, 200)
    bias = "down" if e50[-1] < e200[-1] else "up"
    w = cl[-SMA_N:]
    m = sum(w) / len(w)
    sd = (sum((x - m) ** 2 for x in w) / len(w)) ** 0.5
    z = (cl[-1] - m) / sd if sd else 0.0
    return bias, z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-ticks", type=int, default=1200)
    ap.add_argument("--interval", type=int, default=45)
    a = ap.parse_args()

    acct, token = envval("meta_id"), envval("access_token")
    H = {"auth-token": token, "Content-Type": "application/json"}
    sess = requests.Session()

    def get(path):
        r = sess.get(f"{BASE}/users/current/accounts/{acct}/{path}", headers=H, timeout=30)
        r.raise_for_status(); return r.json()

    def trade(payload):
        return sess.post(f"{BASE}/users/current/accounts/{acct}/trade", headers=H,
                         json=payload, timeout=60).json()

    start_eq = get("account-information").get("equity", 0.0)
    print(f"[hwr-scalp] start ${start_eq:,.2f}  TREND-ALIGNED high-WR: z>=±{ENTRY_Z} "
          f"TP${TP_D} SL${SL_D} pyramid+${PYRAMID_D} maxlegs {MAX_LEGS}")
    log([datetime.now(timezone.utc).isoformat(), "START", "", "", "", "", "", "",
         "", start_eq, "TREND-ALIGNED high-winrate scalper (small TP, fade pullback with trend)"])

    side = None
    legs = []
    last_close_t = 0.0

    for tick in range(a.max_ticks):
        try:
            info = get("account-information"); eq = info.get("equity", 0.0)
            if eq <= start_eq * (1 - DAILY_KILL_PCT / 100.0):
                log([datetime.now(timezone.utc).isoformat(), "KILL", "", "", "", "", "", "",
                     "", eq, "daily loss kill"]); print("[hwr-scalp] KILL"); break
            px = get(f"symbols/{SYMBOL}/current-price")
            bid, ask = px["bid"], px["ask"]; mid = round((bid + ask) / 2, 2)
            bias, z = market()
            open_ids = {p["id"] for p in get("positions") if p.get("symbol") == SYMBOL}
            had = len(legs)
            legs = [(pid, e) for (pid, e) in legs if pid in open_ids]
            if had and not legs:
                last_close_t = time.time()  # basket just fully closed
            if not legs:
                side = None

            action = None
            if side is None:
                if time.time() - last_close_t >= REENTRY_GAP:
                    if bias == "down" and z >= ENTRY_Z:        # fade a bounce, with the downtrend
                        action = ("short", bid)
                    elif bias == "up" and z <= -ENTRY_Z:       # fade a dip, with the uptrend
                        action = ("long", ask)
            else:
                last = legs[-1][1]
                favour = (mid <= last - PYRAMID_D) if side == "short" else (mid >= last + PYRAMID_D)
                if favour and len(legs) < MAX_LEGS:
                    action = (side, bid if side == "short" else ask)

            if action:
                s, ref = action
                if s == "short":
                    sl_px, tp_px, at = round(ref + SL_D, 2), round(ref - TP_D, 2), "ORDER_TYPE_SELL"
                else:
                    sl_px, tp_px, at = round(ref - SL_D, 2), round(ref + TP_D, 2), "ORDER_TYPE_BUY"
                resp = trade({"actionType": at, "symbol": SYMBOL, "volume": LOT,
                              "stopLoss": sl_px, "takeProfit": tp_px, "comment": "hwr-trend-scalp"})
                ok = resp.get("stringCode") == "TRADE_RETCODE_DONE"
                pid = resp.get("positionId") or resp.get("orderId")
                if ok:
                    side = s; legs.append((pid, ref))
                ev = "open_leg" if len(legs) == 1 else "pyramid_add"
                log([datetime.now(timezone.utc).isoformat(), ev if ok else "reject",
                     s, round(z, 2), ref, LOT, sl_px, tp_px, pid, eq,
                     f"bias={bias} {resp.get('stringCode','')}"])
                print(f"[hwr-scalp] {ev} {s} @{ref} z={z:+.2f} bias={bias} -> {resp.get('stringCode')}")
            elif tick % 5 == 0:
                print(f"[hwr-scalp] tick {tick}: mid {mid} bias {bias} z {z:+.2f} "
                      f"legs {len(legs)} eq ${eq:,.2f}")
        except Exception as e:
            print(f"[hwr-scalp] tick {tick} err: {e}", file=sys.stderr)
        time.sleep(a.interval)

    end_eq = get("account-information").get("equity", 0.0)
    log([datetime.now(timezone.utc).isoformat(), "END", "", "", "", "", "", "", "",
         end_eq, f"pnl ${end_eq-start_eq:+.2f}"])
    print(f"[hwr-scalp] done. equity ${end_eq:,.2f} pnl ${end_eq-start_eq:+.2f}")


if __name__ == "__main__":
    main()
