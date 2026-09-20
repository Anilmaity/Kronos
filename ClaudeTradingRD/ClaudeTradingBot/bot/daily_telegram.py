"""Daily Telegram update for the active FundingPips account.

Read-only on the broker (never trades). Sends one message with balance, equity, goal
progress, day-over-day P&L (via a local snapshot), open positions and floating P&L.

Setup (one time):
  1. In Telegram, message @BotFather -> /newbot -> copy the token.
  2. Add to .env (free-form lines, same style as meta_id/access_token):
         telegram_token = 123456:ABC-yourBotToken
     Then message your new bot once (say "hi"), and run:
         .venv/Scripts/python.exe bot/tg_chatid.py
     which writes telegram_chat_id back into .env automatically.
  3. Test:  .venv/Scripts/python.exe bot/daily_telegram.py
  4. Schedule daily (see SCHEDULE note at bottom).
"""
import os, re, json, datetime as dt, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
SNAP = os.path.join(ROOT, "journal", "tg_daily_snapshot.json")
BASE = "https://mt-client-api-v1.london.agiliumtrade.ai"
GOAL = 5500.0
EFF_LEVERAGE, CONTRACT = 30.0, 100.0


def env(key):
    try:
        txt = open(ENV, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def tg_send(text):
    tok, chat = env("telegram_token"), env("telegram_chat_id")
    if not tok or not chat:
        raise SystemExit("missing telegram_token / telegram_chat_id in .env "
                         "(run bot/tg_chatid.py after messaging your bot)")
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                            "disable_web_page_preview": True}, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    acct, token = env("meta_id"), env("access_token")
    if not acct or not token:
        raise SystemExit("missing meta_id/access_token in .env")
    h = {"auth-token": token}

    def get(path):
        r = requests.get(f"{BASE}/users/current/accounts/{acct}/{path}", headers=h, timeout=30)
        r.raise_for_status()
        return r.json()

    info = get("account-information")
    bal, eq = info.get("balance", 0.0), info.get("equity", 0.0)
    pos = get("positions")
    try:
        px = get("symbols/XAUUSD/current-price"); mid = (px.get("bid", 0) + px.get("ask", 0)) / 2
        price_line = f"XAUUSD {px.get('bid')}/{px.get('ask')}"
    except Exception:
        mid, price_line = 0.0, "XAUUSD n/a"
    floating = sum(p.get("profit", 0.0) for p in pos)

    # day-over-day delta via local snapshot
    today = dt.date.today().isoformat()
    prev = None
    if os.path.exists(SNAP):
        try: prev = json.load(open(SNAP))
        except Exception: prev = None
    day_delta = (eq - prev["equity"]) if (prev and prev.get("date") != today) else (
        (eq - prev["equity"]) if prev else None)
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    # store start-of-today baseline once per day; keep yesterday's close for delta
    if not prev or prev.get("date") != today:
        json.dump({"date": today, "equity": eq, "balance": bal,
                   "prev_equity": prev["equity"] if prev else eq}, open(SNAP, "w"))
        base = prev["equity"] if prev else eq
    else:
        json.dump(prev, open(SNAP, "w")); base = prev.get("prev_equity", eq)
    day_delta = eq - base

    need = GOAL - eq
    pct = 100 * need / eq if eq else 0
    arrow = "🟢" if day_delta >= 0 else "🔴"
    lines = [
        f"<b>📊 Daily update — {today}</b>",
        f"Balance <b>${bal:,.2f}</b>   Equity <b>${eq:,.2f}</b>",
        f"{arrow} Day Δ <b>${day_delta:+,.2f}</b>",
        f"🎯 Goal ${GOAL:,.0f} — need <b>${need:+,.2f}</b> ({pct:+.2f}%)",
        f"📈 Floating P/L ${floating:+,.2f}   Open positions: {len(pos)}",
        f"{price_line}",
    ]
    for p in pos[:8]:
        lines.append(f"  • {p['type']} {p['volume']} @ {p['openPrice']} "
                     f"P/L ${p.get('profit',0):+.2f}")
    tg_send("\n".join(lines))
    print("sent:", today, f"equity ${eq:,.2f} dayΔ ${day_delta:+,.2f}")


if __name__ == "__main__":
    main()

# SCHEDULE (Windows, daily at 21:30 local):
#   schtasks /Create /TN "XAU Daily Telegram" /TR "C:\Projects\ClaudeProjects\ClaudeTradingBot\.venv\Scripts\python.exe C:\Projects\ClaudeProjects\ClaudeTradingBot\bot\daily_telegram.py" /SC DAILY /ST 21:30 /F
