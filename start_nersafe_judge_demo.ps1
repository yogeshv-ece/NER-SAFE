# ==============================================================================
# NER-SAFE: ONE-COMMAND JUDGE DEMONSTRATION DAY LAUNCHER
# Release Baseline: nersafe-judge-demo-baseline-1.0 (v1.0.0-judge-demo-freeze)
# ==============================================================================
param (
    [int]$Port = 8000,
    [switch]$SkipSmoke = $false
)

$ErrorActionPreference = "Stop"

# 1. Resolve Project Root Directory
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = "E:\landslide - Copy\landslide - Copy"
}
Set-Location -Path $ProjectRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "NER-SAFE: AI-BASED EARLY WARNING & LANDSLIDE RISK MONITORING IN NER" -ForegroundColor Cyan
Write-Host "JUDGE DEMONSTRATION DAY LAUNCHER (100% LOCAL-FIRST / ZERO CLOUD)" -ForegroundColor Cyan
Write-Host "Baseline: nersafe-judge-demo-baseline-1.0 | Status: FROZEN WITH WARNINGS" -ForegroundColor DarkCyan
Write-Host "Working Directory: $ProjectRoot" -ForegroundColor Gray
Write-Host "================================================================================" -ForegroundColor Cyan

# 2. Locate Python Executable
$PythonExe = ""
$CandidatePythons = @(
    "C:\Users\hp\AppData\Local\Python\bin\python.exe",
    "C:\Users\hp\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
)

foreach ($cand in $CandidatePythons) {
    if ($cand -and (Test-Path $cand)) {
        $PythonExe = $cand
        break
    }
}

if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PythonExe = $cmd.Source }
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Could not find a valid Python 3.10+ executable." -ForegroundColor Red
    Write-Host "Please ensure Python is installed and accessible." -ForegroundColor Yellow
    exit 1
}

Write-Host "[INIT 1/5] Using Python Interpreter: $PythonExe" -ForegroundColor Green

# 3. Verify Required Core Frozen Files
$RequiredFiles = @(
    "server.py",
    "e2e_demo_engine.py",
    "fusion_engine.py",
    "ner_safe_live_dashboard.html",
    "event_records.csv",
    "flow_paths.geojson",
    "runout_corridors.geojson",
    "exposure_intersections.geojson",
    "NER_SAFE_RELEASE_MANIFEST.json"
)

$MissingFiles = @()
foreach ($rf in $RequiredFiles) {
    $fullPath = Join-Path $ProjectRoot $rf
    if (-not (Test-Path $fullPath)) {
        $MissingFiles += $rf
    }
}

if ($MissingFiles.Count -gt 0) {
    Write-Host "[ERROR] Missing critical frozen files: $($MissingFiles -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[INIT 2/5] Verified presence of all core frozen baseline files." -ForegroundColor Green

# 4. Clean Up Stale Server Processes on Port $Port
Write-Host "[INIT 3/5] Checking for existing server process on port $Port..." -ForegroundColor Gray
try {
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $ownerPid = $conn.OwningProcess
            if ($ownerPid -gt 4) {
                Write-Host "  -> Terminating existing process on port $Port (PID: $ownerPid)..." -ForegroundColor Yellow
                Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 1
    }
} catch {
    # Non-fatal if Get-NetTCPConnection lacks elevation
}

# 5. Execute Preflight Smoke Test (Unless Skipped)
if (-not $SkipSmoke) {
    Write-Host "[INIT 4/5] Executing runtime preflight smoke test (test_judge_demo_smoke.py)..." -ForegroundColor Cyan
    & $PythonExe test_judge_demo_smoke.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Smoke preflight checks failed. Halting launch." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[INIT 4/5] Skipping smoke test (-SkipSmoke passed)." -ForegroundColor DarkGray
}

# 6. Start Authenticated REST Server
Write-Host "[INIT 5/5] Launching NER-SAFE live server on port $Port..." -ForegroundColor Green
$ServerUrl = "http://localhost:$Port"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "NER-SAFE SERVER READY FOR JUDGE DEMONSTRATION" -ForegroundColor Green
Write-Host "  Access URL: $ServerUrl" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "  Dashboard:  $ServerUrl/" -ForegroundColor White
Write-Host "  Mode:       100% LOCAL-FIRST STANDALONE" -ForegroundColor Cyan
Write-Host "  Safety:     ZERO CLOUD, ZERO EXTERNAL API FEES, ZERO CREDENTIAL EXPOSURE" -ForegroundColor Cyan
Write-Host "  UI Token:   Digital India UX4G 3.0 Standard | EXACTLY ZERO EMOJIS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "DEMO DAY SEQUENCE:" -ForegroundColor Yellow
Write-Host "  1. Open browser at $ServerUrl" -ForegroundColor Gray
Write-Host "  2. Show OPERATIONAL mode -> CURRENT RISK: NOT AVAILABLE (Freshness Rule)" -ForegroundColor Gray
Write-Host "  3. Click 'Switch to Demo / Replay' -> Select EVT-MEG-001 (Shella, Meghalaya)" -ForegroundColor Gray
Write-Host "  4. Execute Replay -> Observe deterministic fused risk score: 0.7055 (CRITICAL)" -ForegroundColor Gray
Write-Host "  5. Inspect D8 flow path (267.4m), runout corridor (29,264.6 m^2), 2 exposed roads" -ForegroundColor Gray
Write-Host "  6. Inspect CAP advisory (DEMO / LOCAL TEST) & citizen evidence moderation" -ForegroundColor Gray
Write-Host "  7. Return to Operational mode -> verify risk returns cleanly to NOT AVAILABLE" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C in this console to stop the server." -ForegroundColor DarkCyan
Write-Host "================================================================================" -ForegroundColor Gray

# Set environment port and start server
$env:PORT = "$Port"
& $PythonExe server.py
