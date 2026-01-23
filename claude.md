# MBB Dalamud - Custom Repository Project

## Project Information

**Version:** 1.0.0
**Build:** 01222026-01
**Project Name:** MBB Dalamud Custom Repository Distribution

## Origin

This project is migrated from:
- **Original Location:** `C:\Yariman_Babel\MbbDalamud_bridge`
- **Previous Version:** v1.5.28 (Development Build)
- **Migration Date:** January 22, 2026

## Primary Goal

**Transform MBB Dalamud Bridge into a distributable package via Dalamud Custom Plugin Repository**

### Objectives:
1. **Code Cleanup** - Remove all hardcoded paths and make code distribution-ready
2. **Custom Repository Setup** - Create `pluginmaster.json` for Dalamud auto-discovery
3. **PyInstaller Package** - Bundle Python app into standalone executable
4. **One-Click Installation** - Enable users to install via Dalamud plugin installer

### Target User Experience:
- Add repository URL in Dalamud settings
- Install plugin with 1 click
- Download Python app executable
- Configure and use immediately

## Project Structure

```
C:\MBB_Dalamud/
├── python-app/           # Python translation application
├── dalamud-plugin/       # C# Dalamud plugin
├── fonts/                # Font assets
├── MBB/                  # Additional resources
└── claude.md            # This file
```

## Current Status

- [x] Codebase migrated to C:\MBB_Dalamud
- [x] API Key removed from .env (security)
- [ ] Code cleanup (Phase 1)
- [ ] Custom repository setup (Phase 2)
- [ ] PyInstaller packaging (Phase 3)

## Development Notes

This is a distribution-focused rebuild. All changes must prioritize:
- **Portability** - Works on any Windows machine
- **Security** - No hardcoded credentials
- **User-Friendliness** - Minimal setup steps
- **Auto-Update** - Plugin updates via Dalamud

---

**Developed by:** iarcanar
**Framework:** Dalamud Plugin + Python + Gemini AI
**License:** MIT
