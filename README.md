# MBB Dalamud Bridge - Custom Plugin Repository

![MBB Logo](images/icon.png)

**Real-time Thai Translation for Final Fantasy XIV**

---

## 🎯 What is MBB Dalamud Bridge?

**MBB (Magic Babel Bridge)** is a custom Dalamud plugin that provides real-time Thai translation for Final Fantasy XIV using Google Gemini AI. It features:

- ✨ **Real-time Translation** - Text hook architecture for immediate translation
- 🎭 **Character Database** - Personality, gender, status, and terminology tracking
- 🎬 **Netflix-Quality Localization** - Context-aware, natural Thai translation
- 🎨 **Elegant UI** - Auto-show/hide, fully customizable (size, colors, themes)
- ⚡ **Seamless Integration** - Works alongside gameplay with minimal performance impact

---

## 📦 Installation Guide

### Prerequisites
- Final Fantasy XIV with Dalamud installed
- Windows 10/11
- Google Gemini API Key ([Get one free here](https://aistudio.google.com/app/apikey))

### Step 1: Add Custom Repository (30 seconds)

1. Launch FFXIV and open Dalamud settings:
   ```
   /xlsettings
   ```

2. Go to **"Experimental"** tab

3. In **"Custom Plugin Repositories"**, click **"+"** and add:
   ```
   https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
   ```

4. Click **"Save and Close"**

### Step 2: Install Plugin (1 minute)

1. Open plugin installer:
   ```
   /xlplugins
   ```

2. Search for **"MBB Dalamud Bridge"**

3. Click **"Install"**

4. Wait for installation to complete

### Step 3: Download Python App (1 minute)

1. Go to [Releases Page](https://github.com/iarcanar/MBB_Dalamud/releases/latest)

2. Download **`MBB_v1.0.0.zip`** (72 MB)

3. Extract to any location (e.g., `C:\MBB\`)
   - **Important:** Extract the entire folder, not just MBB.exe!

### Step 4: Configure Plugin (2 minutes)

1. In FFXIV, open MBB settings:
   ```
   /mbb
   ```

2. Click **"Browse"** and select **`MBB.exe`** from extracted folder

3. Click **"Save Path"**

4. Click **"Launch Python App"**

### Step 5: Set API Key (1 minute)

1. In the MBB Python app window, click **"Settings"**

2. Paste your **Gemini API Key**

3. Click **"Save"**

4. Press **F9** to start translation

---

## 🎮 Usage

### Basic Commands

| Command | Description |
|---------|-------------|
| `/mbb` | Open main configuration window |
| `/mbb launch` | Launch Python translation app |
| `/mbb reload` | Reload plugin configuration |

### Hotkeys (in Python App)

| Key | Action |
|-----|--------|
| **F9** | Start/Stop translation |
| **F10** | Clear translation screen |
| **F11** | Toggle mini/full UI mode |

### UI Controls

- **START/STOP Button** - Control translation engine
- **Settings** - Configure API key, themes, fonts
- **NPC Manager** - Manage character database
- **Themes** - 6 built-in themes (Cyberpunk, Ocean, Sunset, Forest, Royal, Rose)

---

## 🔧 Troubleshooting

### Plugin doesn't show in installer
- Check that custom repository URL is correct
- Click "Refresh" in plugin installer
- Restart Dalamud (`/xlplugins` → close → reopen)

### "MBB.exe not found" error
- Open `/mbb` and set correct path to `MBB.exe`
- Make sure you extracted the ZIP file
- Check that path doesn't have special characters

### Translation not working
- Verify API key in Settings
- Check that Python app is running (green tray icon)
- Press F9 to start translation
- Check internet connection

### Python app crashes
- Make sure you have .NET Runtime installed
- Check antivirus isn't blocking MBB.exe
- Run as administrator if needed

---

## 📝 Features

### Translation Engine
- **Text Hook Architecture** - Direct game text extraction (no OCR)
- **Gemini AI Integration** - Context-aware translation
- **Character Database** - NPC personality and terminology tracking
- **Translation Memory** - Caches translations for consistency

### User Interface
- **Auto-show/hide** - Appears only when needed
- **Mini UI Mode** - Compact overlay during gameplay
- **Full Control Panel** - Complete settings and management
- **6 Theme Presets** - Customizable colors and styles
- **Font Support** - Thai fonts (Tahoma, Anakotmai, Sarabun)

### Developer Features
- **Named Pipe Communication** - C# ↔ Python bridge
- **Modular Architecture** - Easy to extend and customize
- **Translation Logging** - Debug and quality monitoring
- **Error Handling** - Graceful failure recovery

---

## 🔄 Updates

The plugin will auto-update through Dalamud when new versions are released.

To manually check for updates:
```
/xlplugins → Installed Plugins → MBB Dalamud Bridge → Update
```

---

## 📚 Documentation

- [Installation Testing Guide](INSTALLATION_TESTING.md) - ⭐ Test installation steps
- [Installation Guide](INSTALLATION.md)
- [Build Protocol](BUILD_PROTOCOL.md)
- [Starting Guide](STARTING_GUIDE.md)
- [UI Troubleshooting](UI_TROUBLESHOOTING.md)
- [Master Plan](MASTER_PLAN.md)
- [Changelog](CHANGELOG.md) - Version history

---

## 🐛 Bug Reports & Feature Requests

Please report issues on [GitHub Issues](https://github.com/iarcanar/MBB_Dalamud/issues)

When reporting bugs, include:
- Plugin version (`/mbb` → About)
- Python app version (shown in title bar)
- Steps to reproduce
- Error messages or screenshots

---

## 🤝 Contributing

This project is open for contributions!

Areas where help is needed:
- Translation quality improvements
- Additional language support
- UI/UX enhancements
- Bug fixes and optimizations

---

## 📜 License

**MIT License**

Copyright (c) 2026 iarcanar

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

---

## 🙏 Acknowledgments

- **Dalamud Team** - For the amazing plugin framework
- **Google Gemini AI** - For powerful translation capabilities
- **FFXIV Community** - For testing and feedback
- **Thai Localizers** - For translation quality insights

---

## 📞 Contact

- **Developer:** iarcanar
- **Repository:** https://github.com/iarcanar/MBB_Dalamud
- **Issues:** https://github.com/iarcanar/MBB_Dalamud/issues

---

**Version:** 1.0.0
**Last Updated:** January 23, 2026
**Framework:** Dalamud Plugin + Python + Gemini AI

---

**Enjoy real-time Thai translation in FFXIV! 🎮✨**
