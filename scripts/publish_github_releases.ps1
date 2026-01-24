<#!
.SYNOPSIS
    Publish annotated GitHub Releases for v2.3.0 and v2.3.1 from RELEASE_NOTES.md.
.DESCRIPTION
    Parses sections for the specified tags from RELEASE_NOTES.md and creates GitHub Releases
    via the REST API. Skips creation if release already exists. Supports dry-run mode.

    Requires environment variable GITHUB_TOKEN with repo scope (or fine-grained: contents + metadata + actions).

.PARAMETER Owner
    GitHub repository owner (e.g. reginaldrhoe)
.PARAMETER Repo
    GitHub repository name (e.g. rag-poc)
.PARAMETER Tags
    One or more tags to publish (default: v2.3.0,v2.3.1)
.PARAMETER ReleaseNotesPath
    Path to RELEASE_NOTES.md (default: ./RELEASE_NOTES.md)
.PARAMETER Draft
    If set, creates releases as draft (default: $false)
.PARAMETER Prerelease
    If set, marks release as prerelease (default: $false)
.PARAMETER DryRun
    If set, shows what would be published without calling API.
.EXAMPLE
    .\scripts\publish_github_releases.ps1 -Owner reginaldrhoe -Repo rag-poc
.EXAMPLE
    .\scripts\publish_github_releases.ps1 -Owner reginaldrhoe -Repo rag-poc -Tags v2.3.1 -DryRun
.NOTES
    Uses simple regex window extraction; ensure headings start with '## vX.Y.Z'.
#>
param(
    [string]$Owner = 'reginaldrhoe',
    [string]$Repo = 'rag-poc',
    [string[]]$Tags = @('v2.3.0','v2.3.1','v2.3.2'),
    [string]$ReleaseNotesPath = 'RELEASE_NOTES.md',
    [switch]$Draft,
    [switch]$Prerelease,
    [switch]$DryRun,
    [switch]$Update
)

if (-not $env:GITHUB_TOKEN) {
    Write-Error 'GITHUB_TOKEN environment variable not set. Export a PAT before running.'
    exit 1
}
if (-not (Test-Path $ReleaseNotesPath)) {
    Write-Error "Release notes file not found: $ReleaseNotesPath"
    exit 1
}

$all = Get-Content $ReleaseNotesPath -Raw
$headers = @{ Authorization = "Bearer $($env:GITHUB_TOKEN)"; 'User-Agent' = 'rag-poc-release-script'; Accept = 'application/vnd.github+json' }
$apiBase = "https://api.github.com/repos/$Owner/$Repo"

function Get-SectionForTag([string]$tag, [string]$content) {
    # Match from ## vX.Y.Z until next heading starting with ## v (lookahead)
    $pattern = "## $([regex]::Escape($tag)).*?(?=## v[0-9])"
    $m = [regex]::Match($content, $pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($m.Success) { return $m.Value.Trim() }
    else { return $null }
}

function ReleaseExists([string]$tag) {
    if ($DryRun) { return $false } # Skip API existence check in dry-run mode
    try {
        $url = "$apiBase/releases/tags/$tag"
        $r = Invoke-RestMethod -Method GET -Uri $url -Headers $headers -ErrorAction Stop
        return $true
    } catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 404) { return $false } else { throw }
    }
}

function Get-ReleaseByTag([string]$tag) {
    $url = "$apiBase/releases/tags/$tag"
    return Invoke-RestMethod -Method GET -Uri $url -Headers $headers -ErrorAction Stop
}

function Update-ReleaseBody([string]$tag, [string]$bodyText) {
    if ($DryRun) {
        Write-Host "[DRY-RUN] Would update release body for $tag" -ForegroundColor Cyan
        return
    }
    $rel = Get-ReleaseByTag -tag $tag
    $patchPayload = @{ name = $tag; body = $bodyText } | ConvertTo-Json -Depth 10
    Invoke-RestMethod -Method PATCH -Uri "$apiBase/releases/$($rel.id)" -Headers $headers -ContentType 'application/json' -Body $patchPayload -ErrorAction Stop | Out-Null
}

$results = @()
foreach ($t in $Tags) {
    $section = Get-SectionForTag -tag $t -content $all
    if (-not $section) {
        Write-Warning "No section found for $t; skipping."
        $results += [pscustomobject]@{ tag=$t; status='missing-section' }
        continue
    }
    if (-not $DryRun -and (ReleaseExists $t)) {
        if ($Update) {
            Write-Host "Release for $t exists; updating body from notes..." -ForegroundColor Yellow
            try {
                Update-ReleaseBody -tag $t -bodyText $section
                $results += [pscustomobject]@{ tag=$t; status='updated' }
            } catch {
                $msg = $_.Exception.Message
                Write-Warning ("Failed to update {0}: {1}" -f $t, $msg)
                $results += [pscustomobject]@{ tag=$t; status='update-failed'; error=$msg }
            }
        } else {
            Write-Host "Release for $t already exists; skipping." -ForegroundColor Yellow
            $results += [pscustomobject]@{ tag=$t; status='exists' }
        }
        continue
    }
    $payload = [pscustomobject]@{
        tag_name = $t
        name     = $t
        body     = $section
        draft    = [bool]$Draft
        prerelease = [bool]$Prerelease
    }
    if ($DryRun) {
        Write-Host "[DRY-RUN] Would create release for $t (draft=$Draft prerelease=$Prerelease)" -ForegroundColor Cyan
        $results += [pscustomobject]@{ tag=$t; status='dry-run'; length=$section.Length }
        continue
    }
    Write-Host "Creating release $t..." -ForegroundColor Green
    try {
        $jsonBody = ($payload | ConvertTo-Json -Depth 10)
        $resp = Invoke-RestMethod -Method POST -Uri "$apiBase/releases" -Headers $headers -ContentType 'application/json' -Body $jsonBody -ErrorAction Stop
        $results += [pscustomobject]@{ tag=$t; status='created'; url=$resp.html_url }
    } catch {
        $msg = $_.Exception.Message
        Write-Warning ("Failed to create {0}: {1}" -f $t, $msg)
        $results += [pscustomobject]@{ tag=$t; status='failed'; error=$msg }
    }
}

Write-Host "Summary:" -ForegroundColor Magenta
$results | Format-Table -AutoSize
