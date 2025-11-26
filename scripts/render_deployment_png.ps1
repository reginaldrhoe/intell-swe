<#
Helper script to build a small docker image and render docs/deployment.svg -> docs/deployment.png

Usage (PowerShell):
  .\scripts\render_deployment_png.ps1

This mounts the repo root into the container, runs the conversion, and writes
the output file to `docs/deployment.png` in the repo.
#>

$imageName = "ragpoc-svg2png:latest"
Write-Host "Building docker image $imageName..."
docker build -f tools/svg2png.Dockerfile -t $imageName .
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }

Write-Host "Running conversion container (will write docs/deployment.png)..."
docker run --rm -v ${PWD}:/work $imageName
if ($LASTEXITCODE -ne 0) { throw "Conversion container failed" }

if (Test-Path -Path "docs/deployment.png") {
    Write-Host "Success: docs/deployment.png created"
} else {
    Write-Host "Conversion finished but docs/deployment.png not found"
}
