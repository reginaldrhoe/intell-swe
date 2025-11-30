#!/usr/bin/env pwsh
# Persistent Vite dev server with auto-restart
# Usage: .\scripts\start_vite_persistent.ps1 [-ApiBase "http://localhost:8001"] [-MaxRestarts 10]

param(
    [string]$ApiBase = "http://localhost:8001",
    [int]$MaxRestarts = -1,  # -1 = unlimited
    [switch]$NoAutoRestart
)

$ErrorActionPreference = "Continue"
$webDir = Join-Path $PSScriptRoot "..\web"

if (-not (Test-Path $webDir)) {
    Write-Error "Web directory not found: $webDir"
    exit 1
}

$restartCount = 0
$env:VITE_API_URL = $ApiBase

Push-Location $webDir
try {
    Write-Host "🔄 Persistent Vite Server Manager" -ForegroundColor Cyan
    Write-Host "   API Base: $ApiBase" -ForegroundColor Gray
    Write-Host "   Max Restarts: $(if ($MaxRestarts -eq -1) { 'Unlimited' } else { $MaxRestarts })" -ForegroundColor Gray
    Write-Host "   Auto-Restart: $(if ($NoAutoRestart) { 'Disabled' } else { 'Enabled' })" -ForegroundColor Gray
    Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host ""
    
    # Check dependencies once
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install failed - cannot continue"
            exit 1
        }
        Write-Host ""
    }
    
    while ($true) {
        $restartCount++
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        if ($MaxRestarts -ne -1 -and $restartCount -gt $MaxRestarts) {
            Write-Host "⛔ Max restart limit reached ($MaxRestarts). Exiting." -ForegroundColor Red
            break
        }
        
        Write-Host "[$timestamp] 🚀 Starting Vite (attempt $restartCount)..." -ForegroundColor Green
        
        # Start Vite and capture exit code
        npm run dev
        $exitCode = $LASTEXITCODE
        
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "[$timestamp] ⚠️  Vite exited with code: $exitCode" -ForegroundColor Yellow
        
        if ($NoAutoRestart) {
            Write-Host "Auto-restart disabled. Exiting." -ForegroundColor Gray
            break
        }
        
        # Check if exit was clean (Ctrl+C = exit code 0 or 1)
        if ($exitCode -eq 0 -or $exitCode -eq 1) {
            Write-Host "Clean exit detected. Not restarting." -ForegroundColor Gray
            break
        }
        
        Write-Host "🔄 Restarting in 3 seconds... (Ctrl+C to cancel)" -ForegroundColor Cyan
        Start-Sleep -Seconds 3
        Write-Host ""
    }
}
catch {
    Write-Host "❌ Fatal error: $_" -ForegroundColor Red
    Write-Host "Exception: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Pop-Location
    Write-Host ""
    Write-Host "Vite server manager stopped." -ForegroundColor Gray
}
