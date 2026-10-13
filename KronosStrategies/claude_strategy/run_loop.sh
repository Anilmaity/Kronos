#!/bin/bash
# Claude Strategy loop (runs inside tmux session "claude-strategy" on reaper, or on the
# operator's Mac since 2026-10-13 while reaper is offline -- never on both at once).
# User settings and MCP servers are not loaded: the cycle sees only this folder's CLAUDE.md.
# 24/5 while the market is open (one `claude -p` cycle every 5 min); while it is closed
# only `status`, so a day lock still closes an open trade.
# Exits after 5 failed cycles in a row so launchd (via start.sh) restarts it.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p logs journal_archive
CYCLE_TIMEOUT=240
fails=0

# Auth. The launchd/tmux (GUI) context reads Claude's keychain credentials, whose rotating
# refresh token is invalidated whenever an SSH session refreshes the file copy — then every
# cycle 401s (2026-10-08). So pass a token explicitly: a long-lived one from
# `claude setup-token` saved in .oauth_token (preferred), else the access token that SSH
# sessions keep fresh in ~/.claude/.credentials.json (bridge: valid ~8h after a refresh).
auth_env() {
  if [ -s "$HOME/claude-strategy/.oauth_token" ]; then
    CLAUDE_CODE_OAUTH_TOKEN="$(tr -d '[:space:]' < "$HOME/claude-strategy/.oauth_token")"
  else
    CLAUDE_CODE_OAUTH_TOKEN="$(python3 -c 'import json,os; print(json.load(open(os.path.expanduser("~/.claude/.credentials.json")))["claudeAiOauth"]["accessToken"])' 2>/dev/null)"
  fi
  # Neither file (a Mac whose only login is the keychain): use claude's own login.
  if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then export CLAUDE_CODE_OAUTH_TOKEN; else unset CLAUDE_CODE_OAUTH_TOKEN; fi
}

# The box's market hours (shared/market_timing.py): Sun 22:00 - Fri 21:00 UTC, minus the
# daily 21:00-22:00 maintenance. Args (for testing): ISO weekday 1-7, UTC hour.
market_open() {
  local dow=${1:-$(date -u +%u)} hh=${2:-$(date -u +%H)}
  [ "$hh" -eq 21 ] && return 1
  case $dow in
    6) return 1 ;;
    5) [ "$hh" -lt 21 ] ;;
    7) [ "$hh" -ge 22 ] ;;
    *) return 0 ;;
  esac
}
[ "${1:-}" = "--market-open" ] && { market_open "$2" "$3"; exit; }

while true; do
  now=$(date -u +%FT%TZ)
  log="logs/$(date -u +%F).log"
  if market_open; then
    echo "=== $now cycle" | tee -a "$log"
    prompt=$(sed "s/{{NOW}}/$now/" cycle_prompt.md)
    auth_env
    # perl alarm = portable timeout (macOS has no coreutils timeout)
    if perl -e 'alarm shift; exec @ARGV' "$CYCLE_TIMEOUT" \
         claude -p "$prompt" \
           --setting-sources project,local --strict-mcp-config \
           --allowedTools "Bash(ssh kronos-claude:*)" "Read" "Edit(journal.md)" \
                          "Edit(journal_archive/**)" "Edit(lessons.md)" \
         2>&1 | tee -a "$log"; [ "${PIPESTATUS[0]}" -eq 0 ]; then
      fails=0
    else
      fails=$((fails + 1))
      echo "!!! cycle failed ($fails in a row)" | tee -a "$log"
      [ "$fails" -ge 5 ] && { echo "5 failed cycles - exiting for restart" | tee -a "$log"; exit 1; }
    fi
  else
    echo "$now $(ssh kronos-claude status 2>&1 | cut -c1-300)" >> logs/offhours.log
  fi
  sleep $((300 - $(date +%s) % 300))
done
