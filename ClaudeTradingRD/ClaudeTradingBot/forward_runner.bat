@echo off
REM Durable runner for the forward edge-test collector. Read-only (no orders).
REM Loops forever, auto-restarting research_forward_edge.py if it ever exits/crashes.
REM The collector resumes from journal/forward_edge_log.csv, so restarts lose nothing.
title Forward edge-test collector
cd /d "C:\Projects\ClaudeProjects\ClaudeTradingBot"
set DRY_RUN=true
:loop
.venv\Scripts\python.exe research_forward_edge.py
echo [forward_runner] collector exited; restarting in 15s...
timeout /t 15 /nobreak >nul
goto loop
