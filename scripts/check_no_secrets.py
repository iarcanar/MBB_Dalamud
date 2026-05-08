"""Pre-deploy secrets scanner. Run after every build, BEFORE packaging the
release zip — aborts if anything looks like a leaked credential made it into
the bundle. Catches the "oops we copied .env into _internal/" mistake before
it reaches GitHub Releases.

Usage:
    python scripts/check_no_secrets.py <build_dir>

Exit codes:
    0  clean — safe to deploy
    1  violations found — DO NOT deploy
    2  usage error

Hooked from python-app/mbb.spec post-build so every PyInstaller run runs this
automatically. Also runnable standalone if a human wants to scan a folder.

What we look for:
    * filenames matching .env (except .env.example, which is a template)
    * filenames ending in .key / .pem (private keys)
    * file CONTENTS matching the Gemini API key shape (AIza + 35 chars)
    * other common secret token shapes (Stripe, GitHub PAT, Slack, etc.)

We deliberately don't print the actual matched value — only the filename +
the line where it was found. Printing the secret again in the failure log
would re-leak it into CI/build artifacts.
"""
from __future__ import annotations

import os
import re
import sys


# ─── Patterns we refuse to ship ───
# Gemini/Google API key: "AIza" + 35 chars in [A-Za-z0-9_-]
GEMINI_KEY_RE = re.compile(rb"AIza[A-Za-z0-9_\-]{35}")

# Other common credential shapes — catch-all for accidental ENV var leaks
SUSPICIOUS_PATTERNS = [
    ("Stripe live key",   re.compile(rb"sk_live_[A-Za-z0-9]{24,}")),
    ("GitHub PAT classic", re.compile(rb"ghp_[A-Za-z0-9]{36}")),
    ("GitHub PAT new",    re.compile(rb"github_pat_[A-Za-z0-9_]{80,}")),
    ("Slack token",       re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("AWS access key",    re.compile(rb"AKIA[A-Z0-9]{16}")),
    ("Anthropic key",     re.compile(rb"sk-ant-[A-Za-z0-9_\-]{32,}")),
]

# Only scan text-like files — avoid binary noise. PyInstaller bundles a lot
# of .pyd / .dll / .so files; reading those byte-by-byte for our patterns
# triggers false positives on random byte sequences.
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".txt", ".json", ".md", ".cfg", ".ini",
    ".yaml", ".yml", ".toml", ".js", ".ts", ".html", ".css",
    ".bat", ".sh", ".ps1", ".env", ".log", ".csv", ".xml",
}

# Files that legitimately contain placeholder patterns we'd otherwise flag.
EXEMPT_BASENAMES = {".env.example", "check_no_secrets.py"}

# Path-fragment allowlist for known-safe bundles. These ship public root CA
# certificates (Mozilla bundle, gRPC roots) which our naive ".pem = private
# key" check would otherwise flag. Match is substring-based against the
# normalized relative path so it works on Windows + Unix.
SAFE_PATH_FRAGMENTS = (
    "certifi/cacert.pem",      # Mozilla CA bundle bundled by certifi
    "grpc/_cython/_credentials/roots.pem",  # gRPC public root certs
    "botocore/cacert.pem",     # AWS SDK CA bundle (in case)
)


def is_text_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in TEXT_EXTENSIONS


def scan_file(path: str) -> list:
    """Return list of (pattern_label, line_number) — empty when clean."""
    hits = []
    try:
        with open(path, "rb") as f:
            content = f.read()
    except Exception:
        return hits  # unreadable → not our problem at this layer
    if GEMINI_KEY_RE.search(content):
        for i, line in enumerate(content.splitlines(), 1):
            if GEMINI_KEY_RE.search(line):
                hits.append(("Gemini/Google API key", i))
                break
    for label, pat in SUSPICIOUS_PATTERNS:
        if pat.search(content):
            for i, line in enumerate(content.splitlines(), 1):
                if pat.search(line):
                    hits.append((label, i))
                    break
    return hits


def _is_safe_path(rel_path: str) -> bool:
    """True if this path matches one of our known-safe allowlist fragments."""
    norm = rel_path.replace("\\", "/")
    return any(frag in norm for frag in SAFE_PATH_FRAGMENTS)


def scan_directory(root: str) -> list:
    """Walk root, yielding every violation."""
    violations = []  # list of (rel_path, kind, line_number)
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            base = os.path.basename(name)
            if base in EXEMPT_BASENAMES:
                continue
            # Filename-based flags
            if base.startswith(".env"):
                violations.append((rel, "filename: .env file shipped", 0))
                continue  # don't also content-scan; the filename alone is fatal
            if name.endswith(".key") or name.endswith(".pem"):
                if not _is_safe_path(rel):
                    violations.append((rel, "filename: private key shipped", 0))
                continue
            # Content scan
            if is_text_file(full):
                for pattern_label, line_no in scan_file(full):
                    violations.append((rel, pattern_label, line_no))
    return violations


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: check_no_secrets.py <build_dir>", file=sys.stderr)
        sys.exit(2)
    target = sys.argv[1]
    if not os.path.isdir(target):
        print(f"[no-secrets] not a directory: {target}", file=sys.stderr)
        sys.exit(2)

    print(f"[no-secrets] scanning {target}…")
    violations = scan_directory(target)
    if not violations:
        print("[no-secrets] ✓ clean — no leaked secrets")
        sys.exit(0)

    print(f"[no-secrets] ✗ FOUND {len(violations)} violation(s):")
    for rel, kind, line in violations:
        if line:
            print(f"  • {rel}  →  {kind}  (line {line})")
        else:
            print(f"  • {rel}  →  {kind}")
    print()
    print("[no-secrets] BUILD ABORTED — investigate and fix before deploying")
    print("[no-secrets] (intentionally not printing the matched secret value")
    print("[no-secrets]  to avoid re-leaking it into CI logs)")
    sys.exit(1)


if __name__ == "__main__":
    main()
