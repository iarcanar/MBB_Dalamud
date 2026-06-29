# 🏗️ MBB Dalamud — Build Protocol

**Version:** 1.8.2+
**Last updated:** 2026-05-01
**Replaces:** Old DLL-only protocol (v1.5.2 era, deprecated paths)

โปรเจ็คนี้มี 2 build artifacts แยกกัน — **C# Dalamud Plugin (DLL)** + **Python Application (EXE)** เอกสารนี้คุม flow การ build และปล่อยทั้งสองตัว

---

## 1. Pre-Build Checklist

ก่อนเริ่ม build ทุกครั้ง:

- [ ] ดึง `git pull` ล่าสุด, working tree clean
- [ ] `python check_version_consistency.py` ผ่าน (ทุกไฟล์ version ตรงกัน)
- [ ] `version.py` `__version__` + `__build__` อัพเดตแล้ว (ใช้ `python bump_version.py patch|minor|major|X.Y.Z`)
- [ ] CHANGELOG.md / claude.md changelog เขียนเรียบร้อย
- [ ] ตรวจ `python-app/.env` **ไม่อยู่** ใน `git status` (ต้องมีใน `.gitignore`)
- [ ] ตรวจ `python-app/settings.json` ไม่มี API key หรือ user data sensitive อื่นๆ

---

## 2. C# Plugin Build (Dalamud DLL)

### Output Path (single source of truth)
```
DalamudMBBBridge/bin/Release/DalamudMBBBridge.dll
```

> `<AppendRuntimeIdentifierToOutputPath>false</...>` ใน csproj ทำให้ไม่มี `win-x64/` subfolder

### Steps
```bash
# 1. ตรวจ csproj + json version ตรงกัน
grep -i version c:/MBB_Dalamud/DalamudMBBBridge/DalamudMBBBridge.csproj
grep -i version c:/MBB_Dalamud/DalamudMBBBridge/DalamudMBBBridge.json

# 2. Build Release config
cd c:/MBB_Dalamud
dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release

# 3. Verify output
ls -lh DalamudMBBBridge/bin/Release/DalamudMBBBridge.dll
```

### Package for Custom Repository
```bash
# Repack latest.zip with the FULL required set (incl. WMI runtime deps) and
# refresh pluginmaster.json LastUpdated in one step:
python scripts/pack_plugin.py

# verify
ls -lh c:/MBB_Dalamud/plugins/DalamudMBBBridge/latest.zip   # ~600-700KB expected
```

> ⚠️ **Do NOT hand-zip only `DalamudMBBBridge.dll + .json + icon.png`.** The plugin
> needs `System.Management.dll` + `System.CodeDom.dll` (WMI process-check) bundled
> too — Dalamud does not resolve NuGet deps. `pack_plugin.py` includes all 5 files;
> the old 3-file `zip` command shipped a plugin that throws at runtime.

### pluginmaster.json — version + freshness + API level
- `AssemblyVersion` + `LastUpdated` are now handled automatically by
  `bump_version.py` (and `pack_plugin.py` re-stamps `LastUpdated`). No manual edit.
- `DalamudApiLevel` **must match the built manifest** in
  `DalamudMBBBridge/bin/Release/DalamudMBBBridge.json` (currently **15**). It is
  NOT touched by `bump_version.py` — verify with
  `python check_version_consistency.py` (now cross-checks this field).

---

## 3. Python EXE Build (PyInstaller)

### ⚠️ ปัญหาที่เคยเจอจริง (Lessons Learned)

| ปัญหา | สาเหตุ | ทางแก้ |
|------|--------|--------|
| **RGB chromatic fringe รอบขอบ window** | PyQt6 6.10+ frameless + translucent regression บน Windows DWM | **Pin PyQt6 6.9.0** (ดู section ถัดไป) |
| `Hidden import 'PyQt6.QtCore' not found` | PyInstaller รัน Python 3.11 (system) แต่ PyQt6 ติดใน 3.13 (user) | ติด PyQt6 ใน Python ที่ pyinstaller ใช้ |
| `Icon input file ... not found` | spec ใช้ `mbb_icon.png` แต่ไฟล์จริง `mbb_icon.ico` | ตรวจ icon path ก่อน build |
| `_internal/pyqt_ui/` empty | spec ไม่มี `('pyqt_ui', 'pyqt_ui')` ใน datas + ไม่มี `pyqt_ui.*` ใน hiddenimports | เพิ่มทั้งสองส่วน — ดู spec ปัจจุบัน |
| `NPC.json` vs `npc.json` | spec ใช้ `'NPC.json'` แต่ไฟล์จริง lowercase | filesystem Windows case-insensitive แต่ควรใช้ lowercase ตามจริง |
| `cryptography` hook warning | `_check_cryptography_openssl3()` fail | non-fatal — ignore (build ผ่าน) |

### Environment ที่ต้องการ

**Python 3.11.x** (PyInstaller bootloader build target นี้ stable สุด)

### ⚠️ CRITICAL: PyQt6 Version ต้อง Pin ที่ 6.9.0

```
PyQt6==6.9.0
PyQt6-Qt6==6.9.0
PyQt6-sip==13.10.2
```

**สาเหตุ:** Qt 6.10+ (รวม 6.11) มี compositor regression บน Windows DWM ที่ทำให้
frameless + `WA_TranslucentBackground` window แสดง **RGB chromatic fringe**
รอบขอบทั้ง window — กระทบทุก UI ของ MBB (main, settings, theme, NPC manager,
translated logs, polaroid overlay) ดูตัวอย่างใน `git log` หา commit "PyQt6 6.9 pin"

**ห้าม upgrade** PyQt6 โดยไม่ test frameless rendering ใหม่ทั้งหมด แม้ว่า Qt
จะออก 6.12, 6.13 ก็ตาม — Qt issue tracker ยังเปิดปัญหา frameless อยู่ที่
[QTBUG-33434](https://bugreports.qt.io/browse/QTBUG-33434)

ตรวจก่อน build:
```bash
# Python ที่ pyinstaller ใช้ — ต้องเป็นตัวที่มี deps ครบ
which pyinstaller
pyinstaller --version    # ต้องเป็น 6.x+

# CRITICAL: PyQt6 version check
python -c "from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR; \
print(f'PyQt6={PYQT_VERSION_STR} Qt={QT_VERSION_STR}')"
# ต้องได้: PyQt6=6.9.0 Qt=6.9.0

# ทดสอบ deps ที่จำเป็น
python -c "
import importlib
mods = ['PyQt6', 'google.generativeai', 'PIL', 'requests',
        'dotenv', 'win32com', 'psutil', 'keyboard', 'cryptography']
for m in mods:
    try:
        importlib.import_module(m)
        print(f'  OK    {m}')
    except ImportError as e:
        print(f'  MISS  {m}  ({e})')
"
```

ถ้า PyQt6 version ผิด:
```bash
python -m pip install --force-reinstall \
    "PyQt6==6.9.0" "PyQt6-Qt6==6.9.0" "PyQt6-sip==13.10.2"
```

ถ้าตัวไหน MISS:
```bash
python -m pip install -r requirements.txt
```

> **CRITICAL:** ติด package ใน Python ตัวที่ `pyinstaller` ใช้ (เช็คจาก `which pyinstaller`)
> ถ้ามีหลาย Python (3.11 + 3.13) อาจติดผิดตัวง่าย — ใช้ full path: `/c/Users/.../Python311/python.exe -m pip install ...`

### Build Steps

**Build order matters** (v1.8.4+): build the **updater first**, then main MBB.
The main spec's post-build copies `MBB-Updater.exe` from `dist_test/` into
`dist_test/MBB/`. If updater isn't built yet, MBB folder ships without one.

```bash
# 1. Clean
rm -rf c:/MBB_Dalamud/dist_test/MBB \
       c:/MBB_Dalamud/dist_test/build_work \
       c:/MBB_Dalamud/dist_test/build_updater \
       c:/MBB_Dalamud/dist_test/MBB-Updater.exe

# 2. Build updater (onefile, ~11MB)
cd c:/MBB_Dalamud/updater
pyinstaller updater.spec --clean --noconfirm \
    --distpath ../dist_test \
    --workpath ../dist_test/build_updater

# 3. Build main MBB
cd c:/MBB_Dalamud/python-app
pyinstaller mbb.spec --clean --noconfirm \
    --distpath ../dist_test \
    --workpath ../dist_test/build_work

# 4. Expected output:
#    ../dist_test/MBB-Updater.exe         ← ~11MB (then copied into MBB/)
#    ../dist_test/MBB/MBB.exe              ← ~15MB
#    ../dist_test/MBB/MBB-Updater.exe      ← copy bundled with main release
#    ../dist_test/MBB/npc.json             ← promoted user-editable
#    ../dist_test/MBB/npc_images/          ← promoted user data
#    ../dist_test/MBB/_internal/           ← Python runtime + bundled fallbacks
#    Total                                  ← ~300MB
```

**Pre-deploy secrets scan runs automatically** at end of mbb.spec via
[scripts/check_no_secrets.py](scripts/check_no_secrets.py). If it finds a
`.env`, `*.key`, `*.pem` (outside the certifi/grpc allowlist), or content
matching the Gemini key shape `AIza[A-Za-z0-9_-]{35}`, the build aborts.

**Common cause of false-failure:** smoke-testing `MBB.exe` *before* packaging
the zip creates a `MBB/.env` with your real key. Delete it, rebuild. Or
better: smoke-test in a copy of the dist folder.

### Build Time Reference
- Cold build (--clean): ~30-50 วินาที (M2 ssd, Python 3.11)
- Warm build: ~15-20 วินาที

### Console vs Windowed

[mbb.spec](python-app/mbb.spec) now derives `console` from an env flag — no manual
edit needed:
```python
_release_build = os.environ.get("MBB_RELEASE") == "1"
console = not _release_build      # dev=True (see stdout) · release=False
```

แนะนำ:
- **Internal testing:** build ปกติ → `console=True` เห็น log ทันที
- **End-user release:** ตั้ง env `MBB_RELEASE=1` ก่อน build → `console=False` UI สะอาด
  (bash: `MBB_RELEASE=1 pyinstaller mbb.spec ...` · PowerShell: `$env:MBB_RELEASE=1`)

---

## 4. Smoke Test (ก่อนปล่อย)

หลัง build เสร็จ **ต้อง** run smoke test ก่อนเสมอ:

### 4.1 Boot test (8s timeout)
```bash
cd c:/MBB_Dalamud/dist_test/MBB
timeout 8 ./MBB.exe 2>&1 | head -50
```

ผลลัพธ์ที่ดี:
- ไม่มี `ImportError`, `ModuleNotFoundError`, `FileNotFoundError`
- เห็น log "API key" หรือ "splash" หรือ "main window" — แสดงว่าผ่าน import phase
- ถ้าเห็น `WARNING:mbb-qt:No valid API key — showing setup dialog` = ✅ พร้อม run จริง (รอ user ใส่ key)

### 4.2 Manual functional test (run จริง 5-10 นาที)

ใส่ API key → ทดสอบทีละข้อ:

| ข้อ | ฟีเจอร์ | Expected |
|----|--------|---------|
| 1 | Splash screen | แสดง 5 วินาที, fade in/out smooth |
| 2 | Main window | logo + 3 toggle buttons (TUI/LOG/MINI) |
| 3 | Settings panel (PyQt6) | เปิดได้, font Anuphan, ToggleSwitch animate |
| 4 | TUI (Tkinter) | กด TUI → window แสดง |
| 5 | Translated Logs (PyQt6) | กด LOG → bubble UI แสดง |
| 6 | NPC Manager (PyQt6) | กด NPC Manager → tabs (MAIN/NPCS/LORE) |
| 7 | FontPanel | เลือก font → preview เปลี่ยน → APPLY |
| 8 | Theme panel | คลิก swatch → แอพเปลี่ยน theme ทันที |
| 9 | Test Hook (Dialog/Battle/Cutscene) | ส่งข้อความ → แปลออกบน TUI |
| 10 | Polaroid avatar (NPC Manager) | คลิก avatar → polaroid card |
| 11 | Glass mode toggle | ปุ่ม ● ใน header → ปุ่มทุกตัวจาง |
| 12 | Restart App | Settings → Restart → countdown → relaunch |

ถ้าข้อ 1-9 ผ่าน = พร้อมปล่อย; 10-12 เป็น nice-to-have

### 4.3 Asset audit
```bash
# ตรวจ critical bundled files
ls c:/MBB_Dalamud/dist_test/MBB/_internal/fonts/Anuphan.ttf
ls c:/MBB_Dalamud/dist_test/MBB/_internal/fonts/Caveat.ttf
ls c:/MBB_Dalamud/dist_test/MBB/_internal/pyqt_ui/main_window.py
ls c:/MBB_Dalamud/dist_test/MBB/_internal/PyQt6/QtWidgets.pyd
ls c:/MBB_Dalamud/dist_test/MBB/_internal/npc.json
ls c:/MBB_Dalamud/dist_test/MBB/_internal/.env.example
ls c:/MBB_Dalamud/dist_test/MBB/_internal/assets/mbb_icon.ico
ls c:/MBB_Dalamud/dist_test/MBB/_internal/npc_images/main_characters/

# v1.8.4+ — npc.json + npc_images promoted next to MBB.exe (post-build copy
# in mbb.spec). Resolver prefers these over _internal/ copies.
ls c:/MBB_Dalamud/dist_test/MBB/npc.json
ls c:/MBB_Dalamud/dist_test/MBB/npc_images/main_characters/
```

ทุกข้อต้องเจอ — ถ้าหายข้อใด แสดงว่า [mbb.spec](python-app/mbb.spec) datas/hiddenimports ไม่ครบ
หรือ post-build copy block ตอนท้าย spec ไม่รัน (ดู `[post-build]` ใน build log)

---

## 5. Sensitive Data Audit

**ห้าม** ปล่อย build ที่มีข้อมูลส่วนตัว:

```bash
# 1. ตรวจ .env
ls c:/MBB_Dalamud/dist_test/MBB/.env 2>&1   # ต้องไม่มี

# 2. ตรวจ settings.json (ถ้ามี ต้องไม่มี API key)
cat c:/MBB_Dalamud/dist_test/MBB/settings.json 2>/dev/null | grep -i "key\|token\|secret"

# 3. ตรวจ logs/
ls c:/MBB_Dalamud/dist_test/MBB/logs/ 2>&1   # ต้องไม่มีหรือว่างเปล่า

# 4. ตรวจ npc.json ไม่มี user-added private data
# (ปกติ npc.json bundled ตรงกับ source — ไม่ใช่ snapshot ของ user)
```

ถ้าเจอข้อมูลส่วนตัว → **delete + rebuild** ห้าม manually clean แล้วปล่อย (อาจมีไฟล์อื่นยัง leak)

---

## 6. Package for Distribution

### Zip structure ที่ผู้ใช้ดาวน์โหลด:

```
MBB-vX.Y.Z.zip
└── MBB/
    ├── MBB.exe               ← main runnable
    ├── MBB-Updater.exe       ← (v1.8.4+) standalone updater, ships in every release
    ├── npc.json              ← (v1.8.4+) user-editable database, promoted out of _internal
    ├── npc_images/           ← (v1.8.4+) avatars; promoted out of _internal
    │   └── main_characters/
    ├── _internal/            ← all bundled deps
    │   ├── npc.json          ← fallback (used if MBB/npc.json missing)
    │   ├── npc_images/       ← fallback
    │   ├── .env.example      ← template
    │   ├── fonts/
    │   ├── assets/
    │   ├── pyqt_ui/
    │   ├── PyQt6/
    │   └── ... (Python runtime + libs)
    └── README.txt            ← optional: 3 บรรทัดสอนใส่ API key
```

**Updater rationale (v1.8.4+):** every release ships with `MBB-Updater.exe`
next to the main exe. User runs it any time to pull the latest GitHub
release in-place — preserves `npc.json`, `npc_images/`, `settings.json`,
`backups/`, and the API key (which lives in `%LOCALAPPDATA%\MBB_Dalamud\.env`,
outside the install). 2-stage launch handles Windows .exe self-replace
limitation. Source: [updater/updater.py](updater/updater.py).

**Promoted-files rationale (v1.8.4+):** `npc.json` + `npc_images/` are the
only files users actively touch (NPC Manager edits + manual sharing). Keeping
them buried in `_internal/` was confusing — users couldn't find their data.
Post-build step in [mbb.spec](python-app/mbb.spec) copies them up to the
exe-level directory; `npc_file_utils.get_npc_file_path()` already prefers
that location. Both copies coexist (~1.5MB duplication, negligible).

### Build zip
```bash
cd c:/MBB_Dalamud/dist_test
# Zip with max compression (zstd or xz best, but most users ใช้ Windows = stick with zip)
powershell.exe -Command "Compress-Archive -Path MBB -DestinationPath MBB-v1.8.2.zip -CompressionLevel Optimal"
ls -lh MBB-v1.8.2.zip   # คาด ~80-100MB
```

### Upload to GitHub Release
```bash
gh release create v1.8.2 \
    --title "MBB v1.8.2" \
    --notes-file CHANGELOG.md \
    c:/MBB_Dalamud/dist_test/MBB-v1.8.2.zip
```

---

## 7. Post-Release

- [ ] Push `pluginmaster.json` ไป main branch (Dalamud จะเห็นอัพเดต ภายใน ~1 ชม)
- [ ] อัพเดต landing page เวอร์ชันล่าสุด (ลิงก์ download)
- [ ] อัพเดต README.md ในกรณีที่ flow installation เปลี่ยน
- [ ] Tag git commit: `git tag v1.8.2 && git push --tags`
- [ ] ทดสอบ install จาก zero — ลบ Dalamud plugin + MBB ออกหมด → install ใหม่ → ใช้งานได้?

---

## 8. Quick Reference — Common Commands

```bash
# === Full release flow (after version bump) ===

# 1. C# plugin
cd c:/MBB_Dalamud
dotnet build DalamudMBBBridge/DalamudMBBBridge.csproj -c Release
python scripts/pack_plugin.py            # zip incl. WMI dlls + stamp LastUpdated

# 2. Python EXE  (MBB_RELEASE=1 → windowed/no-console build)
cd c:/MBB_Dalamud/python-app
MBB_RELEASE=1 pyinstaller mbb.spec --clean --noconfirm --distpath ../dist_test --workpath ../dist_test/build_work

# 3. Smoke test
cd c:/MBB_Dalamud/dist_test/MBB && timeout 8 ./MBB.exe 2>&1 | head -50

# 4. Manual functional test (5-10 min, all 12 checks above)

# 5. Zip + release
cd c:/MBB_Dalamud/dist_test
powershell.exe -Command "Compress-Archive -Path MBB -DestinationPath MBB-vX.Y.Z.zip -CompressionLevel Optimal"
gh release create vX.Y.Z --title "MBB vX.Y.Z" --notes-file ../CHANGELOG.md MBB-vX.Y.Z.zip

# 6. Push pluginmaster
git add pluginmaster.json plugins/ && git commit -m "Release vX.Y.Z" && git push
```

---

## 9. Outdated Info (Historical Reference)

ก่อน v1.7.0 build path เคยเป็น:
- ❌ `C:\Yariman_Babel\MbbDalamud_bridge\dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64\` (ย้ายไป `c:\MBB_Dalamud\` แล้ว)
- ❌ `XIVLauncher\devPlugins\` (เลิกใช้ — แทนที่ด้วย Custom Repository)

ก่อน v1.8.0 PyInstaller spec ขาด:
- ❌ `pyqt_ui` ใน datas + `pyqt_ui.*` ใน hiddenimports → PyQt6 panels build ไม่ติด
- ❌ PyQt6 ใน Python 3.11 site-packages → build error

ทั้งหมดถูกแก้ใน v1.8.2 spec แล้ว
