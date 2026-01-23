# GitHub Upload Instructions - Phase 2

**Date:** 2026-01-23
**Repository:** https://github.com/iarcanar/MBB_Dalamud

---

## ✅ Files Ready for Upload

All files in `c:\MBB_Dalamud\repo-structure\` are ready to be uploaded to GitHub.

### Repository Structure

```
MBB_Dalamud/  (GitHub root)
├── pluginmaster.json          ✅ Ready (1.3 KB)
├── README.md                  ✅ Ready (6.8 KB) - Replace existing
├── images/
│   └── icon.png              ✅ Ready (325 KB)
└── plugins/
    └── DalamudMBBBridge/
        └── latest.zip        ✅ Ready (668 KB)
```

---

## 📋 Upload Steps

### Step 1: Navigate to Repository
Go to: https://github.com/iarcanar/MBB_Dalamud

### Step 2: Upload pluginmaster.json

1. Click **"Add file"** → **"Upload files"**
2. Drag `pluginmaster.json` from `c:\MBB_Dalamud\repo-structure\`
3. Commit message: "Add pluginmaster.json for custom repository"
4. Click **"Commit changes"**

### Step 3: Replace README.md

1. Click on existing `README.md` in repository
2. Click **"Edit"** (pencil icon)
3. Delete all content
4. Copy content from `c:\MBB_Dalamud\repo-structure\README.md`
5. Paste into GitHub editor
6. Commit message: "Update README with installation guide"
7. Click **"Commit changes"**

### Step 4: Create images/ Folder and Upload Icon

1. Click **"Add file"** → **"Upload files"**
2. Drag `icon.png` from `c:\MBB_Dalamud\repo-structure\images\`
3. In the path field above the file, type: `images/`
4. This will create the images folder
5. Commit message: "Add plugin icon"
6. Click **"Commit changes"**

### Step 5: Create plugins/DalamudMBBBridge/ Folder and Upload Package

1. Click **"Add file"** → **"Upload files"**
2. Drag `latest.zip` from `c:\MBB_Dalamud\repo-structure\plugins\DalamudMBBBridge\`
3. In the path field, type: `plugins/DalamudMBBBridge/`
4. This will create the nested folder structure
5. Commit message: "Add plugin package v1.0.0"
6. Click **"Commit changes"**

---

## 🔍 Verification Steps

After uploading all files, verify these raw URLs are accessible:

### 1. Pluginmaster JSON
**URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json

**Expected:** JSON file with plugin metadata

### 2. Plugin Icon
**URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/images/icon.png

**Expected:** MBB logo image (325 KB PNG)

### 3. Plugin Package
**URL:** https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/plugins/DalamudMBBBridge/latest.zip

**Expected:** ZIP file download (668 KB)

### 4. README
**URL:** https://github.com/iarcanar/MBB_Dalamud/blob/main/README.md

**Expected:** Formatted installation guide with sections:
- What is MBB?
- Installation Guide (5 steps)
- Usage commands
- Troubleshooting
- Features list

---

## 🧪 Testing in FFXIV

Once files are uploaded and verified:

### Add Custom Repository

1. Launch FFXIV
2. Open Dalamud settings:
   ```
   /xlsettings
   ```
3. Go to **"Experimental"** tab
4. Add custom repository URL:
   ```
   https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
   ```
5. Click **"Save"**

### Install Plugin

1. Open plugin installer:
   ```
   /xlplugins
   ```
2. Search for **"MBB Dalamud Bridge"**
3. Verify plugin shows:
   - ✅ Name: "MBB Dalamud Bridge"
   - ✅ Author: "iarcanar"
   - ✅ Version: "1.0.0"
   - ✅ Description: "Real-time Thai translation for FFXIV"
   - ✅ Icon: MBB logo
4. Click **"Install"**
5. Wait for installation to complete

### Verify Plugin Loaded

1. Check plugin list shows "MBB Dalamud Bridge" as installed
2. Open config window:
   ```
   /mbb
   ```
3. Verify UI shows:
   - ✅ Path selection field
   - ✅ Browse button
   - ✅ Launch button
   - ✅ Status display

---

## 📝 Expected Results

### Pluginmaster.json Content

```json
[
  {
    "Author": "iarcanar",
    "Name": "MBB Dalamud Bridge",
    "Punchline": "Real-time Thai translation for FFXIV",
    "InternalName": "DalamudMBBBridge",
    "AssemblyVersion": "1.0.0",
    "RepoUrl": "https://github.com/iarcanar/MBB_Dalamud",
    "DalamudApiLevel": 13,
    "DownloadLinkInstall": "https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/plugins/DalamudMBBBridge/latest.zip",
    "IconUrl": "https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/images/icon.png"
  }
]
```

### Plugin Package Contents (latest.zip)

- `DalamudMBBBridge.dll` (59 KB)
- `DalamudMBBBridge.json` (877 bytes)
- `icon.png` (325 KB)
- `images/icon.png` (325 KB)

---

## ❌ Common Issues

### Issue 1: "Failed to add custom repository"
- **Check:** URL is exactly correct (no typos)
- **Check:** `pluginmaster.json` is valid JSON (use JSONLint)
- **Fix:** Copy URL exactly from this guide

### Issue 2: "Plugin not found in installer"
- **Check:** Repository was added successfully
- **Check:** Click "Refresh" in plugin installer
- **Fix:** Restart Dalamud (`/xlplugins` → close → reopen)

### Issue 3: "Download failed" when installing
- **Check:** `latest.zip` uploaded correctly to GitHub
- **Check:** Raw URL is accessible in browser
- **Fix:** Re-upload `latest.zip` if corrupted

### Issue 4: Icon not showing
- **Check:** `icon.png` uploaded to `images/` folder
- **Check:** Raw URL returns image (not 404)
- **Fix:** Re-upload icon to correct path

### Issue 5: Plugin loads but shows old version
- **Check:** Clear Dalamud plugin cache
- **Fix:** Delete `%APPDATA%\XIVLauncher\devPlugins\DalamudMBBBridge` folder

---

## 🔄 Update Process (Future)

When releasing new versions:

1. Update version in `DalamudMBBBridge.json` and `.csproj`
2. Build plugin: `dotnet build -c Release`
3. Create new `latest.zip` with updated files
4. Upload new `latest.zip` to GitHub (overwrite old one)
5. Update `AssemblyVersion` in `pluginmaster.json`
6. Dalamud will auto-detect update and notify users

---

## 📊 Upload Checklist

Before marking Phase 2 complete:

- [ ] pluginmaster.json uploaded to root
- [ ] README.md updated in root
- [ ] images/icon.png uploaded
- [ ] plugins/DalamudMBBBridge/latest.zip uploaded
- [ ] All raw URLs accessible (tested in browser)
- [ ] Custom repository added in FFXIV
- [ ] Plugin appears in installer
- [ ] Plugin installs successfully
- [ ] `/mbb` command opens config window
- [ ] Plugin loads without errors

---

## 📞 Next Steps After Upload

1. ✅ **Complete Phase 2 Testing**
   - Add repository in FFXIV
   - Install plugin
   - Verify functionality

2. ⏳ **Begin Phase 3: PyInstaller Package**
   - Create `mbb.spec` file
   - Build Python app executable
   - Create release package
   - Upload to GitHub Releases

3. ⏳ **Documentation**
   - Update CHANGELOG.md with v1.0.0
   - Create video tutorial (optional)
   - Write troubleshooting FAQ

---

**Repository:** https://github.com/iarcanar/MBB_Dalamud
**Local Files:** c:\MBB_Dalamud\repo-structure\
**Status:** Ready for upload
**Version:** 1.0.0

---

**Created by:** Claude Code
**Date:** 2026-01-23
**Phase:** 2 - Create Dalamud Custom Repository
