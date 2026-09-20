"""ONE-SHOT DRY_RUN test of the live cross-venue arbitrage order path.

Runs live_strategy.step() once against a real market snapshot. Because DRY_RUN
is true, BOTH legs are simulated (no real orders, no money moves) but the full
execution pipeline (place_ioc + place_fok + lock recording) is exercised and the
resulting lock is written to journal/live_account.json so it shows up in the
Electron Live Account tab.

If the real live window's gross edge is out of the [0.3c, 6c] band (so step()
skips it as basis risk), we then run a FORCED in-band synthetic snapshot — still
DRY_RUN — purely to prove the order-placement path accepts and records a lock.
"""
import os

# Belt-and-suspenders: this script is a SIMULATED test only.
os.environ["DRY_RUN"] = "true"

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
load_dotenv(".env.bets")
os.environ["DRY_RUN"] = "true"  # re-assert in case .env set it

from bot import exec_kalshi, live_strategy  # noqa: E402
from livearb import snapshot  # noqa: E402

assert exec_kalshi.dry_run() is True, "REFUSING: DRY_RUN is not true"

print("=" * 60)
print(f"DRY_RUN = {exec_kalshi.dry_run()}  (simulated — no real orders)")
print("=" * 60)

print("\n[1] Real live snapshot -> live_strategy.step():")
live = snapshot()
p15 = live.get("poly_15m") or {}
k15 = live.get("kalshi_15m") or {}
print(f"    poly  up={p15.get('up_cost')} down={p15.get('down_cost')} "
      f"secs_left={p15.get('seconds_left')}")
print(f"    kalshi up={k15.get('up_cost')} down={k15.get('down_cost')} "
      f"ticker={k15.get('ticker')}")
res = live_strategy.step(live)
print(f"    RESULT: {res}")

if res.get("status") != "locked":
    print("\n[2] Real window not lockable (above). Forcing an IN-BAND synthetic")
    print("    snapshot to exercise the simulated order path (still DRY_RUN):")
    # 95c lock -> 5c gross, inside [0.3c, 6c]. Reuse the live tokens/ticker so
    # the simulated legs carry realistic identifiers.
    forced = dict(live)
    fp = dict(p15)
    fk = dict(k15)
    fp["up_cost"], fp["down_cost"] = 0.46, 0.54
    fk["up_cost"], fk["down_cost"] = 0.49, 0.51
    # ensure enough time left and a window not already done
    fp["seconds_left"] = max(p15.get("seconds_left") or 600, 600)
    forced["poly_15m"] = fp
    forced["kalshi_15m"] = fk
    forced["arb15m"] = {"status": "evaluated"}
    res2 = live_strategy.step(forced)
    print(f"    RESULT: {res2}")

print("\n[3] Recorded live-account snapshot (what the dashboard tab reads):")
snap = live_strategy.account_snapshot(max_age=0.0)
print(f"    dry_run     : {snap['dry_run']}")
print(f"    n_locks     : {snap['n_locks']}  pairs_total: {snap['pairs_total']}")
for lk in snap["locks"][:3]:
    print(f"    LOCK window={lk.get('window')} pairs={lk.get('pairs')} "
          f"lock_cost={lk.get('lock_cost')} dry={lk.get('dry')}")
    print(f"         kalshi={lk.get('kalshi')}")
    print(f"         poly  ={lk.get('poly')}")
