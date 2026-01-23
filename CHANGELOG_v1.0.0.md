# 📝 CHANGELOG - v1.0.0 Entry

**Date:** 2026-01-23
**Purpose:** New entry to prepend to CHANGELOG.md

---

## 🎯 [v1.0.0] - 2026-01-23 (Initial Public Release)

### 🎉 **First Official Release**

MBB Dalamud Bridge is now publicly available! Complete distribution package with custom Dalamud repository, plugin v1.0.0, and standalone Python executable.

### 📦 **Distribution Complete (Phase 1-3)**

This release represents the completion of all three distribution phases:
- ✅ **Phase 1:** Code Cleanup
- ✅ **Phase 2:** Custom Repository Setup
- ✅ **Phase 3:** PyInstaller Package

---

### 📦 **Phase 2: Custom Repository Setup (Complete)**

#### Repository Structure
- ✅ **pluginmaster.json** - Custom repository manifest
- ✅ **Plugin Package** - DalamudMBBBridge v1.0.0 (683 KB)
  - DalamudMBBBridge.dll
  - DalamudMBBBridge.json
  - icon.png
  - images/icon.png
- ✅ **GitHub Repository** - https://github.com/iarcanar/MBB_Dalamud
- ✅ **Custom Repository URL** - Live and accessible:
  ```
  https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
  ```

#### Files on GitHub
- pluginmaster.json (1.3 KB)
- README.md (6.8 KB) - Installation guide
- images/icon.png (486 KB)
- plugins/DalamudMBBBridge/latest.zip (683 KB)
- .gitignore - .env file protection

#### Plugin Metadata
- **Author:** iarcanar
- **Version:** 1.0.0
- **DalamudApiLevel:** 13
- **Distribution:** Custom Repository (immediate deployment)

---

### 🖥️ **Phase 3: PyInstaller Package (Complete)**

#### Executable Built
- ✅ **MBB.exe** - Standalone Python application (16 MB)
- ✅ **All Dependencies Bundled** - No Python installation required
- ✅ **Assets Included** - Fonts, images, NPC database
- ✅ **Release Package** - MBB_v1.0.0.zip (72 MB)

#### Package Contents
```
MBB_v1.0.0.zip/
├── MBB/
│   ├── MBB.exe (16 MB)
│   ├── _internal/
│   │   ├── fonts/ (Thai fonts: Anakotmai, FC Minimal, Google Sans)
│   │   ├── assets/ (60+ UI images)
│   │   ├── ui_components/ (Python modules)
│   │   ├── NPC.json (109 KB - FFXIV database)
│   │   └── .env.example (API key template)
│   └── README.txt (Quick start guide)
```

#### PyInstaller Configuration
- **Spec File:** mbb.spec (custom configuration)
- **Build Mode:** One-folder (windowed, no console)
- **Icon:** mbb_icon.png
- **Hidden Imports:** 50+ modules auto-detected
- **Excluded:** OCR dependencies (torch, opencv, easyocr)
- **Compression:** UPX enabled

#### Build Statistics
- Build Time: ~1.5 minutes
- Warnings: 1 (cryptography OpenSSL - non-critical)
- Errors: 0
- Package Size: 72 MB

---

### 📊 **Overall Project Statistics**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Code Lines** | ~5,000 | ~4,000 | -1,000 lines (-20%) |
| **Package Size** | ~300 MB | 72 MB | **-76%** |
| **Dependencies** | 15+ | 8 | -7 packages |
| **OCR Code** | 500 lines | 0 | **-100%** |
| **Swap System** | 150 lines | 0 | **-100%** |
| **Area Selection** | 350 lines | 0 | **-100%** |

---

### 🚀 **Installation for End Users**

**Total Time:** ~5 minutes

```
Step 1: Add Custom Repository (30 sec)
   /xlsettings → Experimental → Add URL

Step 2: Install Plugin (1 min)
   /xlplugins → "MBB Dalamud Bridge" → Install

Step 3: Download Python App (1 min)
   GitHub Releases → MBB_v1.0.0.zip (72 MB)

Step 4: Configure Path (2 min)
   /mbb → Browse MBB.exe → Save → Launch

Step 5: Set API Key (1 min)
   Settings → Gemini API Key → F9 to start
```

---

### ✨ **Features**

#### Core System
- **Real-time Thai Translation** via Google Gemini AI
- **Text Hook Architecture** - Direct game text (100% text hook, 0% OCR)
- **Character Database** - NPC personality tracking (109 KB)
- **Translation Memory** - Caches for consistency

#### User Interface
- **6 Theme Presets** - Cyberpunk, Ocean, Sunset, Forest, Royal, Rose
- **Auto-show/hide UI** - Appears only when needed
- **Mini/Full UI Modes** - Toggle with F11
- **Thai Font Support** - Anakotmai, Tahoma, Sarabun

#### Integration
- **Named Pipe Communication** - C# ↔ Python bridge
- **Hotkey Support** - F9/F10/F11
- **One-Click Launch** - From Dalamud plugin
- **Settings Persistence** - Saved to %LocalAppData%\MBB_Dalamud

---

### 🔗 **Distribution Links**

- **Repository:** https://github.com/iarcanar/MBB_Dalamud
- **Custom Repo URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
- **Releases:** https://github.com/iarcanar/MBB_Dalamud/releases
- **Issues:** https://github.com/iarcanar/MBB_Dalamud/issues

---

### 📚 **New Documentation**

- **INSTALLATION_TESTING.md** - Testing checklist for end-to-end installation
- **GITHUB_RELEASE_INSTRUCTIONS.md** - Manual upload guide for releases
- **PHASE2_COMPLETE.md** - Phase 2 completion report
- **PHASE2_PROGRESS.md** - Detailed progress tracking

---

### 🐛 **Known Issues**

None currently reported. This is the first public release.

---

### 📝 **Technical Details**

#### Technologies
- **Plugin:** C# (.NET 10.0-windows), Dalamud SDK 13
- **App:** Python 3.11+
- **AI:** Google Gemini API
- **UI:** Tkinter with custom themes
- **Packaging:** PyInstaller 6.13.0

#### System Requirements
- Windows 10/11 (64-bit)
- FFXIV with Dalamud installed
- Internet connection
- Google Gemini API key (free tier available)

---

**Version:** 1.0.0 build 01232026-01
**Release Type:** Custom Repository Distribution
**License:** MIT
**Developer:** iarcanar

---

**Enjoy real-time Thai translation in FFXIV! 🎮✨**
