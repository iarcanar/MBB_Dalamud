"""
MBB Version Bump Script — อัปเดตเลขเวอร์ชันทุกจุดในโปรเจกต์พร้อมกัน

Usage:
    python bump_version.py 1.8.0
    python bump_version.py patch      # 1.7.8 → 1.7.9
    python bump_version.py minor      # 1.7.8 → 1.8.0
    python bump_version.py major      # 1.7.8 → 2.0.0
    python bump_version.py            # แสดงเวอร์ชันปัจจุบัน
"""
import re
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ── Single source of truth ──
VERSION_FILE = os.path.join(PROJECT_ROOT, "python-app", "version.py")

# ── All files that contain version strings ──
VERSION_LOCATIONS = [
    # Python source of truth
    {
        "file": "python-app/version.py",
        "patterns": [
            (r'__version__\s*=\s*"[^"]*"', '__version__ = "{version}"'),
        ],
    },
    # C# plugin manifest
    {
        "file": "DalamudMBBBridge/DalamudMBBBridge.json",
        "patterns": [
            (r'"Name":\s*"MBB Dalamud Bridge v[^"]*"', '"Name": "MBB Dalamud Bridge v{version}"'),
            (r'"AssemblyVersion":\s*"[^"]*"', '"AssemblyVersion": "{version}"'),
        ],
    },
    # C# project version
    {
        "file": "DalamudMBBBridge/DalamudMBBBridge.csproj",
        "patterns": [
            (r"<Version>[^<]*</Version>", "<Version>{version}</Version>"),
        ],
    },
    # Dalamud custom repo manifest
    {
        "file": "pluginmaster.json",
        "patterns": [
            (r'"AssemblyVersion":\s*"[^"]*"', '"AssemblyVersion": "{version}"'),
        ],
    },
    # Dalamud repo-structure manifest
    {
        "file": "repo-structure/pluginmaster.json",
        "patterns": [
            (r'"AssemblyVersion":\s*"[^"]*"', '"AssemblyVersion": "{version}"'),
        ],
    },
    # PyInstaller spec
    {
        "file": "python-app/mbb.spec",
        "patterns": [
            (r"# Version: [\d.]+", "# Version: {version}"),
        ],
    },
    # README badge
    {
        "file": "README.md",
        "patterns": [
            (r"\*\*Version:\*\* \d+\.\d+\.\d+", "**Version:** {version}"),
        ],
    },
    # claude.md header
    {
        "file": "claude.md",
        "patterns": [
            (r"\*\*Version:\*\* \d+\.\d+\.\d+", "**Version:** {version}"),
        ],
    },
]


def get_current_version() -> str:
    """Read current version from version.py."""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*"([^"]*)"', content)
    if not match:
        print("ERROR: Cannot read current version from version.py")
        sys.exit(1)
    return match.group(1)


def bump(current: str, part: str) -> str:
    """Bump version by part: major, minor, or patch."""
    parts = current.split(".")
    if len(parts) != 3:
        print(f"ERROR: Version '{current}' is not in X.Y.Z format")
        sys.exit(1)
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"ERROR: Unknown bump type '{part}'. Use: major, minor, patch")
        sys.exit(1)


def update_file(location: dict, new_version: str) -> bool:
    """Update version in a single file. Returns True if changed."""
    filepath = os.path.join(PROJECT_ROOT, location["file"])
    if not os.path.exists(filepath):
        print(f"  SKIP  {location['file']} (file not found)")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for pattern, replacement in location["patterns"]:
        formatted_replacement = replacement.format(version=new_version)
        content = re.sub(pattern, formatted_replacement, content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  OK    {location['file']}")
        return True
    else:
        print(f"  SAME  {location['file']} (already up to date)")
        return False


def main():
    current = get_current_version()

    if len(sys.argv) < 2:
        print(f"Current version: {current}")
        print(f"\nUsage: python bump_version.py <new_version|patch|minor|major>")
        return

    arg = sys.argv[1]

    # Determine new version
    if arg in ("major", "minor", "patch"):
        new_version = bump(current, arg)
    elif re.match(r"^\d+\.\d+\.\d+$", arg):
        new_version = arg
    else:
        print(f"ERROR: '{arg}' is not a valid version or bump type")
        print(f"Usage: python bump_version.py <X.Y.Z|patch|minor|major>")
        sys.exit(1)

    print(f"Bumping version: {current} → {new_version}\n")

    changed = 0
    for location in VERSION_LOCATIONS:
        if update_file(location, new_version):
            changed += 1

    print(f"\nDone! Updated {changed} file(s) to v{new_version}")
    print(f"\nNext steps:")
    print(f"  1. cd DalamudMBBBridge && dotnet build -c Release")
    print(f"  2. Test in game")
    print(f"  3. git add -A && git commit")


if __name__ == "__main__":
    main()
