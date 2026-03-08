# Magicite Babel — Dalamud Edition

![MBB Logo](images/icon.png)

**Real-time Thai translation overlay for Final Fantasy XIV**

MBB hooks into FFXIV's text system via [Dalamud](https://github.com/goatcorp/Dalamud) plugin and translates dialogue, cutscenes, and battle text into Thai in real-time using Google Gemini AI.

> **Version:** 1.7.8 &nbsp;|&nbsp; **Build:** 04032026-01

---

## How It Works

```
FFXIV Game  ──>  Dalamud Plugin (C#)  ──>  Named Pipe  ──>  Python App
                 Text Hook                                   Gemini AI
                 Zone Detection                              Translation UI (TUI)
                                                             Chat Log (LOG)
```

1. **Dalamud Plugin** hooks into FFXIV's chat system and captures dialogue text
2. Text is sent to the **Python app** via named pipe (IPC)
3. **Gemini 2.0 Flash** translates with character-aware context
4. Translation appears on the **TUI overlay** directly on top of the game

---

## Project Structure

```
MBB_Dalamud/
|
|-- dalamud-plugin/                   C# Dalamud Plugin
|   +-- DalamudMBBBridge/
|       |-- DalamudMBBBridge.cs       Main plugin: text hook, zone detection, IPC
|       |-- MBBConfigWindow.cs        Plugin config UI (ImGui)
|       |-- DalamudMBBBridge.csproj   .NET project (Dalamud.NET.Sdk)
|       +-- DalamudMBBBridge.json     Plugin manifest
|
|-- python-app/                       Python Translation Application
|   |-- MBB.py                        Main application entry point
|   |-- translator_gemini.py          Gemini AI translation engine
|   |-- dalamud_bridge.py             Named pipe IPC client
|   |-- dalamud_immediate_handler.py  Text routing & translation trigger
|   |-- conversation_logger.py        Wide-context conversation tracking
|   |-- translated_ui.py              TUI: Tkinter overlay (translation display)
|   |-- translated_logs.py            LOG: Chat-style translation history
|   |-- mini_ui.py                    Mini UI: compact mode
|   |-- settings.py                   Settings backend
|   |-- text_corrector.py             Name detection & text correction
|   |-- enhanced_name_detector.py     NPC name matching system
|   |-- npc_manager_card.py           NPC Manager: character database editor
|   |-- api_key_manager.py            API key setup wizard
|   |-- font_manager.py               Tkinter font management
|   |-- npc.json                      Character database (290+ characters)
|   |-- version.py                    Version constants
|   |-- mbb.spec                      PyInstaller build spec
|   |-- .env.example                  API key template
|   |-- pyqt_ui/                      PyQt6 Modern UI
|   |   |-- main_window.py            Main control window
|   |   |-- control_panel.py          Status & controls
|   |   |-- settings_panel.py         Settings panel
|   |   |-- font_panel.py             Font selector
|   |   |-- styles.py                 QSS themes & glass mode
|   |   +-- ...
|   |-- fonts/                        Bundled fonts (Anuphan, FC Minimal)
|   +-- assets/                       Icons and images
|
|-- website/                          Project website (GitHub Pages)
|   |-- index.html                    Single-file website
|   +-- screenshots/                  UI screenshots
|
|-- plugins/                          Dalamud custom repository
|   +-- DalamudMBBBridge/
|       +-- latest.zip                Pre-built plugin package
|
|-- repo-structure/
|   +-- pluginmaster.json             Dalamud plugin discovery manifest
|
+-- claude.md                         Project documentation
```

---

## Features

- **Text Hook** -- Direct memory-based text extraction via Dalamud (no OCR)
- **Gemini 2.0 Flash** -- Fast, context-aware Thai translation
- **Wide-Context Translation** -- Remembers recent dialogue for consistent pronouns and honorifics
- **NPC Database** -- 290+ named characters with customizable tone/personality
- **TUI Overlay** -- Transparent translation overlay with rich text formatting
- **Chat Log (LOG)** -- Scrollable translation history with chat bubbles
- **Glass Mode** -- Fully transparent UI that blends into the game
- **Mini UI** -- Compact 50x176px side panel
- **Zone Change Detection** -- Auto-resets context when changing areas
- **1-Click Install** -- Install via Dalamud custom plugin repository

---

## Installation

### Prerequisites

- [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher) with Dalamud enabled
- [Google Gemini API Key](https://ai.google.dev/) (free tier available)
- Windows 10/11

### Steps

1. Download and install [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher/releases/latest/download/XIVLauncher-win-Setup.exe)
2. Download the MBB application (Python app executable)
3. In Dalamud Plugin Settings, add the MBB custom repository URL
4. Install "Magicite Babel Bridge" from the plugin installer
5. Set the MBB application path in plugin settings
6. Enter your Gemini API key on first launch -- ready to play!

---

## Development Setup

### Python App

```bash
cd python-app
pip install -r requirements.txt
python MBB.py
```

**Key dependencies:** PyQt6, Tkinter, google-generativeai, python-dotenv, Pillow

### Dalamud Plugin (C#)

```bash
cd dalamud-plugin/DalamudMBBBridge
dotnet build
```

**SDK:** Dalamud.NET.Sdk 14.0.1  |  **Target:** .NET 10.0 (win-x64)

---

## API Key Security

- API keys are stored in `.env` (gitignored, never committed)
- `.env.example` provides the template
- `api_key_manager.py` handles first-run setup via UI dialog
- **Never** hardcode API keys in source files

---

## Background

The Python translation application (everything under `python-app/`) is an original work built from the ground up. The project started as an OCR-based screen capture translator and evolved into the current architecture using Dalamud's text hook system for direct text extraction -- eliminating the need for screenshot-based OCR entirely.

---

## Acknowledgments

- **[Echoglossian](https://github.com/kelvin124124/Echoglossian)** -- FFXIV real-time translation plugin. MBB's C# Dalamud plugin component draws inspiration from Echoglossian's approach to hooking into the game's chat event system via Dalamud services.

- **[XIVLauncher / Dalamud](https://github.com/goatcorp/FFXIVQuickLauncher)** -- The custom game launcher and plugin framework that makes this project possible. Provides the plugin API, text hook services (`IChatGui`, `IClientState`), and the custom repository system.

- **[Google Gemini](https://ai.google.dev/)** -- AI model powering the translation engine (Gemini 2.0 Flash).

---

## License

MIT License

Copyright (c) 2026 iarcanar

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

---

**Developed by** [iarcanar](https://github.com/iarcanar)
**Framework:** Dalamud Plugin + Python + Gemini AI
