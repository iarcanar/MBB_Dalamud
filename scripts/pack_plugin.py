#!/usr/bin/env python3
"""
pack_plugin.py — Package the Dalamud plugin into the served latest.zip.

Replaces the manual `zip -r ...` step in BUILD_PROTOCOL §2 that was easy to get
wrong: the old command bundled only DLL + json + icon and DROPPED the WMI
runtime deps (System.Management.dll + System.CodeDom.dll), which Dalamud does
NOT resolve automatically → the plugin throws at runtime on the WMI process
check. This script bundles the full required set and refreshes the
pluginmaster.json LastUpdated timestamp (the served artifact changed, so its
freshness signal should change too).

Usage:
    python scripts/pack_plugin.py            # build latest.zip from bin/Release
    python scripts/pack_plugin.py --no-stamp # skip the LastUpdated bump

Run AFTER: dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release
"""
import os
import re
import sys
import time
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "DalamudMBBBridge", "bin", "Release")
OUT_ZIP = os.path.join(REPO_ROOT, "plugins", "DalamudMBBBridge", "latest.zip")
PLUGINMASTER = os.path.join(REPO_ROOT, "pluginmaster.json")

# Everything the plugin needs at runtime inside Dalamud.
REQUIRED = [
    "DalamudMBBBridge.dll",
    "DalamudMBBBridge.json",
    "icon.png",
    "System.Management.dll",   # WMI process-check
    "System.CodeDom.dll",      # transitive dep of System.Management
]


def stamp_pluginmaster() -> None:
    """Refresh pluginmaster.json LastUpdated to now (matches bump_version.py)."""
    if not os.path.exists(PLUGINMASTER):
        print(f"  WARN  pluginmaster.json not found at {PLUGINMASTER} — skipped stamp")
        return
    with open(PLUGINMASTER, "r", encoding="utf-8") as f:
        content = f.read()
    ts = str(int(time.time()))
    new = re.sub(r'"LastUpdated":\s*"[^"]*"', f'"LastUpdated": "{ts}"', content)
    if new != content:
        with open(PLUGINMASTER, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"  OK    pluginmaster.json LastUpdated -> {ts}")
    else:
        print("  SAME  pluginmaster.json LastUpdated (no field matched?)")


def main() -> int:
    stamp = "--no-stamp" not in sys.argv

    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(SRC_DIR, f))]
    if missing:
        print("ERROR: missing required plugin files in:")
        print(f"       {SRC_DIR}")
        for f in missing:
            print(f"       - {f}")
        print("\nBuild the C# plugin first:")
        print("  dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release")
        return 1

    os.makedirs(os.path.dirname(OUT_ZIP), exist_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in REQUIRED:
            z.write(os.path.join(SRC_DIR, fname), fname)  # store at archive root

    size_kb = os.path.getsize(OUT_ZIP) / 1024
    print(f"  OK    packed {len(REQUIRED)} files -> {OUT_ZIP} ({size_kb:.0f} KB)")
    for fname in REQUIRED:
        print(f"          + {fname}")

    if stamp:
        stamp_pluginmaster()

    print("\nNext: git add pluginmaster.json plugins/ && git commit && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
