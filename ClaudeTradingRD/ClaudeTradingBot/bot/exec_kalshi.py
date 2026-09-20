"""Kalshi authenticated execution adapter (REAL MONEY).

Read-only market data lives in bot/kalshi.py. This module ADDS the authenticated
order-placement surface needed to go live: balance(), place_ioc(), get_order(),
cancel(). Everything is gated by DRY_RUN — when DRY_RUN is true (the default)
NOTHING is sent to Kalshi; calls return a simulated acknowledgement so the whole
pipeline can be exercised without moving money.

Auth (per Kalshi docs): three headers on every request —
  KALSHI-ACCESS-KEY        = API key id
  KALSHI-ACCESS-TIMESTAMP  = unix milliseconds (string)
  KALSHI-ACCESS-SIGNATURE  = base64( RSA-PSS-SHA256( timestamp + METHOD + path ) )
`path` is the request path INCLUDING the /trade-api/v2 prefix, EXCLUDING any
query string. Production base = https://external-api.kalshi.com/trade-api/v2 .

Credentials are read from the environment (you place them in .env yourself):
  KALSHI_API_KEY_ID     - the key id (uuid)
  KALSHI_PRIVATE_KEY    - PEM private key, or
  KALSHI_PRIVATE_KEY_FILE - path to the PEM file
  KALSHI_API_BASE       - optional override of the base URL
"""
import base64
import os
import time

import requests

from bot import secrets as _secrets  # loads .env.bets into os.environ on import

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    _CRYPTO = True
except ImportError:  # pragma: no cover - import guard
    _CRYPTO = False

API_BASE = os.getenv("KALSHI_API_BASE",
                     "https://external-api.kalshi.com/trade-api/v2")
_TIMEOUT = 10
_S = requests.Session()


def dry_run() -> bool:
    """Live orders are sent ONLY when DRY_RUN is explicitly disabled."""
    return os.getenv("DRY_RUN", "true").strip().lower() not in ("0", "false", "no")


def _load_private_key():
    pem = os.getenv("KALSHI_PRIVATE_KEY")
    if not pem:
        path = os.getenv("KALSHI_PRIVATE_KEY_FILE")
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                pem = fh.read().decode()
    if not pem:
        raise RuntimeError("KALSHI_PRIVATE_KEY / KALSHI_PRIVATE_KEY_FILE not set")
    if not _CRYPTO:
        raise RuntimeError("cryptography not installed")
    return serialization.load_pem_private_key(pem.encode(), password=None)


def _sign(ts_ms: str, method: str, path: str) -> str:
    key = _load_private_key()
    msg = (ts_ms + method.upper() + path).encode()
    sig = key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode()


def _headers(method: str, path: str) -> dict:
    key_id = os.getenv("KALSHI_API_KEY_ID")
    if not key_id:
        raise RuntimeError("KALSHI_API_KEY_ID not set")
    ts_ms = str(int(time.time() * 1000))
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts_ms,
        "KALSHI-ACCESS-SIGNATURE": _sign(ts_ms, method, path),
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, body=None):
    # `path` must start with /trade-api/v2 (that is what we sign).
    sign_path = path.split("?", 1)[0]
    headers = _headers(method, sign_path)
    url = API_BASE.replace("/trade-api/v2", "") + path
    r = _S.request(method, url, headers=headers, json=body, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json() if r.content else {}


# --- public surface -------------------------------------------------------

def has_creds() -> bool:
    return bool(os.getenv("KALSHI_API_KEY_ID") and
                (os.getenv("KALSHI_PRIVATE_KEY") or
                 os.getenv("KALSHI_PRIVATE_KEY_FILE")))


def balance_detail() -> dict:
    """Real balance when creds are present (read-only — safe even in DRY_RUN).
    Returns {value: $ or None, real: bool, note: str}."""
    if not has_creds():
        return {"value": float(os.getenv("KALSHI_PAPER_BALANCE", "10")),
                "real": False, "note": "no Kalshi creds"}
    try:
        data = _request("GET", "/trade-api/v2/portfolio/balance")
        return {"value": data.get("balance", 0) / 100.0, "real": True,
                "note": ""}  # Kalshi reports cents
    except Exception as e:  # noqa: BLE001
        return {"value": None, "real": False, "note": str(e)[:140]}


def balance() -> float:
    """Available balance in DOLLARS (sentinel if unavailable)."""
    d = balance_detail()
    return d["value"] if d["value"] is not None else \
        float(os.getenv("KALSHI_PAPER_BALANCE", "10"))


def place_ioc(ticker: str, side: str, count: int, price_cents: int,
              client_order_id: str):
    """Immediate-or-cancel BUY of `count` contracts on `side` ('yes'/'no')
    at a limit of `price_cents` (1-99). IOC so we learn the fill at once and
    never leave a resting leg that could fill after the other leg is gone.

    Returns {order_id, status, filled, avg_price_cents, dry}.
    """
    side = side.lower()
    assert side in ("yes", "no"), side
    price_cents = max(1, min(99, int(round(price_cents))))
    body = {
        "ticker": ticker,
        "action": "buy",
        "side": side,
        "count": int(count),
        "type": "limit",
        "time_in_force": "immediate_or_cancel",
        "client_order_id": client_order_id,
        ("yes_price" if side == "yes" else "no_price"): price_cents,
    }
    if dry_run():
        return {"order_id": f"DRY-{client_order_id}", "status": "dry",
                "filled": int(count), "avg_price_cents": price_cents,
                "dry": True, "request": body}
    data = _request("POST", "/trade-api/v2/portfolio/orders", body)
    o = data.get("order", data)
    return {"order_id": o.get("order_id"), "status": o.get("status"),
            "filled": _fill_count(o),
            "avg_price_cents": price_cents, "dry": False, "raw": o}


def _fill_count(o: dict) -> int:
    """Filled contracts from a Kalshi order object. Kalshi reports this as
    `fill_count_fp` (a STRING like "2.00"). The old code read `count`, which does
    not exist -> every real fill looked like 0 ("no_fill"), so the strategy kept
    re-buying into a NAKED position. Read the real field; tolerate misses."""
    for k in ("fill_count_fp", "filled_count", "count"):
        v = o.get(k)
        if v is not None:
            try:
                return int(float(v))
            except (TypeError, ValueError):
                pass
    return 0


def position_qty(ticker: str) -> int:
    """Signed contracts actually held for `ticker`: +N = N YES, -N = N NO, 0 =
    flat. Read-only ground truth from the venue — used to RECONCILE after every
    order so a misread fill can never leave a hidden naked leg. DRY_RUN -> 0."""
    if dry_run() or not has_creds():
        return 0
    try:
        data = _request("GET", "/trade-api/v2/portfolio/positions")
    except Exception:  # noqa: BLE001
        return 0
    for p in (data.get("market_positions") or []):
        if p.get("ticker") == ticker:
            try:
                return int(float(p.get("position_fp") or p.get("position") or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def flatten(ticker: str, side: str, count: int, client_order_id: str) -> int:
    """EMERGENCY EXIT: SELL `count` contracts of `side` ('yes'/'no') via IOC at a
    1c floor, so it crosses whatever bid exists (you receive the BID price, not
    the floor). Used to unwind an unhedged leg so we never sit naked. Returns the
    number of contracts actually sold."""
    side = side.lower()
    assert side in ("yes", "no"), side
    if int(count) < 1:
        return 0
    body = {
        "ticker": ticker, "action": "sell", "side": side, "count": int(count),
        "type": "limit", "time_in_force": "immediate_or_cancel",
        "client_order_id": client_order_id,
        ("yes_price" if side == "yes" else "no_price"): 1,  # floor -> fill at bid
    }
    if dry_run():
        return int(count)
    data = _request("POST", "/trade-api/v2/portfolio/orders", body)
    return _fill_count(data.get("order", data))


def positions():
    """Open Kalshi market positions (read-only; needs creds)."""
    if not has_creds():
        return []
    try:
        data = _request("GET", "/trade-api/v2/portfolio/positions")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for p in (data.get("market_positions") or []):
        # Current API: `position_fp` (string contracts), `market_exposure_dollars`
        # (string $). The old `position`/`market_exposure` fields are gone, so
        # this loop used to skip EVERY real position — hiding naked legs from the
        # dashboard. Read the real fields.
        try:
            qty = int(float(p.get("position_fp") or p.get("position") or 0))
        except (TypeError, ValueError):
            qty = 0
        if not qty:
            continue
        try:
            exposure = float(p.get("market_exposure_dollars")
                             or (p.get("market_exposure", 0) / 100.0) or 0)
        except (TypeError, ValueError):
            exposure = 0.0
        # Live current mark: last-trade YES price -> value the held side at market.
        cur = None
        try:
            from bot import kalshi as _kdata
            yp, _ = _kdata._last_trade(p.get("ticker"))
            if yp is not None:
                cur = round(yp if qty > 0 else (1.0 - yp), 4)
        except Exception:  # noqa: BLE001
            cur = None
        value = round(abs(qty) * cur, 2) if cur is not None else round(exposure, 2)
        out.append({
            "venue": "Kalshi", "title": p.get("ticker"),
            "outcome": "YES" if qty > 0 else "NO", "size": abs(qty),
            "avg": round((exposure / abs(qty)), 4) if qty else None,
            "cur": cur, "value": value, "redeemable": False,
        })
    return out


def open_orders():
    """Resting Kalshi orders (read-only; needs creds)."""
    if not has_creds():
        return []
    try:
        data = _request("GET", "/trade-api/v2/portfolio/orders?status=resting")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for o in (data.get("orders") or []):
        px = o.get("yes_price") if o.get("side") == "yes" else o.get("no_price")
        out.append({
            "venue": "Kalshi", "side": (o.get("side") or "").upper(),
            "price": (px or 0) / 100.0, "size": o.get("remaining_count") or o.get("count"),
            "filled": None, "market": o.get("ticker"),
        })
    return out


def get_order(order_id: str):
    if dry_run() or str(order_id).startswith("DRY-"):
        return {"order_id": order_id, "status": "dry"}
    return _request("GET", f"/trade-api/v2/portfolio/orders/{order_id}")


def cancel(order_id: str):
    if dry_run() or str(order_id).startswith("DRY-"):
        return {"order_id": order_id, "status": "dry-cancel"}
    return _request("DELETE", f"/trade-api/v2/portfolio/orders/{order_id}")


if __name__ == "__main__":
    print("DRY_RUN =", dry_run(), "| base =", API_BASE)
    try:
        print("balance $", balance())
    except Exception as e:  # noqa: BLE001
        print("balance error:", e)
