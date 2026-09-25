# =============================================================================
# NER-SAFE: Windows Task Scheduler Registration Script
# =============================================================================
# Purpose: Registers the NER-SAFE Autonomous Monitoring Daemon as an unattended
#          Windows Scheduled Task on the local host machine.
# =============================================================================

[CmdletBinding()]
param(
    [string]$TaskName = "NERSAFE_Autonomous_Scheduler",
    [int]$IntervalMinutes = 15,
    [string]$PythonExe = "C:\Users\hp\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    [string]$WorkingDir = "E:\landslide - Copy\landslide - Copy"
)

$ScriptPath = Join-Path $WorkingDir "nersafe_autonomous_scheduler.py"

Write-Host "============================================================"
Write-Host "NER-SAFE AUTONOMOUS SCHEDULER TASK REGISTRATION"
Write-Host "============================================================"
Write-Host "Task Name:        $TaskName"
Write-Host "Python Executable:$PythonExe"
Write-Host "Working Directory:$WorkingDir"
Write-Host "Script:           $ScriptPath"
Write-Host "Polling Cadence:  Every $IntervalMinutes minutes"
Write-Host "------------------------------------------------------------"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python executable not found at: $PythonExe"
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Target script not found at: $ScriptPath"
    exit 1
}

$ActionCommand = "`"$PythonExe`""
$ActionArgs = "`"$ScriptPath`" --mode RUN_ONCE --enforce-master-control"

Write-Host "Registering task via schtasks.exe..."
& schtasks.exe /Create /TN $TaskName /TR "$ActionCommand $ActionArgs" /SC MINUTE /MO $IntervalMinutes /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "Windows Scheduled Task '$TaskName' successfully registered!"
    Write-Host "To query task status:   schtasks.exe /Query /TN `"$TaskName`""
    Write-Host "To execute immediately: schtasks.exe /Run /TN `"$TaskName`""
    Write-Host "To unregister task:     .\unregister_windows_task.ps1"
} else {
    Write-Warning "Registration returned exit code $LASTEXITCODE. Check local Windows permissions."
}
Write-Host "============================================================"
