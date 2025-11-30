param(
    [string]$ApiBase = "http://localhost:8001",
    [switch]$ExposeHost
)

# Auto-restart Vite dev server on exit/crash, set API base env
$env:VITE_API_URL = $ApiBase
Write-Host "Starting Vite dev server with VITE_API_URL=$ApiBase"

$cmd = "npm run dev"
if ($ExposeHost) { $env:VITE_DEV_HOST = "1" }

# Change to web folder
Push-Location "$PSScriptRoot\..\web"
try {
    if (-not (Test-Path node_modules)) {
        Write-Host "Installing dependencies..."
        npm install
    }

    while ($true) {
        try {
            Write-Host "Launching: $cmd"
            & cmd /c $cmd
            Write-Host "Vite dev server exited. Restarting in 2s..."
            Start-Sleep -Seconds 2
        } catch {
            Write-Host "Dev server error: $_. Exception: $($_.Exception.Message)"
            Write-Host "Restarting in 5s..."
            Start-Sleep -Seconds 5
        }
    }
}
finally {
    Pop-Location
}
