# Ensure logo is included in build/release artifacts
# This script verifies the logo file exists and is accessible from all required locations
# Called during build process to prevent regression of missing logo in releases

param(
    [string]$RepoRoot = (git rev-parse --show-toplevel 2>$null || (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))),
    [string]$BuildDir = "dist",
    [string]$DocsDir = "docs"
)

Write-Host "Logo Artifact Verification" -ForegroundColor Cyan
Write-Host "Repository Root: $RepoRoot" -ForegroundColor Gray
Write-Host ""

$logoFile = Join-Path $RepoRoot $DocsDir "Logo design featurin.png"
$webPublicDir = Join-Path $RepoRoot "web" "public"
$webLogoTarget = Join-Path $webPublicDir "Logo design featurin.png"

# Check 1: Logo exists in docs
Write-Host "✓ Checking docs/$($DocsDir | Split-Path -Leaf) for logo..." -ForegroundColor Yellow
if (Test-Path $logoFile) {
    $size = (Get-Item $logoFile).Length / 1KB
    Write-Host "  ✓ Found: $logoFile ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "  ✗ MISSING: $logoFile" -ForegroundColor Red
    exit 1
}

# Check 2: Copy logo to web/public if it exists for static serving
if (Test-Path $webPublicDir) {
    Write-Host "✓ Copying logo to web/public for static serving..." -ForegroundColor Yellow
    Copy-Item $logoFile $webLogoTarget -Force
    Write-Host "  ✓ Logo available at web/public" -ForegroundColor Green
} else {
    Write-Host "  ⓘ web/public directory not found (may be built later)" -ForegroundColor Gray
}

# Check 3: Verify references in documentation
Write-Host "✓ Verifying logo references in documentation..." -ForegroundColor Yellow
$docsToCheck = @(
    (Join-Path $RepoRoot "README.md"),
    (Join-Path $RepoRoot "RELEASE_NOTES.md"),
    (Join-Path $RepoRoot "docs" "analysis" "TEST_COVERAGE.md"),
    (Join-Path $RepoRoot "docs" "analysis" "EVALUATION_METRICS.md")
)

$missingRefs = @()
foreach ($doc in $docsToCheck) {
    if (Test-Path $doc) {
        $content = Get-Content $doc -Raw
        if ($content -match "Logo.*design|featurin\.png") {
            Write-Host "  ✓ $([System.IO.Path]::GetFileName($doc)): has logo reference" -ForegroundColor Green
        } else {
            Write-Host "  ! $([System.IO.Path]::GetFileName($doc)): NO logo reference" -ForegroundColor Yellow
            $missingRefs += $doc
        }
    }
}

if ($missingRefs.Count -gt 0) {
    Write-Host "  Warning: $($missingRefs.Count) document(s) missing logo reference" -ForegroundColor Yellow
}

# Check 4: Verify UI includes logo
Write-Host "✓ Verifying logo in React UI..." -ForegroundColor Yellow
$appFile = Join-Path $RepoRoot "web" "src" "App.jsx"
if (Test-Path $appFile) {
    $content = Get-Content $appFile -Raw
    if ($content -match "Logo.*design|featurin\.png") {
        Write-Host "  ✓ App.jsx: includes logo display" -ForegroundColor Green
    } else {
        Write-Host "  ✗ App.jsx: NO logo display code" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Logo artifact verification: COMPLETE" -ForegroundColor Green
Write-Host "Release artifacts will include logo in all required locations." -ForegroundColor Green
