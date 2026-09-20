@echo off
REM TREND-ALIGNED live scalper on the FundingPips demo (account 6c7ce166).
REM Trades WITH the trend (momentum breakout + pyramid winners), risk-capped:
REM 0.01 lot/leg ($5 SL ~0.1%%), max 3 legs, 3%% daily kill switch.
REM Replaces the mean-reversion dip-buyer (run_scalp_live.py) which fought the trend.
REM Runs in repeating sessions so it stays live; Ctrl+C to stop.
cd /d C:\Projects\ClaudeProjects\ClaudeTradingBot
:loop
.venv\Scripts\python.exe run_trend_scalp_live.py --max-ticks 80 --interval 60
echo [scalp_runner] session ended, restarting in 5s... (Ctrl+C to stop)
timeout /t 5 >nul
goto loop
