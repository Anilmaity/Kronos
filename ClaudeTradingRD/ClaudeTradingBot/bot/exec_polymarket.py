"""Polymarket CLOB **V2** authenticated execution adapter (REAL MONEY).

Read-only market data lives in bot/polymarket.py. This adds the authenticated
order surface via py-clob-client-v2 (the CLOB V2 / pUSD client, required since
Polymarket's 2026-04-28 exchange upgrade): balance(), place_fok(), cancel().
Gated by DRY_RUN (default true) — nothing is sent until you disable it.

Orders are FILL-OR-KILL: each leg fills entirely at once or is killed — the
simplest defense against legging risk (no partial resting leg to reconcile).

Credentials (loaded from .env.bets by bot/secrets):
  POLY_PRIVATE_KEY     - wallet private key that signs orders (the EOA signer)
  POLY_FUNDER          - funding address that HOLDS the pUSD (your proxy wallet)
  POLY_SIGNATURE_TYPE  - 3 = POLY_1271 / deposit-wallet (default, required since
                         the 2026 migration), 1 = legacy POLY_PROXY, 0 = EOA,
                         2 = Gnosis Safe
  POLY_CLOB_HOST       - optional override (default https://clob.polymarket.com)

NOTE: tradable balance is held as pUSD (1:1 USDC ERC-20). The CLOB's
get_balance_allowance reads 0 for proxy wallets (it binds the API key to the
signer EOA, not the funded proxy — py-clob-client-v2 #70), so balance_detail()
reads pUSD on-chain at POLY_FUNDER instead. Orders carry maker=funder via
signature_type=POLY_PROXY, so they are validated against the proxy's real pUSD.
"""
import os

from bot import secrets as _secrets  # loads .env.bets into os.environ on import

try:
    from py_clob_client_v2 import (ClobClient, OrderArgs, OrderType, Side,
                                   PartialCreateOrderOptions, OrderPayload,
                                   OpenOrderParams, BalanceAllowanceParams,
                                   AssetType)
    _CLOB = True
except ImportError:  # pragma: no cover - import guard
    _CLOB = False

HOST = os.getenv("POLY_CLOB_HOST", "https://clob.polymarket.com")
CHAIN_ID = 137  # Polygon
_client = None

# Tradable balance is pUSD (1:1 USDC-backed ERC-20) since the 2026 migration.
PUSD_TOKEN = os.getenv("POLY_PUSD_TOKEN",
                       "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
POLYGON_RPC = os.getenv("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com")

# CLOB V2 exchange contracts that must hold MAX pUSD allowance from the funder
# (set once via Polymarket's "Enable trading" / first trade). Confirmed on-chain.
EXCHANGE_SPENDERS = [
    "0xE111180000d2663C0091e4f400237545B87B996B",
    "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    "0xe2222d279d744050d28e00520010520000310F59",
]
_MAX_THRESHOLD = 10 ** 30  # treat anything above this as "unlimited"


def dry_run() -> bool:
    return os.getenv("DRY_RUN", "true").strip().lower() not in ("0", "false", "no")


def has_creds() -> bool:
    return bool(os.getenv("POLY_PRIVATE_KEY"))


# --- on-chain helpers (read-only, no client/auth needed) ------------------

def _rpc_call(to, data):
    import requests
    r = requests.post(POLYGON_RPC, timeout=12, json={
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"]}).json()
    res = r.get("result")
    return None if (not res or res == "0x") else int(res, 16)


def _onchain_balance(token, address, decimals=6):
    data = "0x70a08231" + "0" * 24 + address.lower().replace("0x", "")
    v = _rpc_call(token, data)
    return None if v is None else v / 10 ** decimals


def _onchain_allowance(token, owner, spender):
    data = ("0xdd62ed3e" + "0" * 24 + owner.lower()[2:]
            + "0" * 24 + spender.lower()[2:])
    return _rpc_call(token, data)


def eoa_address():
    """The wallet address derived from POLY_PRIVATE_KEY (the EOA signer)."""
    pk = os.getenv("POLY_PRIVATE_KEY")
    if not pk:
        return None
    try:
        from eth_account import Account
        return Account.from_key(pk).address
    except Exception:  # noqa: BLE001
        return None


def allowance_status():
    """On-chain pUSD allowance from the funder to each CLOB V2 exchange.
    Returns {ready: bool, spenders: {addr: 'MAX'|amount|None}}."""
    funder = os.getenv("POLY_FUNDER") or eoa_address()
    out, ready = {}, bool(funder)
    for sp in EXCHANGE_SPENDERS:
        a = _onchain_allowance(PUSD_TOKEN, funder, sp) if funder else None
        out[sp] = ("MAX" if (a and a >= _MAX_THRESHOLD)
                   else (a / 1e6 if a is not None else None))
        if not (a and a >= _MAX_THRESHOLD):
            ready = False
    return {"ready": ready, "spenders": out}


# --- authenticated client -------------------------------------------------

def _get_client():
    """Lazily build + authenticate the CLOB V2 client. Never called in DRY_RUN."""
    global _client
    if _client is not None:
        return _client
    if not _CLOB:
        raise RuntimeError("py-clob-client-v2 not installed")
    pk = os.getenv("POLY_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("POLY_PRIVATE_KEY not set")
    funder = os.getenv("POLY_FUNDER") or None
    # 3 = POLY_1271 (the "deposit wallet" ERC-1271 flow). Since Polymarket's 2026
    # account migration, funds sit in a per-user DepositWallet smart contract and
    # the CLOB V2 REJECTS the legacy proxy maker (sig_type 1) with "maker address
    # not allowed, please use the deposit wallet flow". Verified live: a real
    # order from funder 0x4748… is accepted only with signature_type=3.
    sig_type = int(os.getenv("POLY_SIGNATURE_TYPE", "3"))
    c = ClobClient(HOST, chain_id=CHAIN_ID, key=pk,
                   signature_type=sig_type, funder=funder)
    c.set_api_creds(_api_creds(c))
    _client = c
    return c


def _api_creds(c):
    """Get L2 API creds, DERIVING first (the steady-state path).

    The signer EOA is provisioned with an API key on first use, so on every run
    thereafter CREATE returns 400 'Could not create api key'. The library's
    create_or_derive_api_key() tries CREATE first and logs that 400 as an error
    on each call. We invert the order — derive the existing key (deterministic
    from the L1 signature, no error), and only CREATE on the genuine first run.
    """
    try:
        creds = c.derive_api_key()
        if getattr(creds, "api_key", None):
            return creds
    except Exception:  # noqa: BLE001 — first run: no key to derive yet
        pass
    return c.create_api_key()


def sync_clob_balance():
    """Ask the CLOB to re-read on-chain pUSD into its cache (no transaction)."""
    if dry_run() or not has_creds():
        return None
    try:
        return _get_client().update_balance_allowance(
            BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
    except Exception:  # noqa: BLE001
        return None


# --- balance --------------------------------------------------------------

def balance_detail() -> dict:
    """Real tradable balance (read-only — safe even in DRY_RUN).
    Returns {value: $ or None, real: bool, note: str}. Primary source = pUSD
    held by the funder on-chain (matches the UI's 'Available to trade')."""
    if not has_creds():
        return {"value": float(os.getenv("POLY_PAPER_BALANCE", "10")),
                "real": False, "note": "no Polymarket creds"}
    addr = os.getenv("POLY_FUNDER") or eoa_address()
    if addr:
        try:
            v = _onchain_balance(PUSD_TOKEN, addr)
            if v is not None:
                return {"value": round(v, 4), "real": True, "note": "pUSD"}
        except Exception as e:  # noqa: BLE001
            return {"value": None, "real": False, "note": str(e)[:140]}
    return {"value": None, "real": False, "note": "no funder address"}


def balance() -> float:
    d = balance_detail()
    return d["value"] if d["value"] is not None else \
        float(os.getenv("POLY_PAPER_BALANCE", "10"))


# --- orders ---------------------------------------------------------------

def place_fok(token_id: str, price: float, size: int, side: str = "BUY",
              client_id: str = "", tick_size: str = "0.01"):
    """Fill-or-kill order for `size` shares of `token_id` at `price`.
    Returns {order_id, status, filled, dry}."""
    price = round(max(0.01, min(0.99, float(price))), 2)
    size = int(size)
    if dry_run():
        return {"order_id": f"DRY-{client_id}", "status": "dry",
                "filled": size, "price": price, "dry": True,
                "request": {"token_id": token_id, "price": price,
                            "size": size, "side": side}}
    sync_clob_balance()  # nudge the CLOB to re-read pUSD before validating
    c = _get_client()
    poly_side = Side.BUY if side.upper() == "BUY" else Side.SELL
    resp = c.create_and_post_order(
        order_args=OrderArgs(token_id=str(token_id), price=price,
                             size=float(size), side=poly_side),
        options=PartialCreateOrderOptions(tick_size=tick_size),
        order_type=OrderType.FOK)
    resp = resp if isinstance(resp, dict) else getattr(resp, "__dict__", {}) or {}
    oid = resp.get("orderID") or resp.get("orderId") or resp.get("id")
    ok = bool(resp.get("success", False)) or bool(oid)
    return {"order_id": oid,
            "status": resp.get("status") or ("matched" if ok else "killed"),
            "filled": size if ok else 0, "price": price,
            "dry": False, "raw": resp}


def place_limit_gtc(token_id: str, price: float, size: float, side: str = "BUY",
                    tick_size: str = "0.01"):
    """Resting GTC limit order (used for the non-fillable connectivity test).
    Returns the raw CLOB response. Refuses to run in DRY_RUN."""
    if dry_run():
        return {"status": "dry", "dry": True}
    sync_clob_balance()
    c = _get_client()
    poly_side = Side.BUY if side.upper() == "BUY" else Side.SELL
    resp = c.create_and_post_order(
        order_args=OrderArgs(token_id=str(token_id), price=round(float(price), 2),
                             size=float(size), side=poly_side),
        options=PartialCreateOrderOptions(tick_size=tick_size),
        order_type=OrderType.GTC)
    return resp if isinstance(resp, dict) else getattr(resp, "__dict__", {}) or {}


def cancel(order_id):
    if dry_run() or str(order_id).startswith("DRY-"):
        return {"order_id": order_id, "status": "dry-cancel"}
    c = _get_client()
    return c.cancel_order(OrderPayload(orderID=order_id))


def positions():
    """Open Polymarket positions for the funder, via the public data-api."""
    import requests
    funder = os.getenv("POLY_FUNDER") or eoa_address()
    if not funder:
        return []
    try:
        r = requests.get("https://data-api.polymarket.com/positions",
                         params={"user": funder, "sizeThreshold": 0.01},
                         timeout=12).json()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for p in (r if isinstance(r, list) else []):
        out.append({
            "venue": "Polymarket", "title": p.get("title"),
            "outcome": p.get("outcome"), "size": p.get("size"),
            "avg": p.get("avgPrice"), "cur": p.get("curPrice"),
            "value": p.get("currentValue"), "redeemable": p.get("redeemable"),
        })
    return out


def position_qty(token_id: str) -> float:
    """Shares actually held for `token_id` (the outcome token), from the public
    data-api. Read-only ground truth used to RECONCILE a hedge so we never sit
    with one leg unmatched. DRY_RUN / no creds -> 0."""
    if dry_run() or not has_creds():
        return 0.0
    import requests
    funder = os.getenv("POLY_FUNDER") or eoa_address()
    if not funder:
        return 0.0
    try:
        r = requests.get("https://data-api.polymarket.com/positions",
                         params={"user": funder, "sizeThreshold": 0.0},
                         timeout=12).json()
    except Exception:  # noqa: BLE001
        return 0.0
    for p in (r if isinstance(r, list) else []):
        if str(p.get("asset")) == str(token_id):
            try:
                return float(p.get("size") or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def flatten(token_id: str, size, client_id: str = "") -> int:
    """EMERGENCY EXIT: SELL `size` shares of `token_id` at a 1c floor so it
    crosses the bid (deep book -> fills at the real bid). Returns shares sold."""
    size = int(size)
    if size < 1:
        return 0
    r = place_fok(str(token_id), 0.01, size, "SELL", client_id)
    return int(r.get("filled", 0))


def open_orders():
    """Resting Polymarket orders (read-only; needs API creds)."""
    if not has_creds():
        return []
    try:
        orders = _get_client().get_open_orders()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for o in (orders or []):
        o = o if isinstance(o, dict) else getattr(o, "__dict__", {})
        out.append({
            "venue": "Polymarket", "side": o.get("side"),
            "price": o.get("price"), "size": o.get("original_size") or o.get("size"),
            "filled": o.get("size_matched"),
            "market": o.get("market") or o.get("asset_id"),
        })
    return out


def diagnose():
    """Report what the V2 client sees: signer address, configured funder/sig
    type, on-chain pUSD at the funder, allowance readiness, and the CLOB's
    (often EOA-bound, thus 0) balance reading."""
    out = {"eoa_signer": eoa_address(),
           "configured_funder": os.getenv("POLY_FUNDER"),
           "configured_sig_type": os.getenv("POLY_SIGNATURE_TYPE", "1"),
           "onchain_pusd": balance_detail(),
           "allowances": allowance_status()}
    if has_creds() and _CLOB:
        try:
            c = _get_client()
            out["clob_address"] = c.get_address()
            out["clob_balance"] = c.get_balance_allowance(
                BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
        except Exception as e:  # noqa: BLE001
            out["clob_error"] = str(e)[:160]
    return out


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "diagnose":
        print(json.dumps(diagnose(), indent=2, default=str))
    else:
        print("DRY_RUN =", dry_run(), "| host =", HOST)
        print("EOA signer:", eoa_address(), "| funder:", os.getenv("POLY_FUNDER"))
        d = balance_detail()
        print(f"pUSD balance: ${d['value']} (real={d['real']}) {d['note']}")
