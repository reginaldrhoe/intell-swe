# Clean Docker volumes for intell-swe v3.0.0 fresh deployment
# Run this once Docker daemon is available

Write-Host "intell-swe Docker Volume Cleanup Script" -ForegroundColor Cyan
Write-Host ""

# 1. Stop containers
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker compose -f C:\MySQL\intell_swe\docker-compose.yml down -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Containers stopped and volumes removed" -ForegroundColor Green
} else {
    Write-Host "⚠ Docker daemon may not be running" -ForegroundColor Yellow
}

Write-Host ""

# 2. List remaining volumes (for manual inspection)
Write-Host "Checking for orphaned volumes..." -ForegroundColor Yellow
$volumes = docker volume ls --filter "label=com.docker.compose.project=intell_swe" -q 2>$null
if ($volumes) {
    Write-Host "Found intell_swe volumes:" -ForegroundColor Yellow
    $volumes | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "Removing them..." -ForegroundColor Yellow
    $volumes | ForEach-Object { docker volume rm $_ }
    Write-Host "✓ Volumes removed" -ForegroundColor Green
} else {
    Write-Host "✓ No intell_swe volumes found (already clean)" -ForegroundColor Green
}

Write-Host ""

# 3. Prune all unused volumes (optional, removes orphans across all projects)
Write-Host "Pruning unused volumes (all projects)..." -ForegroundColor Yellow
docker volume prune -f
Write-Host "✓ Pruning complete" -ForegroundColor Green

Write-Host ""

# 4. Pull fresh images
Write-Host "Pulling fresh images..." -ForegroundColor Yellow
docker compose -f C:\MySQL\intell_swe\docker-compose.yml pull
Write-Host "✓ Images updated" -ForegroundColor Green

Write-Host ""
Write-Host "Ready for fresh v3.0.0 deployment!" -ForegroundColor Green
Write-Host "Next: docker compose up -d postgres redis qdrant" -ForegroundColor Gray
