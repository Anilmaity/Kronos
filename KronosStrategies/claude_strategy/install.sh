#!/bin/bash
# Idempotent installer, run ON reaper from a copy of this folder.
# Copies the session to ~/claude-strategy, seeds the journal, adds the
# kronos-claude ssh host, and (re)loads the LaunchAgent.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/claude-strategy"
mkdir -p "$DST/logs" "$DST/journal_archive"
cp "$SRC/CLAUDE.md" "$SRC/cycle_prompt.md" "$SRC/run_loop.sh" "$SRC/start.sh" "$DST/"
chmod +x "$DST/run_loop.sh" "$DST/start.sh"
[ -f "$DST/lessons.md" ] || cp "$SRC/lessons.seed.md" "$DST/lessons.md"
[ -f "$DST/journal.md" ] || printf '# Claude Strategy journal\n\n## State\n- (first cycle: build the HTF bias)\n\n## Log\n' > "$DST/journal.md"

grep -q '^Host kronos-claude$' ~/.ssh/config 2>/dev/null || cat >> ~/.ssh/config <<'SSH'

# Claude Strategy gateway: this key can only run claude-gw on the box.
Host kronos-claude
  HostName 15.252.166.251
  User ubuntu
  IdentityFile ~/.ssh/kronos-claude
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
  ConnectTimeout 15
SSH

PLIST="$HOME/Library/LaunchAgents/com.kronos.claude-strategy.plist"
cp "$SRC/com.kronos.claude-strategy.plist" "$PLIST"
launchctl bootout "gui/$(id -u)/com.kronos.claude-strategy" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed: tmux attach -t claude-strategy"
