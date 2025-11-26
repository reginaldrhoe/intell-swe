<#
Run a sentinel-based lock smoke test against the local `mcp` service.

This script:
- Sends two near-concurrent POST /run-agents requests for the same task id.
- Reads sentinel files from the `mcp` container to determine which request acquired the lock
  and which one observed a conflict.

Usage:
  .\scripts\run_lock_smoke.ps1 -TaskId 11

Requirements:
- `docker` / `docker compose` must be available in PATH and compose services running.
- Run from the repo root so `docker compose exec mcp` targets the correct service.
#>

param(
    [int]$TaskId = 11,
    [string]$McpUrl = 'http://localhost:8001',
    [int]$SleepMs = 50,
    [int]$WaitForBgSeconds = 60
)

Write-Host "Running lock smoke test for task id=$TaskId against $McpUrl"

$payload = @{ id = $TaskId } | ConvertTo-Json

# Start background POST
$bg = Start-Job -ScriptBlock {
    param($payload, $url)
    try {
        $r = Invoke-RestMethod -Method Post -Uri $url -Body $payload -ContentType 'application/json' -Headers @{ Authorization = 'Bearer demo' }
        return @{ ok = $true; body = $r }
    } catch {
        return @{ ok = $false; err = $_.Exception.Message }
    }
} -ArgumentList $payload, "$McpUrl/run-agents"

Start-Sleep -Milliseconds $SleepMs

# Immediate foreground POST
try {
    $fg = Invoke-RestMethod -Method Post -Uri "$McpUrl/run-agents" -Body $payload -ContentType 'application/json' -Headers @{ Authorization = 'Bearer demo' }
    Write-Host "Foreground request succeeded:`n" ($fg | ConvertTo-Json -Depth 5)
} catch {
    Write-Host "Foreground request failed (expected if conflict): $($_.Exception.Message)"
}

# Wait for background job
if (Wait-Job -Job $bg -Timeout ($WaitForBgSeconds)) {
    $bgRes = Receive-Job -Job $bg
    Remove-Job -Job $bg -Force
} else {
    Write-Host "Background job did not finish within $WaitForBgSeconds seconds; aborting.`n"
    try { Remove-Job -Job $bg -Force } catch { }
    exit 2
}

Write-Host "Background result:`n" ($bgRes | ConvertTo-Json -Depth 5)

# Read sentinel files from the mcp container using docker exec (avoid complex quoting via compose exec)
Write-Host "Reading sentinel files from container (docker exec)..."
try {
    $cid = (& docker compose ps -q mcp).Trim()
    if (-not $cid) {
        Write-Host "Could not find running mcp container via 'docker compose ps -q mcp'" -ForegroundColor Red
        exit 3
    }
    $remoteCmd = "echo '--- /tmp/run_agents_entered.log ---'; cat /tmp/run_agents_entered.log || true; echo '--- /tmp/run_agents_lock_acquired.log ---'; cat /tmp/run_agents_lock_acquired.log || true; echo '--- /tmp/run_agents_lock_conflict.log ---'; cat /tmp/run_agents_lock_conflict.log || true"
    $sentOut = & docker exec $cid sh -lc $remoteCmd 2>&1
} catch {
    Write-Host "Failed to read container sentinel files: $($_.Exception.Message)"
    exit 3
}

Write-Host $sentOut

# Quick parse for counts
$acq = ($sentOut | Select-String 'LOCK_ACQUIRED').Count
$conf = ($sentOut | Select-String 'LOCK_CONFLICT').Count
$entered = ($sentOut | Select-String 'RUN_AGENTS_ENTERED').Count

Write-Host "Sentinel summary: entered=$entered acquired=$acq conflict=$conf"

if ($entered -lt 2) {
    Write-Host "Expected two handler entries but found $entered. The test may be flaky or mcp not receiving both requests." -ForegroundColor Yellow
}

if ($acq -ge 1 -and $conf -ge 1) {
    Write-Host "SMOKE TEST PASSED: observed at least one LOCK_ACQUIRED and one LOCK_CONFLICT." -ForegroundColor Green
    exit 0
} else {
    Write-Host "SMOKE TEST FAILED: expected >=1 acquired and >=1 conflict.`n" -ForegroundColor Red
    exit 4
}
