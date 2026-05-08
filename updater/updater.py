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
    button (Update Now → Launch MBB → Close)."""

    # Theme colors — match MBB's "Carbon" palette so it feels like the same app
    BG = "#0d1117"
    FG = "#e6edf3"
    DIM = "#7d8590"
    SURFACE = "#161b22"
    BORDER = "#30363d"
    ACCENT = "#58a6ff"
    SUCCESS = "#3fb950"
    WARN = "#f59e0b"
    ERR = "#f85149"

    def __init__(self, target_dir: str):
        self.target_dir = target_dir
        self.local_version: str = ""
        self.remote: dict = {}
        self.zip_path: str = ""
        self.backup_dir: str = ""

        self.root = tk.Tk()
        self.root.title("MBB Updater")
        self.root.geometry("560x480")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        try:
            # Optional icon — only if we managed to bundle one
            icon_path = os.path.join(self.target_dir, "_internal", "assets", "mbb_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.font_h1 = ("Anuphan", 16, "bold")
        self.font_h2 = ("Anuphan", 12, "bold")
        self.font_body = ("Anuphan", 10)
        self.font_small = ("Anuphan", 9)

        self._build_ui()
        # Auto-fetch shortly after mainloop starts (gives UI time to draw)
        self.root.after(150, self._start_check)

    def _build_ui(self) -> None:
        # ── Header ──
        title = tk.Label(
            self.root, text="MBB Updater",
            font=self.font_h1, fg=self.FG, bg=self.BG,
        )
        title.pack(pady=(22, 2))

        subtitle = tk.Label(
            self.root, text=os.path.basename(self.target_dir.rstrip(os.sep)) or self.target_dir,
            font=self.font_small, fg=self.DIM, bg=self.BG,
        )
        subtitle.pack()

        # ── Versions card ──
        card = tk.Frame(
            self.root, bg=self.SURFACE,
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        card.pack(fill="x", padx=24, pady=(18, 14))

        row1 = tk.Frame(card, bg=self.SURFACE)
        row1.pack(fill="x", padx=18, pady=(14, 4))
        tk.Label(
            row1, text="ปัจจุบัน:", font=self.font_body,
            fg=self.DIM, bg=self.SURFACE, width=10, anchor="w",
        ).pack(side="left")
        self.lbl_local = tk.Label(
            row1, text="—", font=self.font_h2,
            fg=self.FG, bg=self.SURFACE, anchor="w",
        )
        self.lbl_local.pack(side="left")

        row2 = tk.Frame(card, bg=self.SURFACE)
        row2.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(
            row2, text="ล่าสุด:", font=self.font_body,
            fg=self.DIM, bg=self.SURFACE, width=10, anchor="w",
        ).pack(side="left")
        self.lbl_remote = tk.Label(
            row2, text="กำลังตรวจสอบ…", font=self.font_h2,
            fg=self.ACCENT, bg=self.SURFACE, anchor="w",
        )
        self.lbl_remote.pack(side="left")

        # ── Status / changelog ──
        self.status_frame = tk.Frame(self.root, bg=self.BG)
        self.status_frame.pack(fill="both", expand=True, padx=24)

        self.lbl_status = tk.Label(
            self.status_frame, text="",
            font=self.font_body, fg=self.DIM, bg=self.BG,
            justify="left", wraplength=510, anchor="nw",
        )
        self.lbl_status.pack(fill="both", expand=True, anchor="nw")

        # ── Progress (hidden until update starts) ──
        # Use ttk style so progress bar matches dark theme reasonably
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
            )
        except Exception:
            pass
        self.progress = ttk.Progressbar(
            self.root, mode="determinate",
            style="MBB.Horizontal.TProgressbar",
            length=512, maximum=100,
        )
        self.progress_label = tk.Label(
            self.root, text="", font=self.font_small,
            fg=self.DIM, bg=self.BG, anchor="w",
        )

        # ── Buttons ──
        self.btn_frame = tk.Frame(self.root, bg=self.BG)
        self.btn_frame.pack(side="bottom", fill="x", pady=(8, 18))

        self.btn_primary = tk.Button(
            self.btn_frame, text="Update Now",
            font=self.font_h2,
            fg="#ffffff", bg=self.ACCENT,
            activeforeground="#ffffff", activebackground="#7ec1ff",
            relief="flat", cursor="hand2",
            padx=24, pady=10, bd=0,
            state="disabled",
            command=self._on_primary_click,
        )
        self.btn_secondary = tk.Button(
            self.btn_frame, text="ปิด",
            font=self.font_body,
            fg=self.FG, bg=self.SURFACE,
            activeforeground=self.FG, activebackground=self.BORDER,
            relief="flat", cursor="hand2",
            padx=20, pady=8, bd=0,
            command=self._on_close,
        )
        self.btn_primary.pack(side="right", padx=(8, 24))
        self.btn_secondary.pack(side="right")

    # ─── State helpers ───
    def _set_status(self, text: str, color: str = "") -> None:
        self.lbl_status.config(text=text, fg=color or self.DIM)

    def _show_progress(self, percent: float, label: str = "") -> None:
        if not self.progress.winfo_ismapped():
            self.progress.pack(after=self.status_frame, padx=24, pady=(4, 0), fill="x")
            self.progress_label.pack(after=self.progress, padx=24, pady=(2, 6), anchor="w")
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
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self) -> None:
        # Sanity: target dir must contain an MBB.exe
        if not os.path.exists(os.path.join(self.target_dir, "MBB.exe")):
            self.root.after(0, lambda: self._show_error(
                f"ไม่พบ MBB.exe ใน:\n{self.target_dir}\n\n"
                f"กรุณาวาง MBB-Updater.exe ไว้ในโฟลเดอร์เดียวกับ MBB.exe"))
            return
        # Local version
        self.local_version = detect_local_version(self.target_dir)
        _log(f"Local version: {self.local_version!r}")
        self.root.after(0, lambda: self.lbl_local.config(
            text=f"v{self.local_version}" if self.local_version else "ตรวจไม่พบ"
        ))
        # Remote
        try:
            data = fetch_github_release()
            self.remote = parse_release(data)
            _log(f"Remote: {self.remote}")
        except HTTPError as e:
            _log(f"HTTPError {e.code} from GitHub")
            # Map HTTP status to a user-actionable message — "Server error 404"
            # is meaningless to most users; "ยังไม่มี release" is.
            if e.code == 404:
                msg = (
                    "ยังไม่มี release บน GitHub สำหรับเวอร์ชันใหม่\n\n"
                    "หมายความว่าทีมพัฒนายังไม่ได้ปล่อยเวอร์ชันใหม่\n"
                    "ลองตรวจอีกครั้งภายหลัง หรือไปที่หน้าเว็บโครงการ"
                )
            elif e.code == 403:
                msg = (
                    "GitHub บอกว่าเรียก API บ่อยเกินไป (Rate limit)\n\n"
                    "รอประมาณ 1 ชั่วโมง แล้วลองใหม่อีกครั้ง"
                )
            elif 500 <= e.code < 600:
                msg = (
                    f"GitHub กำลังมีปัญหาฝั่ง server (HTTP {e.code})\n"
                    f"ลองใหม่ในอีกสักครู่"
                )
            else:
                msg = f"GitHub server error: HTTP {e.code}"
            self.root.after(0, lambda m=msg: self._show_error(m))
            return
        except URLError as e:
            _log(f"URLError: {e.reason}")
            self.root.after(0, lambda: self._show_error(
                f"ไม่สามารถเชื่อมต่ออินเทอร์เน็ต:\n{e.reason}\n\n"
                f"ตรวจการเชื่อมต่อเน็ต / firewall / proxy"))
            return
        except Exception as e:
            _log(f"fetch error: {e}\n{traceback.format_exc()}")
            self.root.after(0, lambda: self._show_error(
                f"ตรวจสอบเวอร์ชันล้มเหลว:\n{e}"))
            return
        self.root.after(0, self._on_check_done)

    def _on_check_done(self) -> None:
        if not self.remote.get("version"):
            self._show_error("ไม่พบ tag_name ใน GitHub release")
            return
        self.lbl_remote.config(text=f"v{self.remote['version']}")
        if not self.remote.get("zip_url"):
            self._show_error(
                "Release นี้ไม่มีไฟล์ .zip\n"
                "ติดต่อทีมพัฒนาให้แนบไฟล์ MBB-X.Y.Z-Update.zip ใน Release")
            return
        if is_newer(self.remote["version"], self.local_version):
            notes = (self.remote.get("notes") or "").strip() or "(ไม่มีรายละเอียด)"
            if len(notes) > 600:
                notes = notes[:600] + "…"
            sz_mb = max(1, self.remote.get("zip_size", 0) // (1024 * 1024))
            self._set_status(
                f"พบเวอร์ชันใหม่!  ขนาด ~{sz_mb} MB\n\n"
                f"📝 What's new:\n{notes}",
                color=self.FG,
            )
            self.btn_primary.config(state="normal", text="Update Now")
        else:
            self.lbl_remote.config(fg=self.SUCCESS)
            self._set_status("✓ คุณใช้เวอร์ชันล่าสุดอยู่แล้ว", color=self.SUCCESS)
            self.btn_primary.config(
                text="ปิด", state="normal",
                bg=self.SURFACE, fg=self.FG,
                activebackground=self.BORDER,
                command=self._on_close,
            )

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

    def _update_status(self, text: str, color: str) -> None:
        self.root.after(0, lambda: self._set_status(text, color))

    def _on_update_done(self, backed_up: list) -> None:
        self._hide_progress()
        msg_lines = [
            f"✅ ติดตั้งเสร็จเรียบร้อย",
            "",
            f"v{self.local_version or '?'}  →  v{self.remote['version']}",
            "",
            "ข้อมูลผู้ใช้ที่เก็บไว้:",
        ]
        if backed_up:
            for name in backed_up:
                msg_lines.append(f"  ✓ {name}")
        else:
            msg_lines.append("  (ไม่มีข้อมูลผู้ใช้ที่ต้องเก็บ)")
        msg_lines.append("")
        msg_lines.append(f"Backup ชั่วคราว: {self.backup_dir}")
        self._set_status("\n".join(msg_lines), color=self.SUCCESS)
        self.btn_primary.config(
            state="normal", text="🚀 Launch MBB",
            bg=self.SUCCESS,
            activebackground="#4dc764",
            command=self._on_launch,
        )
        self.btn_secondary.config(state="normal", text="ปิด")

    def _on_update_failed(self, error: str) -> None:
        self._hide_progress()
        msg = f"❌ Update ล้มเหลว:\n{error}"
        if self.backup_dir and os.path.exists(self.backup_dir):
            msg += f"\n\nข้อมูลของคุณยังเก็บไว้ที่:\n{self.backup_dir}"
        self._set_status(msg, color=self.ERR)
        self.btn_primary.config(
            state="normal", text="ปิด",
            bg=self.SURFACE, fg=self.FG,
            activebackground=self.BORDER,
            command=self._on_close,
        )
        self.btn_secondary.config(state="disabled")

    def _on_launch(self) -> None:
        proc = launch_mbb(self.target_dir)
        if proc:
            _log(f"Launched MBB.exe (pid={proc.pid})")
        self._on_close()

    def _show_error(self, msg: str) -> None:
        self._hide_progress()
        self._set_status(f"❌ {msg}", color=self.ERR)
        self.btn_primary.config(
            state="normal", text="ปิด",
            bg=self.SURFACE, fg=self.FG,
            activebackground=self.BORDER,
            command=self._on_close,
        )

    def _on_close(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    global _log_path

    if ARG_STAGE2 in sys.argv:
        # ── Stage 2 ──
        target = get_target_dir_from_args()
        if not target or not os.path.isdir(target):
            try:
                from tkinter import messagebox
                messagebox.showerror(
                    "MBB Updater",
                    f"Target directory ไม่ถูกต้อง:\n{target}",
                )
            except Exception:
                pass
            sys.exit(1)
        _log_path = os.path.join(target, "MBB-Updater.log")
        _log("=" * 60)
        _log(f"Stage 2 starting | target={target}")
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
    else:
        # ── Stage 1: relaunch from temp ──
        # Log inside the MBB folder so debug info survives across runs
        _log_path = os.path.join(os.path.dirname(get_self_path()), "MBB-Updater.log")
        _log("Stage 1: relaunching from %TEMP%")
        stage1_relaunch_from_temp()


if __name__ == "__main__":
    main()
