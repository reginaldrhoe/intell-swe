#!/usr/bin/env pwsh
# Check status of all development services
# Usage: .\scripts\check_services.ps1

$services = @(
    @{ Name = "Vite Dev UI";  Port = 5173; Url = "http://localhost:5173"; Color = "Cyan" }
    @{ Name = "API (MCP)";    Port = 8001; Url = "http://localhost:8001/health"; Color = "Green" }
    @{ Name = "Frontend";     Port = 3000; Url = "http://localhost:3000"; Color = "Blue" }
    @{ Name = "MySQL";        Port = 3306; Url = $null; Color = "Yellow" }
    @{ Name = "Redis";        Port = 6379; Url = $null; Color = "Red" }
    @{ Name = "Qdrant";       Port = 6333; Url = "http://localhost:6333"; Color = "Magenta" }
)

Write-Host ""
Write-Host "Service Status Check" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host ""

foreach ($svc in $services) {
    $listening = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | 
                 Where-Object { $_.LocalPort -eq $svc.Port }
    
    $status = if ($listening) { "✅ RUNNING" } else { "❌ STOPPED" }
    $statusColor = if ($listening) { "Green" } else { "Red" }
    
    Write-Host ("{0,-18}" -f $svc.Name) -NoNewline
    Write-Host (" Port {0,-6}" -f $svc.Port) -NoNewline -ForegroundColor Gray
    Write-Host $status -ForegroundColor $statusColor
    
    if ($listening -and $svc.Url) {
        Write-Host ("  → {0}" -f $svc.Url) -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=" * 70

# Docker status
Write-Host ""
Write-Host "Docker Containers" -ForegroundColor Cyan
try {
    $running = (docker ps -q 2>$null | Measure-Object).Count
    $total = (docker ps -aq 2>$null | Measure-Object).Count
    
    if ($total -gt 0) {
        Write-Host "   Running: $running / $total" -ForegroundColor $(if ($running -eq $total) { "Green" } else { "Yellow" })
        
        if ($running -lt $total) {
            Write-Host "   💡 Tip: Run 'docker compose up -d' to start all services" -ForegroundColor Gray
        }
    } else {
        Write-Host "   No containers found" -ForegroundColor Gray
    }
} catch {
    Write-Host "   Docker not running or not installed" -ForegroundColor Red
}

Write-Host ""

# Quick actions
Write-Host "Quick Actions" -ForegroundColor Cyan
Write-Host "   Start Vite:    .\scripts\start_vite.ps1" -ForegroundColor Gray
Write-Host "   Start All:     docker compose up -d" -ForegroundColor Gray
Write-Host "   View Logs:     docker compose logs -f mcp" -ForegroundColor Gray
Write-Host ""
