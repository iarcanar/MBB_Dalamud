# GitHub Release Upload Instructions

**File Ready:** `c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip` (72 MB)

---

## Option 1: Manual Upload via GitHub Web Interface (Recommended)

### Step 1: Go to Releases Page
Navigate to: https://github.com/iarcanar/MBB_Dalamud/releases

### Step 2: Create New Release
1. Click **"Create a new release"** or **"Draft a new release"**

### Step 3: Fill Release Information

**Tag Version:**
```
v1.0.0
```

**Release Title:**
```
MBB Dalamud Bridge v1.0.0 - Initial Release
```

**Release Description:**
(Copy from below)

---

### Release Notes (Copy This):

```markdown
# MBB Dalamud Bridge v1.0.0

**Release Date:** 2026-01-23
**Build:** 01232026-01

## 🎉 Initial Public Release

First official release of MBB (Magic Babel Bridge) - Real-time Thai translation for Final Fantasy XIV!

## ✨ Features

### Core Translation System
- **Real-time Thai Translation** via Google Gemini AI
- **Text Hook Architecture** - Direct game text extraction (no OCR)
- **Character Database** - NPC personality and terminology tracking
- **Translation Memory** - Caches translations for consistency

### User Interface
- **Auto-show/hide UI** - Appears only when needed
- **Mini UI Mode** - Compact overlay during gameplay
- **Full Control Panel** - Complete settings and management
- **6 Theme Presets** - Cyberpunk, Ocean, Sunset, Forest, Royal, Rose
- **Thai Font Support** - Tahoma, Anakotmai, Sarabun

### Dalamud Integration
- **Named Pipe Communication** - C# ↔ Python bridge
- **One-Click Launch** - Start directly from Dalamud plugin
- **Seamless Gameplay** - Minimal performance impact
- **Hotkey Support** - F9/F10/F11 for quick controls

## 📦 What's Included

- **MBB.exe** - Standalone Python application (16 MB)
- **Fonts** - Thai language support
- **Assets** - UI images and themes
- **NPC Database** - FFXIV character database (109 KB)
- **README.txt** - Quick start guide

## 📥 Installation Guide

### Step 1: Add Custom Repository (30 seconds)
1. Open FFXIV, type: `/xlsettings`
2. Go to **Experimental** tab
3. Add URL:
   ```
   https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
   ```
4. Save

### Step 2: Install Plugin (1 minute)
1. Type: `/xlplugins`
2. Search: **MBB Dalamud Bridge**
3. Click **Install**

### Step 3: Download Python App (1 minute)
1. Download **MBB_v1.0.0.zip** below
2. Extract to any folder (e.g., `C:\MBB\`)

### Step 4: Configure Path (2 minutes)
1. In FFXIV, type: `/mbb`
2. Browse → Select `MBB.exe`
3. Save → Launch

### Step 5: Set API Key (1 minute)
1. Get free API key: https://aistudio.google.com/app/apikey
2. MBB App → Settings → Paste key → Save
3. Press **F9** to start translation

**Total Time:** ~5 minutes

## ⌨️ Hotkeys

| Key | Action |
|-----|--------|
| **F9** | Start/Stop translation |
| **F10** | Clear translation screen |
| **F11** | Toggle Mini/Full UI mode |

## 🔧 Commands (in FFXIV)

| Command | Description |
|---------|-------------|
| `/mbb` | Open configuration window |
| `/mbb launch` | Launch Python app |

## 📊 Technical Details

### Package Size
- **Before Optimization:** ~300 MB (with OCR)
- **After Cleanup:** ~30-50 MB (83% smaller)
- **MBB.exe:** 16 MB
- **Total Package:** ~72 MB

### Dependencies Removed (Phase 1)
- ❌ OCR System (~500 lines, 270 MB)
- ❌ Swap Data System (~150 lines)
- ❌ Area Selection (~350 lines)

### Technologies
- **Plugin:** C# (.NET 10.0), Dalamud SDK 13
- **App:** Python 3.11+
- **AI:** Google Gemini API
- **UI:** Tkinter with custom themes

## 🐛 Known Issues

None currently reported. Please report issues on GitHub!

## 📝 Changelog

### Added
- ✅ Real-time Thai translation system
- ✅ Dalamud plugin integration
- ✅ Custom repository distribution
- ✅ 6 UI themes
- ✅ Character database management
- ✅ Translation logging
- ✅ Hotkey support (F9/F10/F11)

### Removed
- ❌ OCR system (project is 100% text hook)
- ❌ Database swapping (FFXIV only)
- ❌ Manual area selection (not needed)

## 🔗 Links

- **Repository:** https://github.com/iarcanar/MBB_Dalamud
- **Custom Repo URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
- **Issues:** https://github.com/iarcanar/MBB_Dalamud/issues

## 💡 Support

Having trouble? Check:
1. README.txt inside the package
2. GitHub Issues
3. Custom repository URL is added correctly
4. API key is set in app

## 🙏 Credits

- **Developer:** iarcanar
- **Framework:** Dalamud + Python + Google Gemini AI
- **License:** MIT

---

**Enjoy real-time Thai translation in FFXIV! 🎮✨**
```

---

### Step 4: Upload File
1. Scroll down to **"Attach binaries"** section
2. Drag and drop or click to upload:
   ```
   c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip
   ```
3. Wait for upload to complete (72 MB may take 1-2 minutes)

### Step 5: Publish
1. Click **"Publish release"**
2. Release will be live immediately

---

## Option 2: Install GitHub CLI (gh)

If you want to use command-line:

### Install gh CLI:
```bash
winget install --id GitHub.cli
```

### Then run:
```bash
cd c:\MBB_Dalamud
gh release create v1.0.0 \
  --title "MBB Dalamud Bridge v1.0.0 - Initial Release" \
  --notes-file GITHUB_RELEASE_INSTRUCTIONS.md \
  "c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip"
```

---

## Verify Release

After upload, check:
1. Go to: https://github.com/iarcanar/MBB_Dalamud/releases
2. Verify **v1.0.0** is visible
3. Click on **MBB_v1.0.0.zip** to test download link
4. Check file size shows ~72 MB

---

**File Location:** `c:\MBB_Dalamud\python-app\dist\MBB_v1.0.0.zip`
**Size:** 72 MB
**Ready to upload!**
