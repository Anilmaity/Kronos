#!/usr/bin/env bash
# Observational LIVE run of the cross-venue arb driver (bash version, for the
# in-session `!` prefix which runs bash). Arms (removes journal/STOP), runs
# livearb_once.py for N minutes with the small cap + breakers, then ALWAYS
# restores the kill switch -- even on Ctrl-C -- via an EXIT trap.
#
# Usage:  ! bash live_obs.sh        # 3-minute observation (default)
#         ! bash live_obs.sh 10     # 10 minutes
#
# REAL MONEY (DRY_RUN=false). Expect a stream of "skip ... not arb at real asks" /
# "no book" -- the gate refusing zero/negative-edge locks. Cap $3/account.
set -u
cd "$(dirname "$0")"

restore() { touch journal/STOP; echo "kill switch RESTORED (journal/STOP present) -- safe state"; }
trap restore EXIT

MIN="${1:-3}"
echo "*** LIVE (real money) -- cap \$3/acct, 10-unwind breaker, ${MIN}-min timeout ***"
rm -f journal/STOP
DRY_RUN=false LIVE_MAX_NOTIONAL=3 LIVE_MAX_UNWINDS=10 .venv/Scripts/python.exe livearb_once.py "$MIN"
echo "livearb_once exit: $?  (0=lock placed, 1=timeout/no lock, 2=kill switch, 3=unwind breaker, 4=naked alert)"
