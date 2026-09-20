"""Discover your Telegram chat_id and write it into .env.
Run AFTER you (1) created a bot with @BotFather, (2) put `telegram_token = ...` in .env,
and (3) sent your bot any message (e.g. "hi").

    .venv/Scripts/python.exe bot/tg_chatid.py
"""
import os, re, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")


def env(key):
    txt = open(ENV, encoding="utf-8").read()
    m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", txt)
    return m.group(1).strip().strip('"').strip() if m else None


def main():
    tok = env("telegram_token")
    if not tok:
        raise SystemExit("add `telegram_token = <token>` to .env first")
    r = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates", timeout=30)
    r.raise_for_status()
    data = r.json()
    chats = {}
    for u in data.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        ch = msg.get("chat")
        if ch:
            chats[ch["id"]] = ch.get("username") or ch.get("title") or ch.get("first_name")
    if not chats:
        raise SystemExit("no chats found — message your bot once, then re-run.")
    cid = list(chats)[-1]
    print("found chats:", chats, "-> using", cid)
    txt = open(ENV, encoding="utf-8").read()
    if re.search(r"(?mi)^\s*telegram_chat_id\s*=", txt):
        txt = re.sub(r"(?mi)^\s*telegram_chat_id\s*=.*$", f"telegram_chat_id = {cid}", txt)
    else:
        txt = txt.rstrip() + f"\ntelegram_chat_id = {cid}\n"
    open(ENV, "w", encoding="utf-8").write(txt)
    print(f"wrote telegram_chat_id = {cid} to .env")


if __name__ == "__main__":
    main()
