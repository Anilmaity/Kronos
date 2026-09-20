# Launcher for the XAUUSD dashboard.
# 1) Starts a background loop that refreshes data.json every 60s.
# 2) Runs the Electron app in the foreground.
# Stop with Ctrl+C / closing the window; the refresher job is cleaned up on exit.

$ErrorActionPreference = "Continue"
$dashboard = $PSScriptRoot
$root = Split-Path $dashboard -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
$refresher = Join-Path $dashboard "refresh_data.py"

if (-not (Test-Path $python)) {
    Write-Error "venv python not found at $python"
    exit 1
}

Write-Host "Starting data refresher loop (every 60s)..." -ForegroundColor Cyan
$job = Start-Job -ScriptBlock {
    param($python, $refresher, $root)
    while ($true) {
        Set-Location $root
        & $python $refresher
        Start-Sleep -Seconds 60
    }
} -ArgumentList $python, $refresher, $root

try {
    # Give the first refresh a head start so the app opens with fresh data.
    Start-Sleep -Seconds 3
    Write-Host "Launching Electron dashboard..." -ForegroundColor Cyan
    Set-Location $dashboard
    npm start
}
finally {
    Write-Host "Stopping data refresher..." -ForegroundColor Cyan
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
