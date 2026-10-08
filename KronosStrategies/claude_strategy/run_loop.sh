#!/bin/bash
# Claude Strategy loop (runs inside tmux session "claude-strategy" on reaper).
# In trading hours (Mon-Fri 07:00-20:00 UTC) one `claude -p` cycle every 5 min;
# outside them only `status`, so a day lock still closes an open trade.
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
  export CLAUDE_CODE_OAUTH_TOKEN
}

while true; do
  now=$(date -u +%FT%TZ)
  dow=$(date -u +%u); hh=$(date -u +%H)
  log="logs/$(date -u +%F).log"
  if [ "$dow" -le 5 ] && [ "$hh" -ge 7 ] && [ "$hh" -lt 20 ]; then
    echo "=== $now cycle" | tee -a "$log"
    prompt=$(sed "s/{{NOW}}/$now/" cycle_prompt.md)
    auth_env
    # perl alarm = portable timeout (macOS has no coreutils timeout)
    if perl -e 'alarm shift; exec @ARGV' "$CYCLE_TIMEOUT" \
         claude -p "$prompt" \
           --allowedTools "Bash(ssh kronos-claude:*)" "Read" "Edit(journal.md)" \
                          "Write(journal.md)" "Write(journal_archive/**)" \
                          "Edit(lessons.md)" "Write(lessons.md)" \
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
