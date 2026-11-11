"""
Deploy "S101 Asia Range Fade" into the live Kronos DB (Winprofx-Demo).

Inserts idempotently, reusing deploy_manager's helpers:
  - apis_strategy "S101 Asia Range Fade" (variation KRONOS_S101_ASIA_RANGE, XAU_USD)
  - apis_userstrategy on the Winprofx-Demo UserBroker (meta account 3eefc570...)
  - apis_managedstrategy slot=scalping policy=always_on, arm_mode from MANAGER_ARM_MODE
    (default OFF).

Usage (from strategies/, inside a strategies container on the box):
  MANAGER_ARM_MODE=LIVE python -m db.deploy_s101_asia_range            # dry run
  MANAGER_ARM_MODE=LIVE python -m db.deploy_s101_asia_range --commit   # write
"""
from __future__ import annotations

import sys

from db.deploy_manager import _ensure_managed, _ensure_strategy, _ensure_user_strategy
from shared.models import CurrencyPair, Session, UserBroker

NAME = "S101 Asia Range Fade"
VARIATION = "KRONOS_S101_ASIA_RANGE"
SYMBOL = "XAU_USD"
META_ACCOUNT_PREFIX = "3eefc570"   # Winprofx-Demo (MT5 demo, $10k)


def main(commit: bool) -> int:
    sess = Session()
    try:
        cp = sess.query(CurrencyPair).filter_by(symbol=SYMBOL).first()
        if cp is None:
            print(f"FATAL: CurrencyPair {SYMBOL} not found"); return 1
        ub = sess.query(UserBroker).filter(UserBroker.meta_account_id.like(f"{META_ACCOUNT_PREFIX}%")).first()
        if ub is None:
            print(f"FATAL: no UserBroker with meta account {META_ACCOUNT_PREFIX}..."); return 1
        print(f"UserBroker id={ub.id} meta={ub.meta_account_id[:8]}...")
        strat = _ensure_strategy(sess, cp, NAME, VARIATION,
                                 "Asia-session range fade (M1, 00-08 UTC): fade a 5-min push at the edge of the 2-hour "
                                 "range while gold oscillates; TP 8 / SL 24, one position per signal. Demo by operator "
                                 "decision 2026-11-12; lab PF 0.92-0.94 (backtest_strategies/s101_asia_range.py).")
        us = _ensure_user_strategy(sess, strat, ub)
        _ensure_managed(sess, us, "scalping", "always_on", {}, live_eligible=True)
        if commit:
            sess.commit(); print("COMMITTED.")
        else:
            sess.rollback(); print("\nDRY-RUN (no writes). Re-run with --commit to persist.")
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    sys.exit(main("--commit" in sys.argv))
