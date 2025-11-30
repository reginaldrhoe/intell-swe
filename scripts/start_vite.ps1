#!/usr/bin/env pwsh
# Simple Vite dev server starter
# Usage: .\scripts\start_vite.ps1 [-ApiBase "http://localhost:8001"]

param(
    [string]$ApiBase = "http://localhost:8001"
)

$ErrorActionPreference = "Stop"
$webDir = Join-Path $PSScriptRoot "..\web"

if (-not (Test-Path $webDir)) {
    Write-Error "Web directory not found: $webDir"
    exit 1
}

Push-Location $webDir
try {
    # Set API base URL
    $env:VITE_API_URL = $ApiBase
    Write-Host "Starting Vite dev server..." -ForegroundColor Cyan
    Write-Host "   API Base: $ApiBase" -ForegroundColor Gray
    Write-Host "   Dev URL: http://localhost:5173" -ForegroundColor Gray
    Write-Host ""
    
    # Check dependencies
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install failed"
            exit 1
        }
    }
    
    # Start Vite
    npm run dev
}
finally {
    Pop-Location
}
