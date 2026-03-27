# ResuMatch AI — Windows Service Uninstaller

$TaskName = "ResuMatchAI"

Write-Host "🎯 ResuMatch AI — Uninstalling Windows service..."

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ Service removed." -ForegroundColor Green
} else {
    Write-Host "ℹ️  Service not installed." -ForegroundColor Yellow
}
