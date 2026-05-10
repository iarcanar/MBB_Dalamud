# MBB Dalamud - Custom Repository Project

## Project Information

**Version:** 1.8.5
**Build:** 04032026-01
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
├── DalamudMBBBridge/     # C# Dalamud plugin
├── fonts/                # Font assets
├── MBB/                  # Additional resources
└── claude.md            # This file
```

## Current Status

- [x] Codebase migrated to C:\MBB_Dalamud
- [x] API Key removed from .env (security)
- [x] Code cleanup Phase 1 — dead-code purge + theme system v2 (2026-04-25)
- [x] NPC Manager polish + word_fixes deprecated (2026-04-26)
- [x] Translated Logs PyQt6 rewrite + Settings polish (v1.8.0, 2026-04-26)
- [x] Translation tuning + Theme/NPC polish (v1.8.1, 2026-04-27)
- [x] NPC Manager database visibility + merge tool (v1.8.4, 2026-05-08)
- [x] TUI architecture overhaul — Win32 resize + DissolveOverlay + file split (v1.8.5, 2026-05-10)
- [x] NPC Manager Polaroid view + WebP avatar storage (v1.8.2, 2026-04-27)
- [ ] Custom repository setup (Phase 2)
- [ ] PyInstaller packaging (Phase 3)

---

## Changelog — v1.8.5 (2026-05-10)

### Critical bugs fixed

**1. Unknown speakers vanished from TUI** ([text_corrector.py:150-155, 552-557](python-app/text_corrector.py))
- Root cause: OCR-era whitelist filter (`if speaker in self.names else return NORMAL`) — designed to drop garbled OCR reads, harmful with reliable Dalamud text hook
- Fix: trust speaker always — Dalamud sends 100% accurate text, no need to gate
- Impact: NPCs not in npc.json now display their name properly (in unknown-purple #a855f7)

**2. TUI fade-out race (stutter / freeze in EXE)** ([translated_ui.py:2789-2820, 6431-6448, 6589-6627](python-app/translated_ui.py))
- Root cause: new text arriving mid-fade → fade chain kept decrementing alpha while restore_user_transparency raised it → flicker. If alpha hit 0 mid-render, canvas.delete("all") + execute_tui_hide wiped new text → near-freeze in EXE
- 3-layer fix:
  - Layer 1 (entry): `update_text` cancels fade_timer_id + window_hide_timer_id, resets is_fading, bumps last_activity_time
  - Layer 2 (defer): fade_out_text at alpha=0 → defer destructive cleanup 80ms via after()
  - Layer 3 (recheck): `_do_fade_destructive_cleanup` re-checks is_fading + activity time before wiping; aborts if interrupted
- KEEPS user prefs intact (auto_hide_after_fade not touched — only runtime flags)

**3. LOG transparency stutter on long messages** ([pyqt_ui/translated_logs.py:_apply_bg_alpha_only](python-app/pyqt_ui/translated_logs.py))
- Root cause: every slider tick called `_apply_theme()` → `setStyleSheet(qss)` on entire window → Qt re-polished ALL bubbles + reapplied selectors. With 50+ bubbles + 60 events/sec = freeze
- Fix: surgical `self.bg.setStyleSheet(...)` for BG card only — bubbles paint themselves with solid colours so they don't need updating. Added 350ms QTimer debounce on disk write.

**4. TUI resize handle slow / cursor-escape / hover-miss**
- ⚠ **First attempted Win32 `WM_NCLBUTTONDOWN + HTBOTTOMRIGHT` hand-off — CRASHED with `PyEval_RestoreThread` GIL fatal**. Root cause: `SendMessageW` is blocking and runs Windows' modal resize loop while Python's main thread is suspended inside a Tk callback. During the modal loop Windows fires WM_PAINT/WM_SIZE back to Tk's window proc; Tk tries to dispatch them but Python thread state is NULL → process terminates. **DO NOT retry this approach inside a Tk callback.**
- Final fix: **manual resize + 16ms throttle**
  - `start_resize` routes directly to `_start_manual_resize` (Win32 path removed)
  - `_manual_on_resize` adds 60 FPS throttle on `self.root.geometry()` calls (was unthrottled — 100+ Hz mouse = 100+ WM_SIZE round-trips/sec = lag)
  - `bind_all <B1-Motion>` + `<ButtonRelease-1>` for global mouse capture (cursor escape covered)
  - `on_smart_resize_end → _restore_layout_after_resize_universal` for layout restore + hover refresh
- 16ms throttle eliminates ~95% of WM_SIZE traffic while keeping motion smooth

**5. Splash screen disabled** — [MBB.py:587-589](python-app/MBB.py) had splash commented out for DEV mode. Re-enabled.

### Step-lock transparency

**LOG (4 levels — used less)**: `10 / 40 / 80 / 100` — `TranslatedLogsPanel.TRANSPARENCY_STEPS` ([pyqt_ui/translated_logs.py](python-app/pyqt_ui/translated_logs.py))
- snap-on-drag + no-op detection (drag within step = zero work)
- migration: existing settings.json transparency value snaps to nearest step on load

**TUI (6 levels — used more)**: `80 / 84 / 88 / 92 / 95 / 100` — `ImprovedColorAlphaPickerWindow.TRANSPARENCY_STEPS` (in `tui_color_picker.py` after Phase 1 split)
- 95 picked as 5th step per user preference ("ค่าที่ฉันชอบประมาณ 95")
- Custom Canvas slider (replaced tk.Scale) — handle bright-accent on press, dim grey at rest, step labels (1-6) shown only during drag

### Legacy `transparency` key purge
- 5 sites removed across MBB.py + settings.py + translated_ui.py
- Was OVERRIDING the user's color-picker setting (`bg_alpha`) on every settings save
- TUI alpha now controlled SOLELY by the in-TUI picker — no other source

### TUI Color/Alpha Picker — modernized
- Frameless dark glass design matching Theme Manager / Settings panel
- 1px accent ring (outer Toplevel bg = ACCENT, inner main_frame = BG_SURFACE)
- Title with accent underline
- Hex value label next to color swatch
- Custom canvas slider (NOT tk.Scale) with magnetic snap behavior
- Step pip labels (1-6) appear during drag, hide on release
- Modal sized 300×244, position-only geometry string (preserves setup_ui's size)
- `winfo_reqwidth/reqheight` instead of `winfo_width/height` (latter can return stale values before Win32 catches up)
- Win32 corner radius reduced from 20 → 12 (handle no longer clipped at edges)

### Mode-aware TUI behavior

**1. Per-mode geometry memory** ([translated_ui.py:set_display_mode_for_chat_type](python-app/translated_ui.py))
- New settings key: `tui_geometries[mode] = {w, h}` — stores per-mode size (dialog/battle/cutscene)
- Existing `tui_positions[mode]` already stored per-mode position
- Mode switch saves OUTGOING mode's current size+position, loads INCOMING mode's saved values
- Choice mode is transient — does NOT save (so dialog position restored verbatim when choice ends)
- `_clamp_to_screen` defends against off-screen restore (multi-monitor changes)

**2. Battle/cutscene minimal hover UI** ([translated_ui.py:set_icons_alpha](python-app/translated_ui.py))
- Dialog/choice: all 4 buttons + handle on hover (close, lock, color, fadeout)
- Battle/cutscene: ONLY close + resize_handle (lock/color/fadeout pack_forget)
- Rationale: battle is intense, cutscene is cinematic — user won't tweak settings during them

**3. WASD auto-hide bypass extended** ([MBB.py:hide_and_stop_translation](python-app/MBB.py))
- Battle bypass already existed; added cutscene bypass — text must show continuously through both

**4. Battle text centering race fix** (rare, 2-layer defense in `_handle_normal_text_fast` + `_perform_canvas_resize`)
- Pre-render: force `canvas.update_idletasks()` before reading width when in battle/cutscene + anchor=N
- Post-render: in `_perform_canvas_resize`, compute delta between current centered-text x and new canvas centre, shift all `anchor='n'` items by delta (preserves shadow ring offsets)

### NEW: Dissolve Overlay for Battle/Cutscene ([pyqt_ui/dissolve_overlay.py](python-app/pyqt_ui/dissolve_overlay.py) — 641 lines)

> ✅ **RE-ENABLED 2026-05-10 (post-fix).** Initial v1.8.5 testing surfaced 3 bugs — all resolved:
>
> 1. **Text not centered top** — `paintEvent` vertically centered the speaker+body block (`block_top = max(pad_y, (h - block_h) // 2)`). Fix: `block_top = pad_y` so text reads from the top, overlay grows downward.
> 2. **Tkinter TUI doesn't hide** — root cause was NOT in dispatcher order (dispatch already runs first at line 2301, returns before `set_display_mode_for_chat_type` at line 2366). Real culprit: `MBB._do_tui_auto_show` was firing on every status update during translation (called from `_trigger_tui_auto_show` at MBB.py:2624 inside the status-update flow), and the auto-show kept deiconifying the just-withdrawn root. Fix: added `_dissolve_active` guard — auto-show now skips when overlay is active.
> 3. **Mode switch re-deiconifies** — same root cause as #2 (auto-show firing during cross-mode translations). Same fix.
>
> Defensive add: `_route_to_dissolve_overlay` now also cancels `_deferred_render_id` so a queued `_original_update_text` from the previous chat_type can't paint stale text on the now-hidden canvas.
>
> **Auto-hide (battle/cutscene have no "stay forever" option):** `set_text()` restarts a 10s `QTimer` (`AUTO_HIDE_MS`); on timeout, fade-out via `QPropertyAnimation(windowOpacity)` 500ms then `hide()`. New translations during fade snap opacity back to 1.0 immediately. If cursor is inside overlay (user dragging/resizing), the timer restarts instead of hiding under their hand.

- PyQt6 `QWidget` with frameless + translucent + `WA_TranslucentBackground`
- paintEvent: horizontal `QLinearGradient` — 0% alpha → 5% opaque → 95% opaque → 100% alpha → smooth dissolve on left/right edges (no visible border)
- BG: dark `#14161c` 90% alpha; text drawn AFTER gradient → fully opaque
- Per-mode font color: battle `#FF6B00` / cutscene `#FFD700`
- Reuses existing `tui_geometries[mode]` + `tui_positions[mode]` settings keys
- Wiring (decorator pattern in `translated_ui.update_text`): chat_type 68/71 → show DissolveOverlay + withdraw Tkinter root; chat_type 61 → hide overlay + deiconify root
- Hover-revealed close X + resize grip; QTimer-poll cursor (140ms) — no Enter/Leave flicker
- Self-contained PyQt6 — Tkinter `transparentcolor` is 1-bit and cannot do alpha gradient
- Demo file kept at [demo_dissolve_tui.py](python-app/demo_dissolve_tui.py) for visual evaluation

### Phase 1 file split — translated_ui.py 9080 → 8127 (–953 lines)

Extracted to dedicated modules (independent classes, mechanical extraction):
- **[tui_shadow.py](python-app/tui_shadow.py)** (243 lines) — `ShadowConfig` + `BlurShadowEngine`
- **[tui_color_picker.py](python-app/tui_color_picker.py)** (578 lines) — `ImprovedColorAlphaPickerWindow`
- **[tui_rich_text.py](python-app/tui_rich_text.py)** (229 lines) — `RichTextFormatter`

translated_ui.py imports them at top with `from tui_X import Y` so external consumers (MBB.py) don't need any change — `translated_ui.ImprovedColorAlphaPickerWindow` etc. still works via re-import.

Phase 2 (deferred — coupled feature modules): tui_fade_system, tui_resize_system, tui_auto_hide. Estimated 1100 more lines extractable but require mixin/delegation pattern.

### Pending after compact
- **Build v1.8.5 EXE+DLL** (clean dist_test, run pyinstaller updater + main mbb.spec, then dotnet build for DLL)
- **Commit + push** — `8e44efe v1.8.4` is local-only (push got token-revoke alerts last session); all v1.8.5 changes uncommitted on top
- **Create GitHub release v1.8.4** (so MBB-Updater.exe has a target to pull — currently `/releases/latest` returns 404)
- **In-game user testing** of: dissolve overlay, mode-switch, fade-race fix, unknown speaker, transparency snap, Win32 resize
- **OCR deep-clean** (~1500 lines from 2-agent audits): `model.py` orphan (790 lines), `translation_logger.py` orphan (240 lines), 8 dead settings keys, 3 dead UI methods (~190 lines), text_corrector dead "22"/"222" placeholders + numeric_name guard
- **Phase 2 file split** if user wants more

---

## Changelog — v1.8.4 (2026-05-08)

### NPC Manager — Database Visibility + Merge Tool
- **Header status strip** ([npc_manager_panel.py:_update_db_status](python-app/pyqt_ui/npc_manager_panel.py)): subtitle replaced with live counts + file mtime — `main 218 · npcs 65 · lore 139 · อัปเดต X นาทีที่แล้ว`. Refreshed on init / autosave / reload / 60s QTimer.
- **Manual reload button** (header `↻` → `assets/swap.png`): re-reads npc.json from disk + propagates via `on_save_callback` (translator + text_corrector + caches). Use case: user edits npc.json from external editor or merges from another source.
- **Toast message clarity**: default `"✓ บันทึกแล้ว"` → `"✓ บันทึก · ใช้ในการแปลทันที"` when MBB attached. Tells the user the change is live without needing restart.
- **`_format_relative_time(ts)`** helper: `<60s → "เมื่อสักครู่"`, `<60m → "X นาทีที่แล้ว"`, `<24h → "X ชม.ที่แล้ว"`, `<7d → "X วันที่แล้ว"`, else absolute date.

### Merge Modal — Cross-File Database Sync
- **`Merge` button in header** opens file picker → loads target npc.json → shows diff modal.
- **`_MergeDiff` class**: computes additive diff (new + changed, never deleted) across 4 sections (`main_characters`, `npcs`, `lore`, `character_roles`). Identity: `(firstName, lastName)` lowercase for main, `name` lowercase for npcs, key for dicts. Skips `word_fixes` (deprecated) + `_game_info` (metadata).
- **`_MergeDialog`** ([npc_manager_panel.py:_MergeDialog](python-app/pyqt_ui/npc_manager_panel.py)): frameless 760×660 modal with 2px accent border (so it pops against panel underneath). Layout:
  - Top: 2 file cards (BASE | TARGET) — filename 13pt bold, mtime 12pt bold + colour (`↑` green=newer, `↓` orange=older, `=` neutral=same), counts 11pt 2-line layout
  - Body: scroll area with diff rows grouped by section, checkbox + NEW/CHG badge + label + details (truncated, full text in tooltip)
  - Footer: "Cancel" / "Merge ที่เลือก (N)" — disabled when N=0
- **Merge semantics**: `new` → append to base (preserve target value verbatim, stamp `_added_at` if missing), `change` → overwrite (preserve local `_added_at`). Never deletes anything. After accept → caller calls `panel.autosave()` which propagates via `on_save_callback` to translator/text_corrector/caches.

### Audit Fixes
- **MAX_NPC_BYTES = 50MB cap** before `json.load` — prevent UI freeze / OOM if user picks a malicious huge JSON file.
- **`dlg.deleteLater()`** after `exec()` — without it, repeated merge sessions accumulate dialog widgets parented to the panel (memory leak over long dev sessions).
- **`_apply_diff` / `_apply_list_diff` isinstance hardening**: `setdefault` alone fails if existing value is wrong type (e.g. `data["lore"] = None` on corrupted file); now reset to `{}` / `[]` when type mismatches.

### Build — npc.json + npc_images Promoted Out of `_internal/`
- **Post-build copy in [mbb.spec](python-app/mbb.spec)** (after COLLECT): `_internal/npc.json` → `MBB/npc.json`, `_internal/npc_images/` → `MBB/npc_images/`. Uses `shutil.copyfile` + `shutil.copytree(dirs_exist_ok=True)` so each rebuild refreshes.
- **Why**: PyInstaller default buries everything in `_internal/` but these are the only files users actually want to find / share / back up. Resolver in `npc_file_utils.get_npc_file_path()` already prefers exe-level → `_internal/` fallback, so duplicating ~1.5MB is worth it.
- **Distribution layout (v1.8.4+)**:
  ```
  MBB/
  ├── MBB.exe
  ├── npc.json          ← user-editable, visible
  ├── npc_images/       ← user data, visible
  │   └── main_characters/
  └── _internal/
      ├── npc.json      (fallback)
      ├── npc_images/   (fallback)
      └── ... (Python runtime + libs)
  ```

---

## Changelog — v1.8.2 (2026-04-27)

### NPC Manager — Polaroid Avatar View
- **New feature** ([npc_manager_panel.py:_PolaroidCard / PolaroidOverlay](python-app/pyqt_ui/npc_manager_panel.py)): clicking a character's avatar opens a polaroid-style enlarged photo card (~400×510px) inside the details panel. Card shows the full image (top-cropped, KeepAspectRatioByExpanding) + the firstName below in a handwriting font (Caveat, bundled). Hover the card → "📷 เปลี่ยนภาพ" pill (top-right) + "✕" delete (bottom-right) appear.
- **UX flows**:
  - Empty avatar → click goes straight to file picker (skip empty Polaroid)
  - Avatar with image → click opens Polaroid; "เปลี่ยนภาพ" → file picker → after upload, Polaroid auto-reopens with the new photo
  - Click outside / Resize window / ESC → Polaroid dismisses immediately

### Polaroid Implementation Notes (every one of these took multiple iterations — captured in [project_pyqt6_gotchas.md](memory))
- **Shadow ghost outline fix** ([QTBUG-56081](https://bugreports.qt.io/browse/QTBUG-56081)): action buttons live as **siblings of the shadowed `_PolaroidCard`** (children of the overlay), not children of the card. `QGraphicsDropShadowEffect` rasterizes ALL descendants together — children-of-shadow get their full bounding rect baked into the shadow pass before QSS border-radius clips them, leaking square ghosts. Pattern from [BoxShadow-in-PyQt-PySide](https://github.com/GvozdevLeonid/BoxShadow-in-PyQt-PySide).
- **Custom font fix**: `QtFontManager` runs lazily (only on Settings/Font panel open). Polaroid calls `QFontDatabase.addApplicationFont()` itself in `__init__` (idempotent). Even after registration, panel-level QSS subtree cascade can override `setFont()`. Bulletproof workaround: pre-render the name to a QPixmap via `QPainter.drawText` (uses QFont directly, bypassing QSS pipeline), then `label.setPixmap(pm)`. See `_render_name_pixmap`.
- **Hover flicker fix**: timer-based geometry polling (60ms) instead of Enter/Leave events. When buttons are siblings painted on top of card, cursor crossing onto a button = Leave on card = hide buttons = cursor on card again = Enter on card = show buttons = ... Geometry poll avoids the loop. See `_update_hover_state`.
- **Resize / outside-click dismiss**: app-level `eventFilter` installed only while overlay is visible. Listens for top-level window `Resize` (backdrop wouldn't reflow → dismiss) and `MouseButtonPress` outside the overlay's screen rect (covers title bar / resize grip clicks).

### Avatar Storage — 128 PNG → 512 WebP (~89% smaller files)
- **Resolution bump** ([npc_data_manager.py:set_main_character_image](python-app/npc_data_manager.py)): default `size = 128` → `512`. The 128px legacy default produced visibly blurry images in the Polaroid (which displays at 360 logical px). 512 has just-enough headroom for HiDPI without storage bloat.
- **Format switch** ([image_optimizer.py](python-app/image_optimizer.py)): default save format PNG → **WebP, lossy quality=88**, alpha preserved. Real comparison: y_shtola PNG 503KB → WebP 56KB (11% of original size, visually indistinguishable). `safe_filename` default extension `.png` → `.webp`.
- **Legacy cleanup**: when re-uploading an avatar that previously had a different extension (`.png`), the old file is deleted to prevent orphans.
- **Polaroid no-upscale guard**: `_PolaroidCard.paintEvent` caps `target_logical = min(IMAGE_AREA, source_min_dim)` — small legacy 128px images display at native size centered (letterboxed) instead of being blurry-upscaled to 360.

### Caveat Font Bundled
- **New asset** ([fonts/Caveat-Regular.ttf](python-app/fonts/Caveat-Regular.ttf)): English handwriting font (Google Fonts, OFL license, ~300KB). Renamed to `Caveat.ttf` automatically by `font_manager.py` metadata-rename logic on first run. Used by Polaroid for the firstName strip below the photo.

### NPC Manager — Avatar Badge Icons (MAIN list + Polaroid button)
- **Procedural flat-design icon** ([npc_manager_panel.py:_make_avatar_badge_icon](python-app/pyqt_ui/npc_manager_panel.py)): rounded square in the current theme accent color + white photo glyph (frame outline + mountain V + sun dot) drawn with QPainter. No raster asset needed — scales cleanly with theme.
- **MAIN list rows**: rows whose character has `image` set show the badge at column-0 left edge; rows without get a transparent placeholder same size, so all icons line up vertically. `_make_tree` now calls `setIconSize(QSize(22,22))` to prevent Qt's 16px default from downscaling the icon and destroying glyph detail.
- **Polaroid "เปลี่ยนภาพ" button**: replaced the static `assets/camera.png` with the same procedural badge — visually consistent with the list, picks up theme color automatically. `setIconSize(20,20)` set explicitly for the same downscale reason.

### NPC Manager — Pin Button + Defensive Code
- **Pin default** ([npc_manager_panel.py:NPCManagerPanel.__init__](python-app/pyqt_ui/npc_manager_panel.py)): `_is_pinned = True` matches the `WindowStaysOnTopHint` set in `_init_window`. Previously defaulted to False → user had to click the pin twice before the toggle worked. Now first click correctly unpins.
- **Pin flicker fix** (`_apply_topmost`): hybrid Qt + Win32 — `setWindowFlag` keeps Qt's internal model in sync (otherwise Qt re-applies topmost on next activate), Win32 `SetWindowPos(HWND_TOPMOST/NOTOPMOST)` enforces actual z-order in place without the unmap+remap that flickers.
- **Defensive try/except** around `PolaroidOverlay.eventFilter`, `_update_hover_state`, `showEvent`/`hideEvent` filter install/remove. App-level eventFilters receive events from background threads (e.g. `keyboard` library's global hook) — any exception propagating to Qt's C++ side can silently terminate the app. All wrapped + logged. Was added in pursuit of an intermittent self-close crash that's still not pinned down — but eliminates the most likely propagation paths.

---

## Changelog — v1.8.1 (2026-04-27)

### Translation Quality — Modern Thai Default
- **New prompt v3** ([translator_gemini.py:553-588](python-app/translator_gemini.py#L553-L588)): inverted default register from archaic ข้า/เจ้า/ท่าน → **modern Thai** (ฉัน/ผม/คุณ/นาย/เธอ). Target audience explicitly stated: Thai teens/young adults reading like an anime dub or Frieren Netflix subtitles. Archaic register applies ONLY when `Character's style` says so — most Scions/NPCs now sound contemporary. v2 preserved as `get_rpg_general_prompt_v2()` for revert. Token cost ~487 → ~701 (added 2 EN→TH style anchors)
- **Lore audit + 8 fixes** ([npc.json](python-app/npc.json)): Aether (clarified — energy that sustains, not "origin of all things"), Reflection ("เคยมี 13 ดวง" — historical fact, no current count), Endless (linked to Living Memory + Alexandria), Living Memory (linked back to Endless), Sin eater + Lightwarden (added ทับศัพท์), Tempered (added Primal connection), Dynamis (added Dawntrail context), Electrope (added Alexandria), Eikon (clarified vs Primal — same beings, Allagan/Garlean naming)
- **Character roles rewrite — 12 mains** ([npc.json:2060-2073](python-app/npc.json#L2060)): each entry now specifies Thai pronoun + register precisely (modern vs semi-archaic vs archaic) + 1 distinctive trait. Modern register (default) applied to: Y'shtola/Alphinaud/Alisaie/Wuk Lamat/G'raha Tia/Estinien/Thancred/Zoraal Ja. Semi-archaic/archaic preserved for: Urianger (deeply archaic — canon trait other characters mock in-game), Sphene (gentle royal), Emet-Selch (theatrical ancient), Hythlodaeus (warm ancient)
- **Stale dup cleanup**: removed `EmetSelch` (no-hyphen typo) + `Feo UI` (typo). Backup at `python-app/backups/npc_backup_20260426.json`

### Theme Panel — Drag Bounce Fix
- **Bug** ([theme_panel.py:571-595](python-app/pyqt_ui/theme_panel.py#L571-L595)): clicking a swatch / color picker / empty area with even 1-2px mouse drift moved the entire panel (`mouseMoveEvent` activated on any LMB+move). Fixed: header-only drag using same pattern as `font_panel.py` and `translated_logs.py` — `_dragging` flag set true ONLY when mousePress y ≤ 46 (outer margin 10 + header height 36)

### NPC Manager — Data Font Scaler (LORE tab)
- **Default font 11 → 18** ([npc_manager_panel.py:DictTabBase:DATA_FONT_DEFAULT](python-app/pyqt_ui/npc_manager_panel.py)): list rows + Term/Definition input fields scale together. Labels (Term:/Definition:/Lore Details) stay fixed — they're chrome, not data
- **+/- buttons** in search bar (right side, after toast slot) — visible only when current tab is `DictTabBase` subclass (currently LORE only since Roles+Fixes are hidden). Min 11pt, max 28pt, session-scoped (no persistence)
- **CRITICAL gotcha workaround** ([npc_manager_panel.py:set_data_font_size](python-app/pyqt_ui/npc_manager_panel.py)): panel-level QSS forces `font-size: 11pt` on `QLineEdit.npc_field` + `QTextEdit.npc_textarea`, silently overriding `setFont()`. Fixed by `setStyleSheet(f"font-size: {size}pt;")` on each input — inline rules win against parent class rules. Same gotcha now documented in [project_pyqt6_gotchas.md](memory) — applies to QLineEdit/QTextEdit too, not just QLabel

---

## Changelog — v1.8.0 (2026-04-26)

### Translated Logs UI — PyQt6 Rewrite
- **New file**: [pyqt_ui/translated_logs.py](python-app/pyqt_ui/translated_logs.py) (~1100 LOC) — replaces legacy 2230-LOC Tkinter `translated_logs.py`. Same public API + compatibility shims (`root`, `winfo_exists`, `state`, `withdraw`, `is_visible`, `message_cache`) so MBB.py needed minimal changes
- **LINE-style bubbles**: `ChatBubble(QFrame)` paints ONE rounded rectangle background; speaker label color-coded (`???` purple, dialogue choice gold, Lore dim, normal cyan) + wrapping message label. Multi-line text never breaks the bubble shape
- **Thai-aware soft-wrap** ([translated_logs.py:99-167](python-app/pyqt_ui/translated_logs.py#L99-L167)): Qt's `QLabel.wordWrap` only breaks at whitespace, but Thai has none. `_insert_thai_breakpoints()` injects ZWSP (U+200B) at Thai leading-vowel boundaries (เ แ โ ใ ไ) — algorithm ported from `translated_ui.py:_split_for_wrap`
- **QSS-driven font family** ([translated_logs.py:251-289](python-app/pyqt_ui/translated_logs.py#L251-L289)): Qt stylesheets override `setFont()` for QLabels inside styled widgets — bubble labels apply `font-family` + `font-size` via QSS so FontPanel font changes actually take effect
- **Bubble width constraint via eventFilter on viewport** + cap on inner QLabel maxWidth — fixes overflow caused by `setWidgetResizable(True)` letting children grow past viewport. `setHeightForWidth(True)` + `MinimumExpanding` policy + override `heightForWidth(w)` on bubble — Qt layout uses heightForWidth instead of naive sizeHint, so wordWrap actually wraps
- **Background-only opacity**: `setWindowOpacity()` would fade text + bubbles too. Replaced with rgba in QSS for `QFrame#logs_bg` driven by 10-100 slider — bubbles paint solid colors and stay 100% opaque
- **No animation**: `QGraphicsOpacityEffect` on a frameless+`WA_TranslucentBackground` parent left ghost paint trails on drag. Removed fade entirely — bubbles appear instantly
- **App-wide hover detection**: default Qt widgets only emit `mouseMoveEvent` when a button is pressed. Solution: enable `mouseTracking` + `WA_Hover` recursive on all children + `app.installEventFilter(self)` to catch `MouseMove`/`HoverMove`/`HoverEnter`/`Enter` events anywhere in the panel. Throttled `_save_geometry` (500ms QTimer) so disk writes don't starve the hover poll
- **Smart positioning**: right-edge anchor (or left if MBB on right), vertically centered, never blocks gameplay area. Lock mode session-only (always starts unlocked)
- **Asset icons**: `assets/clear.png` (broom — clear button), `assets/lock.png`/`unlock.png` (lock toggle), `assets/resize.png` (resize grip) — auto-inverted on light themes via `invert_pixmap()`
- **Smart Replacement disabled** in this rewrite — `is_force_retranslation` flag kept as no-op for API compatibility

### Settings Persistence Decoupling
- **Bug fix** ([MBB.py:apply_saved_settings](python-app/MBB.py#L3288)): when `font_target_mode = "logs"`, MBB startup pushed TUI's `font_size` onto logs UI, overwriting whatever the user had set. Now `apply_saved_settings` calls `translated_ui.update_font` + `adjust_font_size` directly — bypasses `update_font_settings` which respects `font_target_mode`. Logs UI loads its own `logs_ui.font_size` independently
- **Settings**: added `transparency_value` parameter to `set_logs_settings()` (replaces legacy `transparency_mode` A/B/C/D mapping)

### Settings Panel Polish
- **Scale +20%**: panel 300×520 → 360×624; ToggleSwitch 44×22 → 52×26; all fonts bumped (11pt→13, 9pt→11, 8pt→10, 7pt→8); button heights bumped proportionally
- **Section headers in Thai**: "Advanced" → "ตั้งค่าอื่นๆ", "Test Hook" → "ทดสอบการแปลรูปแบบต่างๆ", "Shortcuts" → "ปุ่มลัด"
- **Toggle labels in Thai**: "Auto-hide UI (WASD)" → "ซ่อน UI เมื่อวิ่ง (WASD)"; "Auto Show TUI" → "โชว์ TUI อัตโนมัติเมื่อแปล"; "Battle Chat Mode" → "แสดงคำแปลซีนต่อสู้"; "Conversation Log" → "บันทึกประวัติการแปล"; "Starting Key Visual" → "เริ่มโปรแกรมด้วยภาพ artwork"
- **Shortcut labels**: "Toggle UI:" → "เปิด/ปิด UI:", "Start/Stop:" → "เริ่ม/หยุด:"

### FontPanel Polish
- **Bigger by default**: 340×520 → **470×600** — old size clipped Thai/EN preview lines
- **Thai labels**: section labels (Font Family/Size/Apply To/Preview) → ฟอนต์/ขนาด/ใช้กับ/ตัวอย่าง; target buttons (TUI/TUI Log/Both) → "หน้าจอแปล"/"บทสนทนา"/"ทั้งสอง"; APPLY → "นำไปใช้"
- **Dynamic title context** ([font_panel.py:91-104 + 269-279](python-app/pyqt_ui/font_panel.py#L91-L104)): header shows `Font Settings · บทสนทนา` (target-aware, accent-colored) — user sees which UI they're tuning without scrolling

### Mini UI Light-Theme Fix
- **Icon inversion on light themes** ([mini_ui.py:1-37 + 105-130](python-app/mini_ui.py#L1-L37)): added `_invert_rgb_keep_alpha()` (PIL) + `_bg_is_light()` luminance check. White-line icons (play/pause/expand) auto-invert to dark when bg is light. `create_mini_ui()` now reloads icons on every rebuild so theme changes propagate

---

## Changelog — 2026-04-26 (early)

### NPC Manager Polish
- **TUI character click pipeline** ([translated_ui.py:5939](python-app/translated_ui.py#L5939) + [npc_manager_panel.py:827](python-app/pyqt_ui/npc_manager_panel.py#L827)): clicking a name on TUI now opens NPC Manager with two pipelines —
  - A. existing → switch tab MAIN, fill search box, auto-select row
  - B. missing → auto-add `{firstName: name}` → autosave with toast `"✓ เพิ่ม 'X' แล้ว"` → fall through to A
  - Fixed: TUI was calling old Tkinter API `find_and_display_character` (no-op) → now calls `open_with_character`
  - Fixed: `open_with_character` used QListWidget API on a QTreeWidget (`.item()`/`.setCurrentRow()`) → switched to `topLevelItem()`/`setCurrentItem()`
- **Gender chips per-color** ([npc_manager_panel.py:1289](python-app/pyqt_ui/npc_manager_panel.py#L1289)): details panel chips now use the same colors as the filter bar — Male `#58a6ff` blue, Female `#f06292` pink, Neutral `#8e8e93` grey (via `gender_chip[active="true"][gender="..."]` QSS)
- **Search clear button moved inside QLineEdit** ([npc_manager_panel.py:584](python-app/pyqt_ui/npc_manager_panel.py#L584)): X button is now child of `_search_input`, positioned at right edge via `resizeEvent` patch + `setTextMargins(0,0,32,0)`. Visible whenever search has text — including auto-fill from TUI click (signals NOT blocked)
- **Gender filter "ไม่ระบุ" inclusive** ([npc_manager_panel.py:1464](python-app/pyqt_ui/npc_manager_panel.py#L1464)): now matches anything that's not exactly `Male` or `Female` (covers Neutral, Unknown, None, missing — was 5 → ~10 entries)

### word_fixes Deprecated
- **Cleared 80 OCR-era entries** from `npc.json` → `word_fixes: {}` (key kept for backwards-compat, prevents `KeyError` on access)
- **Backup**: `python-app/backups/word_fixes_backup_20260426.json` with metadata (count, reason, restore path)
- **Why**: text hook from server doesn't have OCR character errors (`1↔i`, `0↔o`, `|↔I`, `xxxl↔xxx!`) that word_fixes was built to correct. Name preservation already handles FFXIV proper nouns via 2-layer system (`_mark_names_in_text` + `_restore_names_in_translation`)
- **WORD FIX tab hidden** ([npc_manager_panel.py:783-786](python-app/pyqt_ui/npc_manager_panel.py#L783-L786)): button created but `setVisible(False)` and not added to layout. WordFixesTab page + DictTabBase logic + `_stack` page index still intact (re-enable by adding back to layout)

### ROLES Tab Merged → MAIN
- **TABS reduced 5→3**: ROLES tab removed entirely; personality (`character_roles[firstName]`) now editable inline in MAIN details panel
- **`character_roles` dict in npc.json unchanged** — only the editing UI consolidated. Same `dm.set_character_role()` / `dm.delete_character_role()` API
- **Personality field** ([npc_manager_panel.py:1568-1599](python-app/pyqt_ui/npc_manager_panel.py#L1568-L1599)): `QTextEdit` between Name and Gender, starts at 1 line (`fm.height() + 22`), drag bottom-right grip to expand up to 420px max
- **Custom `_TextEditResizeGrip` class** ([npc_manager_panel.py:386-481](python-app/pyqt_ui/npc_manager_panel.py#L386-L481)): triangle paint at bottom-right corner (`SizeVerCursor`); on drag, BOTH the textarea AND the panel window grow by the same delta — prevents textarea overflow into widgets below
- **Auto-save behavior**: `_on_primary` after `add_main_character`/`update_main_character` calls `set_character_role(first, text)` if textarea has content, `delete_character_role(first)` if empty (keeps dict tidy)
- **Removed**: `btn_personality` + `_on_open_personality` + `_update_personality_button` + `panel.open_role_for_character()` (cross-tab nav no longer needed)

### MAIN Layout Polish
- **List/details ratio**: list `stretch=3→2`, details `stretch=2→3` + `list_widget.setMinimumWidth(380→280)` — more room for the details panel
- **Avatar 80→120 px** ([npc_manager_panel.py:279](python-app/pyqt_ui/npc_manager_panel.py#L279)): placeholder font auto-scales `max(20, int(SIZE * 0.35))`. "Main Characters Details" title removed — redundant with the tab title in tab bar
- **UPDATE + Delete same row** ([npc_manager_panel.py:1664-1685](python-app/pyqt_ui/npc_manager_panel.py#L1664-L1685)): `action_row` HBox (UPDATE stretch=4, Delete stretch=1, both height=40) — saves ~32px vertical
- **Tab description repositioned** ([npc_manager_panel.py:790-814](python-app/pyqt_ui/npc_manager_panel.py#L790-L814)): moved from below search bar to inside tab bar, centered in remaining space (`stretch | title body | stretch`). Two-tone — title 13pt bold (text), body 11pt light (text_dim)
- **TABS now 4-tuple**: `(id, label, title, body)` — title and body styled separately

### Bug Fixes
- **Light theme white headers** ([npc_manager_panel.py:91-94](python-app/pyqt_ui/npc_manager_panel.py#L91-L94)): `_build_list_header` had hardcoded `rgba(255,255,255,160)` → switched to `setObjectName("npc_list_header")` so QSS theming covers it (uses `text_dim`). Same fix for `_PlaceholderTab`
- **Custom `confirm_delete()` helper** ([npc_manager_panel.py:100-237](python-app/pyqt_ui/npc_manager_panel.py#L100-L237)): replaces 4 `QMessageBox.question` calls (delete main char / avatar / NPC / dict entry). Frameless dialog, 14pt title + 12pt message, **red "ใช่ ลบ" button** (`#d23030`), theme-aware via parent panel's palette

---

## 🆕 Major Refactor — 2026-04-25

### Dead-Code Purge (~10,000 LOC removed)

**Files deleted entirely:**
- `simple_monitor.py` — Smart Performance / CPU throttling (OCR-era)
- `performance_analysis.py` — 0 imports
- `ui_manager.py` — 1861 LOC, 0 imports (Tkinter UI manager superseded)
- `style_preview.py` — standalone dev tool
- `advance_ui.py` — 1044 LOC AdvanceUI class never instantiated
- `control_ui.py` — 3444 LOC OCR area-manager UI never shown
- `Legacy/` folder

**Major code removed from MBB.py + settings.py:**
- `SettingsUI` Tkinter class (settings.py 1370 LOC) — superseded by PyQt6
- `area_detection_stability_system` + 4 related funcs (350 LOC)
- 6 dead callback methods: `restart_control_ui`, `on_control_close`,
  `trigger_temporary_area_display`, `toggle_control`, `set_cpu_limit`,
  body of `handle_control_ui_event`
- 7 OCR-era area switching: `test_area_switching`, `explain_area_switching`,
  `smart_switch_area`, `switch_area_using_preset`, `find_appropriate_preset`,
  `switch_area_directly`, `update_detection_history`
- Click-to-translate (~95 LOC across `control_ui.py` + `MBB.py`)
- `translation_loop` simplified — removed CPU throttling + dead unreachable code
- 5 orphan settings keys: `bg_swatch_mode`, `bg_swatch_transparency`,
  `line_spacing`, `text_transparency`, `tui_sizes`, `buffer_settings`
- `enable_cpu_monitoring` + 5 cpu_* keys
- `enable_auto_area_switch`, `enable_click_translate` settings keys

**Settings.py: 2433 → 1053 lines  | MBB.py: 7458 → 6543 lines**

### Audit Fixes (translator + handler) — markers `AUDIT_FIX_*`

- **C2** API retry backoff (translator_gemini.py:~1149) — gracefully fail on rate limits
- **C3** `winfo_exists()` guard in `exit_program` (MBB.py) — eliminates 6-month TclError
- **H1** Bound `last_translations` (200 entries FIFO) + `translation_cache` (100, OrderedDict)
- **H2** `threading.Lock` around shared cache state (translator + handler)
- **H4** Raw text as cache key (no hash collisions)
- **M1+M3** Hot-path `logger.info` → `debug`, `print()` → `logging`

### Theme System v2 — `pyqt_ui/styles.py` + `appearance.py`

**12 modern theme palettes** (replaced old 5):

| # | Theme | bg | accent | Style |
|---|-------|-----|--------|-------|
| 1 | Carbon | `#0d1117` | `#58a6ff` | GitHub Dark |
| 2 | Graphite | `#16181c` | `#7c8aed` | Linear-style |
| 3 | Slate | `#0f172a` | `#38bdf8` | Tailwind |
| 4 | Mocha | `#1e1e2e` | `#cba6f7` | Catppuccin |
| 5 | Tokyo | `#1a1b26` | `#7aa2f7` | Tokyo Night |
| 6 | Dimmed | `#22272e` | `#6cb6ff` | GitHub Dimmed |
| 7 | Neon | `#0a0e1a` | `#00d9ff` | Cyberpunk |
| 8 | Synthwave | `#1a0d2e` | `#ff5599` | 80s Pink |
| 9 | Forge | `#1a0f0a` | `#ff8c42` | Ember Orange |
| 10 | Snow | `#ffffff` | `#0969da` | GitHub Light |
| 11 | Cream | `#faf6ed` | `#c2410c` | Warm paper |
| 12 | Mint | `#f0fdf4` | `#15803d` | Cool fresh |

**`derive_palette(primary, secondary, surface=None, text_override=None)` improvements:**
- Proportional surface elevation: `base = max(0.018, min(0.045, primary_l * 0.32))`
  → very dark themes use small shifts so surfaces don't pop bright; lighter themes use more
- Light-theme branch (bg luminance > 0.5): aggressive negative shifts (-0.075 surface, -0.130 border) for visibility on near-white bg
- WCAG-correct `toggled_text` threshold: `< 0.179 → white text, else dark text`
  (was 0.5 → caused light accents like #58a6ff to use white text → 2.4:1 contrast)
- Helpers added: `_shift_lightness()`, `_desaturate()`, `invert_pixmap()`, `is_light_theme()`

**Migration logic** in `appearance.py` `load_custom_themes`:
- Detect old default theme accents (`#6c5ce7`, `#1E88E5`, etc.) + Thai names
  (`ธีมเริ่มต้น`, `ธีมฟ้า`, etc.) → wipe + re-create with new design
- Backwards-compat: if user customized colors, keep their version

### Critical Bug Fix — `appearance.py:get_theme_color()`

**Symptom:** All buttons in main window appeared WHITE on every theme.

**Root cause (after v2 redesign):** When `derive_palette` was extended to accept
optional `surface_override` / `text_override` parameters, callers used
`am.get_theme_color("surface_override")` (with default=None). But
`get_theme_color()` had a fallthrough that returned `self.fg_color = "#FFFFFF"`
when key was missing AND no default was provided. So the "optional" overrides
were always being filled with white. `derive_palette` interpreted these as user
overrides and made `bg_surface = #FFFFFF`, `text = #FFFFFF` → invisible buttons.

**Fix:** Added `if color_value is None and default is None: return None` —
respect the caller's explicit None default.

### Theme Manager UI — `pyqt_ui/theme_panel.py`

- New `ThemeSwatch(QWidget)` — custom paint with **5 color dots** showing actual palette
  (bg_titlebar, surface, border, accent, text) instead of old 2-color gradient
- Panel: 400×520, **4 cols × 3 rows** grid for 12 themes
- **Instant apply** — clicking a swatch applies immediately, no APPLY button
- **4-color picker** (was 2): Background, Accent, Surface (auto if not set), Text (auto if not set)
- "Auto" state shows diagonal stripe pattern + dashed border
- Removed APPLY button + status label entirely
- All edits (color picks, name input) auto-apply via `_apply_instant()`

### Modern Toggle Switch — `pyqt_ui/settings_panel.py:ToggleSwitch`

iOS-style switch widget replacing QCheckBox pill:
- 44×22px track with 16px sliding knob
- 160ms OutCubic animation via `QPropertyAnimation`
- Hover state, keyboard support (Tab + Space/Enter)
- Drop-in API: `isChecked()`, `setChecked()`, `toggled` signal,
  `stateChanged` signal (compat)
- `set_palette(palette)` — theme-aware

### White-Icon Inversion for Light Themes

`pyqt_ui/styles.py:invert_pixmap()` — RGB-invert preserving alpha
(uses `QImage.invertPixels(InvertMode.InvertRgb)`).

`header_bar.py` + `bottom_bar.py` have `update_icon_theme(invert: bool)`
called by `main_window._apply_theme()` based on bg luminance:
- Dark bg → keep white icons
- Light bg (Snow/Cream/Mint) → invert pin/theme/settings icons to dark

### Splash Screen

`MBB.py:638` — `corner_r = 4` (was `max(12, target_w // 40)`)
Almost-square corners per user preference.

## Development Notes

This is a distribution-focused rebuild. All changes must prioritize:
- **Portability** - Works on any Windows machine
- **Security** - No hardcoded credentials
- **User-Friendliness** - Minimal setup steps
- **Auto-Update** - Plugin updates via Dalamud

---

## UI Design Notes (PyQt6)

### Main Window Layout — `pyqt_ui/main_window.py`

#### ขนาดหน้าต่างและพื้นที่แสดงผล

| ค่าคงที่ | ค่า | ความหมาย |
|---------|-----|---------|
| `BG_W` | 296 px | ความกว้างของพื้นที่แสดงผลหลัก (dark bg panel) |
| `BG_H` | 265 px | ความสูงของพื้นที่แสดงผลหลัก |
| `MARGIN_BASE` | 12 px | margin ด้านขวาและล่าง (เผื่อเงา shadow) |

ขนาดหน้าต่างจริง **คำนวณแบบ dynamic** จาก logo ที่โหลด ไม่ใช่ค่าคงที่:

```
win_w = margin_left + BG_W + margin_right
win_h = margin_top  + BG_H + margin_bottom
```

#### Logo `mbb_meteor.png` — การวางและตำแหน่ง

**ขนาด logo:**
- ความกว้าง = `int(BG_W * 0.6)` = **177 px** (60% ของความกว้าง bg)
- ความสูง = คำนวณจาก aspect ratio ของรูปจริง (`QPixmap.height()` หลัง scale)
- fallback ถ้าไม่มีไฟล์: `logo_h = int(logo_w * 0.73)`

**หลักการวาง (design intent):**
- ขอบขวาของ logo จัดให้ตรงกับ **กึ่งกลางแนวตั้งของ bg panel**
- logo ล้นขึ้นด้านบน bg panel ครึ่งหนึ่งของความสูงตัวเอง

**คำนวณ margin แบบ asymmetric:**
```python
logo_overflow_left = max(0, logo_w - BG_W // 2)  # logo ล้นซ้ายออกนอก bg
logo_overflow_top  = logo_h // 2                  # logo ล้นขึ้นเหนือ bg

margin_left   = logo_overflow_left + 4   # เผื่อช่องว่าง 4 px
margin_top    = logo_overflow_top  + 4
margin_right  = MARGIN_BASE              # 12 px (shadow)
margin_bottom = MARGIN_BASE              # 12 px (shadow)
```

**ตำแหน่ง logo (pixel coordinates ใน widget):**
```python
bg_center_x = margin_left + BG_W // 2   # จุดกึ่งกลาง bg ในแนวนอน
logo_x = bg_center_x - logo_w           # ขอบขวา logo = จุดกึ่งกลาง bg
logo_y = margin_top - logo_h // 2       # logo ล้นขึ้นครึ่งความสูง
```

> **หมายเหตุ:** ค่า `logo_x` และ `logo_y` ต้องเป็น **บวกเสมอ** เพราะ `margin_*` ถูก
> คำนวณมาเพื่อรองรับ overflow แล้ว หากลบ → QWidget clip logo หาย

**Logo layer:** `QLabel` วางเป็น overlay บน `self` (ไม่ใช่ใน layout)
ใช้ `setAttribute(WA_TransparentForMouseEvents)` และ `raise_()` ให้อยู่บนสุด

#### Header Bar — การจัดการ margin ซ้ายหลัง logo overlay

Logo คลุมครึ่งซ้ายของ header → ต้อง push content ไปทางขวา:

```python
header_margin_left = BG_W // 2 - 14   # = 134 px
header_layout.setContentsMargins(header_margin_left, 0, 4, 0)
```

ค่า `BG_W // 2 - 14` (134 px) คือค่าที่ให้ version text มีพื้นที่แสดงผลพอดี
- ถ้าเพิ่มค่า → version text ถูกตัด (เลขท้ายหาย)
- ถ้าลดค่า → version text ทับกับ logo

Version label font: **7pt** (`QFont(FONT_PRIMARY, 7)`) ใน `header_bar.py`
QSS: `font-size: 7pt; padding-top: 4px;` — ขยับลงจากตำแหน่งเดิมเล็กน้อย

---

## Glass Mode — `pyqt_ui/styles.py` `get_glass_overrides()`

### หลักการ

เมื่อเปิด Glass mode (**●** button ใน header):
- **ปุ่มทั้งหมดล่องหน** — transparent bg, ไม่มี border, ตัวอักษรจางมาก (~20% opacity)
- **Hover** — ตัวอักษรสว่างขึ้นเล็กน้อย (~50% opacity), bg จางๆ
- **Toggled buttons** — สว่างกว่าปุ่มปกติเล็กน้อย (~35% opacity)
- **Labels ทั้งหมดจาง** — status, info, version (~14-20% opacity)
- **LOGO แสดงตลอดเวลา** — ไม่อยู่ใน QSS system (QPixmap overlay)

### UI Elements ที่ได้รับผลกระทบ

| Element | Object Name | Glass State |
|---------|------------|-------------|
| Toggle buttons (TUI/LOG/MINI) | `toggle_btn` | transparent, faint text |
| Utility button (NPC Manager) | `utility_btn` | transparent, faint text |
| Start/Stop button | `btn_primary` | transparent, faint text |
| Icon buttons (Theme/Settings) | `icon_btn` | very faint text |
| Header buttons (Glass/Pin) | `header_btn` | very faint text |
| Close button | `btn_close` | very faint, red hover |
| All labels | `status_dot`, `status`, `info_key`, `info_value`, `status_info`, `version` | very faint |

### Toggle Mechanism — `main_window.py`

```python
def _on_toggle_glass(self):
    self._is_glass = not self._is_glass
    self._apply_theme()          # reapply QSS + glass overrides
    header_bar.update_glass_state(self._is_glass)
```

`_apply_theme()` builds QSS then appends `get_glass_overrides()` if `_is_glass == True`

---

## Mini UI — `mini_ui.py`

### ขนาดและตำแหน่ง

| Property | ค่า |
|----------|-----|
| ขนาด | 50×176 px |
| ตำแหน่ง | ชิดขอบซ้ายของจอ, ตรง Y กับ main window |
| Window type | Tkinter Toplevel, frameless (`overrideredirect`) |
| Z-order | Always on top |

### Asymmetric Rounded Corners (Win32)

ใช้ `CreateRoundRectRgn` สร้าง window region:
- **ฝั่งซ้าย**: เหลี่ยม (ชิดขอบจอ)
- **ฝั่งขวา**: โค้งมน, ellipse = **10** (~5px radius)

> **สำคัญ:** ค่า corner ต้องไม่มากเกินไป มิฉะนั้น window region จะตัดขอบ
> highlight border ที่มุมบนขวาและล่างขวาหายไป (border เป็นสี่เหลี่ยม Tkinter
> ไม่โค้งตาม region)

### Highlight Border

เมื่อ Mini UI ปรากฏ จะกระพริบขอบสีขาว 1.2 วินาที:
- Flash: `highlightthickness=2`, สี `#e0e0e0`
- ปกติ: `highlightthickness=1`, สี `#2a2a2a`

---

## TUI Lock Mode Shadow System — `translated_ui.py`

### สถาปัตยกรรม

ระบบเงาข้อความมี 2 engine สลับกันได้ผ่าน flag `self._use_pil_shadow`:

| Flag | Engine | สถานะ |
|------|--------|-------|
| `False` (ปัจจุบัน) | **Canvas Multi-Ring** | ใช้งานจริง — เสถียร |
| `True` | PIL Gaussian Blur | ทดลอง — ยังใช้ไม่ได้กับ `transparentcolor` |

### Canvas Multi-Ring (Active) — `_create_text_shadows_canvas()`

สร้างเงาด้วย Canvas text items ซ้อนหลายชั้นที่ pixel offsets ต่างๆ:

**Lock mode 1 (พื้นหลังโปร่งใส) — 3 ชั้น, 36 items:**

| ชั้น | ระยะ | จำนวนตำแหน่ง | สี |
|------|------|-------------|-----|
| Outer | ~3px | 16 (วงกลม) | `#111111` |
| Middle | ~2px | 12 (วงกลม) | `#080808` |
| Inner | ~1px | 8 (สี่เหลี่ยม) | `#000000` |

**โหมดปกติ (มีพื้นหลัง) — 1 ชั้น, 8 items:**

| ชั้น | ระยะ | จำนวนตำแหน่ง | สี |
|------|------|-------------|-----|
| Outline | ~1px | 8 (สี่เหลี่ยม) | `#000000` |

### ข้อจำกัดของ `transparentcolor` กับ Blur Shadow

`transparentcolor` ใช้ **1-bit color-key** — pixel ต้องทึบ 100% หรือโปร่งใส 100%
ไม่รองรับ partial alpha → Gaussian blur ที่มีขอบจางจะแสดงเป็นพื้นสี่เหลี่ยมทึบ

**แนวทางที่ทดลองแล้ว:**

| วิธี | ผลลัพธ์ | ปัญหา |
|------|---------|-------|
| Canvas multi-ring (3 ชั้น) | ใช้งานได้ | ขอบไม่นุ่มนวล (integer pixel) |
| Tkinter stipple patterns | ล้มเหลว | สร้าง dot pattern บนตัวอักษร |
| PIL Gaussian Blur → solid colors | ล้มเหลว | pixel สีเทาไม่ตรง key → แสดงเป็นพื้นทึบ |

**แนวทางที่ยังไม่ได้ทดลอง:**
- Win32 `UpdateLayeredWindow` + per-pixel alpha (ซับซ้อนมาก, ต้อง bypass Tkinter rendering)

### Call Sites — จุดที่สร้างเงา (6 จุด)

ทุกจุดต้องส่ง `text=""` เพื่อให้เงา sync กับ typewriter effect:

| Path | ที่อยู่ | ข้อความ |
|------|--------|---------|
| Fast + speaker name | `_handle_normal_text_fast` | `text=speaker` (มีข้อความทันที) |
| Fast + dialogue | `_handle_normal_text_fast` | `text=""` (เติมทีหลัง) |
| Fast + no speaker | `_handle_normal_text_fast` | `text=""` (เติมทีหลัง) |
| Normal + speaker name | `_handle_normal_text` | `text=name` (มีข้อความทันที) |
| Normal + dialogue | `_handle_normal_text` | `text=""` (typewriter เติม) |
| Normal + no speaker | `_handle_normal_text` | `text=""` (typewriter เติม) |

> **สำคัญ:** ห้ามเปลี่ยน `text=""` เป็น `text=dialogue` ในจุดที่ใช้ typewriter
> มิฉะนั้นเงาจะแสดงเต็มก่อนตัวอักษรหลัก

### Safety — itemconfig Type Check

เนื่องจาก `outline_container` อาจมีทั้ง text items และ image items (จาก PIL engine)
ทุกจุดที่ทำ `canvas.itemconfig(outline, ...)` ต้องเช็ค type ก่อน:

```python
if self.components.canvas.type(outline) == "text":
    self.components.canvas.itemconfig(outline, text=...)
```

จุดที่เพิ่ม type check แล้ว: `fill`, `font`, `width`, `text` operations ทั้งหมด

### PIL Shadow Engine (Dormant) — `_generate_solid_shadow()`

โค้ดยังอยู่ในไฟล์แต่ไม่ถูกเรียกใช้ (`_use_pil_shadow = False`):
- `_resolve_pil_font()` — แปลงชื่อฟอนต์ Tkinter → PIL ImageFont
- `_wrap_text_pil()` — ตัดบรรทัดสำหรับ PIL (รองรับภาษาไทย)
- `_generate_solid_shadow()` — สร้าง shadow image ด้วย Gaussian Blur + LUT
- `_create_pil_shadow()` — วาง shadow image บน Canvas

---

## TUI Auto-Show Opacity System — `translated_ui.py`

### ปัญหาที่พบและแก้ไขแล้ว

**อาการ:** Auto-show (จากการแปล) แสดง TUI ที่ opacity ~80-90% แทนที่จะเป็น 97%
**สาเหตุ:** `show_tui_on_new_translation()` restore opacity **เฉพาะ** เมื่อ `is_window_hidden == True`
ถ้า fade-out กำลังทำงานอยู่ (alpha กำลังลด) แต่ window ยังไม่ hidden → `is_window_hidden == False` → ไม่ restore

**สถานการณ์ที่ทำให้เกิดบัค:**
```
ข้อความแสดง → fade เริ่ม → alpha ลด (เช่น 0.85)
→ ข้อความใหม่มาระหว่างนั้น
→ is_window_hidden == False → ไม่ restore
→ window ค้างที่ alpha 0.85
```

**การแก้ไข:** ย้าย `restore_user_transparency()` ออกมานอก `if is_window_hidden` block — ทำให้ restore ทุกครั้งที่ข้อความใหม่มา

```python
def show_tui_on_new_translation(self):
    if self.state.is_window_hidden:
        self.root.deiconify()
        self.state.is_window_hidden = False

    # คืนค่า opacity ทุกครั้ง — ไม่ขึ้นกับ is_window_hidden
    self.restore_user_transparency()
```

### Auto-Show Setting Toggle — `settings.py`

Setting `enable_tui_auto_show` ถูก hardcode เป็น `True` → ผู้ใช้ toggle ปิดไม่ได้ ได้แก้ไขแล้ว:

| ไฟล์ | บรรทัด | ก่อนแก้ | หลังแก้ |
|------|--------|---------|---------|
| `settings.py` | ~1134 | `set(True)` hardcode | อ่านจาก settings จริง |
| `settings.py` | ~1317 | `always_on=True` (คลิกไม่ได้) | ลบออก → toggle ปกติ |
| `settings.py` | ~2217 | `= True` hardcode | อ่านจาก `tui_auto_show_var` |

> **สำคัญ:** `show_tui_on_new_translation()` ต้องไม่มี setting check ภายใน
> setting gate อยู่ที่ `_trigger_tui_auto_show()` ใน `MBB.py` เท่านั้น
> ถ้าเพิ่ม check ใน `show_tui_on_new_translation()` → auto-show พัง

### Two Auto-Show Code Paths

| Path | ไฟล์ | Trigger | Opacity Restore |
|------|------|---------|----------------|
| Text hook detection | `MBB.py` `_trigger_tui_auto_show()` | ตรวจพบ text hook ใหม่ | ไม่ restore (แค่ `deiconify`) |
| Text rendering | `translated_ui.py` line ~2952 | คำแปลมาถึงและ render | restore เสมอ (fixed) |

---

## ControlPanel + BottomBar Layout — การจัด Status Info

### Layout ปัจจุบัน (หลัง redesign)

```
┌─────────────────────────┐
│ HeaderBar (44px)        │
├─────────────────────────┤
│ ● Ready        [Stop]   │  ← status dot + btn_start_stop
│ Game          FFXIV     │  ← game info row (11pt)
│ MODEL: GEMINI [READY]   │  ← lbl_status_info (8pt mono, dim)
│                         │  ← addStretch(1) ≈ 31px
├─────────────────────────┤
│ TUI  LOG  MINI          │
│ NPC Manager  🎨 ⚙       │
│                         │  ← bottom padding 16px
└─────────────────────────┘
```

### ขนาดส่วนประกอบ (px)

| Component | Height | หมายเหตุ |
|-----------|--------|---------|
| HeaderBar | 44 | `setFixedHeight(44)` |
| divider1 | 1 | |
| ControlPanel content | ~88 | margins + rows รวมกัน |
| addStretch(1) | ~31 | `BG_H - fixed_content` |
| divider2 | 1 | |
| BottomBar | 100 | `setFixedHeight(100)` |
| **รวม** | **265** | = BG_H |

### Status Info — `lbl_status_info`

- Widget: `QLabel` objectName `"status_info"` ใน `control_panel.py`
- Font: `FONT_MONO, 8pt`, alignment center, wordWrap=True
- API: `control_panel.set_status_info(text)` และ `MBB.py` ชี้ `self.info_label` มาที่นี้
- QSS: `QLabel#status_info` สี `text_dim` ใน `styles.py`
- Signal path: `signals.info_update` → `_on_info_signal()` → `control_panel.set_status_info()`

### การย้ายจาก BottomBar (เหตุผล)

Status info เดิมอยู่ใน BottomBar ล่างสุด ห่างจาก Game info มาก — ย้ายขึ้นมาอยู่ใต้ Game row
ใน ControlPanel เพื่อให้ข้อมูล context (Game + Model + Dalamud) อยู่ใกล้กัน

**ไฟล์ที่เปลี่ยน:**

| ไฟล์ | การเปลี่ยนแปลง |
|------|---------------|
| `control_panel.py` | เพิ่ม `lbl_status_info` + `set_status_info()` |
| `bottom_bar.py` | ลบ `lbl_info`, ลด height 130→100, bottom padding 10→16px |
| `main_window.py` | `_on_info_signal` → เรียก `control_panel.set_status_info()`, BG_H 296→265 |
| `styles.py` | เพิ่ม `QLabel#status_info` QSS |
| `MBB.py` | `self.info_label = self.control_panel.lbl_status_info` |

> **หมายเหตุ BG_H:** ถ้าเพิ่ม/ลด component ใน ControlPanel หรือ BottomBar ให้ปรับ BG_H ด้วย
> เพื่อให้ stretch gap ตรงกลางอยู่ที่ ~25-35px

---

## Translation System — `translator_gemini.py`

### System Prompt Versioning

มี 2 versions สลับได้ผ่าน flag `self.use_verbose_prompt`:

| Flag | Method | Token ประมาณ | สถานะ |
|------|--------|-------------|-------|
| `False` (ค่าเริ่มต้น) | `get_rpg_general_prompt()` — v2 optimized | ~450 | **ใช้งานจริง** |
| `True` | `get_rpg_general_prompt_v1()` — v1 verbose | ~1,000 | Backup สำหรับ revert |

**วิธี Revert:** เปลี่ยน `self.use_verbose_prompt = True` ใน `__init__()` แล้ว restart

### Token Budget

| ส่วนประกอบ | v1 (เดิม) | v2 (ปัจจุบัน) |
|------------|-----------|--------------|
| System prompt | ~1,000 | ~450 |
| Protected names (290 ชื่อ, in system) | ~400 | 0 (ลบออก) |
| Preserve names (relevant, per-request) | ~80 | ~80 |
| Lore context | ~150 | ~80 |
| Context + style + dialogue | ~500 | ~500 |
| **รวม** | **~2,100** | **~1,100** |

### Name Preservation System (2 ชั้น)

ป้องกันไม่ให้ Gemini แปลชื่อตัวละครที่อยู่ในฐานข้อมูลเป็นภาษาไทย

**ชั้นที่ 1 — Pre-processing: Name Marking**

`_mark_names_in_text(text, names)` ครอบชื่อที่พบใน dialogue ด้วย `[brackets]`:
```
Input:  "Well met, Bol Noq'. We're on our way to Wachunpelo."
Output: "Well met, [Bol Noq']. We're on our way to [Wachunpelo]."
```

- เรียงชื่อยาว→สั้น เพื่อไม่ให้ match ชื่อบางส่วน (เช่น "Bol" ใน "Bol Noq'")
- ไม่ครอบ `???`
- System prompt rule 3 บอก: "Names in [brackets] must NEVER be translated. Output without brackets."

**ชั้นที่ 2 — Post-processing: Name Restoration**

`_restore_names_in_translation(translation, names_in_source)` strip brackets ทุกชนิดรอบชื่อ:

```python
# Regex: ลบ bracket/quote ทุก combo ที่ครอบชื่อ
pattern = rf'[\[「『【«"\'(]*{re.escape(name)}[\]」』】»"\'）]*'
```

**Patterns ที่จัดการได้:**

| Input | Output | กรณี |
|-------|--------|------|
| `[「Bol Noq'」]` | `Bol Noq'` | Gemini ครอบซ้อน (พบจริง) |
| `[Bol Noq']` | `Bol Noq'` | brackets ธรรมดา |
| `「Bol Noq'」` | `Bol Noq'` | Japanese brackets |
| `**Bol Noq'**` | `**Bol Noq'**` | Bold markers คงเดิม |
| `**[Bol Noq']**` | `**Bol Noq'**` | ลบ brackets, เก็บ bold |

> **สำคัญ:** Regex ไม่ลบ `*` (asterisk) — rich text markers `*italic*` และ `**bold**`
> ต้องคงไว้สำหรับ `RichTextFormatter` ใน `translated_ui.py`

**ชั้นที่ 3 — General Bracket Cleanup (หลัง Name Restoration)**

`re.sub(r'\[([^\[\]]{1,30})\]', r'\1', translated_dialogue)` — strip `[brackets]` ที่ Gemini เพิ่มเอง

- Gemini บางครั้งครอบคำด้วย `[brackets]` เองโดยไม่ได้สั่ง (เช่น `[adventurer]`, `[WoL]`)
- `_restore_names_in_translation()` strip เฉพาะชื่อที่รู้จัก — คำอื่นหลุดรอดมาได้
- Regex จำกัด 1-30 ตัวอักษร เพื่อไม่ให้ลบ bracket ที่ยาวเกินไป (อาจเป็น content จริง)
- **ตำแหน่ง**: `translator_gemini.py` line ~917, หลัง `_restore_names_in_translation()`

### Rich Text Markers (จากระบบเกม)

| Marker | สไตล์ | Font | จัดการโดย |
|--------|-------|------|----------|
| `*text*` | Italic | FC Minimal Medium | `RichTextFormatter.parse_rich_text()` |
| `**text**` | Highlight word | Base font + bold, สี `#FFB366` | `RichTextFormatter.parse_rich_text()` |
| `<NL>` | Newline | - | Text preprocessor |

> **เปลี่ยนแปลง v4:** `『name』` brackets ถูกลบออก — `highlight_special_names()` เป็น no-op
> ชื่อตัวละครตรวจจับที่ render time ผ่าน `parse_rich_text_with_names()`

---

### TUI Text Style System v4 — `translated_ui.py`

#### หลักการ

สไตล์ข้อความแบ่งตาม **ประเภท segment** และ **โหมดการแสดงผล** (dialogue/cutscene/battle)

#### Speaker Name (ชื่อผู้พูด)

| โหมด | สี | Font |
|------|-----|------|
| Dialogue — Known | `#38bdf8` (cyan) | Normal (thin) |
| Dialogue — Unknown (???) | `#a855f7` (purple) | Normal (thin) |
| Battle | `#FF6B00` (orange) = สีเดียวกับ text | Normal (thin) |
| Cutscene | `#FFD700` (yellow) = สีเดียวกับ text | Normal (thin) |

> **หลักการ:** Speaker ใช้ตัวปกติ (ไม่ bold) ทุกโหมด เพื่อความเข้ากันได้กับระบบ name detection
> Safety: strip `**`, `*`, zero-width chars จาก speaker name ก่อน `name in self.names` check
> แก้ไขที่ 3 จุด: `_handle_normal_text_fast`, `_handle_normal_text`, `display_speaker_name`

#### Dialogue Text Segments

| Segment | Dialogue | Cutscene | Battle |
|---------|----------|----------|--------|
| Normal text | white | `#FFD700` yellow | `#FF6B00` orange |
| Character name | `#38bdf8` cyan, thin | yellow, **bold** | orange, **bold** |
| `**highlight**` | `#FFB366` light orange, **bold** | `#FFB366` | `#FFB366` |
| `*italic*` | text color, FC Minimal | text color, FC Minimal | text color, FC Minimal |

#### Name Detection Pipeline (v4)

เดิม: `highlight_special_names()` → ครอบชื่อด้วย `『』` → สีจาก brackets
ใหม่: ตรวจจับชื่อที่ render time — ไม่มี brackets

```
text + names list
    ↓
RichTextFormatter.parse_rich_text_with_names(text, names)
    ↓
segments: [{text, font_style: 'normal'|'bold'|'italic'|'name'}]
    ↓
create_rich_text_with_outlines() → สีตาม mode + font_style
```

**Key methods:**
- `parse_rich_text_with_names(text, names)` — parse markers + detect names → segments
- `_split_text_by_names(text, sorted_names)` — word-boundary name matching
- `_needs_rich_text(text)` — check if text has `*` markers OR character names (replaces `has_rich_text_markers`)
- `highlight_special_names()` — **no-op** (returns text unchanged)

**Call sites ที่ใช้ `_needs_rich_text`** (4 จุด):
1. Fast path no-speaker (line ~3258)
2. Post-typewriter (line ~4323)
3. Show full text (line ~4477)
4. Font change re-apply (line ~4998)

### Zero-Width Character Safety — `text_corrector.py`

`text_corrector.py` โหลดชื่อจาก `npc.json` โดย strip zero-width chars ก่อนเก็บ:

```python
_zws = "\u200b\u200c\u200d\ufeff"
clean = char["firstName"].strip().translate(str.maketrans("", "", _zws))
```

- ใช้กับทั้ง `main_characters` (firstName + lastName) และ `npcs` (name)
- ป้องกันกรณีข้อมูลจาก game text hook มี ZWS ติดมา → ชื่อ match ไม่เจอ
- **เหตุการณ์จริง**: พบ `"Tataru\u200b"` ใน npc.json → ชื่อซ้ำกับ `"Tataru"` ที่มีอยู่แล้ว

### get_relevant_names() — Name Filtering

- ดึงชื่อที่ปรากฏจริงใน dialogue text + essential names (20 ตัวหลัก)
- จำกัดสูงสุด 20 ชื่อ เพื่อควบคุม token
- Essential names: Y'shtola, Alphinaud, Alisaie, Wuk Lamat, Estinien, G'raha Tia, Thancred, Urianger, Krile, Emet-Selch, Hythlodaeus, Venat, Meteion, Zenos, Koana, Zoraal Ja, Gulool Ja, Sphene, Otis

---

## TUI Resize System — `translated_ui.py`

### สถาปัตยกรรม

Resize ใช้ 3 methods: `start_resize()` → `on_resize()` → `stop_resize()`
Bindings อยู่ใน `setup_bindings()` เท่านั้น (ไม่ bind ซ้ำใน `_create_resize_handle()`)

### ป้องกัน Resize กระตุก (4 จุดสำคัญ)

| จุด | สาเหตุ | การแก้ไข |
|-----|--------|---------|
| `geometry()` ไม่มีตำแหน่ง | `f"{w}x{h}"` ไม่ระบุ +x+y → Tkinter คำนวณตำแหน่งใหม่ทุก frame | `start_resize()` บันทึก `resize_anchor_x/y`, `on_resize()` ใช้ `f"{w}x{h}+{x}+{y}"` |
| `SetWindowRgn` ระหว่าง drag | `apply_rounded_corners_to_ui()` ทุก 100ms → Win32 สร้าง region ใหม่ + redraw | ลบออกจาก `on_resize()` — ใส่กลับใน `stop_resize()` (`root.after(150, ...)`) |
| Duplicate bindings | resize_handle ถูก bind ทั้งใน `setup_bindings()` และ `_create_resize_handle()` | ลบ bindings ใน `_create_resize_handle()` เหลือแค่ที่เดียว |
| Root drag conflict | root `<B1-Motion>` → `on_drag()` → `_do_move()` fire พร้อม resize | `on_drag()` เพิ่ม `is_resizing` guard, `on_click()` เพิ่ม `_is_click_on_resize_handle()` check |

### Bug Fix Session — Buttons + Handle หายตอน Resize ใหญ่ (v1.8.2 / 2026-05-08)

**อาการ:** ลาก resize handle ขยาย TUI → buttons (X, lock, transparency, font) ทั้งคอลัมน์ขวาหาย, resize handle ก็หายไปด้วย → resize ไม่ได้อีก. เกิดเฉพาะตอน **ขยาย** (extend) ขนาดถึงจุดหนึ่ง — การย่อ (shrink) ทำงานปกติ. หลัง buttons หาย หาก hover ก็ไม่ตอบสนอง.

**Root Causes (4 ชั้น):**

| ชั้น | ต้นเหตุ | Diagnostic |
|-----|--------|-----------|
| 1. **Pack manager collapse** | Tkinter `pack_propagate(False)` + รัว Configure events ระหว่าง resize → control_area's children (close/lock/color buttons) ถูก collapsed เป็น `(x=0, y=0, w=1, map=0, view=0)` แม้ frame เองยังอยู่ตำแหน่งถูก | log แสดง `buttons=close(x=0,y=0,w=1,map=0,view=0)` ตอน BEFORE restore |
| 2. **stop_resize ไม่ fire** | Win32 `SetWindowRgn` clip resize_handle ออกนอก viewport → ButtonRelease event ที่ส่งไปที่ handle หาย | log: 5 "UI resize completed" entries แต่ 0 [RESIZE-DEBUG] entries (debug ใส่ใน stop_resize) |
| 3. **Canvas.lift TclError** | Canvas widget override `lift = tag_raise` (รับ tagOrId) → เรียก `lift()` no-args โยน TclError `wrong # args: should be ".!toplevel2.!frame.!canvas raise tagOrId ?aboveThis?"` | error log จาก _restore_layout |
| 4. **Stale `default_width` cache** | `self.default_width = self.settings.get('width')` ถูก set ครั้งเดียวที่ startup. ผู้ใช้ resize → settings.json ได้ค่าใหม่ แต่ `self.default_width` ยังเก่า → chat-type switch กลับ dialog ใช้ค่าเก่า → window snap | line 1352 (init), line 1645 (dialog mode `geometry({default_width}x{default_height})`) |

**การแก้ไข:**

1. **Global ButtonRelease bind** (`start_resize`): `bind_all("<ButtonRelease-1>", stop_resize)` ก่อน drag, `unbind_all` ตอน stop → release event fire เสมอแม้ handle ถูก clip
2. **`_restore_layout_after_resize_universal`** เรียกจาก `on_smart_resize_end` (Configure-driven) — universal endpoint, fires after any resize-end:
   - `pack_configure` (NOT `pack_forget`) ที่ control_area + each button → ไม่ unmap children
   - `tk.call("raise", widget._w)` แทน `widget.lift()` → bypass Canvas override
   - Force re-bind auto-hide hover bindings (ไม่ conditional บน cache change)
   - Re-apply rounded corners
3. **Light/Full restore split** (เพิ่ม responsiveness):
   - `_restore_layout_light` (ระหว่าง drag, throttle 150ms): เฉพาะ pack_configure + place — ไม่มี logging, update_idletasks, auto-hide rebind, Win32 → drag responsive
   - Universal restore (ที่ release): full version with all expensive ops
4. **Sync default_width/_height** ใน `stop_resize`: `self.default_width = final_w` หลัง save settings → chat-type switch ไม่ snap กลับ
5. **ลบ orphan `tui_sizes`** จาก settings.json (code ไม่ได้ใช้แล้วตั้งแต่ 2026-04-25)

> **เพิ่มเติม:** translated_logs (PyQt6) ไม่มีปัญหาเดียวกัน เพราะ Qt resize เป็น native + ใช้ `QTimer 500ms throttle` สำหรับ disk I/O + ไม่มี Win32 SetWindowRgn calls (Qt paintEvent ทำ rounded corner เอง)

### หลักการออกแบบ

- **ข้อความแสดงตลอด** ระหว่าง resize — ไม่ซ่อน ไม่ re-render จนกว่า `stop_resize()`
- **ขอบโค้งมน** ไม่อัพเดตระหว่าง drag (Win32 `SetWindowRgn` + `update_idletasks()` หนักเกินไป)
- **ตำแหน่ง window** lock ไว้ตั้งแต่ `start_resize()` ด้วย `resize_anchor_x/y`
- **Binding ที่เดียว** ใน `setup_bindings()` เท่านั้น — ป้องกัน handler fire 2 ครั้ง

> **สำคัญ:** ห้ามเพิ่ม `apply_rounded_corners_to_ui()` กลับใน `on_resize()`
> Win32 `CreateRoundRectRgn` + `SetWindowRgn(redraw=True)` + `update_idletasks()` = กระตุกทันที

---

## Bug Fixes Log — `translated_ui.py`

### แก้ไขแล้ว (Session Feb 2026)

| Bug | สาเหตุ | การแก้ไข |
|-----|--------|---------|
| Previous dialog ลำดับผิด | `show_previous_dialog()` decrement ก่อน show ทุกครั้ง | เพิ่ม `_is_browsing_history` flag — ครั้งแรกแสดง latest, ครั้งต่อไป decrement |
| Timer ไม่ nullify หลัง cancel | `after_cancel()` ไม่ set เป็น None | เพิ่ม `= None` หลัง cancel ทุกจุด (3 ที่) |
| itemconfig บน non-text item | `outline_container` อาจมี image items | เพิ่ม `canvas.type(outline) == "text"` check (2 ที่) |
| tag_lower บน image item | เรียก tag_lower นอก type check | ย้ายเข้าไปใน `if item_type == "text"` block |
| Shadow images memory leak | `_shadow_images` list โตไม่จำกัด | เพิ่ม cap: ถ้า >50 ตัด เหลือ 20 |
| Feedback tooltip ค้าง | `winfo_exists()` เรียกจาก thread | เปลี่ยนจาก `threading.Thread` เป็น `root.after()` chain + `_active_feedback` tracking |

> **สำคัญ:** ห้ามใช้ Tkinter widget methods ใน thread — ใช้ `root.after()` เท่านั้น

---

## NPC Database — `npc.json`

### สถานะปัจจุบัน (หลัง Audit มีนาคม 2026)

| ประเภท | จำนวน |
|--------|-------|
| main_characters | 218 |
| npcs | 65 |
| word_fixes | 80 |
| lore | 135 |
| character_roles | 197 |

### Backup

- ไฟล์: `python-app/backups/npc_backup_20260303.json`
- สร้างก่อนการ cleanup ครั้งใหญ่ (80 fixes)

### การ Cleanup ที่ทำแล้ว

| ประเภท | รายละเอียด |
|--------|-----------|
| ZWS duplicates | ลบ `Tataru\u200b`, `Hydaelyn\u200b` (ซ้ำกับตัวปกติ) |
| Typo duplicates | ลบ `Feo UI` (เก็บ `Feo Ul`), `EmetSelch` (ซ้ำ `Emet-Selch`), `KaiShirr` |
| NPC↔main ซ้ำ | ลบ 8 npcs ที่ซ้ำกับ main_characters |
| word_fixes อันตราย | ลบ 12 รายการ: `1→i`, `0→o`, `2→?`, `$→s`, `\|→i`, `'ll→will`, `MI→I'll`, `Im→I'm`, `50→so`, `95→9S`, `III→I will`, `Tia→Tia` |
| Casing | Normalize gender/relationship/role 50 entries |
| Lore typos | "City of Gold" (ณ→น), "Thirth Promise"→"Third Promise" |
| lastName | Cloud: "Striff"→"Strife" |
| word_fixes | "Sphenel"→"Sphene" |

> **สำคัญ:** word_fixes ที่สั้นมาก (1-2 ตัวอักษร) เช่น `1→i` อันตรายมาก
> จะ replace ทุกตำแหน่งในข้อความที่มีตัวเลข/สัญลักษณ์นั้น → ข้อความเพี้ยน

---

## Test Message System — `pyqt_ui/settings_panel.py`

### หลักการ

ปุ่มทดสอบ 3 ปุ่ม (Dialog / Battle / Cutscene) ใน Settings panel ส่งข้อความจำลอง
เข้าระบบแปลจริง กดแต่ละครั้งจะสุ่มข้อความจากชุด 6 ข้อความ (รวม 18 ชุด)

### ชุดข้อความ

| Pool | ChatType | ตัวอย่าง speakers |
|------|----------|-----------------|
| `_TEST_DIALOG` (6) | 61 | Tataru, Alphinaud, Alisaie, Thancred, Y'shtola, G'raha Tia |
| `_TEST_BATTLE` (6) | 68 | Gaius, Zenos, Nidhogg, Emet-Selch, Sephirot, ??? |
| `_TEST_CUTSCENE` (6) | 71 | Hydaelyn, Venat, Meteion, Emet-Selch, Hythlodaeus, Wuk Lamat |

### การทำงาน

```python
def _inject_test_dialog(self):
    speaker, message = random.choice(self._TEST_DIALOG)
    self._inject_test_message("dialogue", speaker, message, 61)
```

- `_inject_test_message()` สร้าง dict เหมือน Dalamud text hook → ส่งเข้า `immediate_handler`
- ข้อความผ่านระบบแปลจริง (Gemini API) → แสดงผลบน TUI

---

## Wide-Context Translation System (สถานะ: Implemented — v1.7.8)

### สถาปัตยกรรม

ระบบ inject บทสนทนาล่าสุด (translated Thai) เข้า Gemini prompt เพื่อรักษาความสม่ำเสมอ:
- **สรรพนาม**: ตัวละครเดียวกันใช้คำเดียวกัน (ข้า ไม่สลับเป็น ชั้น)
- **คำเรียก**: honorifics คงที่ (ท่านหญิง ไม่เปลี่ยนเป็น คุณผู้หญิง)
- **ชื่อ**: ไม่ transliterate สลับ (Pelupelu ไม่เป็น เปรูเปรุ)
- **ประโยคสั้น**: ตอบสนอง/ตกใจ ได้ context จากประโยคก่อนหน้า

#### Data Flow

```
ConversationLogger.log_message()        ← บันทึกทุกข้อความ (always-on)
ConversationLogger.update_translation() ← เพิ่มคำแปล
          ↓
ConversationLogger.get_recent_context() ← cutscene=8, dialogue=6, battle=3
          ↓
dalamud_immediate_handler.py  ← เรียก get_recent_context() ก่อน translate()
          ↓
translator_gemini.py translate(conversation_context="...")  ← inject เข้า prompt
```

#### Token Budget (หลังเพิ่ม Context)

| ส่วนประกอบ | Before | After |
|------------|--------|-------|
| System prompt | ~450 | ~490 (+rule 10) |
| **Recent dialogue** | **0** | **~150-400** |
| Character context + names + lore | ~180 | ~180 |
| Dialogue | ~200 | ~200 |
| **รวม** | **~830** | **~1,020-1,270** |

### `get_recent_context()` — `conversation_logger.py`

- ดึงจาก `_current_conv['messages']` (in-memory, conversation เดียวกัน)
- ใช้ `translated` field เท่านั้น (ไม่ส่ง EN ไป เพราะ Gemini อาจ copy)
- Skip messages ที่ไม่มี translated หรือ `chattype_group == 'other'`
- ตัดข้อความแต่ละ entry ไว้ไม่เกิน **80 chars** (เพิ่มจาก 60 — v1.7.8)
- `exclude_last=True` เพื่อไม่ซ้ำกับ "Text to translate"
- ลบ speaker prefix ซ้ำ (translated อาจมี "Speaker: ..." อยู่แล้ว)

### Rule 10 — System Prompt v2

```
10. **Context Consistency**: When [Recent dialogue] is provided, maintain the SAME
    pronouns (สรรพนาม), honorifics, and name formats used in previous lines.
```

### Conversation Logger — `conversation_logger.py`

ระบบ always-on in-memory context + optional disk logging (debug mode)

#### Two-Mode Architecture (v1.7.8)

| Mode | `disk_logging` | ทำอะไร |
|------|---------------|--------|
| **Memory-only** (default) | `False` | track context ใน RAM, ไม่เขียน disk |
| **Full** (debug) | `True` | track + save JSON ลง disk |

- **Context ทำงานเสมอ** — ไม่ขึ้นกับ Settings toggle
- **Settings toggle "Conversation Log"**: ควบคุม `disk_logging` เท่านั้น
- `set_disk_logging(bool)` — toggle disk I/O กลางคัน
- **Output**: JSON ที่ `AppData/Local/MBB_Dalamud/logs/conversations/conv_YYYYMMDD_HHMMSS.json`
- **บันทึกเฉพาะ**: ChatType {61, 68, 71, 0x0045, 0x0046} — กรอง player chat ออก

#### Conversation Boundary Heuristics

| เงื่อนไข | ค่า | ผล |
|---------|-----|-----|
| Time gap | >45s | เริ่ม conversation ใหม่ |
| ChatType group change | ~~dialogue↔cutscene~~ | ~~ลบออกแล้ว~~ — context ไหลข้ามได้ |
| Speaker limit | >**8** คน (เพิ่มจาก 5 — v1.7.8) | เริ่ม conversation ใหม่ |
| System event (zone_change) | ทุกครั้ง | ตัด in-memory context ทันที |

> **`CONVERSATION_MAX_SPEAKERS = 8`** constant ใน `conversation_logger.py`

#### ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | บทบาท |
|------|-------|
| `python-app/conversation_logger.py` | Core module — always-on context, optional disk log |
| `python-app/dalamud_immediate_handler.py` | Integration — context sizes, route system events |
| `python-app/MBB.py` | Lifecycle — always init logger, disk_logging ตาม setting |
| `pyqt_ui/settings_panel.py` | Toggle UI — controls disk_logging only |

#### MBB.py Lifecycle (v1.7.8)

```python
# Init: สร้าง logger เสมอ (memory-only default)
self.conversation_logger = ConversationLogger(disk_logging=False)

# Start: อัพเดท disk_logging → start session
self.conversation_logger.set_disk_logging(conv_log_enabled)
self.conversation_logger.start_session()

# Stop: end session (save JSON เฉพาะ disk_logging=True)
self.conversation_logger.end_session()
# ไม่ set None — reuse logger ได้ทันทีใน next session
```

### Scene Change Detection (Zone Change)

#### ฝั่ง C# — `DalamudMBBBridge.cs`

- **IClientState** service (line 37) — Dalamud service สำหรับ TerritoryChanged
- **OnTerritoryChanged** handler — สร้าง `TextHookData{Type="system", Message="zone_change:{id}"}` → `messageQueue`
- Dispose cleanup: `ClientState.TerritoryChanged -= OnTerritoryChanged`

#### ฝั่ง Python — `dalamud_immediate_handler.py`

- ตรวจ `Type=="system"` ก่อน filtering → เรียก `conversation_logger.log_system_event()` → return ทันที
- ไม่ส่งต่อไปแปล

#### Manual Zone Change — ปุ่มบน MBB UI

- ปุ่ม **"Zone Change"** ใน Game info row (`control_panel.py`)
- คลิก → `MBB.manual_zone_change()` → `log_system_event('zone_change', 'manual')`
- แสดง feedback **"Zone changed — context reset"** บน status_info 2.5 วินาที
- QSS: `zone_btn` ใน `styles.py` (ปกติ + glass mode)

### ผลการทดสอบ (ก่อน maintenance)

- Auto zone change (TerritoryChanged): ทำงานถูกต้อง — Territory ID ถูกบันทึก
- Manual zone change: ทำงานถูกต้อง — details="manual"
- Translation pairing: 100% สำหรับ ChatType 61, 71
- Player chat กรองออกแล้ว (ChatType 27, 3 ไม่เข้า log)

---

## Font System — Dual Storage Architecture

### หลักการ

TUI และ Logs UI ใช้ font แยกกัน จัดเก็บคนละที่ใน settings:

| UI | Settings Key | Default Font | Default Size |
|----|-------------|-------------|-------------|
| TUI (`translated_ui.py`) | `settings["font"]` / `settings["font_size"]` | Anuphan | 24 |
| Logs (`translated_logs.py`) | `settings["logs_ui"]["font_family"]` / `settings["logs_ui"]["font_size"]` | Anuphan | 16 |

### FontPanel Target System — `pyqt_ui/font_panel.py`

FontPanel ส่ง target key `"tui"` / `"logs"` / `"both"` ผ่าน `_on_apply()`:

```python
# MBB.py apply_font_with_target()
if target_mode in ("tui", "both"):
    self.settings.set("font", font_name, save_immediately=False)
    self.settings.set("font_size", font_size)

if target_mode in ("logs", "both"):
    # ถ้า logs instance ไม่มี → save ตรงนี้
    if not translated_logs_instance:
        self.settings.set_logs_settings(font_family=font_name, font_size=font_size)
```

> **สำคัญ:** ห้ามบันทึก top-level `font`/`font_size` เมื่อ target="logs" — จะทับ TUI font

### Target Switch — `_set_target(key)`

เมื่อคลิกปุ่ม TUI / TUI Log / Both จะ:
1. โหลด font+size ของ target นั้นจาก settings (`_get_font_for_target()`)
2. อัพเดต size display + เลือก font ใน list (`blockSignals` ป้องกัน double update)
3. อัพเดต preview ทันที

### Bidirectional Sync (Font Size)

```
FontPanel APPLY → MBB.apply_font_with_target() → Logs UI update_font_settings()
Logs UI +/- buttons → _sync_font_to_settings() → persist + FontPanel update (if open & target=logs)
```

- `_sync_font_to_settings()`: persist ลง `logs_ui` + sync FontPanel size/preview ถ้าเปิดอยู่
- `reload_target()`: เรียกเมื่อ FontPanel ถูก re-show (เช่น เปิดจาก Logs UI ขณะ panel มีอยู่แล้ว)

### การเปิด FontPanel จาก Logs UI — `open_font_manager()`

> **สำคัญ:** ใช้ `_ensure_font_panel()` + `reload_target()` — **ห้ามใช้ `_toggle_font()`**
> เพราะถ้า panel เปิดอยู่แล้ว `_toggle_font()` จะ **ปิด** แทนที่จะสลับ target

```python
# ถูก: ensure + reload + raise
sp._ensure_font_panel()
fp.reload_target()
fp.raise_()

# ผิด: toggle จะปิด panel ถ้าเปิดอยู่
sp._toggle_font()  # ← ห้ามใช้จาก Logs UI
```

### Settings Backend — `settings.py`

- `get_logs_settings()` → default `{"width": 480, "height": 320, "font_size": 16, "font_family": "Anuphan", "visible": True}`
- `set_logs_settings(width, height, font_size, font_family, visible, x, y, transparency_mode, logs_reverse_mode)`
- **สำคัญ:** `self.settings` ใน Settings class คือ dict — ใช้ `self.settings["key"] = value` (ไม่ใช่ `self.settings.set()`)

---

## Translated Logs UI — `translated_logs.py`

### Module-Level Constants

```python
DEFAULT_LOG_WIDTH = 300
DEFAULT_LOG_HEIGHT = 800
FALLBACK_LOG_GEOMETRY = "240x600+1480+100"
ALPHA_MAP = {"A": 0.95, "B": 0.70, "C": 0.50, "D": 1.00}
TRANSPARENCY_MODES = list(ALPHA_MAP.keys())
MAX_CACHE_SIZE = 200
```

### Header Layout — Tkinter Pack Order

> **กฎ:** RIGHT-packed widgets ต้อง pack ก่อน LEFT-packed widgets
> มิฉะนั้น LEFT widget กิน horizontal space ทั้งหมด → RIGHT widget ถูกตัดหาย

**ลำดับ pack ที่ถูกต้อง:**
```python
# 1. controls_frame (RIGHT) — ต้อง pack ก่อน
controls_frame.pack(side="right", ...)
# 2. title_label (LEFT) — pack ทีหลัง
title_label.pack(side="left", ...)
```

### Header Title

- ข้อความ: `"💬 บทสนทนา"` (10pt bold) — ย่อจาก `"💬 ประวัติบทสนทนา"` เพื่อไม่แหว่งที่ขนาดเริ่มต้น
- Status label: **ลบออกแล้ว** — `_update_status()` และ `_show_replacement_indicator()` เป็น no-op

### Bottom Controls Hover System

ปุ่มด้านล่าง (lock / transparency / reverse / smart / font) ซ่อนตามปกติ แสดงเมื่อเมาส์อยู่ใน window

#### หลักการ

- **Show/Hide**: `place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=30)` / `place_forget()`
  - ห้ามใช้ `configure(height=0)` — Tkinter Frame ไม่ clip children บน Windows
  - `place()` overlay บน chat area ได้ เพราะ `_bottom_frame` มี z-order สูงกว่า
- **Hover detection**: polling `_is_mouse_over_window()` ทุก 120ms (ไม่ใช้ `<Enter>/<Leave>` — ไม่ reliable บน Windows)
- **`winfo_containing(px, py)`**: คืน widget ณ screen coordinates → `.winfo_toplevel() == self.root` ตรวจว่าอยู่ใน window

#### CRITICAL — Z-Order Creation Rule

> **`setup_bottom_controls()` ต้องเรียกหลัง `setup_chat_area()` เสมอ**
> Tkinter widget ที่สร้างทีหลัง = z-order สูงกว่า
> ถ้าสร้าง bottom_frame ก่อน chat_frame → place() วาง bottom_frame ไว้ใต้ chat_frame → มองไม่เห็น

```python
# ลำดับที่ถูกต้องใน setup_ui():
self.setup_header()
self.setup_chat_area()        # chat_frame สร้างก่อน (z-order ต่ำกว่า)
self.setup_bottom_controls()  # bottom_frame สร้างทีหลัง (z-order สูงกว่า → place() มองเห็น)
self.setup_resize_handle()
```

#### Implementation

```python
def _is_mouse_over_window(self) -> bool:
    px = self.root.winfo_pointerx()
    py = self.root.winfo_pointery()
    widget_at = self.root.winfo_containing(px, py)
    if not widget_at:
        return False
    return widget_at.winfo_toplevel() == self.root

def _start_hover_check(self):
    hovering = self._is_mouse_over_window()
    if hovering != self._controls_visible:
        self._controls_visible = hovering
        if hovering:
            self._bottom_frame.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=30)
        else:
            self._bottom_frame.place_forget()
    self.root.after(120, self._start_hover_check)
```

- `_controls_visible`: state flag ป้องกัน place/place_forget ซ้ำทุก tick
- เริ่มผ่าน `root.after(200, self._start_hover_check)` ใน `setup_bindings()`

### Transparency

- ใช้ `root.attributes("-alpha", value)` — ส่งผลต่อทั้ง window รวม text และ bubbles
- `toggle_transparency()` วน cycle A→B→C→D→A ตาม `ALPHA_MAP`
- `show_window()` restore alpha ตาม `current_mode` ทุกครั้งที่แสดง

> **หมายเหตุ:** เคยลองแนวทาง two-window (bg_layer + transparentcolor) เพื่อให้ transparency กระทบแค่พื้นหลัง แต่ซับซ้อนโดยไม่จำเป็น — `transparentcolor` ทำให้ chat area click-through ทั้งหมด ทำให้ scroll พัง, ยกเลิกแนวทางนี้แล้ว

### Cache Eviction

```python
if len(self.message_cache) > MAX_CACHE_SIZE:
    sorted_keys = sorted(self.message_cache, key=lambda k: self.message_cache[k]["timestamp"])
    for k in sorted_keys[:len(self.message_cache) - MAX_CACHE_SIZE]:
        del self.message_cache[k]
```

### Font Button → FontPanel

- `open_font_manager()` ใช้ `_ensure_font_panel()` + `reload_target()` (ไม่ใช่ `_toggle_font()`)
- **ต้องมี** `main_app` reference — ส่งผ่าน `Translated_Logs(..., main_app=self)` ใน `MBB.py`
- **Attribute name:** `settings_ui` (ไม่ใช่ `settings_panel`)
- FontPanel วางตำแหน่งใกล้ Logs UI ผ่าน `_position_font_panel_near_logs()`

### Font Size +/- Buttons → `_sync_font_to_settings()`

- กด +/- บน Logs UI → persist ลง `settings["logs_ui"]` ทันที
- ถ้า FontPanel เปิดอยู่ + target="logs" → อัพเดต size display + preview ให้ตรงกัน

### Lock Mode Logging

- `do_move()`: ไม่มี `print()` ระหว่าง drag — ลด console spam
- `stop_move()`: บันทึก position ครั้งเดียว + `logging.info`
- Resize save: `logging.debug` (ไม่ใช่ `print`)
- Exception handlers: `except (AttributeError, tk.TclError):` (ไม่ใช่ bare `except:`)

---

## MBB.py — Attribute Naming Reference

### ชื่อ Attribute ที่ถูกต้อง

| Attribute | ชี้ไปที่ | ⚠️ ชื่อที่ผิด (ห้ามใช้) |
|-----------|---------|----------------------|
| `self.translated_logs_instance` | `Translated_Logs` object | ~~`self.translated_logs`~~ |
| `self.settings_ui` | PyQt6 Settings panel | ~~`self.settings_panel`~~ |
| `self.info_label` | `control_panel.lbl_status_info` | — |
| `self.conversation_logger` | `ConversationLogger` (always-on) | — |

### Initial Window Position

```python
screen = QApplication.primaryScreen()
sg = screen.availableGeometry()
pos_x = int(sg.width() * 0.10)       # 10% จากซ้าย
pos_y = sg.top() + (sg.height() - win_h) // 2  # กึ่งกลางแนวตั้ง
self.qt_main_window.move(pos_x, pos_y)
```

---

## Splash Screen — `MBB.py`

### สถาปัตยกรรม

Splash screen แสดงตอนเริ่มโปรแกรม ใช้ Tkinter Toplevel + PIL rendering

### ขนาดและรูปแบบ

| Property | ค่า |
|----------|-----|
| ขนาด | 40% ของความกว้างหน้าจอ, รักษา aspect ratio |
| มุมโค้ง | PIL rounded mask + `transparentcolor` (ไม่มีขอบ) |
| Corner radius | `max(12, target_w // 40)` |
| Image | `assets/splash.png` (fallback `assets/MBBvisual.png`) |

### แถบล่าง (Bottom Bar)

```
┌──────────────────────────────────────────────────┐
│                   (ภาพ splash)                    │
│                                                  │
│▓▓ ☐ ไม่แสดงอีกในวันนี้    MBB v1.7.8 ▓▓│ ← แถบดำ 80%
└──────────────────────────────────────────────────┘
```

- **แถบดำ**: PIL `alpha_composite` สีดำ `(0,0,0,204)` ≈ 80% opacity
- **Version text** (ขวา): `Magicite Babel Bridge v{__version__}` — อ่านจาก `version.py` อัตโนมัติ
- **Checkbox** (ซ้าย): Tkinter `Checkbutton` วางบน Canvas ด้วย `create_window()`
- **Font**: Anuphan, size = `max(12, target_w // 50)`

### ระบบควบคุมการแสดง (2 ชั้น)

| ชั้น | Setting Key | ผล |
|------|------------|-----|
| **Master toggle** | `enable_starting_key_visual` (Settings panel) | `False` → ไม่แสดงเลย |
| **Daily skip** | `splash_skip_date` (Checkbox บน splash) | ตรงกับวันนี้ → ข้าม |

> **สำคัญ:** ทั้งสอง setting อ่าน/เขียน `settings.json` โดยตรงด้วย `json.load()`/`json.dump()`
> เพราะ splash สร้างที่ line ~549 ก่อน `self.settings = Settings()` ที่ line ~698

### Timing

| Phase | Duration | วิธี |
|-------|----------|------|
| Fade-in | 20 steps × 20ms = 400ms | blocking loop ใน `show_splash()` |
| แสดงค้าง | อย่างน้อย 5 วินาที | `_splash_start_time` + `_complete_startup()` เช็คเวลา |
| Fade-out | 20 steps × 25ms = 500ms | non-blocking `_fade_splash_step()` ด้วย QTimer |

**ประวิงเวลา:** ถ้าระบบพร้อมเร็วกว่า 5 วินาที `_complete_startup()` จะ reschedule ตัวเอง
ด้วย `QTimer.singleShot(remaining_ms)` จนครบ 5 วิแล้วค่อย fade-out

### Call Flow

```
__init__()
  └→ show_splash()           ← สร้าง + fade-in (blocking)
  └→ _splash_start_time      ← บันทึกเวลาเริ่ม
  └→ ... (init ระบบอื่นๆ) ...
  └→ QTimer.singleShot(2000, _complete_startup)
       └→ เช็คเวลา: ครบ 5 วิ?
            ├→ ยังไม่ครบ → QTimer.singleShot(remaining, _complete_startup)
            └→ ครบแล้ว → _fade_splash_step() → _finish_startup_tasks()
```

---

## Solution File Fix — `MBB_Dalamud.sln`

### การเปลี่ยนแปลง

หลังย้ายโฟลเดอร์ `dalamud-plugin/DalamudMBBBridge/` → `DalamudMBBBridge/` ต้องอัพเดต `.sln`:

| ก่อน | หลัง |
|------|------|
| `dalamud-plugin\DalamudMBBBridge\DalamudMBBBridge.csproj` | `DalamudMBBBridge\DalamudMBBBridge.csproj` |
| Solution folder `dalamud-plugin` + NestedProjects mapping | ลบออก (ไม่ต้องการแล้ว) |

> **อาการ:** VS Code แสดง `error MSB3202: The project file ... was not found`
> **สาเหตุ:** `.sln` ยังอ้างอิง path เก่าหลังย้ายโฟลเดอร์

---

## Test Message System — `pyqt_ui/settings_panel.py`

### ชุดข้อความ (อัพเดต มีนาคม 2026)

| Pool | ChatType | จำนวน | Speakers |
|------|----------|-------|----------|
| `_TEST_DIALOG` | 61 | 10 | Tataru, Alphinaud, Alisaie, Thancred, Y'shtola, G'raha Tia, Estinien, Urianger, Krile, Wuk Lamat |
| `_TEST_BATTLE` | 68 | 6 | Zenos, Nidhogg, Emet-Selch, Sephirot, Thordan VII, ??? |
| `_TEST_CUTSCENE` | 71 | 6 | ไม่มี speaker (narration) — `speaker=""` |

> **Cutscene = narration เสมอ** — ไม่มีชื่อผู้พูด
> **TODO:** เมื่อมีประวัติ conversation log จริง ให้คัดเลือกข้อความที่แปลได้ดีมาแทนที่

---

**Developed by:** iarcanar
**Framework:** Dalamud Plugin + Python + Gemini AI
**License:** MIT
