"""Place EXACTLY ONE real cross-venue arbitrage lock, then stop.

Supervised, bounded mirror of `livearb.py run` for a single trade:
  * LIVE (DRY_RUN=false) — places real Kalshi IOC + Polymarket FOK legs.
  * Waits for a genuine in-band edge (MIN_NET <= gross <= MAX_GROSS) with
    enough time left — the SAME filter the paper bot uses. Out-of-band windows
    (e.g. 9c "locks" = basis risk) are skipped.
  * Exits the instant one lock is placed (status 'locked'), or after MAX_MINUTES,
    or if the kill switch (journal/STOP) appears. One lock, ever.

Run:  DRY_RUN=false  .venv/Scripts/python.exe livearb_once.py [max_minutes]
"""
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.bets")

from bot import exec_kalshi, exec_polymarket, live_strategy  # noqa: E402
from livearb import snapshot  # noqa: E402

MAX_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
POLL = 4.0


def main():
    dry = exec_kalshi.dry_run()
    mode = "DRY-RUN (simulated)" if dry else "*** LIVE — REAL MONEY ***"
    print(f"[livearb_once] {mode}  cap=${live_strategy.MAX_NOTIONAL}/acct  "
          f"band {live_strategy.MIN_NET*100:.1f}-{live_strategy.MAX_GROSS*100:.0f}c  "
          f"timeout={MAX_MINUTES:.0f}m")
    print(f"[livearb_once] poly=${exec_polymarket.balance():.2f}  "
          f"kalshi=${exec_kalshi.balance():.2f}")
    # KEEP TRYING across windows until a real LOCK lands. Circuit breakers bound
    # the bleed: stop after MAX_UNWINDS clean flattens (~$0.12 each) or MAX_MINUTES.
    max_unwinds = int(os.getenv("LIVE_MAX_UNWINDS", "10"))
    deadline = MAX_MINUTES * 60.0
    t0 = time.time()
    n = unwinds = 0
    print(f"[livearb_once] KEEP-TRYING until a lock — breakers: "
          f"{max_unwinds} unwinds or {MAX_MINUTES:.0f}m.")
    while time.time() - t0 < deadline:
        if live_strategy.killed():
            print(f"[livearb_once] kill switch ON — stopping. unwinds={unwinds}")
            return 2
        live = snapshot()
        p15 = live.get("poly_15m") or {}
        res = live_strategy.step(live)
        n += 1
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        st = res.get("status")
        # Show the REAL-ASK gross (what the gate actually trades on), not the
        # last-trade gross — the latter looks huge but is illusory (you can't fill
        # at last trade). Uses the enriched *_ask fields the snapshot now carries.
        gross = None
        k15 = live.get("kalshi_15m") or {}
        pu, pd = p15.get("up_ask"), p15.get("down_ask")
        ku, kd = k15.get("up_ask"), k15.get("down_ask")
        if None not in (pu, pd, ku, kd):
            lc = min(pu + kd, ku + pd)
            gross = (1 - lc) * 100
        gstr = f"{gross:.1f}c" if gross is not None else "no-book"
        print(f"{stamp}  left={p15.get('seconds_left')}s  "
              f"gross={gstr}  -> {st}"
              + (f"  {res.get('reason','')}" if st in ("skip", "idle") else ""))
        # A naked_alert means a flatten could not fully fill -> real exposure.
        # Stop immediately so a human can act; do NOT keep trading.
        if res.get("naked_alert"):
            print("\n!!! NAKED ALERT — could not fully flatten. STOPPING.", res)
            return 4
        if st == "locked":
            print("\n>>> LOCK PLACED (REAL):", res)
            return 0
        if st == "legged_unwound":
            unwinds += 1
            print(f"    (legged_unwound #{unwinds} — flattened clean, continuing)")
            if unwinds >= max_unwinds:
                print(f"\n[livearb_once] breaker: {unwinds} unwinds reached. Stopping.")
                return 3
        time.sleep(POLL)
    print(f"[livearb_once] timeout {MAX_MINUTES:.0f}m — no lock. unwinds={unwinds}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
