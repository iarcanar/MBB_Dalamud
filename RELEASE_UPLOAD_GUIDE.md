# 🚀 Quick Release Upload Guide

**ไฟล์พร้อม Upload:** `c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip` (72 MB)

---

## ขั้นตอนการ Upload (3 นาที)

### 1. ไปที่ GitHub Releases
```
https://github.com/iarcanar/MBB_Dalamud/releases
```

### 2. คลิก "Draft a new release"

### 3. กรอกข้อมูล Release

**Tag:**
```
v1.0.0
```

**Release title:**
```
MBB Dalamud Bridge v1.0.0 - Initial Release
```

**Description:** (คัดลอกจากด้านล่าง)

---

## 📋 Release Notes (คัดลอกนี้)

```markdown
# MBB Dalamud Bridge v1.0.0

**Release Date:** 2026-01-23
**Build:** 01232026-01

## 🎉 First Official Release

Real-time Thai translation for Final Fantasy XIV via Dalamud + Gemini AI!

---

## ✨ Features

### Core Translation
- ✅ Real-time Thai translation (Google Gemini AI)
- ✅ Text Hook architecture (no OCR needed)
- ✅ NPC character database
- ✅ Translation memory & caching

### User Interface
- ✅ Auto-show/hide UI
- ✅ Mini UI mode for gameplay
- ✅ Full Control Panel
- ✅ 6 theme presets (Cyberpunk, Ocean, Sunset, Forest, Royal, Rose)
- ✅ Thai font support (Tahoma, Anakotmai, Sarabun)

### Dalamud Integration
- ✅ Named Pipe communication (C# ↔ Python)
- ✅ One-click launch from plugin
- ✅ Hotkey support (F9/F10/F11)

---

## 📥 Installation (5 minutes)

### Step 1: Add Custom Repository (30 sec)
1. In FFXIV, type: `/xlsettings`
2. Go to **Experimental** tab
3. Add URL:
   ```
   https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
   ```
4. Save

### Step 2: Install Plugin (1 min)
1. Type: `/xlplugins`
2. Search: **MBB Dalamud Bridge**
3. Click **Install**

### Step 3: Download Python App (1 min)
1. Download **MBB_v1.0.0.zip** below (72 MB)
2. Extract to any folder (e.g., `C:\MBB\`)

### Step 4: Configure Path (2 min)
1. In FFXIV, type: `/mbb`
2. Browse → Select `MBB.exe`
3. Save → Launch

### Step 5: Set API Key (1 min)
1. Get free API: https://aistudio.google.com/app/apikey
2. MBB App → Settings → Paste key → Save
3. Press **F9** to start translation

---

## ⌨️ Hotkeys

| Key | Action |
|-----|--------|
| **F9** | Start/Stop translation |
| **F10** | Clear screen |
| **F11** | Toggle Mini/Full UI |

---

## 📦 Package Contents

- **MBB.exe** (16 MB) - Standalone application
- **Fonts** - Thai language support
- **Assets** - UI themes & images
- **NPC.json** (109 KB) - FFXIV character database
- **README.txt** - Quick start guide

**Total Size:** 72 MB (vs 300 MB before optimization = 76% smaller!)

---

## 🔧 Technical Details

### Technologies
- **Plugin:** C# (.NET 10.0), Dalamud API 13
- **App:** Python 3.11+, PyInstaller 6.9
- **AI:** Google Gemini API
- **UI:** Tkinter with custom themes

### Optimizations (Phase 1 Cleanup)
- ❌ Removed OCR system (~500 lines, 270 MB)
- ❌ Removed swap data system (~150 lines)
- ❌ Removed area selection (~350 lines)
- ✅ Result: 76% smaller package

---

## 🐛 Known Issues

None reported yet! Please submit issues on GitHub.

---

## 📝 Full Documentation

- **Installation Guide:** [README.md](https://github.com/iarcanar/MBB_Dalamud/blob/main/README.md)
- **Testing Guide:** [INSTALLATION_TESTING.md](https://github.com/iarcanar/MBB_Dalamud/blob/main/INSTALLATION_TESTING.md)
- **Changelog:** [CHANGELOG.md](https://github.com/iarcanar/MBB_Dalamud/blob/main/CHANGELOG.md)

---

## 🔗 Links

- **Repository:** https://github.com/iarcanar/MBB_Dalamud
- **Custom Repo URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
- **Issues:** https://github.com/iarcanar/MBB_Dalamud/issues

---

## 🙏 Credits

**Developer:** iarcanar
**Framework:** Dalamud + Python + Google Gemini AI
**License:** MIT

---

**Enjoy real-time Thai translation in FFXIV! 🎮✨**
```

---

### 4. Upload File

1. คลิก **"Attach binaries"**
2. เลือกไฟล์: `c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip`
3. รอจนอัปโหลดเสร็จ (72 MB ~ 2-3 นาที)

### 5. Publish

1. เลือก **"Set as the latest release"** ✓
2. คลิก **"Publish release"**

---

## ✅ เสร็จแล้ว!

Download URL จะเป็น:
```
https://github.com/iarcanar/MBB_Dalamud/releases/download/v1.0.0/MBB_v1.0.0.zip
```

---

## 🧪 ทดสอบหลัง Upload

ทดสอบตามคำแนะนำใน: `INSTALLATION_TESTING.md`

**Quick Test (5 min):**
1. ✅ Add custom repository URL
2. ✅ Install plugin via /xlplugins
3. ✅ Download MBB_v1.0.0.zip
4. ✅ Extract & launch MBB.exe
5. ✅ Set API key & press F9
6. ✅ Verify translation works

---

**ไฟล์พร้อม Upload:** `c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip`
