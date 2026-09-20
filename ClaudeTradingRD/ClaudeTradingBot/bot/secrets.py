"""Load venue credentials from .env.bets into os.environ.

.env.bets is a free-form, human-edited file (NOT dotenv KEY=VALUE), shaped like:

    polymarket
    api : <uuid>
    key : 0x<wallet private key>

    Kalshi
    api_id = <uuid>
    key
    -----BEGIN RSA PRIVATE KEY-----
    <pem body...>
    -----END RSA PRIVATE KEY-----

This parser extracts those into the env vars the exec adapters expect:
  POLY_PRIVATE_KEY, POLY_API_KEY, KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY.

Idempotent and import-safe: it runs once on import and NEVER overwrites a value
already present in the real environment (so explicit env vars still win).
SECURITY: this file holds a raw wallet key + RSA key in plaintext — keep it out
of git and only fund the wallet with the smoke-test float.
"""
import os

_LOADED = False


def _set(key, val):
    if val and not os.environ.get(key):
        os.environ[key] = val


def load(path=None):
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    if path is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, ".env.bets")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return

    section = None
    poly_key = poly_api = kalshi_api = None
    poly_funder = poly_sigtype = None
    pem, in_pem = [], False

    for ln in lines:
        s = ln.strip()
        if in_pem:
            pem.append(ln)
            if "END" in s and "PRIVATE KEY" in s:
                in_pem = False
            continue
        if "BEGIN" in s and "PRIVATE KEY" in s:
            pem = [ln]
            in_pem = True
            continue
        low = s.strip("[]").lower()
        if low == "polymarket":
            section = "poly"
            continue
        if low == "kalshi":
            section = "kalshi"
            continue
        sep = ":" if ":" in s else ("=" if "=" in s else None)
        if not sep:
            continue
        k, v = s.split(sep, 1)
        k, v = k.strip().lower(), v.strip()
        if section == "poly":
            if k == "key":
                poly_key = v
            elif k == "api":
                poly_api = v
            elif k in ("funder", "proxy", "deposit", "address", "wallet"):
                poly_funder = v
            elif k in ("signature_type", "sig_type", "sigtype"):
                poly_sigtype = v
        elif section == "kalshi":
            if k in ("api_id", "api", "api_key", "key_id"):
                kalshi_api = v

    _set("POLY_PRIVATE_KEY", poly_key)
    _set("POLY_API_KEY", poly_api)
    _set("POLY_FUNDER", poly_funder)
    _set("POLY_SIGNATURE_TYPE", poly_sigtype)
    _set("KALSHI_API_KEY_ID", kalshi_api)
    if pem:
        _set("KALSHI_PRIVATE_KEY", "\n".join(pem).strip() + "\n")


load()
