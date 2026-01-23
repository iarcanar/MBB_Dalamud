# Phase 2: Create Dalamud Custom Repository - Task List

**Date:** 2026-01-23
**Status:** IN PROGRESS

---

## ✅ Task 2.1: Create Repository Structure (COMPLETED)

### Folder Structure Created

```
repo-structure/
├── pluginmaster.json          ✅ Created
├── plugins/
│   └── DalamudMBBBridge/
│       └── latest.zip         ⏳ Pending (Task 2.2)
├── releases/
│   └── MBB_v1.0.0.zip        ⏳ Pending (Task 3.4)
├── images/
│   └── icon.png              ✅ Copied
└── README.md                 ✅ Created
```

### Files Created

#### pluginmaster.json
- ✅ Repository manifest with correct GitHub URLs
- ✅ Author: iarcanar
- ✅ Version: 1.0.0 (distribution version)
- ✅ DalamudApiLevel: 13
- ✅ Download links pointing to raw.githubusercontent.com
- ✅ Icon URL configured
- ✅ Tags: Translation, Text Hook, Bridge, MBB, Thai, Utility

#### README.md
- ✅ Comprehensive installation guide (5-step process, ~5 minutes total)
- ✅ Feature overview
- ✅ Usage commands and hotkeys
- ✅ Troubleshooting section
- ✅ Contributing guidelines
- ✅ MIT License text
- ✅ Contact information

#### images/icon.png
- ✅ Plugin icon copied from root directory

---

## ⏳ Task 2.2: Build Plugin Package (NEXT)

### Objective
Create `latest.zip` containing plugin DLL and assets for Dalamud installation

### Steps Required

1. **Update Plugin Version** (1.5.28 → 1.0.0)
   - File: `dalamud-plugin/DalamudMBBBridge/DalamudMBBBridge.json`
   - Update `AssemblyVersion` to "1.0.0"
   - Update `Name` to match repository (shorter, cleaner)

2. **Update .csproj Version**
   - File: `dalamud-plugin/DalamudMBBBridge/DalamudMBBBridge.csproj`
   - Update `<Version>` tag to "1.0.0"

3. **Build Plugin in Release Mode**
   ```bash
   cd dalamud-plugin/DalamudMBBBridge
   dotnet build -c Release
   ```

4. **Create Plugin ZIP Package**
   - Contents required:
     - `DalamudMBBBridge.dll`
     - `DalamudMBBBridge.json`
     - `icon.png`
     - `images/icon.png`
   - Source: `dalamud-plugin/DalamudMBBBridge/bin/Release/win-x64/DalamudMBBBridge/`
   - Destination: `repo-structure/plugins/DalamudMBBBridge/latest.zip`

5. **Verify Package**
   - Extract and check all files present
   - Verify JSON has correct metadata
   - Check icon files are valid PNGs

### Files to Modify

| File | Change | Purpose |
|------|--------|---------|
| `DalamudMBBBridge.json` | Version 1.5.28 → 1.0.0 | Distribution version |
| `DalamudMBBBridge.csproj` | Version 1.5.28 → 1.0.0 | .NET project version |

---

## ⏳ Task 2.3: Verify pluginmaster.json (READY)

### Current Configuration

```json
{
  "Author": "iarcanar",
  "Name": "MBB Dalamud Bridge",
  "InternalName": "DalamudMBBBridge",
  "AssemblyVersion": "1.0.0",
  "RepoUrl": "https://github.com/iarcanar/MBB_Dalamud",
  "DownloadLinkInstall": "https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/plugins/DalamudMBBBridge/latest.zip",
  "IconUrl": "https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/images/icon.png"
}
```

### Verification Checklist
- ✅ GitHub username correct: iarcanar
- ✅ Repository name correct: MBB_Dalamud
- ✅ Branch correct: main
- ✅ Download links use raw.githubusercontent.com
- ✅ Icon URL points to images/icon.png
- ⏳ Test download links after upload

---

## ⏳ Task 2.4: GitHub Upload (PENDING)

### Files to Upload

1. **Root Directory**
   - `pluginmaster.json` → Upload to root
   - `README.md` → Replace existing

2. **images/ Directory**
   - `icon.png` → Upload to images/

3. **plugins/DalamudMBBBridge/ Directory**
   - `latest.zip` → Upload after Task 2.2 complete

### Upload Steps

1. Navigate to https://github.com/iarcanar/MBB_Dalamud
2. Create `images` folder and upload icon.png
3. Create `plugins/DalamudMBBBridge` nested folders
4. Upload pluginmaster.json to root
5. Update README.md in root
6. Verify raw URLs are accessible:
   - https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
   - https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/images/icon.png
   - https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/plugins/DalamudMBBBridge/latest.zip

---

## 📋 Testing Checklist (After Upload)

### Phase 2 Testing
- [ ] pluginmaster.json is accessible via raw URL
- [ ] Icon displays correctly when accessed via raw URL
- [ ] Add custom repository in FFXIV `/xlsettings`
- [ ] Plugin appears in `/xlplugins` installer
- [ ] Plugin shows correct icon and description
- [ ] Plugin installs successfully
- [ ] Plugin config window opens with `/mbb`
- [ ] Path selection UI works correctly

### Error Cases to Test
- [ ] Invalid repository URL → Shows error message
- [ ] Missing latest.zip → Installation fails gracefully
- [ ] Corrupted icon → Shows placeholder
- [ ] Wrong DalamudApiLevel → Shows compatibility warning

---

## 🎯 Success Criteria

Phase 2 is complete when:
1. ✅ Repository structure exists locally
2. ⏳ Plugin package (latest.zip) is built and tested
3. ⏳ All files uploaded to GitHub
4. ⏳ Raw URLs are accessible
5. ⏳ Plugin installs via custom repository in FFXIV
6. ⏳ Plugin loads without errors
7. ⏳ Config window opens and shows correct UI

---

## 📝 Notes

### Version Strategy
- **Plugin Version:** 1.0.0 (clean distribution release)
- **Python App Version:** Will be 1.0.0 after PyInstaller packaging (Phase 3)
- **Previous Dev Version:** 1.5.28 (not distributed)

### Repository URLs
- **Main Repo:** https://github.com/iarcanar/MBB_Dalamud
- **Raw Base:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/
- **Pluginmaster:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json

### Important Files
- **Local Structure:** `c:\MBB_Dalamud\repo-structure\`
- **Plugin Build Output:** `dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64\DalamudMBBBridge\`
- **Icon Source:** `c:\MBB_Dalamud\icon.png`

---

**Next Action:** Update plugin version to 1.0.0 and build Release package (Task 2.2)
