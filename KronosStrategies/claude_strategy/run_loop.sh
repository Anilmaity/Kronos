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

while true; do
  now=$(date -u +%FT%TZ)
  dow=$(date -u +%u); hh=$(date -u +%H)
  log="logs/$(date -u +%F).log"
  if [ "$dow" -le 5 ] && [ "$hh" -ge 7 ] && [ "$hh" -lt 20 ]; then
    echo "=== $now cycle" | tee -a "$log"
    prompt=$(sed "s/{{NOW}}/$now/" cycle_prompt.md)
    # perl alarm = portable timeout (macOS has no coreutils timeout)
    if perl -e 'alarm shift; exec @ARGV' "$CYCLE_TIMEOUT" \
         claude -p "$prompt" \
           --allowedTools "Bash(ssh kronos-claude:*)" "Read" "Edit(journal.md)" \
                          "Write(journal.md)" "Write(journal_archive/**)" \
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
