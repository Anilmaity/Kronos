# Observational LIVE run of the cross-venue arb driver.
# Arms (removes journal\STOP), runs livearb_once.py for N minutes with the small
# cap + breakers, then ALWAYS restores the kill switch (even on Ctrl-C) via finally.
#
# Usage:   .\live_obs.ps1            # 3-minute observation (default)
#          .\live_obs.ps1 -Minutes 20
#
# REAL MONEY: DRY_RUN=false. Expect a stream of "skip ... not arb at real asks" /
# "no book" -- the gate refusing zero/negative-edge locks. It only places if a real
# positive-after-fees edge appears (research says: rare-to-never). Cap $3/account.
param([int]$Minutes = 3)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Remove-Item journal\STOP -ErrorAction SilentlyContinue
$env:DRY_RUN = 'false'
$env:LIVE_MAX_NOTIONAL = '3'
$env:LIVE_MAX_UNWINDS = '10'

Write-Host "*** LIVE (real money) -- cap `$3/acct, 10-unwind breaker, $Minutes-min timeout ***" -ForegroundColor Yellow
try {
    & .venv\Scripts\python.exe livearb_once.py $Minutes
    Write-Host "livearb_once exit code: $LASTEXITCODE  (0=lock placed, 1=timeout/no lock, 2=kill switch, 3=unwind breaker, 4=naked alert)"
}
finally {
    New-Item journal\STOP -ItemType File -Force | Out-Null
    Write-Host "kill switch RESTORED (journal\STOP present) -- safe state" -ForegroundColor Green
}
