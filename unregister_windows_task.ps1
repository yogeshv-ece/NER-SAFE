# =============================================================================
# NER-SAFE: Windows Task Scheduler Unregistration Script
# =============================================================================
# Purpose: Safely deletes the NER-SAFE Autonomous Monitoring Scheduled Task.
# =============================================================================

[CmdletBinding()]
param(
    [string]$TaskName = "NERSAFE_Autonomous_Scheduler"
)

Write-Host "============================================================"
Write-Host "NER-SAFE AUTONOMOUS SCHEDULER TASK REMOVAL"
Write-Host "============================================================"
Write-Host "Unregistering Windows task: $TaskName"

& schtasks.exe /Delete /TN $TaskName /F

if ($LASTEXITCODE -eq 0) {
    Write-Host "Task '$TaskName' removed successfully."
} else {
    Write-Host "Task '$TaskName' was not found or already deleted."
}
Write-Host "============================================================"
