# 🏗️ Build Protocol Documentation

## Official Build Path
**Starting from Version 1.5.2, all builds will be consolidated to a single location:**

```
C:\Yariman_Babel\MbbDalamud_bridge\dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64
```

## Build Protocol Rules

### ✅ **Primary Build Location (ONLY)**
- **Path:** `C:\Yariman_Babel\MbbDalamud_bridge\dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64\DalamudMBBBridge.dll`
- **Purpose:** Single source of truth for all builds
- **Action:** All development, testing, and distribution will use this location

### ❌ **Deprecated Paths (NO LONGER USED)**
- `C:\Users\arcan\Documents\DalamudMBBBridge_PreReceiveEvent_Build\` - Manual copy target (discontinued)
- `C:\Users\arcan\AppData\Roaming\XIVLauncher\devPlugins\DalamudMBBBridge\` - Old dev plugin location
- `C:\Users\arcan\AppData\Roaming\XIVLauncher\devPlugins\MBBDalamud\` - Legacy plugin location

## Build Process

### 1. Version Update
- Update version in `DalamudMBBBridge.csproj`
- Update version in `DalamudMBBBridge.json`
- Update version references in code if needed

### 2. Build Command
```bash
cd dalamud-plugin/DalamudMBBBridge
dotnet build -c Release
```

### 3. Output Verification
- Verify files exist in: `bin/Release/win-x64/`
- Check DLL timestamp and version
- Validate plugin manifest (DalamudMBBBridge.json)

### 4. Installation
- Point XIVLauncher to the single build path
- No manual copying required
- Single source reduces version conflicts

## Benefits of Single Path Protocol

### ✅ **Advantages**
- **No Version Confusion** - One source of truth
- **Simplified Development** - No manual copying
- **Reduced Errors** - No sync issues between multiple locations
- **Easy Tracking** - Clear build history
- **Better Git Management** - Single build artifact location

### 🎯 **Result**
- Cleaner development workflow
- Reduced maintenance overhead
- Faster iteration cycles
- Consistent plugin distribution

## Historical Context

### Previous Multi-Path Issues
- Version 1.4.10.4 and earlier used multiple locations
- Manual copying led to version mismatches
- XIVLauncher dev folders contained outdated versions
- Confusion about which version was "current"

### Resolution (Version 1.5.2+)
- Consolidated to single build location
- Eliminated manual copy steps
- Simplified installation process
- Clear version tracking

---

**Last Updated:** September 21, 2025
**Effective From:** Version 1.5.2
**Protocol Status:** ✅ Active