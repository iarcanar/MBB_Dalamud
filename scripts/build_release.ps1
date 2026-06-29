<#
.SYNOPSIS
    One-shot MBB release builder. Runs the full pipeline in the correct order so
    a release can't ship with a missing piece (the historical foot-guns: updater
    built after main -> updater absent; console=True debug build; plugin zip
    missing WMI dlls; no sha256 sidecar -> updater skips integrity check).

.DESCRIPTION
    Steps (each aborts on failure):
      1. (optional) bump version            -Version X.Y.Z
      2. check_version_consistency.py        (must pass)
      3. dotnet build C# plugin (Release)
      4. pack_plugin.py                      (latest.zip incl. WMI dlls + LastUpdated)
      5. build updater                       (must precede main build)
      6. build main EXE                      (MBB_RELEASE=1 -> windowed/no-console)
      7. zip dist_test/MBB -> MBB-vX.Y.Z.zip
      8. write MBB-vX.Y.Z.zip.sha256.txt     (updater verifies this)
      9. (optional) gh release create        -Publish
     10. (optional) Drive mirror upload      -Mirror

.EXAMPLE
    powershell scripts/build_release.ps1 -Version 1.8.22 -Publish
    powershell scripts/build_release.ps1            # build only, current version

.NOTES
    Requires the Python that has PyQt6==6.9.0 + pyinstaller on PATH (see BUILD_PROTOCOL.md).
    After this: git add pluginmaster.json plugins/ ; commit ; push  ->  then set the
    web version on /admin/release ("Set web to vX.Y.Z").
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [switch]$Publish,
    [switch]$Mirror,
    [string]$NotesFile = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist_test"

function Step($n, $msg) { Write-Host "`n=== [$n] $msg ===" -ForegroundColor Cyan }
function Die($msg) { Write-Host "BUILD ABORTED: $msg" -ForegroundColor Red; exit 1 }

Push-Location $root
try {
    # 1. Optional version bump
    if ($Version) {
        Step 1 "Bump version -> $Version"
        python bump_version.py $Version
        if ($LASTEXITCODE -ne 0) { Die "bump_version failed" }
    } else {
        Step 1 "Skip bump (using current version.py)"
    }

    # 2. Version consistency (includes DalamudApiLevel cross-check)
    Step 2 "Version consistency check"
    python python-app/check_version_consistency.py
    if ($LASTEXITCODE -ne 0) { Die "version consistency check failed - fix before building" }

    # Resolve the version we are building.
    $verLine = Select-String -Path (Join-Path $root "python-app\version.py") -Pattern '__version__\s*=\s*"([^"]+)"'
    if (-not $verLine) { Die "could not read __version__ from version.py" }
    $ver = $verLine.Matches[0].Groups[1].Value
    Write-Host "Building MBB v$ver" -ForegroundColor Green

    # 3. C# plugin
    Step 3 "Build C# Dalamud plugin (Release)"
    dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release
    if ($LASTEXITCODE -ne 0) { Die "dotnet build failed" }

    # 4. Pack plugin zip (incl. WMI dlls) + stamp pluginmaster LastUpdated
    Step 4 "Pack plugin latest.zip"
    python scripts/pack_plugin.py
    if ($LASTEXITCODE -ne 0) { Die "pack_plugin failed" }

    # PyQt6 sanity (frameless+translucent regression on 6.10+).
    $pyqt = (python -c "from PyQt6.QtCore import PYQT_VERSION_STR as v; print(v)" 2>$null)
    if ($pyqt -and $pyqt -ne "6.9.0") {
        Write-Host "WARNING: PyQt6 $pyqt (expected 6.9.0). 6.10+ has a frameless rendering regression." -ForegroundColor Yellow
    }

    # Clean previous build outputs.
    Step 5 "Clean + build updater (must precede main build)"
    Remove-Item -Recurse -Force (Join-Path $dist "MBB"), (Join-Path $dist "build_work"), `
        (Join-Path $dist "build_updater"), (Join-Path $dist "MBB-Updater.exe") -ErrorAction SilentlyContinue

    # 5. Updater FIRST (main spec copies MBB-Updater.exe into MBB/).
    Push-Location (Join-Path $root "updater")
    pyinstaller updater.spec --clean --noconfirm --distpath ../dist_test --workpath ../dist_test/build_updater
    $rc = $LASTEXITCODE
    Pop-Location
    if ($rc -ne 0) { Die "updater build failed" }

    # 6. Main EXE - MBB_RELEASE=1 -> windowed (no console).
    Step 6 "Build main EXE (MBB_RELEASE=1, windowed)"
    $env:MBB_RELEASE = "1"
    try {
        Push-Location (Join-Path $root "python-app")
        pyinstaller mbb.spec --clean --noconfirm --distpath ../dist_test --workpath ../dist_test/build_work
        $rc = $LASTEXITCODE
        Pop-Location
    } finally {
        Remove-Item Env:MBB_RELEASE -ErrorAction SilentlyContinue
    }
    if ($rc -ne 0) { Die "main EXE build failed (or secrets scan tripped)" }

    # 7. Zip
    Step 7 "Package MBB-v$ver.zip"
    $zip = Join-Path $dist "MBB-v$ver.zip"
    Remove-Item $zip -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $dist "MBB") -DestinationPath $zip -CompressionLevel Optimal
    if (-not (Test-Path $zip)) { Die "zip not produced" }

    # 8. SHA256 sidecar (updater reads first whitespace token -> sha256sum format)
    Step 8 "Write sha256 sidecar"
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    $sidecar = "$zip.sha256.txt"
    "$hash  MBB-v$ver.zip" | Out-File -FilePath $sidecar -Encoding ascii -NoNewline
    Write-Host "  $hash" -ForegroundColor Green

    $zipSize = "{0:N1} MB" -f ((Get-Item $zip).Length / 1MB)
    Write-Host "`nBuilt: $zip ($zipSize)" -ForegroundColor Green
    Write-Host "       $sidecar"

    # 9. Optional GitHub release
    if ($Publish) {
        Step 9 "Create GitHub release v$ver"
        $ghArgs = @("release", "create", "v$ver", "--title", "MBB v$ver", $zip, $sidecar)
        if ($NotesFile -and (Test-Path $NotesFile)) { $ghArgs += @("--notes-file", $NotesFile) }
        else { $ghArgs += @("--generate-notes") }
        gh @ghArgs
        if ($LASTEXITCODE -ne 0) { Die "gh release create failed" }
    }

    # 10. Optional Drive mirror
    if ($Mirror) {
        Step 10 "Upload Drive mirror"
        & (Join-Path $PSScriptRoot "upload_release.ps1") -ZipPath $zip
    }

    Write-Host "`n[OK] DONE v$ver" -ForegroundColor Green
    Write-Host "Next:" -ForegroundColor Cyan
    Write-Host "  1. git add pluginmaster.json plugins/ ; git commit -m `"Release v$ver`" ; git push"
    if (-not $Publish) { Write-Host "  2. gh release create v$ver --generate-notes `"$zip`" `"$sidecar`"" }
    Write-Host "  3. /admin/release -> click 'Set web to v$ver (from GitHub)'"
}
finally {
    Pop-Location
}
