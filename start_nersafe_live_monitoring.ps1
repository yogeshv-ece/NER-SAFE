<#
=============================================================================
NER-SAFE: Live Operational Monitoring Launcher & Daemon Script
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Launches the local-first live multi-source landslide early warning
         runtime on Windows PowerShell.

Operational Principles:
1. Operates ONLY while this process is running.
   (The laptop does NOT pretend to monitor when powered off or asleep.)
2. Live Multi-Source Ingestion: Polls NASA GPM NRT (half-hourly), tracks
   SMAP contextual soil saturation, and ingests real ground sensor readings.
3. Decoupled Timestamps: Preserves authentic observation timestamps.
4. Mode Distinction: Live operational cards are strictly separated from
   deterministic DEMO / REPLAY scenarios.
=============================================================================
#>

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "               NER-SAFE — LIVE OPERATIONAL MONITORING SYSTEM                   " -ForegroundColor Cyan
Write-Host "        AI-Based Early Warning & Multi-Source Landslide Risk (SIH 26001)        " -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = "E:\landslide - Copy\landslide - Copy"
Set-Location $ProjectRoot
$env:NER_SAFE_ROOT = $ProjectRoot
$env:PORT = "8000"
$env:SUSCEPTIBILITY_MODEL = "xgboost"

# 1. Verify Python Environment
Write-Host "[1/5] Checking Python runtime..." -ForegroundColor Yellow
$PythonCmd = (Get-Command py -ErrorAction SilentlyContinue)
if (-not $PythonCmd) {
    $PythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
}
if (-not $PythonCmd) {
    Write-Host "ERROR: Python was not found in system PATH." -ForegroundColor Red
    exit 1
}
$PyVer = (& py -V 2>&1)
Write-Host "  -> Python active: $PyVer" -ForegroundColor Green

# 2. Verify NASA Earthdata Credentials (~/.netrc)
Write-Host "[2/5] Inspecting Earthdata authentication..." -ForegroundColor Yellow
$NetrcPath = Join-Path $HOME ".netrc"
if (Test-Path $NetrcPath) {
    $NetrcContent = Get-Content $NetrcPath -Raw
    if ($NetrcContent -match "urs.earthdata.nasa.gov") {
        Write-Host "  -> Active Earthdata Login credentials detected in ~/.netrc" -ForegroundColor Green
        Write-Host "     (NASA GPM IMERG NRT half-hourly HDF5 binary downloads enabled)" -ForegroundColor DarkGreen
    } else {
        Write-Host "  -> ~/.netrc found, but urs.earthdata.nasa.gov entry is missing." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  -> Notice: ~/.netrc not found. GPM queries will operate via open CMR metadata." -ForegroundColor DarkYellow
}

# 3. Initialize Database and Shared Schemas
Write-Host "[3/5] Initializing local-first database and SQLite provenance tables..." -ForegroundColor Yellow
& py -c "import database; database.init_db(); from live_assessment_service import live_assessment_service; print('  -> Database initialized cleanly.')"

# 4. Trigger Preflight Multi-Source Ingestion Check
Write-Host "[4/5] Executing initial multi-source observation preflight..." -ForegroundColor Yellow
& py -c "from live_assessment_service import live_assessment_service; asm=live_assessment_service.execute_live_assessment(); print('  -> Current Live Assessment ID:', asm.get('assessment_id')); print('  -> Status:', asm.get('assessment_status'))"

# 5. Launch Extended Live Server
Write-Host "[5/5] Launching NER-SAFE Extended Live Server on http://localhost:8000 ..." -ForegroundColor Yellow
Write-Host "  -> Dashboard URL:           http://localhost:8000/" -ForegroundColor Cyan
Write-Host "  -> Live Operational Status:  http://localhost:8000/api/monitoring/status" -ForegroundColor White
Write-Host "  -> Current Assessment:       http://localhost:8000/api/assessment/current" -ForegroundColor White
Write-Host "  -> Assessment History:       http://localhost:8000/api/assessment/history" -ForegroundColor White
Write-Host "  -> Sensors Health:           http://localhost:8000/api/monitoring/sources/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop live monitoring." -ForegroundColor Gray
Write-Host ""

Start-Process "http://localhost:8000/"
& py live_sensor_server_extension.py
