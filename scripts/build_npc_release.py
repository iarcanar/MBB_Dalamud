"""Publish a new release of npc.json to iarcanar/MBB_NPCData (Phase A — public/plaintext).

Usage:
    python scripts/build_npc_release.py [--notes "release notes in Thai"]
                                        [--version YYYY.MM.DD]
                                        [--dry-run]

Flow:
    1. Read python-app/npc.json (the canonical local copy)
    2. Resolve next data_version (default: today's date; auto-suffix .N if same date already released)
    3. Clone MBB_NPCData to a temp working dir
    4. Copy npc.json → data/npc.json + data/archive/npc-<version>.json
    5. Commit + push data (commit #1)
    6. Wait 3s, download from raw URL, compute sha256 of served bytes
       (this matters because git may LF-normalize despite .gitattributes;
        we always trust the served bytes as the source of truth)
    7. Generate manifest.json with verified sha256
    8. Commit + push manifest (commit #2)
    9. Cleanup temp dir

MBB clients fetch manifest.json → compare data_version → if newer, fetch + sha256-verify + hand to _MergeDialog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen


REPO_URL = "https://github.com/iarcanar/MBB_NPCData.git"
RAW_DATA_URL = "https://raw.githubusercontent.com/iarcanar/MBB_NPCData/main/data/npc.json"
RAW_MANIFEST_URL = "https://raw.githubusercontent.com/iarcanar/MBB_NPCData/main/manifest.json"
MIN_MBB_VERSION = "1.8.8"

# python-app/npc.json relative to repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LOCAL_NPC_JSON = os.path.join(REPO_ROOT, "python-app", "npc.json")


def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess + stream output. Raises on non-zero if check=True."""
    print(f"  $ {' '.join(cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def fetch_url(url: str, decompress_to_bytes: bool = True) -> bytes:
    """GET url → bytes. Uses identity encoding so we get raw served bytes
    (no gzip auto-decompression that could mask byte differences)."""
    req = Request(url, headers={
        "User-Agent": "mbb-npc-release-script/1.0",
        "Accept-Encoding": "identity",  # don't accept gzip
        "Cache-Control": "no-cache",
    })
    with urlopen(req, timeout=15) as r:
        return r.read()


def resolve_next_version(today: str | None = None) -> str:
    """Pick next data_version. Default = today YYYY.MM.DD. If today's version
    already exists on cloud, suffix .2, .3, ... so each push is unique."""
    base = today or datetime.now(timezone.utc).strftime("%Y.%m.%d")
    # Check current manifest
    try:
        m = json.loads(fetch_url(RAW_MANIFEST_URL).decode("utf-8"))
        current = m.get("data_version", "")
    except Exception as e:
        print(f"  (could not fetch current manifest — assuming first release: {e})")
        return base
    if not current.startswith(base):
        return base
    # Same day — find next suffix
    rest = current[len(base):]
    if rest == "":
        return f"{base}.2"
    if rest.startswith(".") and rest[1:].isdigit():
        return f"{base}.{int(rest[1:]) + 1}"
    return f"{base}.2"


def load_local_npc() -> tuple[bytes, dict]:
    if not os.path.exists(LOCAL_NPC_JSON):
        raise SystemExit(f"local npc.json not found at {LOCAL_NPC_JSON}")
    with open(LOCAL_NPC_JSON, "rb") as f:
        raw = f.read()
    parsed = json.loads(raw)
    return raw, parsed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--notes", default="", help="Release notes (Thai) for manifest.release_notes_th")
    ap.add_argument("--version", default=None, help="Override data_version (default: today's date)")
    ap.add_argument("--dry-run", action="store_true", help="Show plan + skip push")
    args = ap.parse_args()

    # Step 1: load local npc.json + sanity check
    print("\n[1/8] Loading local npc.json...")
    local_bytes, npc = load_local_npc()
    stats = {
        "main": len(npc.get("main_characters", [])),
        "npcs": len(npc.get("npcs", [])),
        "lore": len(npc.get("lore", [])),
        "character_roles": len(npc.get("character_roles", {})),
    }
    print(f"  loaded {len(local_bytes)} bytes  |  stats={stats}")

    # Step 2: resolve version
    print("\n[2/8] Resolving next data_version...")
    version = args.version or resolve_next_version()
    print(f"  → v{version}")

    if args.dry_run:
        print("\n--dry-run: stopping before clone/push")
        print(f"  would publish v{version} with {stats}")
        return

    # Step 3: clone to temp working dir
    print("\n[3/8] Cloning MBB_NPCData to temp dir...")
    work = tempfile.mkdtemp(prefix="mbb_npcdata_pub_")
    try:
        run(["git", "clone", "--depth", "1", REPO_URL, work])

        # Step 4: copy npc.json + archive
        print(f"\n[4/8] Copying npc.json into work tree...")
        dst_main = os.path.join(work, "data", "npc.json")
        dst_arch = os.path.join(work, "data", "archive", f"npc-{version}.json")
        os.makedirs(os.path.dirname(dst_main), exist_ok=True)
        os.makedirs(os.path.dirname(dst_arch), exist_ok=True)
        shutil.copyfile(LOCAL_NPC_JSON, dst_main)
        shutil.copyfile(LOCAL_NPC_JSON, dst_arch)
        print(f"  → data/npc.json")
        print(f"  → data/archive/npc-{version}.json")

        # Step 5: commit + push data (commit #1)
        print("\n[5/8] Commit #1 — push data files...")
        run(["git", "add", "data/"], cwd=work)
        # Skip if nothing changed (e.g., republishing identical bytes)
        status = run(["git", "status", "--porcelain"], cwd=work, check=False).stdout.strip()
        if not status:
            print("  (no changes — data identical to current. Aborting.)")
            return
        run(["git", "commit", "-m", f"Release v{version}: npc.json data update"], cwd=work)
        run(["git", "push", "origin", "main"], cwd=work)

        # Step 6: wait + download from raw, compute served sha256
        print("\n[6/8] Waiting for raw URL to propagate...")
        time.sleep(3)
        for attempt in range(5):
            try:
                served = fetch_url(RAW_DATA_URL)
                served_sha = hashlib.sha256(served).hexdigest()
                served_size = len(served)
                # Sanity: served file must be parseable JSON with expected stats
                parsed_served = json.loads(served)
                if len(parsed_served.get("main_characters", [])) == stats["main"]:
                    print(f"  served sha256: {served_sha}")
                    print(f"  served size:   {served_size} bytes")
                    break
            except Exception as e:
                print(f"  attempt {attempt + 1}: {e}")
                time.sleep(2)
        else:
            raise SystemExit("Failed to verify served bytes after 5 attempts. Manual fix needed.")

        # Step 7: write manifest.json
        print("\n[7/8] Generating manifest.json...")
        manifest = {
            "schema_version": 1,
            "data_version": version,
            "released_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_url": RAW_DATA_URL,
            "data_sha256": served_sha,
            "data_size_bytes": served_size,
            "stats": stats,
            "min_mbb_version": MIN_MBB_VERSION,
            "release_notes_th": args.notes or f"Release v{version}",
        }
        manifest_path = os.path.join(work, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  manifest ready")

        # Step 8: commit + push manifest (commit #2)
        print("\n[8/8] Commit #2 — push manifest.json...")
        run(["git", "add", "manifest.json"], cwd=work)
        run(["git", "commit", "-m", f"Release v{version}: manifest"], cwd=work)
        run(["git", "push", "origin", "main"], cwd=work)

        print(f"\n✓ Published v{version}")
        print(f"  https://github.com/iarcanar/MBB_NPCData")
        print(f"  raw manifest: {RAW_MANIFEST_URL}")
        if args.notes:
            print(f"  notes: {args.notes}")

    finally:
        # Cleanup
        try:
            shutil.rmtree(work, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
