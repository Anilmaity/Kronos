"""CLI for the LIVE cross-venue 15m lock smoke test ($10/account).

  python livearb.py status      # show DRY_RUN, balances, kill switch, config
  python livearb.py run [secs]  # supervised loop (default poll 3s)
  python livearb.py stop        # create the kill-switch file
  python livearb.py go          # remove the kill-switch file

GOING LIVE: orders are SIMULATED until you set DRY_RUN=false in the environment
AND have funded both accounts with credentials in .env. Start in DRY_RUN, watch
a few windows print "would place ...", THEN flip it.
"""
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.bets")  # venue creds may live here

from bot import polymarket, kalshi, arbitrage, exec_kalshi, exec_polymarket, live_strategy  # noqa: E402


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def _enrich_asks(live):
    """Add REAL book asks + sizes to the 15m legs so the shared gate (arb_gate)
    prices/sizes off the live order book, not last-trade. Mirrors the feed's
    enrichment (dashboard/refresh_live5m.py). Read-only; any failure degrades the
    affected side to (None, 0) -> the gate skips with 'no book'. WITHOUT this the
    live driver's gate would NEVER see asks and would skip every window."""
    p15 = live.get("poly_15m")
    if isinstance(p15, dict):
        for side, tok in (("up", p15.get("up_token")), ("down", p15.get("down_token"))):
            if tok:
                r = _safe(lambda tok=tok: polymarket.book_ask(tok))
                px, sz = r if isinstance(r, tuple) else (None, 0)
                p15[f"{side}_ask"], p15[f"{side}_ask_size"] = px, sz
    k15 = live.get("kalshi_15m")
    if isinstance(k15, dict) and k15.get("ticker"):
        tk = k15["ticker"]
        for side in ("up", "down"):
            kside = "yes" if side == "up" else "no"
            r = _safe(lambda kside=kside: kalshi.book_ask(tk, kside))
            px, sz = r if isinstance(r, tuple) else (None, 0)
            k15[f"{side}_ask"], k15[f"{side}_ask_size"] = px, sz


def snapshot():
    live = {"generated_at": datetime.now(timezone.utc).isoformat()}
    live["poly_15m"] = _safe(lambda: polymarket.updown_window_live("15m", 900))
    live["kalshi_15m"] = _safe(kalshi.updown_live)
    live["arb15m"] = _safe(lambda: arbitrage.cross_venue_15m(
        live["poly_15m"], live["kalshi_15m"])) or {}
    _enrich_asks(live)
    return live


def status():
    dry = exec_kalshi.dry_run()
    print(f"DRY_RUN          : {dry}  ({'SIMULATED — no real orders' if dry else 'LIVE — REAL MONEY'})")
    print(f"MAX_NOTIONAL     : ${live_strategy.MAX_NOTIONAL:.2f} / account / lock")
    print(f"MIN_SECS_LEFT    : {live_strategy.MIN_SECS_LEFT}s")
    print(f"edge filters     : net>={live_strategy.MIN_NET*100:.1f}c  gross<={live_strategy.MAX_GROSS*100:.0f}c")
    print(f"kill switch      : {'ON (no new orders)' if live_strategy.killed() else 'off'}")
    print(f"Kalshi balance   : ${_safe(exec_kalshi.balance)}")
    print(f"Polymarket bal   : ${_safe(exec_polymarket.balance)}")


def run(poll=3.0):
    dry = exec_kalshi.dry_run()
    print(f"[livearb] starting loop — DRY_RUN={dry}  poll={poll}s  "
          f"cap=${live_strategy.MAX_NOTIONAL}/acct.  Ctrl-C to stop.")
    if not dry:
        print("[livearb] *** LIVE MODE — REAL MONEY WILL BE PLACED ***")
    try:
        while True:
            live = snapshot()
            res = live_strategy.step(live)
            p15 = live.get("poly_15m") or {}
            stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"{stamp}  left={p15.get('seconds_left')}s  "
                  f"poly_up={p15.get('up_cost')}  "
                  f"kalshi_up={(live.get('kalshi_15m') or {}).get('up_cost')}  "
                  f"-> {res.get('status')}"
                  + (f" {res}" if res.get('status') in
                     ('locked', 'legged_unwound', 'no_fill') else ""))
            time.sleep(poll)
    except KeyboardInterrupt:
        print("\n[livearb] stopped.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "run":
        run(float(sys.argv[2]) if len(sys.argv) > 2 else 3.0)
    elif cmd == "stop":
        import os
        os.makedirs("journal", exist_ok=True)
        open(live_strategy.STOP_FLAG, "w").close()
        print(f"kill switch ON -> {live_strategy.STOP_FLAG}")
    elif cmd == "go":
        import os
        if os.path.exists(live_strategy.STOP_FLAG):
            os.remove(live_strategy.STOP_FLAG)
        print("kill switch off")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
