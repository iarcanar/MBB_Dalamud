# MBB Dalamud — Distribution Plan

**Created:** 2026-05-01
**Target version:** v1.8.2 (build 04032026-01)
**Goal:** ลดขั้นตอนการติดตั้งให้ผู้ใช้ใหม่เริ่มใช้งานได้เร็วและแน่ใจว่าทุกอย่างทำงาน

---

## ความเข้าใจสำคัญ (Misconception Clearing)

**เดิมเข้าใจว่า:** ผู้ใช้ต้อง
1. ติดตั้ง Dalamud platform
2. ติดตั้ง Python MBB app
3. ใส่ path ของ DLL ใน Dalamud เอง
4. ใส่ path ของ MBB.exe ใน plugin config

**จริงๆ แล้ว:** ขั้นตอน 3 ไม่จำเป็นอีกต่อไป — เพราะใช้ **Custom Plugin Repository** (`pluginmaster.json`) ผ่านระบบ Dalamud โดยตรง

### Flow ผู้ใช้ใหม่ที่ถูกต้อง:

| ขั้นตอน | สถานที่ | จำนวนคลิก |
|---------|--------|-----------|
| 1. Copy Custom Repo URL จากเว็บ MBB | เว็บ landing page | 1 (Copy ปุ่ม) |
| 2. Paste URL ใน Dalamud Settings → Experimental | XIVLauncher in-game | ~3 |
| 3. กด `/xlplugins` → Install "Magicite Babel Bridge" | In-game plugin browser | 1 |
| 4. ดาวน์โหลด MBB.exe (zip จาก GitHub release) | เว็บ MBB | 1 |
| 5. แตก zip ไปไหนก็ได้ | File explorer | drag |
| 6. กด `/mbb` → Browse → เลือก MBB.exe | In-game config window | ~3 |
| 7. กด Launch → เริ่มใช้ได้ | Plugin window | 1 |

**ขั้นที่ลดได้อีก:** 4-6 รวมเป็น 1 ขั้นตอนได้ (ดู Phase 2B ด้านล่าง)

---

## Phase Roadmap

### ✅ Phase 1 — Foundation (สถานะปัจจุบัน)
ทำเสร็จแล้ว:
- `pluginmaster.json` ชี้ไป `iarcanar/MBB_Dalamud` repo (raw GitHub)
- `plugins/DalamudMBBBridge/latest.zip` (668KB) พร้อม distribute
- `MBBConfigWindow` มี Browse + Save Path + Launch button
- Status indicators (🟢 Connected / 🔴 Not Running) ใน config window
- PyInstaller spec มี — build เป็น `dist/MBB/MBB.exe` (28MB exe / 356MB folder)

ต้องตรวจสอบ/แก้ก่อนปล่อย:
- [ ] `mbb.spec` typo `NPC.json` → `npc.json` (case-sensitive on Linux/macOS, OK on Windows but inconsistent)
- [ ] เช็คว่า PyInstaller รวม PyQt6 + tkinter + ทุก asset ครบ
- [ ] GitHub Release มี zip MBB.exe สำหรับผู้ใช้ดาวน์โหลด
- [ ] Landing page (mbb.iarcanar.com?) แสดง Custom Repo URL ชัดเจน + GIF สาธิต
- [ ] เอกสาร `INSTALLATION.md` ปรับให้ตรงกับ flow ปัจจุบัน (ไม่ใช่ Dev Plugin Location เก่า)

### Phase 2A — Quick Wins (1-2 วัน)

**1. Setup Wizard / Health Check Panel** (ไฟล์: `DalamudMBBBridge/MBBConfigWindow.cs`)

แทนที่ section ปัจจุบันที่มี indicators กระจาย ด้วย panel เดียวรวม:

```
┌─ 🔧 Setup Status ─────────────────────────┐
│ ✅ 1. Plugin loaded         v1.8.2       │
│ ✅ 2. MBB.exe found         [path...]    │
│ 🟡 3. MBB process running   [Launch]     │
│ ⚪ 4. Pipe connected        (waiting)    │
│ ⚪ 5. Translation test      [Send test]  │
└──────────────────────────────────────────┘
        🟢 ALL READY — Type /mbb to start
```

แต่ละข้อมีไฟ + ปุ่มแก้ไข inline ผู้ใช้เห็นทันทีว่าค้างที่ขั้นไหน

**2. Auto-discovery ฉลาดขึ้น** (ไฟล์: `DalamudMBBBridge/DalamudMBBBridge.cs:LoadMbbPath`)

Scan locations เหล่านี้ตามลำดับ ถ้าเจอ MBB.exe ให้ set อัตโนมัติ:
- `%LOCALAPPDATA%\MBB\MBB.exe`
- `%LOCALAPPDATA%\Programs\MBB\MBB.exe`
- `%PROGRAMFILES%\MBB\MBB.exe`
- `%USERPROFILE%\Documents\MBB\MBB.exe`
- `%USERPROFILE%\Desktop\MBB\MBB.exe`
- `%USERPROFILE%\Downloads\MBB\MBB.exe`
- เก่า: `C:\MBB_Dalamud\python-app\MBB.py`

**3. Landing page polish**
- ปุ่ม "📋 Copy Repo URL" + tooltip
- GIF 10 วินาที สาธิตการ paste URL ใน Dalamud
- ลิงก์ตรงไป GitHub Release (ดาวน์โหลด MBB.exe)
- ลิงก์สมัคร Gemini API key (aistudio.google.com)

### Phase 2B — One-Click MBB Download (3-5 วัน)

**4. ปุ่ม "⬇ Download MBB" ใน config window**

Logic:
1. กดปุ่ม → HTTP GET zip จาก GitHub Releases API (latest หรือ pinned version)
2. แสดง progress bar (28MB exe + ~330MB internals = ~80MB เมื่อ zip)
3. แตก zip ไป `%LOCALAPPDATA%\MBB\`
4. SetPath อัตโนมัติ
5. แสดง "✅ Installed — ready to launch"

ผู้ใช้ไม่ต้องออกจากเกมเลย

**5. ปุ่ม "🔄 Check for Update"**
- เทียบ `pluginmaster.json` AssemblyVersion vs MBB version ที่ติดตั้ง
- ถ้ามีใหม่กว่า → แจ้ง + ปุ่ม update

### Phase 2C — Optional Polish

**6. Inno Setup standalone installer**
สำหรับผู้ใช้ที่ดาวน์โหลด MBB จากเว็บก่อนติดตั้ง Dalamud:
- ติดตั้งไป `%LOCALAPPDATA%\Programs\MBB\`
- เขียน path ลง plugin config dir ล่วงหน้า (ถ้าเจอ Dalamud อยู่)
- แสดง Custom Repo URL ในหน้าจอสุดท้ายของ installer พร้อมปุ่ม copy

**7. Built-in Gemini API key wizard**
- ผู้ใช้ใหม่ติดที่นี่บ่อยที่สุด
- หน้า wizard ใน MBB เปิดเองครั้งแรก:
  1. ปุ่มเปิด aistudio.google.com (browser)
  2. ช่อง paste API key
  3. ปุ่ม Test → ส่ง dummy request → ✅
  4. Save → encrypted ใน settings.json

---

## Build Pipeline Standards

### PyInstaller Build Process

**ก่อน build ทุกครั้ง ต้องเช็ค:**

1. `version.py` ตรงกับ `pluginmaster.json` AssemblyVersion
2. `mbb.spec` data files ตรงกับไฟล์จริง (`npc.json` ไม่ใช่ `NPC.json`)
3. `requirements.txt` มี dependency ครบ
4. `.env` ไม่อยู่ใน build (ใช้ `.env.example` แทน)
5. ไม่มี API key หลุดใน `settings.json` หรือไฟล์อื่น

**คำสั่ง build:**
```bash
cd python-app
pyinstaller mbb.spec --clean --noconfirm --distpath ../dist_test
```

**ผลลัพธ์ที่คาดหวัง:**
- `dist_test/MBB/MBB.exe` (~28MB)
- `dist_test/MBB/_internal/` (~330MB) — PyQt6, tkinter, Pillow, fonts, assets
- รวม ~356MB

**หลัง build เช็ค:**
- [ ] รัน MBB.exe เปิดได้
- [ ] โหลด font Anuphan ถูกต้อง (ไม่ fallback)
- [ ] เปิด Settings panel ได้ (PyQt6 ทำงาน)
- [ ] เปิด Translated UI ได้ (Tkinter ทำงาน)
- [ ] เปิด Translated Logs ได้ (PyQt6)
- [ ] เปิด NPC Manager ได้ (PyQt6)
- [ ] Test Hook (Dialog/Battle/Cutscene) ส่งข้อความได้
- [ ] เชื่อมต่อ Dalamud bridge pipe ได้

### GitHub Release Checklist

ก่อนปล่อย version ใหม่:
- [ ] `bump_version.py X.Y.Z` (อัพ 8 ไฟล์อัตโนมัติ)
- [ ] Build C# plugin (Release config) → `plugins/DalamudMBBBridge/latest.zip`
- [ ] Build PyInstaller → zip dist folder
- [ ] อัพโหลด zip MBB.exe ไป GitHub Release
- [ ] อัพเดต `pluginmaster.json` LastUpdated timestamp
- [ ] Push to `main` branch → Dalamud จะเห็นอัพเดต ภายใน ~1 ชม
- [ ] CHANGELOG entry

---

## Verification UX (จุดสำคัญที่ผู้ใช้ต้องแน่ใจ)

ผู้ใช้จะรู้ได้ว่าทุกอย่างทำงานเมื่อ:

1. **ใน Dalamud** — `/xlplugins` แสดง "Magicite Babel Bridge" สถานะ Enabled (เขียว)
2. **ใน Plugin Config** (`/mbb`) — Setup Status panel มีไฟเขียวครบ 5 ข้อ
3. **ใน MBB app** — Header bar แสดง "✅ Dalamud Connected"
4. **Test message** — กด Test Hook ส่งข้อความได้ + แปลออกภาษาไทยถูกต้อง

ถ้าครบ 4 ข้อนี้ = พร้อมใช้งานจริง

---

## Files to Modify

| ไฟล์ | งาน | Phase |
|------|-----|-------|
| `DalamudMBBBridge/MBBConfigWindow.cs` | Setup Status panel + diagnostic buttons | 2A |
| `DalamudMBBBridge/DalamudMBBBridge.cs:LoadMbbPath` | Auto-discovery scanner | 2A |
| `DalamudMBBBridge/MBBConfigWindow.cs` | "Download MBB" button + HTTP client | 2B |
| `python-app/mbb.spec` | Fix `NPC.json` typo + verify imports | 1 |
| `INSTALLATION.md` | Rewrite flow ตาม Custom Repo + screenshots | 1 |
| Web landing page | Copy Repo URL button + GIF | 2A |
| `python-app/MBB.py` | Built-in Gemini API key wizard | 2C |

---

## Out-of-Scope (ตอนนี้)

- Auto-update MBB.exe ผ่าน plugin (ต้อง process restart, ซับซ้อน)
- Cross-platform (โปรเจ็คนี้ Windows-only เท่านั้น)
- Web-based config UI (overkill — ImGui ใน plugin เพียงพอ)
- Multi-user / shared install (assume single user)

---

## Modern Secret Management — แนวทางจัดเก็บ API Key

### ปัจจุบัน (v1.8.2)
```
python-app/.env             ← gitignored, plain text
GEMINI_API_KEY=AIzaSy...
```

ข้อดี: simple, dotenv standard
ข้อเสีย:
- Plain text ไฟล์ next to exe — anyone with file access อ่านได้
- ถ้าผู้ใช้ zip dist folder แชร์ → key หลุด (เคยเกิดมาก่อน — รอบนี้ revoke แล้ว)
- ไม่มี per-user encryption

### ระดับ 1 — Better .env hygiene (แนะนำเริ่มจากนี่ทันที)

**Move .env ออกจาก dist folder → ไป AppData**
```python
# api_key_manager.py — เพิ่ม path search
search_paths = [
    os.path.join(get_user_data_dir(), ".env"),  # %LOCALAPPDATA%\MBB_Dalamud\.env  ← preferred
    os.path.join(get_app_dir(), ".env"),         # next to exe (legacy fallback)
    os.path.join(os.getcwd(), ".env"),           # cwd (dev mode)
]
```

ข้อดี: ผู้ใช้ zip dist ส่งให้คนอื่น → key ไม่ตามไป (เพราะอยู่ AppData)
ข้อเสีย: ยังเป็น plain text

### ระดับ 2 — Windows DPAPI encryption (แนะนำสำหรับ v1.9+)

ใช้ `pywin32` `win32crypt.CryptProtectData` — **per-user encryption** (key เข้ารหัสด้วย Windows credential ของ user นั้น)

```python
# api_key_manager.py
import win32crypt

def save_api_key(key: str):
    encrypted = win32crypt.CryptProtectData(
        key.encode("utf-8"),
        "MBB Gemini API Key",  # description
        None, None, None, 0
    )
    path = os.path.join(get_user_data_dir(), "api_key.dat")
    with open(path, "wb") as f:
        f.write(encrypted)

def load_api_key() -> str | None:
    path = os.path.join(get_user_data_dir(), "api_key.dat")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        encrypted = f.read()
    desc, decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
    return decrypted.decode("utf-8")
```

ข้อดี:
- Decrypt ได้เฉพาะ user เดียวกัน — copy ไฟล์ไปเครื่องอื่นใช้ไม่ได้
- ไม่ต้อง prompt password
- ใช้ Windows native (no extra dependency)

ข้อเสีย: Windows-only (โปรเจ็คนี้ Windows อยู่แล้ว — ไม่เป็นปัญหา)

### ระดับ 3 — Windows Credential Manager (alternative)

ใช้ `keyring` library (cross-platform แต่บน Windows ใช้ Credential Manager backend)

```python
import keyring
keyring.set_password("MBB_Dalamud", "gemini_api_key", "AIzaSy...")
key = keyring.get_password("MBB_Dalamud", "gemini_api_key")
```

ข้อดี: standard library, GUI tool ดู Credential Manager ได้
ข้อเสีย: ต้องเพิ่ม `keyring` ใน requirements.txt

### Migration Plan

**Phase 1 (v1.8.x):** Status quo (.env next to exe)
**Phase 2 (v1.9.0):**
- เพิ่ม path search ไปยัง `%LOCALAPPDATA%\MBB_Dalamud\.env` ก่อน
- API Key Dialog เขียนไฟล์ที่ AppData แทน next to exe
- backwards-compat: ยังอ่าน next-to-exe ได้
**Phase 3 (v2.0):**
- DPAPI encryption เป็น default
- migration helper อ่าน .env เก่า → encrypt → ลบ .env

### Defense in depth — เพิ่มเติม

1. **`.gitignore` ครอบคลุม:**
```
.env
.env.local
*.key
api_key.dat
settings.json   # อาจมี user data
```

2. **Pre-commit hook** (.git/hooks/pre-commit):
```bash
#!/bin/sh
if git diff --cached --name-only | xargs grep -lE 'AIza[0-9A-Za-z_-]{35}' 2>/dev/null; then
    echo "❌ Potential Gemini API key in staged changes!"
    exit 1
fi
```

3. **Build script** ตรวจ dist:
```bash
# audit ก่อน zip
grep -rE 'AIza[0-9A-Za-z_-]{35}' dist_test/ && echo "LEAK!" && exit 1
```

4. **GitGuardian / TruffleHog** scan repo อย่างน้อยเดือนละครั้ง
