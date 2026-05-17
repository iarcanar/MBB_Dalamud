"""MBB Updater — standalone in-app updater for Magicite Babel Bridge.

Lives at <MBB folder>/MBB-Updater.exe alongside the main MBB.exe. User runs it
to pull the latest GitHub release and apply it in-place, preserving all user
data. The .env (API key) lives in %LOCALAPPDATA%/MBB_Dalamud/ — outside the
install folder — so it's untouched no matter what.

Two-stage launch (mandatory because Windows locks the running .exe):

    Stage 1 — running from MBB folder:
        1. Copy self → %TEMP%/MBB-Updater-Active.exe
        2. Spawn that copy with --stage2 --target <MBB folder>, then exit
           (so the original exe in MBB/ is unlocked and can be replaced).

    Stage 2 — running from %TEMP%, file-handle on original released:
        1. Show UI, detect local version + GitHub manifest
        2. On user click: download zip → wait MBB exit → backup user data →
           extract zip → restore user data → launch MBB → close updater

User data preserved across the swap (kept OUTSIDE the zip):
    npc.json, npc_images/, settings.json, backups/, .env (in MBB folder if any)
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import math
import tkinter as tk
from tkinter import ttk

# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────
GITHUB_API_URL = "https://api.github.com/repos/iarcanar/MBB_Dalamud/releases/latest"
TEMP_EXE_NAME = "MBB-Updater-Active.exe"
USER_AGENT = "MBB-Updater/1.0"
ARG_STAGE2 = "--stage2"
ARG_TARGET = "--target"
WIN_DETACHED = 0x00000008  # subprocess.DETACHED_PROCESS

# Files kept across the update — these live OUTSIDE the zip's bundled defaults.
# Top-level entries inside MBB/ that survive are listed here. Anything else in
# MBB/ (MBB.exe, _internal/, plugin/) gets replaced by the zip.
PRESERVED_PATHS = [
    "npc.json",          # user-customized character database
    "npc_images",        # user-uploaded avatars (folder)
    "settings.json",     # font/theme/UI preferences
    "backups",           # NPCDataManager auto-backups
    ".env",              # API key fallback (real one is in AppData)
    "MBB-Updater.log",   # our own log — keep across runs
]


# ────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────
_log_path: str = ""

def _log(msg: str) -> None:
    """Append to log file + stderr. Never raises."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        if _log_path:
            with open(_log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass
    try:
        sys.stderr.write(line + "\n")
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# Stage 1 — copy self to temp + relaunch
# ────────────────────────────────────────────────────────────────────
def get_self_path() -> str:
    """Path to the currently-running updater (frozen .exe or .py source)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def stage1_relaunch_from_temp() -> None:
    """Copy self → %TEMP%, spawn detached, exit. Stage 2 takes over from a
    location that's NOT inside the MBB folder — so we can replace anything
    there, including the original updater.exe."""
    my_path = get_self_path()
    target_dir = os.path.dirname(my_path)
    temp_path = os.path.join(tempfile.gettempdir(), TEMP_EXE_NAME)
    try:
        # If a previous Stage-2 instance left a stale copy, overwrite is fine
        # (file handle is no longer held once that process exited).
        shutil.copyfile(my_path, temp_path)
    except Exception as e:
        # Nothing else we can do — surface to user
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "MBB Updater",
                f"ไม่สามารถคัดลอกไฟล์ไปยัง temp:\n{e}\n\n"
                f"ตรวจสอบสิทธิ์การเขียนหรือพื้นที่ดิสก์",
            )
        except Exception:
            pass
        sys.exit(1)
    args = [temp_path, ARG_STAGE2, ARG_TARGET, target_dir]
    creationflags = WIN_DETACHED if sys.platform == "win32" else 0
    subprocess.Popen(args, creationflags=creationflags, close_fds=True)
    sys.exit(0)


def get_target_dir_from_args() -> str:
    """Read --target <path> from argv. Empty string if missing/malformed."""
    if ARG_TARGET in sys.argv:
        idx = sys.argv.index(ARG_TARGET)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return ""


# ────────────────────────────────────────────────────────────────────
# Version detection + GitHub manifest
# ────────────────────────────────────────────────────────────────────
def detect_local_version(target_dir: str) -> str:
    """Read __version__ from version.py inside _internal/ (PyInstaller layout)
    or from the project root (dev mode). Returns empty string if not found."""
    candidates = [
        os.path.join(target_dir, "_internal", "version.py"),
        os.path.join(target_dir, "version.py"),
    ]
    for vfile in candidates:
        if not os.path.exists(vfile):
            continue
        try:
            with open(vfile, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                return m.group(1)
        except Exception as e:
            _log(f"detect_local_version error reading {vfile}: {e}")
    return ""


def fetch_github_release() -> dict:
    """Fetch GitHub /releases/latest. Raises URLError/HTTPError on net failure."""
    req = Request(
        GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_release(data: dict) -> dict:
    """Extract version + zip URL + sha url + size + notes from release JSON."""
    tag = (data.get("tag_name") or "").lstrip("vV")
    notes = data.get("body") or ""
    zip_url = ""
    sha_url = ""
    zip_size = 0
    for asset in data.get("assets") or []:
        name = (asset.get("name") or "").lower()
        url = asset.get("browser_download_url") or ""
        size = int(asset.get("size") or 0)
        if name.endswith(".sha256") or name.endswith(".sha256.txt"):
            sha_url = url
        elif name.endswith(".zip") and not zip_url:
            zip_url = url
            zip_size = size
    return {
        "version": tag,
        "notes": notes,
        "zip_url": zip_url,
        "sha_url": sha_url,
        "zip_size": zip_size,
    }


def version_tuple(v: str) -> tuple:
    """'1.8.5' / 'v1.8.5' / '1.8.5-rc1' → (1, 8, 5). Returns (0,) on garbage."""
    if not v:
        return (0,)
    nums = re.findall(r"\d+", v)
    return tuple(int(x) for x in nums) if nums else (0,)


def is_newer(remote: str, local: str) -> bool:
    """True when remote is strictly newer than local. If local is unknown
    (empty), assume an update is available so the user isn't stranded."""
    if not remote:
        return False
    if not local:
        return True
    try:
        return version_tuple(remote) > version_tuple(local)
    except Exception:
        return False


# ────────────────────────────────────────────────────────────────────
# Download + verify
# ────────────────────────────────────────────────────────────────────
def download_with_progress(url: str, dest: str, progress_cb) -> int:
    """Stream URL to dest, calling progress_cb(downloaded, total)."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as r:
        total = int(r.headers.get("Content-Length", "0") or "0")
        downloaded = 0
        chunk = 64 * 1024
        with open(dest, "wb") as f:
            while True:
                buf = r.read(chunk)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                progress_cb(downloaded, total)
    return downloaded


def fetch_text(url: str) -> str:
    """GET URL → decoded text. For sha256 sidecar."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(64 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ────────────────────────────────────────────────────────────────────
# Defense-in-depth: refuse to apply a poisoned release zip
# ────────────────────────────────────────────────────────────────────
# Note: the AUTHORITATIVE secrets scan happens at build time via
# scripts/check_no_secrets.py — that's what stops a leak from ever reaching
# GitHub Releases in the first place. The check below is a redundant user-
# side safeguard so a compromised release host can't push secrets onto the
# user's disk. Cheap to do, useful insurance.

def zip_contains_secrets(zip_file: str) -> list:
    """Refuse-list scan of zip contents. Returns suspicious member paths.

    A real release zip should contain MBB.exe + _internal/ + plugin/ — never
    a .env file. If we see one, the release is poisoned (or someone packaged
    by mistake) — we ABORT before extracting, otherwise we'd splatter someone
    else's API key onto the user's disk. Allows .env.example (template, no key)."""
    suspicious = []
    try:
        with zipfile.ZipFile(zip_file, "r") as zf:
            for name in zf.namelist():
                lower = name.lower().replace("\\", "/")
                base = lower.rsplit("/", 1)[-1]
                # Reject anything starting with .env EXCEPT .env.example (template)
                if base.startswith(".env") and base != ".env.example":
                    suspicious.append(name)
                # Also reject any *.key file — same idea, common credential extension
                elif base.endswith(".key") or base.endswith(".pem"):
                    suspicious.append(name)
    except Exception as e:
        _log(f"zip_contains_secrets error: {e}")
    return suspicious


# ────────────────────────────────────────────────────────────────────
# MBB process control
# ────────────────────────────────────────────────────────────────────
def find_mbb_pids(target_dir: str) -> list:
    """List of PIDs for MBB.exe inside target_dir. Empty if not running or
    psutil missing (we ship psutil with the updater, but be defensive)."""
    pids = []
    try:
        import psutil
    except ImportError:
        _log("psutil not bundled — skipping running-MBB detection")
        return pids
    target_exe = os.path.normcase(os.path.join(target_dir, "MBB.exe"))
    for p in psutil.process_iter(["exe"]):
        try:
            exe = p.info.get("exe")
            if exe and os.path.normcase(exe) == target_exe:
                pids.append(p.pid)
        except Exception:
            continue
    return pids


def wait_or_kill_mbb(target_dir: str, soft_timeout: float = 8.0) -> None:
    """Wait soft_timeout seconds for MBB to exit, then force-terminate any
    leftovers. Most users will close MBB themselves before running updater;
    this is a safety net."""
    pids = find_mbb_pids(target_dir)
    if not pids:
        return
    _log(f"MBB running pids={pids}, waiting up to {soft_timeout}s")
    deadline = time.time() + soft_timeout
    while time.time() < deadline:
        if not find_mbb_pids(target_dir):
            _log("MBB exited gracefully")
            return
        time.sleep(0.5)
    _log("MBB still running after soft timeout — force-terminating")
    try:
        import psutil
    except ImportError:
        return
    for pid in find_mbb_pids(target_dir):
        try:
            p = psutil.Process(pid)
            p.terminate()
            try:
                p.wait(timeout=3)
            except psutil.TimeoutExpired:
                p.kill()
        except Exception as e:
            _log(f"force-kill pid={pid} failed: {e}")


# ────────────────────────────────────────────────────────────────────
# Backup → extract → restore
# ────────────────────────────────────────────────────────────────────
def backup_user_data(target_dir: str, backup_dir: str) -> list:
    """Copy each PRESERVED entry from target_dir → backup_dir. Returns the
    list of names actually backed up (so we can show user how many bytes/dirs
    were preserved)."""
    os.makedirs(backup_dir, exist_ok=True)
    done = []
    for name in PRESERVED_PATHS:
        src = os.path.join(target_dir, name)
        if not os.path.exists(src):
            continue
        dst = os.path.join(backup_dir, name)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copyfile(src, dst)
            done.append(name)
        except Exception as e:
            _log(f"backup {name} failed: {e}")
    return done


def stage_extract(zip_file: str, stage_dir: str, progress_cb) -> None:
    """Extract zip into a pristine stage_dir. Crashing here is recoverable
    — target_dir hasn't been touched yet."""
    with zipfile.ZipFile(zip_file, "r") as zf:
        members = zf.namelist()
        total = len(members)
        for i, m in enumerate(members):
            zf.extract(m, stage_dir)
            if i % 25 == 0:
                progress_cb(i, total)
        progress_cb(total, total)


def find_zip_root(stage_dir: str) -> str:
    """The release zip is normally MBB/MBB.exe + MBB/_internal/ + ...
    Find that MBB/ subdir. Returns "" if structure unrecognized."""
    # Direct: MBB.exe at stage_dir top level
    if os.path.exists(os.path.join(stage_dir, "MBB.exe")):
        return stage_dir
    # One level deep (the common case): stage_dir/MBB/MBB.exe
    for entry in os.listdir(stage_dir):
        full = os.path.join(stage_dir, entry)
        if os.path.isdir(full) and os.path.exists(os.path.join(full, "MBB.exe")):
            return full
    return ""


def apply_staged_files(stage_root: str, target_dir: str) -> None:
    """Replace target_dir contents with stage_root contents, EXCEPT entries
    in PRESERVED_PATHS (we'll restore those from backup right after).

    For directories like _internal/, we do rmtree+copytree atomically per
    entry. For files like MBB.exe, simple overwrite. Raises on any failure
    so caller can fall back to restoring user data."""
    for entry in os.listdir(stage_root):
        if entry in PRESERVED_PATHS:
            # User-data slot — bundled defaults stay in _internal/, restore wins
            continue
        src = os.path.join(stage_root, entry)
        dst = os.path.join(target_dir, entry)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)


def restore_user_data(backup_dir: str, target_dir: str) -> None:
    """Copy preserved entries back from backup → target. Idempotent — if zip
    happened to bundle one of these paths, we overwrite with user's version."""
    if not os.path.exists(backup_dir):
        return
    for name in PRESERVED_PATHS:
        src = os.path.join(backup_dir, name)
        if not os.path.exists(src):
            continue
        dst = os.path.join(target_dir, name)
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copyfile(src, dst)
        except Exception as e:
            _log(f"restore {name} failed: {e}")


def launch_mbb(target_dir: str):
    """Start MBB.exe inside target_dir, detached so updater can exit freely.
    Returns Popen object or None if MBB.exe is missing."""
    exe = os.path.join(target_dir, "MBB.exe")
    if not os.path.exists(exe):
        _log(f"launch_mbb: MBB.exe not found at {exe}")
        return None
    creationflags = WIN_DETACHED if sys.platform == "win32" else 0
    return subprocess.Popen(
        [exe], cwd=target_dir, creationflags=creationflags, close_fds=True
    )


# ────────────────────────────────────────────────────────────────────
# Tkinter UI
# ────────────────────────────────────────────────────────────────────
class UpdaterApp:
    """Single-window Tkinter UI for the updater. State drives the bottom
    button (Update Now → Launch MBB → Close).

    UI layout (640×540):
      ┌────────────────────────────────────┐
      │       MBB Updater (24pt bold)      │
      │   Magicite Babel Bridge (12pt dim) │
      ├────────────────────────────────────┤
      │       เวอร์ชั่นของคุณ                │
      │         v 1.8.6 (40pt bold)         │
      ├────────────────────────────────────┤
      │   [spinner] ตรวจสอบ... (animated)  │
      │       ↓ becomes status badge        │
      │  ✓ คุณใช้เวอร์ชั่นล่าสุดแล้ว         │
      └────────────────────────────────────┘
    """

    # Theme colors — match MBB's "Carbon" palette
    BG = "#0d1117"
    FG = "#e6edf3"
    DIM = "#7d8590"
    SURFACE = "#161b22"
    SURFACE2 = "#1c2128"
    BORDER = "#30363d"
    ACCENT = "#58a6ff"
    ACCENT_DIM = "#1f6feb"
    SUCCESS = "#3fb950"
    SUCCESS_BG = "#0d2818"
    WARN = "#f59e0b"
    WARN_BG = "#2a1c0a"
    ERR = "#f85149"
    ERR_BG = "#2d0e0e"

    def __init__(self, target_dir: str):
        self.target_dir = target_dir
        self.local_version: str = ""
        self.remote: dict = {}
        self.zip_path: str = ""
        self.backup_dir: str = ""

        # Animation state
        self._spinner_angle = 0
        self._spinner_after_id = None
        self._dots_after_id = None
        self._dots_count = 0
        self._dots_base_text = ""

        self.root = tk.Tk()
        self.root.title("MBB Updater")
        self.root.geometry("640x620")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        # Bind X-button close → _on_close so spinner/dots timers get cancelled.
        # Without this, closing via the OS title-bar destroys the root with
        # pending `after` callbacks still queued — they fire on the destroyed
        # widget and raise TclError noise (or worse, crash on shutdown).
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            icon_path = self._resolve_asset("mbb_icon.ico")
            if icon_path and os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # Header logo (mbb_meteor.png) — must hold a reference on self or
        # Tkinter garbage-collects the PhotoImage and the label shows blank.
        self._logo_photo = self._load_logo()

        # Larger, more modern type scale
        self.font_title = ("Anuphan", 24, "bold")
        self.font_subtitle = ("Anuphan", 12)
        self.font_section = ("Anuphan", 11)
        self.font_version_huge = ("Anuphan", 40, "bold")
        self.font_status = ("Anuphan", 16, "bold")
        self.font_body = ("Anuphan", 12)
        self.font_btn = ("Anuphan", 13, "bold")
        self.font_small = ("Anuphan", 10)

        self._build_ui()
        self.root.after(150, self._start_check)

    # ─── Asset resolution (dev .py vs frozen .exe) ───
    def _resolve_asset(self, name: str) -> str:
        """Look up a bundled asset in MEIPASS (frozen) or fall back to the
        repo's python-app/assets/ during dev. Returns "" if not found.

        Defense-in-depth: reject absolute paths or any "../" components in
        `name`. Today every caller passes a literal filename, but a future
        caller forwarding user input could traverse out of the asset dirs.
        """
        if not name or os.path.isabs(name) or ".." in name.replace("\\", "/").split("/"):
            return ""
        # PyInstaller frozen layout — datas are extracted next to the running .exe
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            cand = os.path.join(meipass, name)
            if os.path.exists(cand):
                return cand
        # Dev mode — repo layout: <repo>/updater/updater.py + <repo>/python-app/assets/
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cand = os.path.join(repo_root, "python-app", "assets", name)
        if os.path.exists(cand):
            return cand
        # Last fallback — installed MBB folder (target_dir/_internal/assets)
        cand = os.path.join(self.target_dir, "_internal", "assets", name)
        if os.path.exists(cand):
            return cand
        return ""

    def _load_logo(self):
        """Load mbb_meteor.png subsampled to ~150×100 for the header.

        Tk's built-in PhotoImage handles PNG natively in Py3 (no PIL needed —
        we exclude PIL from updater.spec to keep the exe small). subsample(N)
        downsamples by integer factor — for 308×201 source, subsample(2) gives
        154×100, a clean fit above the title text.
        """
        path = self._resolve_asset("mbb_meteor.png")
        if not path:
            return None
        try:
            img = tk.PhotoImage(file=path)
            return img.subsample(2, 2)
        except Exception as e:
            _log(f"_load_logo failed: {e}")
            return None

    def _build_ui(self) -> None:
        # ── Header ──
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", pady=(20, 0))

        # Logo (above title) — keeps visual continuity with the main MBB UI
        if self._logo_photo is not None:
            tk.Label(
                header, image=self._logo_photo, bg=self.BG, bd=0,
            ).pack(pady=(0, 8))

        tk.Label(
            header, text="MBB Updater",
            font=self.font_title, fg=self.FG, bg=self.BG,
        ).pack()

        tk.Label(
            header, text="Magicite Babel Bridge",
            font=self.font_subtitle, fg=self.DIM, bg=self.BG,
        ).pack(pady=(2, 0))

        # Thin accent divider
        sep = tk.Frame(self.root, bg=self.BORDER, height=1)
        sep.pack(fill="x", padx=80, pady=(20, 0))

        # ── Current version (BIG centered) ──
        ver_section = tk.Frame(self.root, bg=self.BG)
        ver_section.pack(fill="x", pady=(22, 4))

        tk.Label(
            ver_section, text="เวอร์ชั่นของคุณ",
            font=self.font_section, fg=self.DIM, bg=self.BG,
        ).pack()

        self.lbl_local_huge = tk.Label(
            ver_section, text="—",
            font=self.font_version_huge, fg=self.FG, bg=self.BG,
        )
        self.lbl_local_huge.pack(pady=(4, 0))

        # ── Status badge / spinner area ──
        # Single container that swaps between spinner+text (during check)
        # and a colored status pill (after check completes).
        self.status_card = tk.Frame(
            self.root, bg=self.SURFACE2,
            highlightthickness=0,
        )
        self.status_card.pack(fill="x", padx=40, pady=(24, 0), ipady=18)

        self.status_inner = tk.Frame(self.status_card, bg=self.SURFACE2)
        self.status_inner.pack()

        # Spinner canvas (drawn here, hidden when status badge shows)
        self.spinner_canvas = tk.Canvas(
            self.status_inner, width=28, height=28,
            bg=self.SURFACE2, highlightthickness=0,
        )
        self.spinner_canvas.pack(side="left", padx=(0, 12))

        self.lbl_status_text = tk.Label(
            self.status_inner, text="",
            font=self.font_status, fg=self.ACCENT, bg=self.SURFACE2,
        )
        self.lbl_status_text.pack(side="left")

        # Secondary line for sub-info / changelog notes
        self.lbl_status_sub = tk.Label(
            self.status_card, text="",
            font=self.font_body, fg=self.DIM, bg=self.SURFACE2,
            justify="center", wraplength=520,
        )
        # Pack later when there's content

        # ── Progress (hidden until update starts) ──
        style = ttk.Style()
        try:
            style.theme_use("clam")
            style.configure(
                "MBB.Horizontal.TProgressbar",
                troughcolor=self.SURFACE,
                background=self.ACCENT,
                bordercolor=self.BORDER,
                lightcolor=self.ACCENT,
                darkcolor=self.ACCENT,
                thickness=6,
            )
        except Exception:
            pass
        self.progress = ttk.Progressbar(
            self.root, mode="determinate",
            style="MBB.Horizontal.TProgressbar",
            length=560, maximum=100,
        )
        self.progress_label = tk.Label(
            self.root, text="", font=self.font_small,
            fg=self.DIM, bg=self.BG,
        )

        # ── Buttons (bottom) ──
        self.btn_frame = tk.Frame(self.root, bg=self.BG)
        self.btn_frame.pack(side="bottom", fill="x", pady=(10, 24), padx=24)

        self.btn_primary = tk.Button(
            self.btn_frame, text="Update Now",
            font=self.font_btn,
            fg="#ffffff", bg=self.ACCENT,
            activeforeground="#ffffff", activebackground="#7ec1ff",
            relief="flat", cursor="hand2",
            padx=28, pady=12, bd=0,
            state="disabled",
            command=self._on_primary_click,
        )
        self.btn_secondary = tk.Button(
            self.btn_frame, text="ปิด",
            font=self.font_body,
            fg=self.FG, bg=self.SURFACE,
            activeforeground=self.FG, activebackground=self.BORDER,
            relief="flat", cursor="hand2",
            padx=22, pady=10, bd=0,
            command=self._on_close,
        )
        self.btn_primary.pack(side="right", padx=(10, 0))
        self.btn_secondary.pack(side="right")

    # ─── Animated spinner (Canvas-drawn rotating arc) ───
    def _draw_spinner(self) -> None:
        """Draw a rotating arc — modern indeterminate progress style."""
        c = self.spinner_canvas
        c.delete("all")
        # Light background ring
        c.create_oval(4, 4, 24, 24, outline=self.BORDER, width=2)
        # Bright rotating arc (90° span)
        c.create_arc(
            4, 4, 24, 24,
            start=self._spinner_angle, extent=90,
            outline=self.ACCENT, width=2,
            style="arc",
        )
        self._spinner_angle = (self._spinner_angle + 12) % 360

    def _start_spinner(self) -> None:
        """Begin spinner animation tick.

        Cancels any existing pending tick first — otherwise calling this
        twice (e.g., retry path or re-entry) leaks parallel after-callbacks
        that race each other and double the redraw rate.
        """
        if self._spinner_after_id is not None:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        self._draw_spinner()
        self._spinner_after_id = self.root.after(40, self._start_spinner)

    def _stop_spinner(self) -> None:
        """Stop animation + clear canvas."""
        if self._spinner_after_id:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        try:
            self.spinner_canvas.delete("all")
        except Exception:
            pass

    def _hide_spinner(self) -> None:
        """Stop + remove the spinner canvas from layout entirely."""
        self._stop_spinner()
        try:
            self.spinner_canvas.pack_forget()
        except Exception:
            pass

    # ─── Animated dots ("ตรวจสอบ" → "ตรวจสอบ." → ".." → "...") ───
    def _start_dots_animation(self, base_text: str) -> None:
        """Cycle dots 0→3 after `base_text` every 400ms.

        Cancels any existing tick first (same reason as _start_spinner).
        """
        if self._dots_after_id is not None:
            try:
                self.root.after_cancel(self._dots_after_id)
            except Exception:
                pass
            self._dots_after_id = None
        self._dots_base_text = base_text
        self._dots_count = 0
        self._tick_dots()

    def _tick_dots(self) -> None:
        dots = "." * self._dots_count + " " * (3 - self._dots_count)  # pad to fix width
        self.lbl_status_text.config(text=f"{self._dots_base_text}{dots}")
        self._dots_count = (self._dots_count + 1) % 4
        self._dots_after_id = self.root.after(400, self._tick_dots)

    def _stop_dots_animation(self) -> None:
        if self._dots_after_id:
            try:
                self.root.after_cancel(self._dots_after_id)
            except Exception:
                pass
            self._dots_after_id = None

    # ─── Status badge variants (after check completes) ───
    def _show_checking(self, text: str = "ตรวจสอบเวอร์ชั่น") -> None:
        """Show spinner + animated dots."""
        self.status_card.config(bg=self.SURFACE2)
        self.status_inner.config(bg=self.SURFACE2)
        self.spinner_canvas.config(bg=self.SURFACE2)
        self.lbl_status_text.config(bg=self.SURFACE2, fg=self.ACCENT)
        try:
            self.spinner_canvas.pack(side="left", padx=(0, 12))
        except Exception:
            pass
        self._start_spinner()
        self._start_dots_animation(text)
        # Hide sub-line
        try:
            self.lbl_status_sub.pack_forget()
        except Exception:
            pass

    def _show_status_badge(
        self, icon: str, text: str, sub: str = "",
        accent: str = "", bg_tint: str = "",
    ) -> None:
        """Replace spinner state with a colored final badge.

        icon: leading character/emoji (✓ / ✦ / ⚠ / ✕)
        text: main status line (large)
        sub: optional secondary line
        accent: text color
        bg_tint: card background color
        """
        self._stop_spinner()
        self._stop_dots_animation()
        self._hide_spinner()

        accent = accent or self.ACCENT
        bg_tint = bg_tint or self.SURFACE2
        self.status_card.config(bg=bg_tint)
        self.status_inner.config(bg=bg_tint)
        self.lbl_status_text.config(
            bg=bg_tint, fg=accent,
            text=f"{icon}  {text}",
        )
        if sub:
            self.lbl_status_sub.config(bg=bg_tint, fg=self.DIM, text=sub)
            try:
                self.lbl_status_sub.pack(pady=(8, 0))
            except Exception:
                pass
        else:
            try:
                self.lbl_status_sub.pack_forget()
            except Exception:
                pass

    def _show_progress(self, percent: float, label: str = "") -> None:
        if not self.progress.winfo_ismapped():
            self.progress.pack(padx=40, pady=(14, 0), fill="x")
            self.progress_label.pack(padx=40, pady=(4, 0))
        self.progress["value"] = percent
        self.progress_label.config(text=label)

    def _hide_progress(self) -> None:
        try:
            self.progress.pack_forget()
            self.progress_label.pack_forget()
        except Exception:
            pass

    # ─── Phase 1: version check ───
    def _start_check(self) -> None:
        # Show animated checking state immediately
        self._show_checking("ตรวจสอบเวอร์ชั่น")
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self) -> None:
        # Sanity: target dir must contain an MBB.exe
        if not os.path.exists(os.path.join(self.target_dir, "MBB.exe")):
            self.root.after(0, lambda: self._show_error(
                f"ไม่พบ MBB.exe ใน {self.target_dir}",
                sub="กรุณาวาง MBB-Updater.exe ไว้ในโฟลเดอร์เดียวกับ MBB.exe"))
            return
        # Local version
        self.local_version = detect_local_version(self.target_dir)
        _log(f"Local version: {self.local_version!r}")
        self.root.after(0, lambda: self.lbl_local_huge.config(
            text=f"v {self.local_version}" if self.local_version else "ตรวจไม่พบ"
        ))
        # Remote
        try:
            data = fetch_github_release()
            self.remote = parse_release(data)
            _log(f"Remote: {self.remote}")
        except HTTPError as e:
            _log(f"HTTPError {e.code} from GitHub")
            if e.code == 404:
                # No release on GitHub = nothing newer than what user already has.
                # Frame this positively (green badge) — user is technically on
                # the latest version, even if the dev hasn't published one yet.
                self.root.after(0, self._show_latest_no_release)
                return
            elif e.code == 403:
                msg, sub = (
                    "GitHub Rate limit",
                    "เรียก API บ่อยเกินไป — รอประมาณ 1 ชั่วโมงแล้วลองใหม่",
                )
            elif 500 <= e.code < 600:
                msg, sub = (
                    f"GitHub server error (HTTP {e.code})",
                    "ลองใหม่ในอีกสักครู่",
                )
            else:
                msg, sub = f"GitHub server error: HTTP {e.code}", ""
            self.root.after(0, lambda m=msg, s=sub: self._show_warn(m, sub=s))
            return
        except URLError as e:
            _log(f"URLError: {e.reason}")
            self.root.after(0, lambda: self._show_error(
                "ไม่สามารถเชื่อมต่ออินเทอร์เน็ต",
                sub=f"{e.reason} — ตรวจการเชื่อมต่อเน็ต / firewall / proxy"))
            return
        except Exception as e:
            _log(f"fetch error: {e}\n{traceback.format_exc()}")
            self.root.after(0, lambda: self._show_error(
                "ตรวจสอบเวอร์ชั่นล้มเหลว", sub=str(e)))
            return
        self.root.after(0, self._on_check_done)

    def _on_check_done(self) -> None:
        if not self.remote.get("version"):
            self._show_error("ไม่พบ tag_name ใน GitHub release")
            return
        if not self.remote.get("zip_url"):
            self._show_error(
                "Release ไม่มีไฟล์ .zip",
                sub="ติดต่อทีมพัฒนาให้แนบ MBB-X.Y.Z-Update.zip ใน Release")
            return
        if is_newer(self.remote["version"], self.local_version):
            notes = (self.remote.get("notes") or "").strip() or "(ไม่มีรายละเอียด)"
            if len(notes) > 200:
                notes = notes[:200] + "…"
            sz_mb = max(1, self.remote.get("zip_size", 0) // (1024 * 1024))
            self._show_status_badge(
                "✦",
                f"มีเวอร์ชั่นใหม่  v {self.remote['version']}",
                sub=f"ขนาด ~{sz_mb} MB · {notes}",
                accent=self.ACCENT, bg_tint=self.SURFACE2,
            )
            self.btn_primary.config(state="normal", text="📥  อัพเดตเลย")
        else:
            self._show_status_badge(
                "✓",
                f"คุณใช้เวอร์ชั่นล่าสุดแล้ว",
                sub=f"v {self.local_version} ตรงกับเวอร์ชั่นล่าสุดบน GitHub",
                accent=self.SUCCESS, bg_tint=self.SUCCESS_BG,
            )
            # Hide the redundant "ปิด" — only one close button needed
            try:
                self.btn_primary.pack_forget()
            except Exception:
                pass

    # ─── Final state helpers ───
    def _show_error(self, text: str, sub: str = "") -> None:
        """Red error badge + close-only button."""
        self._hide_progress()
        self._show_status_badge(
            "✕", text, sub=sub,
            accent=self.ERR, bg_tint=self.ERR_BG,
        )
        try:
            self.btn_primary.pack_forget()
        except Exception:
            pass

    def _show_warn(self, text: str, sub: str = "") -> None:
        """Amber warning badge (transient — not necessarily fatal)."""
        self._hide_progress()
        self._show_status_badge(
            "⚠", text, sub=sub,
            accent=self.WARN, bg_tint=self.WARN_BG,
        )
        try:
            self.btn_primary.pack_forget()
        except Exception:
            pass

    def _show_latest_no_release(self) -> None:
        """GitHub returned 404 = no published release exists yet. Frame this
        as positive — user can't possibly have anything older than nothing.
        Same green badge as the "you're on latest" path so the experience is
        consistent and reassuring instead of looking like an error."""
        ver = self.local_version or "?"
        self._show_status_badge(
            "✓",
            "เวอร์ชั่นของคุณเป็นเวอร์ชั่นล่าสุด",
            sub=f"v {ver} ยังเป็นเวอร์ชั่นใหม่สุดในขณะนี้",
            accent=self.SUCCESS, bg_tint=self.SUCCESS_BG,
        )
        try:
            self.btn_primary.pack_forget()
        except Exception:
            pass

    # ─── Phase 2: do the update ───
    def _on_primary_click(self) -> None:
        self.btn_primary.config(state="disabled")
        self.btn_secondary.config(state="disabled")
        threading.Thread(target=self._update_thread, daemon=True).start()

    def _update_thread(self) -> None:
        try:
            # 1. Download
            self._update_status("⏳ กำลังดาวน์โหลดเวอร์ชันใหม่…", self.FG)
            zip_path = os.path.join(
                tempfile.gettempdir(),
                f"MBB-{self.remote['version']}-Update.zip",
            )
            self.zip_path = zip_path

            def download_cb(done, total):
                if total > 0:
                    pct = int(done * 100 / total)
                    md = done / (1024 * 1024)
                    mt = total / (1024 * 1024)
                    self.root.after(0, lambda: self._show_progress(
                        pct, f"{md:.1f} / {mt:.1f} MB"))

            download_with_progress(self.remote["zip_url"], zip_path, download_cb)

            # 2. SHA256 verify (best effort — only if sidecar present)
            if self.remote.get("sha_url"):
                self._update_status("🔒 ตรวจสอบ checksum…", self.FG)
                try:
                    sha_text = fetch_text(self.remote["sha_url"]).strip().split()[0]
                    actual = file_sha256(zip_path)
                    if actual.lower() != sha_text.lower():
                        raise ValueError(
                            f"checksum mismatch:\n  expected: {sha_text}\n  actual:   {actual}"
                        )
                    _log("SHA256 verified")
                except Exception as e:
                    self.root.after(0, lambda: self._on_update_failed(
                        f"Checksum verification failed:\n{e}"))
                    return

            # 2b. SECURITY: refuse to extract a zip that smuggles in .env / *.key.
            #     A legit release should never contain those — if we see them,
            #     either the release is mis-packaged or the asset was poisoned.
            #     Either way, applying it would splatter someone else's secrets
            #     onto the user's disk. Abort.
            self._update_status("🔒 ตรวจหาไฟล์ลับใน zip…", self.FG)
            secrets_found = zip_contains_secrets(zip_path)
            if secrets_found:
                _log(f"REFUSED: zip contains suspicious files: {secrets_found}")
                self.root.after(0, lambda: self._on_update_failed(
                    "ปฏิเสธ — zip มีไฟล์ลับ (.env / *.key) ที่ไม่ควรอยู่ใน release\n\n"
                    f"พบ: {', '.join(secrets_found[:3])}"
                    f"{f' (และอีก {len(secrets_found)-3} ไฟล์)' if len(secrets_found) > 3 else ''}\n\n"
                    "ติดต่อทีมพัฒนาให้ตรวจสอบ release"
                ))
                return

            # 3. Wait for MBB
            self._update_status("⏳ รอ MBB ปิด…", self.FG)
            wait_or_kill_mbb(self.target_dir)

            # 4. Backup user data
            self._update_status("📦 สำรองข้อมูลผู้ใช้…", self.FG)
            self.backup_dir = os.path.join(
                tempfile.gettempdir(), f"MBB-userdata-backup-{int(time.time())}"
            )
            backed_up = backup_user_data(self.target_dir, self.backup_dir)
            _log(f"Backed up: {backed_up}")

            # 5. Extract to staging (NOT yet over MBB folder — recoverable)
            self._update_status("⏳ กำลังแตกไฟล์…", self.FG)
            stage_dir = os.path.join(
                tempfile.gettempdir(), f"MBB-update-stage-{int(time.time())}"
            )
            if os.path.exists(stage_dir):
                shutil.rmtree(stage_dir)
            os.makedirs(stage_dir)

            def stage_cb(done, total):
                if total > 0:
                    pct = int(done * 100 / total)
                    self.root.after(0, lambda: self._show_progress(
                        pct, f"แตกไฟล์ {done}/{total}"))

            stage_extract(zip_path, stage_dir, stage_cb)

            # 6. Locate MBB/ inside staged content
            stage_root = find_zip_root(stage_dir)
            if not stage_root:
                raise RuntimeError(
                    "zip ที่ดาวน์โหลดมาไม่มี MBB.exe — รูปแบบไฟล์ไม่ถูกต้อง"
                )

            # 7. Apply (this is the destructive step)
            self._update_status("⏳ กำลังติดตั้ง…", self.FG)
            apply_staged_files(stage_root, self.target_dir)

            # 8. Restore user files
            self._update_status("♻ คืนข้อมูลผู้ใช้…", self.FG)
            restore_user_data(self.backup_dir, self.target_dir)

            # 9. Cleanup transient build artifacts.
            try:
                shutil.rmtree(stage_dir)
            except Exception:
                pass
            try:
                os.remove(zip_path)
            except Exception:
                pass

            self.root.after(0, lambda: self._on_update_done(backed_up))

        except Exception as e:
            _log(f"Update failed: {e}\n{traceback.format_exc()}")
            self.root.after(0, lambda: self._on_update_failed(str(e)))

    def _update_status(self, text: str, color: str = "") -> None:
        """Update the status text during the install phase. Stops the spinner
        on first call (we have a real progress bar now)."""
        def apply():
            self._stop_spinner()
            self._stop_dots_animation()
            self._hide_spinner()
            self.lbl_status_text.config(text=text, fg=color or self.ACCENT)
        self.root.after(0, apply)

    def _on_update_done(self, backed_up: list) -> None:
        self._hide_progress()
        kept = ", ".join(backed_up) if backed_up else "(ไม่มี)"
        self._show_status_badge(
            "✓",
            f"ติดตั้งเสร็จ  v {self.remote['version']}",
            sub=f"v {self.local_version or '?'}  →  v {self.remote['version']}\n"
                f"ข้อมูลผู้ใช้ที่เก็บไว้: {kept}",
            accent=self.SUCCESS, bg_tint=self.SUCCESS_BG,
        )
        self.btn_primary.config(
            state="normal", text="🚀  เปิด MBB",
            bg=self.SUCCESS,
            activebackground="#4dc764",
            command=self._on_launch,
        )
        self.btn_secondary.config(state="normal", text="ปิด")

    def _on_update_failed(self, error: str) -> None:
        sub = error
        if self.backup_dir and os.path.exists(self.backup_dir):
            sub += f"\nข้อมูลของคุณเก็บไว้ที่ {self.backup_dir}"
        self._show_error("ติดตั้งล้มเหลว", sub=sub)
        self.btn_secondary.config(state="normal")

    def _on_launch(self) -> None:
        proc = launch_mbb(self.target_dir)
        if proc:
            _log(f"Launched MBB.exe (pid={proc.pid})")
        self._on_close()

    def _on_close(self) -> None:
        try:
            self._stop_spinner()
            self._stop_dots_animation()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    global _log_path

    is_frozen = bool(getattr(sys, "frozen", False))

    if ARG_STAGE2 in sys.argv:
        # ── Stage 2 (explicit) ──
        target = get_target_dir_from_args()
    elif not is_frozen:
        # ── Dev mode (running .py via interpreter) ──
        # Stage 1 doesn't work for .py files (subprocess.Popen can't execute
        # a .py extension as binary → WinError 216). Skip the temp-relaunch
        # dance entirely; resolve target from --target arg or sensible default.
        target = get_target_dir_from_args() or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "dist_test", "MBB",
        )
        sys.stderr.write(
            f"[dev] Skipping Stage 1 (running .py, not frozen .exe). "
            f"Using target: {target}\n"
        )
    else:
        # ── Stage 1: frozen .exe, relaunch from temp ──
        _log_path = os.path.join(os.path.dirname(get_self_path()), "MBB-Updater.log")
        _log("Stage 1: relaunching from %TEMP%")
        stage1_relaunch_from_temp()
        return  # never reached — stage1_relaunch_from_temp calls sys.exit

    # ── Run UI (Stage 2 path: explicit OR dev-mode short-circuit) ──
    if not target or not os.path.isdir(target):
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "MBB Updater",
                f"Target directory ไม่ถูกต้อง:\n{target!r}\n\n"
                f"Dev mode: pass --target <MBB folder> or build to dist_test/MBB",
            )
        except Exception:
            pass
        sys.stderr.write(f"Bad target: {target!r}\n")
        sys.exit(1)
    _log_path = os.path.join(target, "MBB-Updater.log")
    _log("=" * 60)
    _log(f"Stage 2 starting | target={target} | frozen={is_frozen}")
    try:
        UpdaterApp(target).root.mainloop()
    except Exception as e:
        _log(f"UI crashed: {e}\n{traceback.format_exc()}")
        try:
            from tkinter import messagebox
            messagebox.showerror("MBB Updater", f"Updater crashed:\n{e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
