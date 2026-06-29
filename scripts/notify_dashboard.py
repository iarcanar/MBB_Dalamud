#!/usr/bin/env python3
"""
notify_dashboard.py — push the latest commit's status/version to the MBB web
admin dashboard (POST /api/dev-status). Invoked by the git post-commit hook.

SECURITY: sends ONLY git metadata + version.py version — never file contents,
never .env. The endpoint secret is read from the environment or a gitignored
`.dev_hook` file; it is NEVER hardcoded here and never printed.

Config (env var OR `.dev_hook` KEY=VALUE at repo root; env wins):
    MBB_DASHBOARD_URL     default https://mbb-ffxiv.vercel.app
    MBB_DASHBOARD_SECRET  required (= DEV_STATUS_SECRET or ADMIN_SECRET on the web)

Best-effort + non-blocking: any failure prints a short notice and exits 0 so it
can never block a commit.
"""
import json
import os
import subprocess
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_URL = "https://mbb-ffxiv.vercel.app"
REPO_SLUG = "iarcanar/MBB_Dalamud"


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", REPO_ROOT, *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return ""


def _load_dev_hook() -> dict:
    """Parse the gitignored .dev_hook (KEY=VALUE). Returns {} if absent."""
    cfg = {}
    path = os.path.join(REPO_ROOT, ".dev_hook")
    if not os.path.exists(path):
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except Exception:
        pass
    return cfg


def _read_version() -> str:
    path = os.path.join(REPO_ROOT, "python-app", "version.py")
    try:
        import re
        with open(path, "r", encoding="utf-8") as f:
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
            return m.group(1) if m else ""
    except Exception:
        return ""


def main() -> int:
    cfg = _load_dev_hook()
    secret = os.environ.get("MBB_DASHBOARD_SECRET") or cfg.get("MBB_DASHBOARD_SECRET")
    url = (os.environ.get("MBB_DASHBOARD_URL") or cfg.get("MBB_DASHBOARD_URL") or DEFAULT_URL).rstrip("/")

    if not secret:
        print("[notify_dashboard] no secret configured — skipped.")
        print("[notify_dashboard] copy .dev_hook.example -> .dev_hook and set MBB_DASHBOARD_SECRET.")
        return 0

    payload = {
        "repo": REPO_SLUG,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git("rev-parse", "--short", "HEAD"),
        "message": _git("log", "-1", "--pretty=%s"),
        "committedAt": _git("log", "-1", "--pretty=%cI"),
        "version": _read_version(),
    }
    if not payload["commit"]:
        print("[notify_dashboard] no commit found — skipped.")
        return 0

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/dev-status",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "x-dev-secret": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if 200 <= resp.status < 300:
                print(f"[notify_dashboard] ✓ {payload['commit']} v{payload['version']} -> {url}")
            else:
                print(f"[notify_dashboard] dashboard returned HTTP {resp.status}")
    except Exception as e:
        # Never fail a commit over a notify problem.
        print(f"[notify_dashboard] could not reach dashboard ({e.__class__.__name__}) — skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
