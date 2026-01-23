# MBB Dalamud v1.0.0 - Master Distribution Plan

**Build:** 01222026-01
**Goal:** Dalamud Custom Plugin Repository Distribution

---

## Project Status

### ✅ Phase 1: Code Cleanup (COMPLETED)

All hardcoded paths removed and codebase made distribution-ready:

- [x] Created `python-app/resource_utils.py` for dynamic path management
- [x] Fixed `DalamudMBBBridge.cs` - removed hardcoded default path
- [x] Fixed `MBBConfigWindow.cs` - updated path suggestions
- [x] Fixed `translated_ui.py` - uses `resource_path()` for fonts
- [x] Fixed `text_corrector.py` - removed hardcoded NPC path
- [x] Fixed `translation_logger.py` - uses user data directory
- [x] Created `.env.example` template
- [x] Created `.gitignore` to protect secrets

---

## 📋 Phase 2: Create Dalamud Custom Repository

### Objective
Set up GitHub repository with `pluginmaster.json` for Dalamud auto-discovery

### Tasks

#### 2.1 Create Repository Structure
```
MBB-DalamudRepo/
├── pluginmaster.json          # Main repository manifest
├── plugins/
│   └── DalamudMBBBridge/
│       └── latest.zip         # Plugin DLL package
├── releases/
│   └── MBB_v1.0.0.zip        # Python app executable
├── images/
│   └── icon.png              # Plugin icon
└── README.md                 # Installation guide
```

#### 2.2 Build Plugin Package

**Steps:**
1. Build plugin in Release mode:
   ```bash
   cd dalamud-plugin/DalamudMBBBridge
   dotnet build -c Release
   ```

2. Create plugin ZIP package containing:
   - DalamudMBBBridge.dll
   - DalamudMBBBridge.json
   - icon.png
   - images/icon.png

#### 2.3 Create pluginmaster.json

**Template:** See `pluginmaster.json.template` below

```json
[
  {
    "Author": "iarcanar",
    "Name": "MBB Dalamud Bridge",
    "Punchline": "Real-time Thai translation for FFXIV",
    "Description": "แปลภาษา FFXIV เป็นไทยแบบ real-time ผ่าน Gemini AI",
    "InternalName": "DalamudMBBBridge",
    "AssemblyVersion": "1.0.0",
    "RepoUrl": "https://github.com/YOUR_USERNAME/MBB-DalamudRepo",
    "ApplicableVersion": "any",
    "DalamudApiLevel": 13,
    "DownloadLinkInstall": "https://raw.githubusercontent.com/YOUR_USERNAME/MBB-DalamudRepo/main/plugins/DalamudMBBBridge/latest.zip",
    "DownloadLinkUpdate": "https://raw.githubusercontent.com/YOUR_USERNAME/MBB-DalamudRepo/main/plugins/DalamudMBBBridge/latest.zip",
    "IconUrl": "https://raw.githubusercontent.com/YOUR_USERNAME/MBB-DalamudRepo/main/images/icon.png"
  }
]
```

#### 2.4 GitHub Setup

1. Create new GitHub repository: `MBB-DalamudRepo`
2. Enable GitHub Pages (optional but recommended)
3. Upload all files
4. Get raw URL: `https://raw.githubusercontent.com/YOUR_USERNAME/MBB-DalamudRepo/main/pluginmaster.json`

---

## 🔧 Phase 3: PyInstaller Package

### Objective
Create standalone executable of Python app

### Tasks

#### 3.1 Install PyInstaller
```bash
pip install pyinstaller
```

#### 3.2 Create mbb.spec File

**Location:** `python-app/mbb.spec`

**Key configurations:**
- Include all assets (fonts, images, npc.json)
- Hidden imports for all dependencies
- No console window
- Icon from assets

#### 3.3 Build Executable

```bash
cd python-app
pyinstaller mbb.spec --clean
```

**Output:** `dist/MBB/MBB.exe` with all dependencies

#### 3.4 Create Release Package

**Structure of MBB_v1.0.0.zip:**
```
MBB_v1.0.0/
├── MBB.exe
├── _internal/          # PyInstaller dependencies
├── fonts/
├── assets/
├── npc.json
├── .env.example
└── README.txt
```

#### 3.5 Upload to GitHub Releases

1. Go to repository → Releases → Create new release
2. Tag: `v1.0.0`
3. Upload `MBB_v1.0.0.zip`
4. Add release notes

---

## 📝 Testing Checklist

### Phase 2 Testing
- [ ] Plugin installs via custom repository URL
- [ ] Plugin shows correct icon and description
- [ ] Plugin config window opens with `/mbb`
- [ ] Path selection works correctly

### Phase 3 Testing
- [ ] MBB.exe runs on clean Windows (no Python installed)
- [ ] All assets load correctly (fonts, images)
- [ ] Settings saved to AppData\Local\MBB_Dalamud
- [ ] Connects to Dalamud plugin via Named Pipe
- [ ] Translation works end-to-end

### Integration Testing
- [ ] Fresh FFXIV install test
- [ ] Complete installation flow
- [ ] Real translation test in game
- [ ] Auto-update test

---

## 🎯 Final User Installation Flow

### Step 1: Add Custom Repository (30 seconds)
1. Open FFXIV, type `/xlsettings`
2. Go to "Experimental" tab
3. Add URL: `https://raw.githubusercontent.com/YOUR_USERNAME/MBB-DalamudRepo/main/pluginmaster.json`
4. Save

### Step 2: Install Plugin (1 minute)
1. Type `/xlplugins`
2. Find "MBB Dalamud Bridge"
3. Click "Install"

### Step 3: Download Python App (1 minute)
1. Go to releases page
2. Download `MBB_v1.0.0.zip`
3. Extract anywhere

### Step 4: Configure (2 minutes)
1. In FFXIV, type `/mbb`
2. Browse → Select `MBB.exe`
3. Save path
4. Click "Launch"

### Step 5: Set API Key (1 minute)
1. Open MBB app
2. Settings → Paste Gemini API Key
3. Start translation (F9)

**Total time:** ~5 minutes

---

## 🔄 Version Update Process

### To release new version:

1. Update version numbers in:
   - `DalamudMBBBridge.csproj`
   - `DalamudMBBBridge.json`
   - `pluginmaster.json`

2. Build and package:
   ```bash
   dotnet build -c Release
   pyinstaller mbb.spec --clean
   ```

3. Create ZIP packages
4. Upload to GitHub
5. Update pluginmaster.json
6. Dalamud auto-detects update

---

## 📦 Important Files Reference

### Files Created in Phase 1:
- [python-app/resource_utils.py](python-app/resource_utils.py) - Path utilities
- [python-app/.env.example](python-app/.env.example) - API key template
- [.gitignore](.gitignore) - Git ignore rules

### Files Modified in Phase 1:
- [dalamud-plugin/DalamudMBBBridge/DalamudMBBBridge.cs](dalamud-plugin/DalamudMBBBridge/DalamudMBBBridge.cs)
- [dalamud-plugin/DalamudMBBBridge/MBBConfigWindow.cs](dalamud-plugin/DalamudMBBBridge/MBBConfigWindow.cs)
- [python-app/translated_ui.py](python-app/translated_ui.py)
- [python-app/text_corrector.py](python-app/text_corrector.py)
- [python-app/translation_logger.py](python-app/translation_logger.py)

### Files to Create in Phase 2:
- `pluginmaster.json`
- `MBB-DalamudRepo/README.md`
- Plugin package ZIP

### Files to Create in Phase 3:
- `python-app/mbb.spec`
- Release package ZIP
- Quick start guide

---

## 🛠️ Next Steps

1. **Immediate:** Start Phase 2 in VSCode
2. **Create:** GitHub repository structure
3. **Build:** Plugin package
4. **Test:** Installation flow
5. **Document:** User guide

---

**Project:** MBB Dalamud Custom Repository
**Version:** 1.0.0 build 01222026-01
**Status:** Phase 1 Complete ✅
**Next:** Phase 2 - Repository Setup

---

**Developer:** iarcanar
**License:** MIT
**Framework:** Dalamud + Python + Gemini AI
