@echo off
REM Auto-open an INTERACTIVE Claude Code session in this project at login.
REM Interactive = you stay in the loop and approve sensitive actions, so there is
REM NO --dangerously-skip-permissions here (don't add it for an unattended boot).
REM
REM --append-system-prompt-file keeps Claude Code's default behavior and ADDS your
REM custom prompt. Use --system-prompt-file instead to REPLACE the default entirely
REM (strips the built-in operating/safety scaffolding -- not recommended).

cd /d "C:\Projects\ClaudeProjects\ClaudeTradingBot"
claude --append-system-prompt-file "CLAUDE-FABLE-5.md"

REM If you prefer a nicer Windows Terminal tab, comment the line above and use:
REM wt -d "C:\Projects\ClaudeProjects\ClaudeTradingBot" cmd /k claude --append-system-prompt-file "CLAUDE-FABLE-5.md"
