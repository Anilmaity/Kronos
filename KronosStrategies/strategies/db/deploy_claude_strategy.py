"""
Deploy "Claude Strategy" into the live Kronos DB.

Design spec: docs/superpowers/specs/2026-10-06-claude-strategy-design.md (§3.1).

Inserts (idempotently, reusing deploy_manager's helpers):
  - apis_strategy  "Claude Strategy" (variation claude_strategy, XAU_USD)
  - apis_userstrategy on the Winprofx-Demo UserBroker (meta account 3eefc570…),
    deployed=True, is_active=False — the manager starts it once armed.
  - apis_managedstrategy slot=discretionary policy=always_on,
    arm_mode from MANAGER_ARM_MODE (default OFF; first rollout PAPER).

Trades are placed only by strategies/claude_trade.py, driven by the Claude
Code session on reaper. Nothing trades on --commit alone.

Usage (from strategies/, inside the box's strategies container):
  MANAGER_ARM_MODE=PAPER python -m db.deploy_claude_strategy           # dry run
  MANAGER_ARM_MODE=PAPER python -m db.deploy_claude_strategy --commit  # write
"""
from __future__ import annotations

import sys

from db.deploy_manager import _ensure_managed, _ensure_strategy, _ensure_user_strategy
from shared.models import CurrencyPair, Session, UserBroker

NAME = "Claude Strategy"
VARIATION = "claude_strategy"
SYMBOL = "XAU_USD"
META_ACCOUNT_PREFIX = "3eefc570"   # Winprofx-Demo (MT5 demo, $10k)


def main(commit: bool) -> int:
    sess = Session()
    try:
        cp = sess.query(CurrencyPair).filter_by(symbol=SYMBOL).first()
        if cp is None:
            print(f"FATAL: CurrencyPair {SYMBOL} not found")
            return 1
        ub = (sess.query(UserBroker)
              .filter(UserBroker.meta_account_id.like(f"{META_ACCOUNT_PREFIX}%"))
              .first())
        if ub is None:
            print(f"FATAL: no UserBroker with meta account {META_ACCOUNT_PREFIX}…")
            return 1
        print(f"UserBroker id={ub.id} meta={ub.meta_account_id[:8]}…")
        strat = _ensure_strategy(sess, cp, NAME, VARIATION,
                                 "Discretionary ICT/SMC by a Claude Code session on reaper; "
                                 "±$100/day, $25/trade, one open (claude_guard)")
        us = _ensure_user_strategy(sess, strat, ub)
        _ensure_managed(sess, us, "discretionary", "always_on", {}, live_eligible=True)
        if commit:
            sess.commit()
            print("COMMITTED.")
        else:
            sess.rollback()
            print("\nDRY-RUN (no writes). Re-run with --commit to persist.")
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main(commit="--commit" in sys.argv))
