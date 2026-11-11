#!/bin/sh
# Rebuild everything in this folder from the read-only inputs in ../../
set -e
cd "$(dirname "$0")"
PY=/Users/anil/Projects/Kronos/ClaudeTradingRD/.venv/bin/python
for s in 01_basis 02_reconstruct 03_positions 04_tables 05_edge 06_extra 07_charts 08_report; do
  echo "== $s"; $PY $s.py > /dev/null
done
echo done
