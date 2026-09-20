"""Read the Swappy Trading / Gold Syndicate channel (t.me/SNTrading786) via Telethon and
download its posts + chart images locally, so Claude can interpret them and build a bias.

ONE-TIME SETUP (you do this):
  1. Go to https://my.telegram.org -> API development tools -> create an app.
     Copy the api_id (a number) and api_hash (a long string).
  2. Add to .env (free-form lines):
         telegram_api_id   = 1234567
         telegram_api_hash = abcdef0123456789abcdef0123456789
         telegram_phone    = +91XXXXXXXXXX      (your Telegram phone, optional)
  3. FIRST login is interactive (Telegram sends you a code). Run it YOURSELF in the
     session prompt so you can type the code:
         ! .venv\\Scripts\\python.exe bot\\tg_channel_reader.py
     Enter the phone (if not in .env), then the code Telegram sends, then 2FA password
     if you have one. This creates bot/sntrading.session — after that it's non-interactive.

USAGE (after login):
  .venv\\Scripts\\python.exe bot\\tg_channel_reader.py            # last 120 messages
  .venv\\Scripts\\python.exe bot\\tg_channel_reader.py 400        # last 400 messages
Outputs:
  tg_channel/images/<id>.jpg   downloaded chart images
  tg_channel/index.json        [{id, date, text, image, has_video, has_voice}]
"""
import os, re, sys, json, datetime as dt
from telethon.sync import TelegramClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
OUT = os.path.join(ROOT, "tg_channel")
IMG = os.path.join(OUT, "images")
SESSION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sntrading")
CHANNEL = "SNTrading786"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 120


def env(*keys):
    """Return the first matching key's value. Accepts '=' or ':' separators."""
    txt = open(ENV, encoding="utf-8").read()
    for key in keys:
        m = re.search(rf"(?mi)^\s*{re.escape(key)}\s*[:=]\s*(.+?)\s*$", txt)
        if m:
            return m.group(1).strip().strip('"').strip()
    return None


def main():
    api_id = env("telegram_api_id", "api_id")
    api_hash = env("telegram_api_hash", "api_hash")
    if not api_id or not api_hash:
        raise SystemExit("add telegram_api_id / telegram_api_hash to .env (from my.telegram.org)")
    os.makedirs(IMG, exist_ok=True)
    phone = env("telegram_phone", "phone")
    with TelegramClient(SESSION, int(api_id), api_hash) as client:
        if not client.is_user_authorized():
            client.start(phone=phone) if phone else client.start()
        ent = client.get_entity(CHANNEL)
        rows = []
        for msg in client.iter_messages(ent, limit=LIMIT):
            img = None
            if msg.photo:
                img = os.path.join(IMG, f"{msg.id}.jpg")
                if not os.path.exists(img):
                    client.download_media(msg, img)
                img = os.path.relpath(img, ROOT)
            rows.append({
                "id": msg.id,
                "date": msg.date.astimezone(dt.timezone.utc).isoformat() if msg.date else None,
                "text": (msg.message or "").strip(),
                "image": img,
                "has_video": bool(getattr(msg, "video", None)),
                "has_voice": bool(getattr(msg, "voice", None)),
            })
        rows.sort(key=lambda r: r["id"])
        json.dump(rows, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        imgs = sum(1 for r in rows if r["image"])
        print(f"saved {len(rows)} messages ({imgs} images) -> tg_channel/index.json")
        if rows:
            safe = (rows[-1]["text"][:80] or "<media>").encode("ascii", "ignore").decode()
            print("newest:", rows[-1]["date"], "| text:", safe)


if __name__ == "__main__":
    main()
