# Upload MBB release zip to Google Drive.
# Usage:
#   .\scripts\upload_release.ps1                          # auto-picks newest MBB-v*.zip in dist_test/
#   .\scripts\upload_release.ps1 -ZipPath C:\path\to.zip  # explicit file
#   .\scripts\upload_release.ps1 -Force                   # overwrite if same name exists on Drive

param(
    [string]$ZipPath,
    [string]$FolderId = "1KonywPrLdda7GMi-aBeS4AF95HJ9MOe4",
    [string]$RemoteName = "mbb_drive",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Resolve-Rclone {
    $cmd = Get-Command rclone -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $wingetPath = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Rclone.Rclone*" -Filter "rclone.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($wingetPath) { return $wingetPath.FullName }
    throw "rclone.exe not found. Install via: winget install --id Rclone.Rclone"
}

$rclone = Resolve-Rclone

# Auto-detect latest zip if not specified
if (-not $ZipPath) {
    $distDir = Join-Path $PSScriptRoot "..\dist_test"
    $latest = Get-ChildItem (Join-Path $distDir "MBB-v*.zip") -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { throw "No MBB-v*.zip found in $distDir" }
    $ZipPath = $latest.FullName
}
if (-not (Test-Path $ZipPath)) { throw "Zip not found: $ZipPath" }

$local = Get-Item $ZipPath
$localSizeMB = [math]::Round($local.Length / 1MB, 2)
Write-Host "Local zip   : $($local.Name) ($localSizeMB MB)"
Write-Host "Folder ID   : $FolderId"
Write-Host ""

# Check if same-name file already on Drive — skip unless -Force
$remoteList = & $rclone lsl "${RemoteName}:" --drive-root-folder-id $FolderId 2>$null
$existing = $remoteList | Where-Object { $_ -match "\s$([regex]::Escape($local.Name))\s*$" }
if ($existing) {
    $existingSize = ($existing.Trim() -split '\s+')[0]
    if (-not $Force -and [int64]$existingSize -eq $local.Length) {
        Write-Host "SKIP: $($local.Name) already on Drive with identical size ($existingSize bytes)."
        Write-Host "Use -Force to re-upload."
        exit 0
    }
    if (-not $Force) {
        Write-Host "WARN: $($local.Name) exists on Drive with different size ($existingSize vs $($local.Length))."
        Write-Host "Use -Force to overwrite." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "OVERWRITE: $($local.Name) (forced)" -ForegroundColor Yellow
}

Write-Host "Uploading..." -ForegroundColor Cyan
& $rclone copy $ZipPath "${RemoteName}:" `
    --drive-root-folder-id $FolderId `
    --progress `
    --stats 2s `
    --drive-chunk-size 32M

Write-Host ""
Write-Host "=== Verification ===" -ForegroundColor Green
& $rclone lsl "${RemoteName}:" --drive-root-folder-id $FolderId |
    Where-Object { $_ -match [regex]::Escape($local.Name) }
