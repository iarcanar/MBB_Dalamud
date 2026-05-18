"""MBB-side cloud sync for npc.json (Phase A — public + plaintext).

Public API:
    check_for_update(local_version: str) → UpdateCheckResult
        Fetch the cloud manifest and decide if remote is newer than local.
    download_and_verify(manifest: CloudManifest) → dict
        Download the data blob, verify sha256, parse JSON, return dict.

Pairs with the existing `_MergeDiff` / `_MergeDialog` in npc_manager_panel.py —
the caller hands the returned dict (full npc.json structure) into _MergeDiff
along with the local database, then surfaces the cherry-pick UI.

Phase A constraints:
    - No encryption (manifest + data fetched as plaintext via raw URL)
    - No auth (public repo, anonymous HTTPS)
    - All stdlib (urllib, hashlib, json) — no extra deps
    - Same urllib pattern used by translator + updater already

Future Phase B will add: AES-256-GCM decrypt, PAT auth, key rotation.
The module structure here is designed so Phase B is a straight swap of
`_fetch_bytes()` (add auth header) + `_extract_data()` (add decrypt) —
no callers should need to change.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("npc-cloud-sync")


# ────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────
MANIFEST_URL = "https://raw.githubusercontent.com/iarcanar/MBB_NPCData/main/manifest.json"
USER_AGENT = "MBB-NPCSync/1.0"
HTTP_TIMEOUT_S = 15.0
MAX_DATA_BYTES = 5 * 1024 * 1024  # 5MB cap — sanity bound, real data ~100KB

# Local cache (last known good manifest — used as offline fallback display)
def _cache_dir() -> str:
    """Per-user AppData dir (Windows) for caching last-fetched manifest."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "MBB_Dalamud", "cloud_cache")
    os.makedirs(d, exist_ok=True)
    return d


CACHED_MANIFEST_PATH = lambda: os.path.join(_cache_dir(), "last_manifest.json")


# ────────────────────────────────────────────────────────────────────
# Data models
# ────────────────────────────────────────────────────────────────────
@dataclass
class CloudManifest:
    """Parsed manifest.json from the cloud. All fields required except
    release_notes_th + stats (graceful degrade if missing)."""
    schema_version: int
    data_version: str
    released_at: str
    data_url: str
    data_sha256: str
    data_size_bytes: int
    min_mbb_version: str
    stats: dict = field(default_factory=dict)
    release_notes_th: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "CloudManifest":
        # Required fields — raise KeyError if missing (caught by caller as error state)
        return cls(
            schema_version=int(d["schema_version"]),
            data_version=str(d["data_version"]),
            released_at=str(d["released_at"]),
            data_url=str(d["data_url"]),
            data_sha256=str(d["data_sha256"]).lower(),
            data_size_bytes=int(d["data_size_bytes"]),
            min_mbb_version=str(d.get("min_mbb_version", "0.0.0")),
            stats=dict(d.get("stats") or {}),
            release_notes_th=str(d.get("release_notes_th", "")),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "data_version": self.data_version,
            "released_at": self.released_at,
            "data_url": self.data_url,
            "data_sha256": self.data_sha256,
            "data_size_bytes": self.data_size_bytes,
            "min_mbb_version": self.min_mbb_version,
            "stats": self.stats,
            "release_notes_th": self.release_notes_th,
        }


@dataclass
class UpdateCheckResult:
    """Outcome of check_for_update — fed to UI to render the right state.

    States:
        has_update=True, manifest=<filled>, error=None
            → cloud has a newer version; surface "Download v X" button
        has_update=False, manifest=<filled>, error=None
            → local is current; surface "Up to date" message
        has_update=False, manifest=None, error="..."
            → fetch failed; surface error toast (offline / 404 / parse fail)
    """
    has_update: bool
    manifest: Optional[CloudManifest]
    error: Optional[str]
    local_version: str
    checked_at: float = field(default_factory=time.time)


# ────────────────────────────────────────────────────────────────────
# Low-level fetch (Phase B swap point: add auth header here)
# ────────────────────────────────────────────────────────────────────
def _fetch_bytes(url: str, max_size: int = MAX_DATA_BYTES) -> bytes:
    """GET url → bytes. Enforces a max size to prevent runaway downloads.

    Phase A: no auth headers. Phase B will add `Authorization: token <PAT>`
    + may handle 401/403 here.

    Note on size validation: we DO NOT pre-check Content-Length because
    GitHub raw can report a header size that differs from the actual
    transferred body (e.g., when transport-level transforms apply). Instead
    we rely on a hard cap on actual bytes read. Add some slack to max_size
    (caller passes data_size_bytes + small buffer) so legitimate downloads
    near the manifest's stated size aren't false-positive rejected.
    """
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        # Disable cache so a stale CDN copy doesn't mask a fresh release
        "Cache-Control": "no-cache",
        # Get raw bytes without auto-decompression so size + sha256 are deterministic
        "Accept-Encoding": "identity",
    })
    with urlopen(req, timeout=HTTP_TIMEOUT_S) as r:
        data = r.read(max_size + 1)
        if len(data) > max_size:
            raise ValueError(f"Download exceeded max_size cap of {max_size} bytes")
        return data


# ────────────────────────────────────────────────────────────────────
# Version comparison
# ────────────────────────────────────────────────────────────────────
def version_tuple(v: str) -> tuple[int, ...]:
    """'2026.05.20' → (2026, 5, 20). '2026.05.20.2' → (2026, 5, 20, 2).
    Strips non-numeric segments. Empty → (0,)."""
    if not v:
        return (0,)
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(remote: str, local: str) -> bool:
    """True if remote version is strictly newer than local. If local is empty
    (never synced), treat any remote as newer so the user gets the first sync."""
    if not remote:
        return False
    if not local:
        return True
    try:
        return version_tuple(remote) > version_tuple(local)
    except Exception:
        return False


# ────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────
def check_for_update(local_version: str) -> UpdateCheckResult:
    """Fetch the cloud manifest + decide if there's an update for us.

    Args:
        local_version: the data_version this client last synced (from settings).
                       Empty string means "never synced" → any remote = update.

    Returns:
        UpdateCheckResult — has_update / manifest / error fields drive UI.

    Side effects: writes a cached copy of the fetched manifest so we can show
    something useful while offline.
    """
    log.info(f"[cloud-sync] checking for update (local v{local_version or '?'})")
    # Cache-bust the manifest URL — raw.githubusercontent.com can cache for
    # up to ~5 minutes per CDN edge, which would make "just-published" updates
    # invisible until cache expires. The data file is sha256-verified so we
    # don't need to bust it (a stale data + correct manifest = sha mismatch
    # → safe abort). Manifest itself MUST be fresh to detect new versions.
    cache_bust_url = f"{MANIFEST_URL}?_t={int(time.time())}"
    try:
        raw = _fetch_bytes(cache_bust_url, max_size=64 * 1024)  # 64KB cap on manifest
        d = json.loads(raw.decode("utf-8"))
        manifest = CloudManifest.from_dict(d)
    except HTTPError as e:
        log.warning(f"[cloud-sync] HTTPError {e.code} fetching manifest")
        return UpdateCheckResult(
            has_update=False, manifest=None,
            error=f"HTTP {e.code} จาก cloud server",
            local_version=local_version,
        )
    except URLError as e:
        log.warning(f"[cloud-sync] network error: {e.reason}")
        return UpdateCheckResult(
            has_update=False, manifest=None,
            error=f"เครือข่ายขัดข้อง — {e.reason}",
            local_version=local_version,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log.error(f"[cloud-sync] manifest parse failed: {e}")
        return UpdateCheckResult(
            has_update=False, manifest=None,
            error=f"manifest จาก cloud อ่านไม่ออก — {e}",
            local_version=local_version,
        )
    except Exception as e:
        log.error(f"[cloud-sync] unexpected fetch error: {e}", exc_info=True)
        return UpdateCheckResult(
            has_update=False, manifest=None,
            error=f"ดึง manifest ล้มเหลว — {e}",
            local_version=local_version,
        )

    # Cache the manifest (best-effort, never fatal)
    try:
        with open(CACHED_MANIFEST_PATH(), "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.debug(f"[cloud-sync] manifest cache write failed: {e}")

    newer = is_newer(manifest.data_version, local_version)
    log.info(
        f"[cloud-sync] manifest OK: cloud v{manifest.data_version}, "
        f"local v{local_version or '?'} → {'UPDATE' if newer else 'current'}"
    )
    return UpdateCheckResult(
        has_update=newer, manifest=manifest, error=None,
        local_version=local_version,
    )


def download_and_verify(manifest: CloudManifest) -> dict:
    """Download the data blob referenced by manifest, verify sha256, parse JSON.

    Raises:
        ValueError if sha256 mismatch (don't trust the data — could be in-flight
                   corruption or a tampered mirror)
        urllib.error.URLError / HTTPError on network/server failure
        json.JSONDecodeError if the blob isn't valid JSON

    The caller (NPC Manager) hands the returned dict into _MergeDiff(local, cloud)
    for the cherry-pick merge dialog.
    """
    log.info(f"[cloud-sync] downloading v{manifest.data_version} ({manifest.data_size_bytes} bytes)")
    blob = _fetch_bytes(manifest.data_url, max_size=manifest.data_size_bytes + 1024)
    actual_sha = hashlib.sha256(blob).hexdigest()
    if actual_sha.lower() != manifest.data_sha256.lower():
        raise ValueError(
            f"sha256 mismatch — expected {manifest.data_sha256}, got {actual_sha}. "
            f"Download corrupted OR cloud manifest stale; do not merge."
        )
    log.info(f"[cloud-sync] sha256 verified: {actual_sha[:16]}...")
    parsed = json.loads(blob.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"data is not a dict (got {type(parsed).__name__})")
    return parsed


def load_cached_manifest() -> Optional[CloudManifest]:
    """Load the last-successfully-fetched manifest from disk. Used to show
    "last synced: X days ago" while offline. Returns None if no cache yet."""
    path = CACHED_MANIFEST_PATH()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return CloudManifest.from_dict(json.load(f))
    except Exception as e:
        log.debug(f"[cloud-sync] cached manifest read failed: {e}")
        return None


# ────────────────────────────────────────────────────────────────────
# CLI smoke test — `python npc_cloud_sync.py` from python-app/
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(f"Fetching manifest from {MANIFEST_URL}...")
    result = check_for_update(local_version="")
    if result.error:
        print(f"ERROR: {result.error}")
        raise SystemExit(1)
    m = result.manifest
    print(f"\nCloud manifest:")
    print(f"  version:  {m.data_version}")
    print(f"  released: {m.released_at}")
    print(f"  stats:    {m.stats}")
    print(f"  size:     {m.data_size_bytes} bytes")
    print(f"  sha256:   {m.data_sha256}")
    print(f"  notes:    {m.release_notes_th}")

    print(f"\nDownloading + verifying...")
    data = download_and_verify(m)
    print(f"OK — parsed {len(data.get('main_characters', []))} main characters")
