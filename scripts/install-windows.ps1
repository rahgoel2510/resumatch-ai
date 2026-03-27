# ============================================================
# ResuMatch AI — Windows Background Service Installer
# Uses Windows Task Scheduler to run the RAG pipeline as a
# background task that starts on login and restarts on failure.
# ============================================================

$ErrorActionPreference = "Stop"

$TaskName = "ResuMatchAI"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectDir "backend"
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$MainScript = Join-Path $BackendDir "main.py"
$LogDir = Join-Path $BackendDir "logs"

Write-Host "🎯 ResuMatch AI — Windows Service Installer" -ForegroundColor Cyan
Write-Host "============================================="
Write-Host "Backend:  $BackendDir"
Write-Host "Python:   $VenvPython"
Write-Host ""

# Check venv exists
if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Virtual environment not found at $VenvPython" -ForegroundColor Red
    Write-Host "   Run: cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt"
    exit 1
}

# Create log directory
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the scheduled task
$Action = New-ScheduledTaskAction `
    -Execute $VenvPython `
    -Argument "main.py" `
    -WorkingDirectory $BackendDir

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "ResuMatch AI — Local RAG pipeline for resume analysis"

Write-Host ""
Write-Host "✅ Task '$TaskName' registered successfully" -ForegroundColor Green
Write-Host ""

# Start it now
Start-ScheduledTask -TaskName $TaskName
Write-Host "✅ Service started" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Yellow
Write-Host "   Status:   Get-ScheduledTask -TaskName $TaskName"
Write-Host "   Stop:     Stop-ScheduledTask -TaskName $TaskName"
Write-Host "   Start:    Start-ScheduledTask -TaskName $TaskName"
Write-Host "   Remove:   Unregister-ScheduledTask -TaskName $TaskName"
Write-Host "   Logs:     Get-Content $LogDir\resumatch.log -Tail 50"
Write-Host ""
Write-Host "The service will:" -ForegroundColor Cyan
Write-Host "  • Start automatically on login"
Write-Host "  • Restart up to 3 times on failure"
Write-Host "  • Auto re-index when you add/update resumes in resume_data/"
