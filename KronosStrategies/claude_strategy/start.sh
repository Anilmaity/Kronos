#!/bin/bash
# launchd entry point: keep exactly one tmux session "claude-strategy" running
# run_loop.sh, and stay alive while it lives so KeepAlive restarts it if it dies.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
DIR="$HOME/claude-strategy"
tmux has-session -t claude-strategy 2>/dev/null ||
  tmux new-session -d -s claude-strategy "$DIR/run_loop.sh"
# A sleeping Mac runs no cycles (the operator's laptop idles to sleep in 1 min on battery).
caffeinate -i -w $$ &
while tmux has-session -t claude-strategy 2>/dev/null; do sleep 30; done
