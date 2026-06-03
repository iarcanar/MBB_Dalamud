# MBB Dalamud — Project Reference

**Version:** 1.8.18 · **Build:** 04032026-01
**Framework:** Dalamud Plugin (C#) + Python (PyQt6 + Tkinter hybrid) + Gemini API
**Developed by:** iarcanar · **License:** MIT

> Canonical project reference. **Compacted 2026-05-19** — old per-version changelogs live in git (`git log`); this doc holds current architecture, rules, and lessons that inform future development.

---

## 🛑 Dev Protocol — read this FIRST before any code edit

**Required reading before editing code in this project:** [`.claude/skills/karpathy-guidelines/SKILL.md`](.claude/skills/karpathy-guidelines/SKILL.md)

The skill is a 4-section behavioral checklist (Think before coding · Simplicity first · Surgical changes · Goal-driven execution) derived from Andrej Karpathy's observations on LLM coding pitfalls. Read it once at the start of every coding session — keep its principles active throughout. Trivial fixes (typos, 1-line edits) may skip; non-trivial changes (≥ 10 LOC, new logic, refactors) must follow it.

---

## Documentation Convention

**CLAUDE.md (this file) is the canonical source.** All knowledge edits flow here first. Other docs derive from this one.

**Two surfaces, one source:**

| Surface | Location | Use when |
|---------|----------|----------|
| **CLAUDE.md** (canonical) | `c:\MBB_Dalamud\CLAUDE.md` | Daily dev · bug fixes · AI agent context · `grep`/`Ctrl-F` lookups · single source of truth |
| **HTML manual** (derived view) | `docs/manual/` (5 pages) | Onboarding new contributors · visual reference for layout math / data flow / cloud sync (SVG diagrams + UI screenshots) · understanding new subsystems faster than reading prose · sharing the project externally |

**Why both, not just one** (validated by QA review 2026-05-19):
- HTML is **2.6× more verbose** than MD for the same content (~4× token cost for AI). Bad for daily grep work and AI context.
- HTML adds **genuine value markdown cannot deliver**: inline SVG diagrams (data flow, name preservation pipeline, dual font storage), 12-palette color swatches, Diagram↔Real-UI toggle on Main Window, real screenshots for Mini UI / TUI / NPC Manager / Settings / Splash / DissolveOverlay / Logs.
- So: MD for **doing**, HTML for **understanding the shape of something new**.

**Update rules:**
1. Edit CLAUDE.md first — always. Treat it as the working reference.
2. Re-sync HTML when:
   - A subsystem grows large enough to benefit from a diagram
   - You're about to share the project with an external collaborator
   - On each release (bump the banner date + version)
3. HTML pages carry a `Snapshot derived from CLAUDE.md · last synced YYYY-MM-DD · vX.Y.Z` banner — keep it honest. Update the date in all 5 files when you re-sync (find-replace).
4. **HTML drift risk:** if banner date lags 2+ versions, treat HTML as suspect; trust this file.

**HTML file inventory** (`docs/manual/`):
- `index.html` — overview, project structure, data flow SVG, ChatType routing, build pipeline
- `ui.html` — Main Window layout math, Mini UI, TUI dialog/choice, DissolveOverlay 3 dispatcher rules, Translated Logs, Glass Mode
- `npc-translation.html` — NPC Manager + Polaroid patterns, Cloud Sync flow, Translation engine, 3-layer name preservation, Wide-context, NPC database
- `styling.html` — Theme system (12 palettes), Font dual storage, Settings, Splash, Updater
- `reference.html` — Gemini models, test messages, Hard-Won Rules (6 PyQt6 gotchas + Win32 don'ts), plugin manifest, roadmap
- Shared: `assets/manual.css` + `assets/manual.js` (sidebar nav, scroll-spy TOC, copy-code buttons, diagram toggles)

**Landing page** (`docs/index.html`) is a separate public-facing artifact (user-friendly hero, screenshots, install guide). Don't conflate it with the manual — the manual is for developers/AI; the landing page is for users.

---

## Project Goal

Transform MBB Dalamud Bridge into a distributable package via Dalamud Custom Plugin Repository.

**Phases:**
- [x] Phase 1 — code cleanup (OCR-era dead code purged 2026-04-25; theme system v2; PyQt6 migration)
- [ ] Phase 2 — custom repository setup (`pluginmaster.json`)
- [ ] Phase 3 — PyInstaller packaging + 1-click install

## Project Structure

```
C:\MBB_Dalamud/
├── python-app/           # Python translation app
│   ├── MBB.py            # Entry point
│   ├── translated_ui.py  # TUI (Tkinter, dialog/choice mode)
│   ├── translator_gemini.py
│   ├── npc.json          # Character database
│   ├── pyqt_ui/          # PyQt6 panels + overlays
│   ├── fonts/            # Anuphan, FC Minimal, Caveat, Pacifico, Google Sans
│   └── assets/           # 60+ icons (white-themed, auto-invert on light bg)
├── DalamudMBBBridge/     # C# Dalamud plugin
├── docs/                 # Landing page (index.html) + screenshots
├── scripts/              # build_npc_release.py + automation
└── updater/              # Standalone updater (Tkinter)
```

---

# Architecture

## Data Flow

```
FFXIV game text
   ↓
Dalamud Plugin (C#)         ← OnChatMessage / OnTerritoryChanged
   ↓
Named Pipe (TextHookData)
   ↓
dalamud_immediate_handler.py
   ↓
text_corrector + translator_gemini
   ↓
TUI (Tkinter) or DissolveOverlay (PyQt6)  ← per chat_type
   ↓
TranslatedLogs (PyQt6) — history
```

## ChatType Routing

| ChatType | Mode | Renderer |
|----------|------|----------|
| 61 | Dialog | Tkinter TUI |
| 68 | Battle | PyQt6 DissolveOverlay |
| 71 | Cutscene | PyQt6 DissolveOverlay |
| 70 (0x0046) | Choice | PyQt6 ChoiceOverlay |
| 27, 3 (player chat) | Filtered out | — |

**Choice routing detail:** real game choices arrive as `Type="choice"` + `ChatType=70` with pipe-separated body (`"What will you say? | Choice1 | Choice2"`). The handler ([dalamud_immediate_handler.py:363-370](python-app/dalamud_immediate_handler.py#L363-L370)) detects `Type=="choice"` and calls `translate_choice()` which converts pipes → newlines + bullet prefixes BEFORE Gemini, preserving format through translation. Output reaches `translated_ui.update_text` with `chat_type=70`; dispatcher routes to `_route_to_choice_overlay`. **Tk Canvas `_handle_choice_text` is kept as fallback** if `self.choice_overlay is None` (creation failed in MBB.py).

---

# Main Window (PyQt6) — `pyqt_ui/main_window.py`

## Layout Math

| Constant | Value | Meaning |
|----------|-------|---------|
| `BG_W` | 296 px | Main display area width |
| `BG_H` | 265 px | Main display area height |
| `MARGIN_BASE` | 12 px | Right/bottom margin (shadow allowance) |

Window size is **dynamic** — calculated from logo overflow:
```python
logo_w = int(BG_W * 0.6)              # 177 px
logo_overflow_left = max(0, logo_w - BG_W // 2)
logo_overflow_top  = logo_h // 2

margin_left   = logo_overflow_left + 4
margin_top    = logo_overflow_top  + 4
margin_right  = MARGIN_BASE  # shadow
margin_bottom = MARGIN_BASE  # shadow
win_w = margin_left + BG_W + margin_right
win_h = margin_top  + BG_H + margin_bottom
```

**Logo placement intent:** logo's right edge = center of bg panel; logo overflows top by half its height.
`logo_x = bg_center_x - logo_w`, `logo_y = margin_top - logo_h // 2` (must be positive).

Logo is a `QLabel` overlay (not in layout) with `WA_TransparentForMouseEvents` + `raise_()`.

## Header Bar

Logo covers left half of header → push content right with:
```python
header_margin_left = BG_W // 2 - 14   # 134 px
```
Version label: 7pt (`FONT_PRIMARY`), QSS `padding-top: 4px`.

## ControlPanel + BottomBar Layout

```
┌─────────────────────────┐
│ HeaderBar (44px)        │
├─────────────────────────┤
│ ● Ready        [Stop]   │  ← status dot + btn_start_stop
│ Game          FFXIV     │  ← game info row (11pt)
│ MODEL: GEMINI [READY]   │  ← lbl_status_info (8pt mono, dim)
│                         │  ← addStretch(1) ≈ 31px gap
├─────────────────────────┤
│ TUI  LOG  MINI          │
│ NPC Manager  🎨 ⚙       │
└─────────────────────────┘  ← BottomBar 100px, 16px bottom padding
```

**Sum:** 44 + 1 + 88 + 31 + 1 + 100 = 265 = `BG_H`. Adjust `BG_H` if components change.

**Status info widget:** `QLabel#status_info` in `control_panel.py` (was in BottomBar — moved closer to Game info).
`MBB.py` aliases: `self.info_label = self.control_panel.lbl_status_info`. Signal path `signals.info_update → _on_info_signal() → set_status_info()`.

## Initial Window Position

```python
pos_x = int(sg.width() * 0.10)                  # 10% from left
pos_y = sg.top() + (sg.height() - win_h) // 2   # vertically centered
```

## Glass Mode — `pyqt_ui/styles.py:get_glass_overrides()`

Toggle via ● button in header → `main_window._on_toggle_glass()` rebuilds QSS:
- All buttons: transparent bg, no border, faint text (~20% opacity)
- Hover: brighter (~50%)
- Toggled: ~35%
- Labels: very faint (~14-20%)
- **Logo always visible** (QPixmap overlay, not in QSS)

Shadow: blur 24→16, alpha 160→60 (when glass on).

---

# Mini UI — `mini_ui.py`

Tkinter Toplevel, 50×176, frameless (`overrideredirect`), always-on-top.
Snapped to left edge of screen, vertically aligned with main window.

**Asymmetric rounded corners (Win32):** `CreateRoundRectRgn` with ellipse=10 (~5px) → right side rounded, left side flush with screen edge.

> Don't increase corner radius — region clipping cuts highlight border at top-right/bottom-right.

**Highlight border:** flashes white 1.2s on show (`highlightthickness=2 #e0e0e0` → `1 #2a2a2a`).

**Theme change:** destroy + rebuild (Tkinter color baking). Snapshot/restore position around rebuild.

**Light theme:** white-line icons auto-invert via PIL `_invert_rgb_keep_alpha()` + luminance check.

---

# TUI — Dialog & Choice Mode (Tkinter, `translated_ui.py`)

## Text Style System v4

**Speaker name** — normal weight (no bold) in every mode for name-detection compat. Strip `**`, `*`, ZWS chars before `name in self.names` check (3 sites: `_handle_normal_text_fast`, `_handle_normal_text`, `display_speaker_name`).

| Mode | Speaker color | Body color |
|------|---------------|------------|
| Dialogue — known | `#38bdf8` cyan | white |
| Dialogue — unknown (`???`) | `#a855f7` purple | white |
| Battle | orange (same as body) | `#FF6B00` |
| Cutscene | yellow (same as body) | `#FFD700` |

**Segments inside dialogue:**
| Segment | Style |
|---------|-------|
| `**highlight**` | `#FFB366` light orange, bold |
| `*italic*` | FC Minimal Medium, italic |
| Character name (detected at render) | cyan thin / mode-color bold |

**Name detection pipeline (v4):**
```
text + names list
   ↓
RichTextFormatter.parse_rich_text_with_names()
   ↓
segments: [{text, font_style: 'normal'|'bold'|'italic'|'name'}]
   ↓
create_rich_text_with_outlines()
```

`highlight_special_names()` is a **no-op** (legacy `『』` brackets removed). `_needs_rich_text()` checks for `*` markers OR names.
**Call sites of `_needs_rich_text` (4):** fast-no-speaker (~3258), post-typewriter (~4323), show-full-text (~4477), font-change-reapply (~4998).

## Lock Mode Shadow System

Two engines via `self._use_pil_shadow` flag:
- `False` (active): **Canvas Multi-Ring** — stable
- `True` (dormant): PIL Gaussian Blur — doesn't work with `transparentcolor` (1-bit color-key)

**Multi-Ring in lock mode 1 (transparent bg) — 3 layers, 36 items:**
| Layer | Offset | Positions | Color |
|-------|--------|-----------|-------|
| Outer | ~3px | 16 (circle) | `#111111` |
| Middle | ~2px | 12 (circle) | `#080808` |
| Inner | ~1px | 8 (square) | `#000000` |

**Normal mode (with bg) — 1 layer, 8 items:** outline `#000000` ~1px offset.

**Shadow text=""** rule — shadows must sync with typewriter. Shadow creation sites pass empty string when typewriter is active; only speaker-name shadows pass actual text.

**`canvas.itemconfig(outline, ...)` safety:** `outline_container` may hold text + image items. Always guard:
```python
if canvas.type(outline) == "text":
    canvas.itemconfig(outline, text=...)
```

## Auto-Show Opacity

**Rule:** `show_tui_on_new_translation()` MUST restore opacity unconditionally (not gated by `is_window_hidden`). Without this, mid-fade arrivals leave window stuck at low alpha.

```python
def show_tui_on_new_translation(self):
    if self.state.is_window_hidden:
        self.root.deiconify()
        self.state.is_window_hidden = False
    self.restore_user_transparency()   # always, every call
```

**Setting gate** lives in `MBB.py:_trigger_tui_auto_show()` ONLY. Don't add setting check inside `show_tui_on_new_translation()` — breaks auto-show.

## Fade-Race Defense (3 layers)

| Layer | Where | What |
|-------|-------|------|
| 1. Entry | `update_text` | Cancel `fade_timer_id` + `window_hide_timer_id`, reset `is_fading`, bump `last_activity_time` |
| 2. Defer | `fade_out_text` at α=0 | 80ms `after()` before destructive cleanup |
| 3. Recheck | `_do_fade_destructive_cleanup` | Re-check `is_fading` + activity time before wiping; abort if interrupted |

User prefs (e.g. `auto_hide_after_fade`) untouched — only runtime flags reset.

## Resize System

Methods: `start_resize()` → `on_resize()` → `stop_resize()`. Bindings live ONLY in `setup_bindings()`.

**Hard rules:**
- `geometry()` MUST include position (`f"{w}x{h}+{x}+{y}"`) — `resize_anchor_x/y` saved at `start_resize()`.
- **NO `apply_rounded_corners_to_ui()` during drag** (Win32 `SetWindowRgn` + `update_idletasks()` = jank). Re-apply in `stop_resize()` after 150ms `after()`.
- **NO duplicate bindings** — `_create_resize_handle()` does NOT re-bind.
- 16ms throttle on `self.root.geometry()` calls (~60 FPS).
- `bind_all <ButtonRelease-1>` for global capture (so release fires even if handle is clipped by region).

**Win32 `WM_NCLBUTTONDOWN` hand-off — DO NOT USE** (causes `PyEval_RestoreThread` GIL fatal inside Tk callbacks; SendMessageW blocks main thread inside modal resize loop).

**Layout restore after resize:** `_restore_layout_light` (during drag, throttled 150ms) + `_restore_layout_after_resize_universal` (on release).
- `pack_configure` (NOT `pack_forget`)
- `tk.call("raise", widget._w)` (NOT `widget.lift()` — Canvas overrides `lift` as `tag_raise`)
- Re-bind auto-hide hover bindings
- Re-apply rounded corners

**`default_width/_height` sync** in `stop_resize` after save — chat-type switch back to dialog otherwise snaps to old cached size.

## Per-Mode Geometry

`tui_positions[mode]` + `tui_geometries[mode]` — saved per dialog/battle/cutscene.
- Mode switch saves OUTGOING + loads INCOMING.
- Choice mode is transient (not saved).
- `_clamp_to_screen` guards multi-monitor edge cases.

**Default positions (v1.8.14+, no saved state)** — all expressed as % of screen so they scale across resolutions. Chosen 2026-05-20 from drag-prototype testing (`docs/manual/prototype.html#tui-positions`):

| Mode | Default x | Default y |
|------|-----------|-----------|
| Dialog | center (`(sw − w) / 2`) | `round(sh × 0.707)` (70.7% from top) |
| Battle | center | `80` (fixed px, near top — set in `dissolve_overlay.py`) |
| Cutscene | center | `sh − h − max(80, sh/20)` (near bottom) |
| Choice | center | `round(sh × 0.601)` (60.1% from top — **absolute**, was relative-to-dialog before v1.8.14) |

Dialog initial geometry applied in `setup_ui()` (line ~651) so the window doesn't flash at OS-default on first launch; the dialog-mode chat-type handler (line ~1037) applies the same default when chat_type=61 fires with no saved position.

## Mode-Specific UI

| Mode | Hover-revealed buttons |
|------|-----------------------|
| Dialog / Choice | close + lock + color + fadeout + resize handle |
| Battle / Cutscene | close + resize handle only (lock/color/fadeout `pack_forget`) |

WASD auto-hide bypass extends to **both** battle + cutscene (text must stream continuously).

## Step-Lock Transparency (TUI, 6 levels)

`80 / 84 / 88 / 92 / 95 / 100` — `ImprovedColorAlphaPickerWindow.TRANSPARENCY_STEPS` in `tui_color_picker.py`.
- Custom Canvas slider (not `tk.Scale`) with magnetic snap.
- Step pips (1-6) shown only during drag.
- Win32 corner radius **12** (was 20 — handle clipped at edges).
- Legacy top-level `transparency` key purged; TUI alpha controlled SOLELY by in-TUI picker.

## File Split (Phase 1, v1.8.5)

`translated_ui.py` extracted to:
- `tui_shadow.py` — `ShadowConfig` + `BlurShadowEngine`
- `tui_color_picker.py` — `ImprovedColorAlphaPickerWindow`
- `tui_rich_text.py` — `RichTextFormatter`

Re-imported at top of `translated_ui.py` so external API unchanged.

---

# TUI — Battle & Cutscene Mode (PyQt6, `pyqt_ui/dissolve_overlay.py`)

641-line `QWidget`, frameless + translucent (`WA_TranslucentBackground`). Self-contained PyQt6 because Tkinter `transparentcolor` is 1-bit (no alpha gradient).

## Visual

- `paintEvent` draws horizontal `QLinearGradient`: 0% → 5% opaque → 95% opaque → 0% (dissolve left/right edges).
- BG `#14161c` **99% alpha** (`BG_ALPHA = 252`, v1.8.10 — was 230 ≈ 90%, but original FFXIV cinematic text was bleeding through and competing with the translation). Text painted AFTER gradient → fully opaque.
- Vertical centering: `block_top = max(pad_y, (h - block_h) // 2)`.
- Per-mode font color: battle `#FF6B00`, cutscene `#40E0D0` (turquoise — changed from gold v1.8.9).
- Battle speaker name in `#FFFFFF` white (contrast against orange body).
- Cutscene speaker matches body (cinematic single-tone).
- **Font size pulled from `settings["font_size"]`** (v1.8.10) — same source as TUI dialog mode, so battle/cutscene match what user tuned in FontPanel. Speaker label is `body_pt - 8` (kept smaller for visual hierarchy). Refreshed on every `show_for_mode` call via `_apply_user_font_size()`.

## Cutscene Width — forced 90% screen (v1.8.10)

`show_for_mode("cutscene")` **overrides** any saved `tui_geometries["cutscene"]["w"]` (and `DEFAULT_W_CUTSCENE` 1400) with `int(screen_width * CUTSCENE_WIDTH_FRACTION)` (= 0.90), then recenters `x` so the overlay sits 5% from each screen edge.

Rationale: FFXIV cutscene prose can be very long; an 1100-1400px panel truncates and forces hard wraps that ruin the cinematic rhythm. 90% guarantees one-line cinematic prose fits on 1920+ screens.

Saved height + y-position are preserved (user-tunable). Width override means user-resize during a session works visually but resets to 90% on next mode show. Acceptable for cutscene which is event-driven + auto-hides after 10s anyway.

## Auto-Hide

`set_text()` restarts a 10s `QTimer` (`AUTO_HIDE_MS`). On timeout, fade-out via `QPropertyAnimation(windowOpacity)` 500ms → `hide()`.
- New translation during fade → snap opacity back to 1.0.
- Cursor inside overlay → timer restarts (no hide under user's hand).

## Dispatcher Rules — CRITICAL

`translated_ui.update_text` decorator routes by chat_type. 3 must-not-violate rules:

1. **`_route_to_dissolve_overlay` MUST NOT update Tk's `current_chat_type` / `battle_mode_active` / `cutscene_mode_active`.** Those flags drive `_get_current_mode_name()` for Tk save logic; flipping them while Tk has pending move/resize timers corrupts `tui_positions[battle/cutscene]` with dialogue's coords.

2. **Mode change within overlay (battle↔cutscene) MUST call `show_for_mode(mode)`** — `set_mode` alone only changes color, not geometry. `show_for_mode` is idempotent.

3. **`MBB._do_tui_auto_show` MUST early-return when `_dissolve_active = True`** — otherwise auto-show fires on every status update and re-deiconifies just-withdrawn root.

**Defensive:** `_route_to_dissolve_overlay` cancels `move_end_timer` + `resize_end_timer` + `_deferred_render_id` to kill any pending stale saves.

## Pre-flight for DissolveOverlay (v1.8.10) — handler-side dispatch

**Symptom:** First cutscene/battle line flashed the old TUI dialog content for ~1s before the dissolve overlay took over. Subsequent lines worked fine.

**Root cause:** `_trigger_tui_auto_show` fires from the status-update path the moment `_translating_in_progress=True` is set inside the translation thread (line 295 of `dalamud_immediate_handler.py`). At that point, MBB.py doesn't know the chat_type yet, so the `_dissolve_active` guard in `_do_tui_auto_show` hasn't been armed. Auto-show deiconifies TK; the translation takes another ~1s; `_route_to_dissolve_overlay` finally withdraws TK and shows the overlay — but the user already saw the stale dialog flash.

**Fix:** in `dalamud_immediate_handler.py` `process_message`, right before `thread.start()` (after all early-return gates + cache check), if `chat_type ∈ {68, 71}` — pre-flight:

1. Set `translated_ui._dissolve_active = True` synchronously on the bridge thread (atomic Python attribute write — GIL covers it).
2. Schedule `ui.root.withdraw()` on the Tk main thread via `safe_after(0, ...)`. The withdraw callback also sets `_tk_was_visible_before_dissolve` based on actual `root.state()`.
3. Mark `was_pre_flighted = True` in the outer closure so the thread's `finally` block can reset on failure.

**Cleanup (in thread `finally`):**
- If `was_pre_flighted` AND `_translation_displayed=False` (`_show_immediately` was never called), reset `_dissolve_active=False`. Otherwise a translation failure leaves TUI hidden forever — next dialogue's auto-show stays blocked.

**Placement notes:** pre-flight must be AFTER all early returns (cache hit calls `_show_immediately` synchronously; "already translating" defers to the in-flight thread). Pre-flighting before those would leak `_dissolve_active=True` without a thread to clean up.

## First-Show HWND Race — Fix (v1.8.10)

**Symptom:** Battle/cutscene overlay flashed at top-left of screen on the very first show after app startup, then snapped to saved position on second show.

**Root cause:** Qt frameless+translucent + Windows = `setGeometry(x,y,w,h)` queued before `show()` doesn't apply visibly until AFTER the native HWND exists. First `show()` creates HWND at OS-default position (0,0 area) and paints one frame there before the queued geometry catches up.

**Fix (2 parts, both in `dissolve_overlay.py`):**

1. **Force HWND creation at end of `__init__`** via `self.winId()` — creates the platform window without showing it. Must be at the very end of `__init__` after all timers (`_save_timer`, `_hover_timer`, `_auto_hide_timer`) and `_fade_anim` are initialized — otherwise the move/resize events Qt fires immediately after HWND creation access uninitialized attributes.

2. **Defensive `move(x, y)` after `show()` in `show_for_mode`** — even with `winId()`, some Qt versions still defer the pre-show `setGeometry`. The post-show `move()` is a no-op when geometry already applied, harmless otherwise.

**Side effect of `winId()` — spurious save:** HWND creation fires a moveEvent at the OS-default position. moveEvent → `_schedule_save_geometry()` → debounced save → **overwrites the user's saved position** with the OS default (~screen center). Fix with `_save_armed = False` flag:

- Set in `__init__` initially `False`
- `_schedule_save_geometry()` early-returns if `not self._save_armed`
- Armed at end of `show_for_mode` after `show()` and the defensive `move()`
- From there on, real user move/resize events save normally

Cancel any pending timer at arm time (`self._save_timer.stop()` if `isActive`) as a defensive flush — `_save_armed` was False the whole prior time so there shouldn't be anything queued, but cheap insurance.

## Diagnostic Logs

Keep `[DISSOLVE-DBG]` trace logs at every dispatch + save site. Cheap to maintain, invaluable for mode-switch bugs.
```
route_to_overlay: mode=X chat_type=Y tk_state=Z dissolve_active=B tk_was_visible=B
show_for_mode(M): loaded pos=(X,Y) size=(W,H) → clamped=...
OVERLAY saved M / TK saved M
```

## Settings JSON Cleanup

If `tui_positions[battle/cutscene]` corrupts to dialogue's position (legacy bug): delete those keys + `tui_geometries[battle/cutscene]` → DissolveOverlay falls back to defaults (battle=top-center, cutscene=bottom-center).

---

# TUI — Choice Mode (PyQt6, `pyqt_ui/choice_overlay.py`)

~430-line `QWidget`, frameless + translucent. Replaces Tk Canvas choice rendering for `Type="choice"` messages (real FFXIV SelectString addon → ChatType 70).

## Visual

- **Vertical** dissolve gradient (top + bottom fade, 10% each — wider than DissolveOverlay's 5% because the canvas is short ≤400px). Distinct from battle/cutscene's horizontal dissolve.
- Container BG `#14161c` α=242 (95% opaque — slight see-through to game scene behind, per user preference 2026-05-26).
- **Header** "คุณจะพูดว่าอย่างไร?" — gold `#FFD700`, bold, Anuphan body_pt+4, **left-aligned** at PADDING_X (matches original Tk anchor="nw").
- **Choices** rendered as **pills** — each one a rounded-rect (radius=8) with bright BG `#1f242d` α=255 (fully opaque so choices stay readable against the semi-transparent container). Width = snug-fit text width (NOT full container width); height = single line + paddings. Long choices elide with "...".
- "• " prefix added by parser, NOT by overlay.
- Font size pulled from `settings["font_size"]` (TUI dialog's font, set via FontPanel target=`tui` or `both`). Font family hardcoded to Anuphan (same as DissolveOverlay — Tk dialog mode is the only renderer that honors `settings["font"]` family).

## Position behavior — in-memory cache (transient)

`self._cached_pos: Optional[tuple[int, int]]` — `None` on first show, set on `mouseReleaseEvent` after drag. Survives auto-hide + re-show within the same app session; reset on app restart. **Never persisted to settings.json** (user explicit decision 2026-05-26 — "จำตำแหน่งไว้ในแคช จนกว่าจะปิดโปรแกรม"). Clamp to screen at every show so a cached pos can't push the window off-screen if user changes resolution mid-session.

Default position (when cache is None): `x = center horizontally`, `y = int(screen_h × 0.601)` — preserves the 60.1% rule from the original Tk choice geometry.

## UI elements

- **Drag-to-move** — anywhere on overlay. Cursor changes to `ClosedHandCursor` during drag. Auto-hide timer pauses while dragging; restarts on release.
- **Close (X) button** — top-right, 22×22, hover-revealed (cursor poll 140ms — see PyQt6 gotchas, Enter/Leave flickers on overlapping siblings). Red on hover. Click → `hide_overlay()`. Drag is suppressed when click lands on close button rect.
- **ESC key** → instant hide.
- **No resize**, no save geometry, no lock/color/fadeout (transient overlay — minimal chrome).

## Auto-hide

- `AUTO_HIDE_MS = 10000`, `FADE_OUT_MS = 500` — same as DissolveOverlay.
- New `show_choice()` cancels any in-flight fade and snaps opacity back to 1.0.
- Hover prevention: if cursor inside overlay rect at fire time → restart timer instead of fading.

## Parser — `pyqt_ui/choice_parser.py`

`parse_choice_text(text: str) → (header, choices: list[str])`. Extracted byte-for-byte from old Tk `_handle_choice_text` parsing block. Handles:
- Pipe format: `"Header | A | B"`
- Newline fallback with Thai header keyword detection (`พูด ว่า ไร ดี อะไร จะ คุณ ท่าน`)
- Long-line split on sentence boundaries (>100 chars + 2+ punctuation)
- Unwanted-header leak strip + 70% similarity dedup
- Bullet prefix `"• "` applied per choice (parser, not overlay)

## Dispatcher routing — `translated_ui._route_to_choice_overlay`

Modeled on `_route_to_dissolve_overlay`. The 3 must-not-violate rules apply identically (substitute `_choice_overlay_active` for `_dissolve_active`):

1. **MUST NOT update** `current_chat_type` / `choice_mode_active` (Tkinter state stays untouched while overlay is active — same reason as battle/cutscene).
2. **Mode change choice → other** → `_exit_choice_overlay()` hides overlay + restores Tk root if it was visible before. Triggered in `update_text` dispatcher when `is_choice_dialogue=False` AND `_choice_overlay_active=True`.
3. **`MBB._do_tui_auto_show` early-returns** when `_choice_overlay_active=True` (extended OR-condition with `_dissolve_active`).

**Cross-mode hook** in `_route_to_dissolve_overlay`: if `_choice_overlay_active` when dissolve fires (choice → battle), hide choice overlay first, preserve `_tk_was_visible_before_*` chain so exit logic restores correctly.

**Defensive timer cancel** — same set as dissolve: `move_end_timer` + `resize_end_timer` + `_deferred_render_id` + fade/window_hide timers killed before withdrawing root.

## Choice detection — `_is_choice_dialogue` + chat_type=70 fallback

[translated_ui.py:3347](python-app/translated_ui.py#L3347) detects pipe-separated format with Thai header patterns (`"คุณจะพูดว่าอย่างไร"` / `"คุณจะพูด"`). After `translate_choice()` removes pipes and adds bullet prefixes, pipe-detection fails — so dispatcher has a second-chance check: `getattr(self, '_current_chat_type', 0) == 70`. Either path routes to `_route_to_choice_overlay`.

## Theme switch crash mitigation

`MBB._apply_theme_update` stops fade animations + hides both overlays + calls `_exit_*_overlay()` BEFORE Mini UI Tk widget rebuild. Without this, the Tk event queue holds stale references during rebuild → GIL fatal in next `root.update()` poll. See [[feedback-tk-qt-theme-switch-crash]].

## Test injection

`pyqt_ui/settings_panel.py` "Choice" button — sends `Type="choice"` + `ChatType=70` + pipe-separated English body (mirrors real C# bridge). `_TEST_CHOICE_2` (2-choice) + `_TEST_CHOICE_3` (3-choice) pools, alternates randomly. **Critical:** `Type` must be `"choice"` (not `"dialogue"`) so handler hits `translate_choice()` path — otherwise Gemini may use a different Thai header wording that `_is_choice_dialogue` doesn't recognize.

## Tk fallback (kept for safety)

If `MBB.choice_overlay` fails to construct (PyQt6 error), `translated_ui.choice_overlay` stays `None` and the dispatcher falls through to the legacy `_handle_choice_text` Tk renderer (kept intact at lines 3366-3762). Safe-by-default — never deletes user-visible feedback.

## Diagnostic logs

`[CHOICE-DBG]` prefix on every dispatch/show/hide site + `[CHOICE-PARSE]` from parser. Grep for fast diagnosis. Keep these in.

---

# Translated Logs UI (PyQt6, `pyqt_ui/translated_logs.py`)

~1100 LOC; replaced Tkinter version. Compatibility shims (`root`, `winfo_exists`, `state`, `withdraw`, etc.) keep `MBB.py` minimal-change.

## Bubbles

`ChatBubble(QFrame)` paints one rounded rect. Speaker label color-coded:
- `???` purple, dialogue choice gold, Lore dim, normal cyan

## Thai-Aware Wrap

Qt `QLabel.wordWrap` only breaks at whitespace; Thai has none. `_insert_thai_breakpoints()` injects ZWSP (U+200B) at Thai leading-vowel boundaries (เ แ โ ใ ไ).

## Bubble Width

`setHeightForWidth(True)` + `MinimumExpanding` policy + `heightForWidth(w)` override — Qt uses heightForWidth instead of naive sizeHint, so `wordWrap` actually wraps.
Plus `eventFilter` on viewport + inner `QLabel` maxWidth cap to prevent overflow from `setWidgetResizable(True)`.

## QSS Font

Qt stylesheets override `setFont()` for QLabels inside styled widgets. Apply `font-family` + `font-size` via QSS so FontPanel changes propagate.

## Background-Only Opacity

`setWindowOpacity()` fades everything. Replaced with rgba in QSS for `QFrame#logs_bg` driven by 10-100 slider — bubbles paint solid colors and stay 100% opaque.
Surgical `self.bg.setStyleSheet(...)` per slider tick (NOT full `_apply_theme()`) avoids 60Hz polish thrash.
350ms QTimer debounce on disk write.

## App-Wide Hover Detection

Default Qt widgets emit `mouseMoveEvent` only when button pressed. Solution: enable `mouseTracking` + `WA_Hover` recursive on children + `app.installEventFilter(self)` for `MouseMove`/`HoverMove`/`HoverEnter`/`Enter`. Throttle `_save_geometry` to 500ms QTimer.

## Step-Lock Transparency (LOG, 4 levels)

`10 / 40 / 80 / 100` — `TranslatedLogsPanel.TRANSPARENCY_STEPS`. Snap-on-drag + no-op detection.
Migration: existing `settings.json` value snaps to nearest step on load.

## Lock Mode

Session-only (always starts unlocked). Drag with no `print()` between events. `stop_move` logs once with `logging.info`. Exception handlers `except (AttributeError, tk.TclError):` — never bare except.

---

# NPC Manager (PyQt6, `pyqt_ui/npc_manager_panel.py`)

## Tabs (3): MAIN / NPCS / LORE

- **Personality** inline in MAIN (`character_roles[firstName]` editable as `QTextEdit` between Name and Gender)
- **WORD FIX tab hidden** — `setVisible(False)`. word_fixes deprecated (see Database section).
- **ROLES tab merged into MAIN** (v1.7.9)

## Search match indicator (cross-tab, v1.8.16+)

When the panel-level search box has text, the panel scans **all three sections** (main + npcs + lore) for substring matches. Any tab OTHER than the currently-active one that contains a match gets a **dual visual indicator**:

1. **2px accent-coloured border around the tab button** — theme-aware (uses `palette['accent']`). Driven by `QPushButton#npc_tab_btn[has_match="true"]` QSS rule + dynamic property toggle (`setProperty` + `unpolish/polish`). Padding compensated `8px 22px → 7px 21px` so the border addition doesn't change button geometry.
2. **Hardcoded bright-red badge** (`#ff2d2d` with 2px white ring) — 12×12 child `QFrame` at the top-right corner of the button. Hardcoded red (NOT theme accent) ensures the badge is always distinguishable even when accent itself is reddish.

The active tab never gets an indicator (user is already there). `_compute_match_tabs(query)` returns the set of tabs with at least one match; `_update_tab_dots()` calls `set_has_match(bool)` on each `_TabButton` accordingly. Hooked into `_on_search_changed`, `_switch_tab`, and `_apply_theme` (border colour re-renders automatically via the theme rebuild).

**Performance:** ~423 entries (main 218 + npcs 65 + lore 140), early-exit per section → <1ms per keystroke even with 4-char queries. No throttle/debounce needed.

**Why two visuals, not one:** the border alone could blend with a theme whose accent is close to the active-tab fill; the badge alone could be missed at a glance. Together they're impossible to miss but neither dominates the UI.

## Header-only drag (UI shift fix, v1.8.16+)

`mousePressEvent` checks `event.position().toPoint().y() <= 64` (10px outer margin + 54px header height) before starting a drag. Clicks below that zone (list, details panel, empty bg) leave `self.old_pos = QPoint()` → `mouseMoveEvent` skips drag via `isNull()` check.

**Why this matters:** previously any LMB press anywhere on the panel armed the drag state. Even a 1-2px micro-drift between press and release would nudge the window, producing a subtle "UI shift" visible as a small jitter. The header-only check eliminates this. Matches the same fix pattern used by Theme Manager (`mousePress y ≤ 46`).

## `open_with_character` — cross-section search (v1.8.16+)

When user clicks a character name on the TUI, [npc_manager_panel.py:open_with_character](python-app/pyqt_ui/npc_manager_panel.py) searches **both** `main_characters` and `npcs` before deciding to auto-add. Order:

1. Match in `main_characters` → switch to MAIN tab + select row
2. Match in `npcs` → switch to NPCS tab + select row
3. No match anywhere → add new entry to `main_characters` (default for unknown names)

Each match step uses the same first-token fuzziness as the speaker confirm-icon: target "Nashu Mhakaracca" matches a registry firstName "Nashu" because the registry typically stores only the first token. For npcs (single `name` field) the fuzziness is bidirectional: target's first token vs registry's `name` AND registry's first token vs target. Prevents duplicate entries when a character already lives in the NPCs database.

## Polaroid Avatar View (v1.8.2)

Clicking avatar opens `_PolaroidCard` overlay (~400×510px) inside details panel. Card shows full image (top-cropped) + firstName in Caveat handwriting font.

**Hover-revealed:** "📷 เปลี่ยนภาพ" pill (top-right) + "✕" delete (bottom-right).

**UX flows:**
- Empty avatar → click goes straight to file picker (skip empty Polaroid)
- Avatar with image → click opens Polaroid
- Click outside / Resize window / ESC → dismisses

**Critical Polaroid patterns (each took multiple iterations):**

1. **Shadow ghost outline** ([QTBUG-56081](https://bugreports.qt.io/browse/QTBUG-56081)): action buttons live as **siblings of `_PolaroidCard`** (children of overlay), NOT children of card. `QGraphicsDropShadowEffect` rasterizes ALL descendants together — children-of-shadow get their bounding rect baked before QSS border-radius clips, leaking square ghosts.

2. **Custom font**: panel-level QSS subtree cascade overrides `setFont()`. Bulletproof workaround: pre-render name to `QPixmap` via `QPainter.drawText` (uses `QFont` directly), then `label.setPixmap(pm)`. See `_render_name_pixmap`. Also `Polaroid` calls `QFontDatabase.addApplicationFont()` itself (idempotent) since `QtFontManager` is lazy.

3. **Hover flicker**: timer-based geometry polling (60ms), NOT Enter/Leave events. Cursor on sibling button → Leave on card → hide buttons → cursor on card → Enter → show buttons → loop. Geometry poll avoids it.

4. **Resize / outside-click dismiss**: app-level `eventFilter` installed only while overlay visible. Listens for top-level `Resize` + `MouseButtonPress` outside overlay rect.

## Avatar Hover Menu (v1.8.7)

Hover-revealed action menu when character selected:
- **เลือกภาพจากไฟล์** (icon `images.png`) — file picker
- **ถ่ายภาพจอ (Screenshot)** (icon `camera.png`) — fullscreen capture + crop

**POLLING-based visibility (NOT event-driven):** QTimer in `_MainTab` checks cursor position every 80ms. Show when cursor in avatar OR menu rects; close after 180ms grace.
Avatar `set_force_hover(bool)` keeps accent border steady while menu open (Qt fires spurious leaveEvent when popup grabs mouse focus).

## Screenshot Tool — `pyqt_ui/screenshot_tool.py`

For avatar capture only (NOT general screen-area-detection — that legacy is removed).
- Hide NPC Manager → 120ms wait → `QScreen.grabWindow(0)` on the screen panel is currently on (`QGuiApplication.screenAt(panel center)`)
- `ScreenshotCropOverlay`: 60% black mask + punched-out crop rect (`QPainterPath` subtract) + 2px cyan `#00d4ff` border + 8 handles
- Click-drag select, min 32×32, HiDPI-aware (`devicePixelRatio` scaling)
- ENTER or double-click → emit `crop_confirmed(QPixmap)` → save temp PNG → `dm.set_main_character_image()` → 512 WebP → restore panel + reopen Polaroid
- ESC → cancel → restore panel only
- `WA_DeleteOnClose` releases ~10MB pixmap immediately
- try/except around overlay construction (panel restore on failure)

## Avatar Storage — 512 WebP

`npc_data_manager.set_main_character_image()` defaults `size=512`, format `WebP` quality=88, alpha preserved.
- 128 PNG → 512 WebP: ~89% smaller (y_shtola 503KB → 56KB), visually indistinguishable
- `safe_filename` default `.webp`
- Re-upload deletes legacy `.png` to prevent orphans
- Polaroid no-upscale guard: `target_logical = min(IMAGE_AREA, source_min_dim)` — small 128px shows letterboxed, not blurry-upscaled

## Cloud Sync (v1.8.9, Phase A)

Cherry-pick merge UX from cloud-hosted npc.json.

**Cloud repo:** [iarcanar/MBB_NPCData](https://github.com/iarcanar/MBB_NPCData) (public, plaintext)
- `manifest.json` at root — schema_version, data_version (date-based), data_url, data_sha256, data_size_bytes, stats, min_mbb_version, release_notes_th
- `data/npc.json` — latest
- `data/archive/npc-<version>.json` — per-release snapshots
- `.gitattributes` forces `data/*.json` as binary (sha256 integrity)

**Publish workflow:** [scripts/build_npc_release.py](scripts/build_npc_release.py)
- Reads local `python-app/npc.json` → stats + sha256
- 2-commit flow: push data → download from raw URL for authoritative sha256 (CDN LF-normalization workaround) → generate manifest → push
- `--dry-run`, `--notes "..."` flags

**MBB side:** [python-app/npc_cloud_sync.py](python-app/npc_cloud_sync.py)
- `check_for_update(local_version) → UpdateCheckResult` (dataclass drives UI state machine)
- `download_and_verify(manifest)` (sha256 mismatch raises)
- `Accept-Encoding: identity` (bypass auto-decompression that would skew sha256)
- Caches manifest to `%LOCALAPPDATA%/MBB_Dalamud/cloud_cache/`

**UI integration:** unified action group (Import data + Cloud Sync buttons share 1 border-radius + 1px divider). Click flow: check → confirm dialog → download → existing `_MergeDialog` cherry-pick UI.

**Settings persistence:** `QSettings("MBB", "NPCManager")` — `cloud_sync.last_version` + `last_check_at`.

**CRITICAL PyQt6 pattern:** cross-thread results marshaled via `pyqtSignal` (auto-queued connection). `QTimer.singleShot(0, ...)` from worker thread silently no-ops (timer fires on calling thread, not UI thread).

**Roadmap:** Phase A.5 (auto-check on startup), Phase B (encryption + private repo), Phase C (paid tier gate) — all deferred.

## Merge Modal (v1.8.4)

`_MergeDiff` class — additive diff across 4 sections (`main_characters`, `npcs`, `lore`, `character_roles`). Never deletes. Identity: `(firstName, lastName)` lower for main; `name` lower for npcs; key for dicts. Skips `word_fixes` + `_game_info`.

`_MergeDialog` — frameless 760×660, 2px accent border. Top: 2 file cards (BASE | TARGET) with mtime arrows `↑↓=`. Body: scroll diff with checkbox + NEW/CHG badge. Footer: Cancel / Merge ที่เลือก (N).

**Audit:**
- `MAX_NPC_BYTES = 50MB` cap before `json.load`
- `dlg.deleteLater()` after `exec()`
- `_apply_diff` isinstance hardening (reset to `{}`/`[]` if type mismatches)

## Header

Live counts + file mtime: `main 218 · npcs 65 · lore 139 · อัปเดต X นาทีที่แล้ว`. Refreshed on init/autosave/reload + 60s QTimer.

`_format_relative_time(ts)`: `<60s "เมื่อสักครู่"`, `<60m "X นาทีที่แล้ว"`, `<24h "X ชม.ที่แล้ว"`, `<7d "X วันที่แล้ว"`, else absolute date.

Manual **↻ reload** button — re-reads npc.json + propagates via `on_save_callback` (translator + text_corrector + caches).

**Toast:** `"✓ บันทึก · ใช้ในการแปลทันที"` when MBB attached.

## Pin

Default `_is_pinned = True` (matches `WindowStaysOnTopHint` at init). Hybrid Qt + Win32 `_apply_topmost`:
- `setWindowFlag` keeps Qt's internal model in sync
- Win32 `SetWindowPos(HWND_TOPMOST/NOTOPMOST)` enforces z-order without unmap+remap flicker

## Avatar Badge Icons

Procedural flat-design icon via `QPainter` — rounded square in theme accent + white photo glyph (frame + V mountain + sun dot). No raster asset.
MAIN list rows show badge at col-0 if `image` set; placeholder same size if not (vertical alignment).
`setIconSize(QSize(22,22))` to prevent Qt's 16px default downscale.

---

# Translation Engine — `translator_gemini.py`

## System Prompt Versions

| Flag | Method | Tokens | State |
|------|--------|--------|-------|
| `False` (default) | `get_rpg_general_prompt()` v2/v3 | ~490 (+rule 10) | ACTIVE |
| `True` | `get_rpg_general_prompt_v1()` | ~1000 | Backup for revert |

Revert: flip `self.use_verbose_prompt = True` in `__init__()` (~line 129), restart.

**Modern Thai default (since v1.8.1):** ฉัน/ผม/คุณ/นาย/เธอ (anime-dub register, Frieren Netflix subs style). Archaic ข้า/เจ้า/ท่าน only when `Character's style` says so.

**Per-character register** in `npc.json:character_roles` — Modern: Y'shtola/Alphinaud/Alisaie/Wuk Lamat/G'raha Tia/Estinien/Thancred/Zoraal Ja. Semi-archaic/archaic: Urianger (deeply archaic — canon trait), Sphene, Emet-Selch (theatrical), Hythlodaeus (warm ancient).

## Token Budget

| Component | v1 | v2 (current) |
|-----------|-----|----|
| System prompt | ~1000 | ~490 |
| Protected names (in system) | ~400 | 0 (removed) |
| Per-request names | ~80 | ~80 |
| Lore context | ~150 | ~80 |
| Context + style + dialogue | ~500 | ~500 |
| Recent dialogue (wide-context) | 0 | ~150-400 |
| **Total** | ~2100 | ~1020-1270 (target <1200) |

## Name Preservation (3 layers)

**Layer 1 — Pre-process `_mark_names_in_text(text, names)`:**
```
"Well met, Bol Noq'." → "Well met, [Bol Noq']."
```
- Names sorted longest→shortest (no partial match)
- `???` not wrapped
- System prompt rule 3: "Names in [brackets] must NEVER be translated. Output without brackets."

**Layer 2 — Post-process `_restore_names_in_translation(translation, names_in_source)`:**
```python
pattern = rf'[\[「『【«"\'(]*{re.escape(name)}[\]」』】»"\'）]*'
```

Strips ALL bracket combos around known names. Examples:
| Input | Output |
|-------|--------|
| `[「Bol Noq'」]` | `Bol Noq'` |
| `[Bol Noq']` | `Bol Noq'` |
| `「Bol Noq'」` | `Bol Noq'` |
| `**Bol Noq'**` | `**Bol Noq'**` (preserves bold) |
| `**[Bol Noq']**` | `**Bol Noq'**` |

> Regex does NOT touch `*` — rich text markers must survive for `RichTextFormatter`.

**Layer 3 — General bracket cleanup** (`translator_gemini.py` ~line 917, after layer 2):
```python
re.sub(r'\[([^\[\]]{1,30})\]', r'\1', translated_dialogue)
```
Strips `[brackets]` Gemini added on its own (e.g. `[adventurer]`, `[WoL]`).

## Rich Text Markers

| Marker | Style | Font | Handled by |
|--------|-------|------|-----------|
| `*text*` | Italic | FC Minimal Medium | `RichTextFormatter.parse_rich_text()` |
| `**text**` | Highlight | base + bold, `#FFB366` | `RichTextFormatter.parse_rich_text()` |
| `<NL>` | Newline | — | Text preprocessor |

## get_relevant_names()

- Names appearing in dialogue text + essential names
- Capped at 20 (token control)
- Essential (20): Y'shtola, Alphinaud, Alisaie, Wuk Lamat, Estinien, G'raha Tia, Thancred, Urianger, Krile, Emet-Selch, Hythlodaeus, Venat, Meteion, Zenos, Koana, Zoraal Ja, Gulool Ja, Sphene, Otis

---

# Wide-Context Translation (always-on, v1.7.8+)

Inject recent Thai translations into Gemini prompt for consistency (pronouns, honorifics, transliteration).

## Flow

```
ConversationLogger.log_message()         (always-on, in-memory)
ConversationLogger.update_translation()
        ↓
ConversationLogger.get_recent_context()  cutscene=8, dialogue=6, battle=3
        ↓
dalamud_immediate_handler.py
        ↓
translator_gemini.translate(conversation_context="...")
```

## get_recent_context()

- Source: `_current_conv['messages']` (same conversation)
- Uses `translated` field only (don't send EN — Gemini may copy)
- Skip if no `translated` or `chattype_group == 'other'`
- Max **80 chars** per entry
- `exclude_last=True` (avoid dup with "Text to translate")
- Strips dup speaker prefix

## Rule 10 (System Prompt)

> Context Consistency: When [Recent dialogue] is provided, maintain the SAME pronouns (สรรพนาม), honorifics, and name formats used in previous lines.

## Conversation Boundaries

| Condition | Value | Effect |
|-----------|-------|--------|
| Time gap | >45s | New conversation |
| Speaker limit | >8 (`CONVERSATION_MAX_SPEAKERS`, was 5) | New conversation |
| System event (zone_change) | always | Reset in-memory context |
| Cross-type (dialogue/cutscene/battle) | flows freely | (no longer triggers split) |

## ConversationLogger — Two-Mode

| Mode | `disk_logging` | Behavior |
|------|---------------|----------|
| Memory-only (default) | `False` | Context in RAM only |
| Full (debug) | `True` | + JSON to `%LOCALAPPDATA%/MBB_Dalamud/logs/conversations/` |

- **Context always active** — independent of Settings toggle
- "Conversation Log" toggle controls disk only
- `set_disk_logging(bool)` flips mid-session
- Logged ChatTypes: `{61, 68, 71, 0x0045, 0x0046}` (player chat 27/3 filtered out)

**Lifecycle in MBB.py:**
```python
self.conversation_logger = ConversationLogger(disk_logging=False)  # always init
# On start:
self.conversation_logger.set_disk_logging(conv_log_enabled)
self.conversation_logger.start_session()
# On stop:
self.conversation_logger.end_session()  # save JSON only if disk_logging=True
# Never set None — reuse next session
```

## Zone Change Detection

**C# (`DalamudMBBBridge.cs`):**
- `IClientState` service
- `OnTerritoryChanged` → `TextHookData{Type="system", Message="zone_change:{id}"}` → queue
- Dispose: unsub event

**Python (`dalamud_immediate_handler.py`):**
- Check `Type=="system"` before filtering → `conversation_logger.log_system_event()` → return
- Does NOT forward to translation

**Manual zone change** — button in Game info row (`control_panel.py`). Click → `MBB.manual_zone_change()` → feedback "Zone changed — context reset" on `status_info` for 2.5s.

---

# Zero-Width Character Safety

`text_corrector.py` strips ZWS chars from npc.json names on load:
```python
_zws = "​‌‍﻿"
clean = char["firstName"].strip().translate(str.maketrans("", "", _zws))
```

Applies to `main_characters` (firstName + lastName) and `npcs` (name).

**Real incident:** `"Tataru​"` in npc.json shadowed `"Tataru"` → speaker icon broke.

Also strip `**`, `*`, ZWS from **speaker name** before `name in self.names` check (3 sites in `translated_ui.py`).

---

# NPC Database — `npc.json`

| Section | Count |
|---------|-------|
| main_characters | 218 |
| npcs | 65 |
| word_fixes | 0 (deprecated) |
| lore | 135 |
| character_roles | 197 |

**word_fixes deprecated** — Dalamud text hook is byte-accurate (not OCR), so character-substitution corrections (`1→i`, `0→o`, etc.) are unneeded. Name preservation handles FFXIV proper nouns. Backup: `python-app/backups/word_fixes_backup_20260426.json`. Tab hidden in NPC Manager. Key kept in JSON for backwards-compat.

**Backup before bulk ops:** `python-app/backups/npc_backup_*.json`.

**DANGER — never re-add short word_fixes (1-2 chars).** A single-char fix like `1→i` replaces every occurrence in every line, corrupting text irreversibly.

---

# Font System — Dual Storage

| UI | Settings key | Default font | Default size |
|----|-------------|-------------|-------------|
| TUI | `settings["font"]` / `["font_size"]` | Anuphan | 24 |
| Logs | `settings["logs_ui"]["font_family"]` / `["font_size"]` | Anuphan | 16 |

**Bundled fonts:** Anuphan (default Thai), FC Minimal Medium (italic), Caveat (Polaroid handwriting), Pacifico, Google Sans 17pt.

Tkinter uses OS resolver. **PyQt6 needs `QFontDatabase.addApplicationFont()`** — `QtFontManager` (`pyqt_ui/qt_font_manager.py`) handles registration (lazy — runs on Settings/Font panel open).

## FontPanel Target System — `pyqt_ui/font_panel.py`

Target keys: `tui` / `logs` / `both` — saved as `font_target_mode`.

```python
# MBB.apply_font_with_target()
if target_mode in ("tui", "both"):
    self.settings.set("font", font_name, save_immediately=False)
    self.settings.set("font_size", font_size)
if target_mode in ("logs", "both"):
    if not translated_logs_instance:
        self.settings.set_logs_settings(font_family=font_name, font_size=font_size)
```

> NEVER save top-level `font`/`font_size` when target=`logs` — overwrites TUI font.

**Open from Logs UI:** use `_ensure_font_panel()` + `reload_target()`. **NEVER `_toggle_font()`** (it closes panel if open).
```python
# Correct:
sp._ensure_font_panel()
fp.reload_target()
fp.raise_()
```

**Bidirectional sync:** FontPanel +/- ↔ Logs UI +/-. `_sync_font_to_settings()` persists + updates FontPanel if open & target=`logs`.

## CRITICAL Gotcha — QSS Overrides setFont

Panel-level QSS subtree cascade overrides `setFont()` silently. Two workarounds:
- **For QSS-styled containers:** apply `font-family` + `font-size` via QSS, not `setFont()`.
- **For QLabel/QLineEdit/QTextEdit:** use inline `setStyleSheet(f"font-size: {n}pt;")` (inline wins against class rules) OR pre-render to QPixmap via `QPainter.drawText` (bypasses QSS pipeline entirely — Polaroid pattern).

## Settings Backend

- `get_logs_settings()` default: `{width: 480, height: 320, font_size: 16, font_family: "Anuphan", visible: True}`
- `set_logs_settings(**kwargs)` accepts: width, height, font_size, font_family, visible, x, y, transparency_value, logs_reverse_mode
- **Inside Settings class:** `self.settings["key"] = value` (dict, not `.set()`)

---

# Theme System — `pyqt_ui/styles.py` + `appearance.py`

12 modern palettes (replaced old 5):

| # | Theme | bg | accent |
|---|-------|-----|--------|
| 1 | Carbon | `#0d1117` | `#58a6ff` |
| 2 | Graphite | `#16181c` | `#7c8aed` |
| 3 | Slate | `#0f172a` | `#38bdf8` |
| 4 | Mocha | `#1e1e2e` | `#cba6f7` |
| 5 | Tokyo | `#1a1b26` | `#7aa2f7` |
| 6 | Dimmed | `#22272e` | `#6cb6ff` |
| 7 | Neon | `#0a0e1a` | `#00d9ff` |
| 8 | Synthwave | `#1a0d2e` | `#ff5599` |
| 9 | Forge | `#1a0f0a` | `#ff8c42` |
| 10 | Snow | `#ffffff` | `#0969da` |
| 11 | Cream | `#faf6ed` | `#c2410c` |
| 12 | Mint | `#f0fdf4` | `#15803d` |

**`derive_palette(primary, secondary, surface=None, text_override=None)`:**
- Proportional surface elevation: `base = max(0.018, min(0.045, primary_l * 0.32))`
- Light-theme branch (bg luminance > 0.5): aggressive negative shifts (-0.075 surface, -0.130 border)
- WCAG `toggled_text` threshold: `< 0.179 → white, else dark` (was 0.5 — caused 2.4:1 contrast on light accents)
- Helpers: `_shift_lightness()`, `_desaturate()`, `invert_pixmap()`, `is_light_theme()`

**`get_theme_color(key, default=None)` rule:** if `color_value is None and default is None: return None`. **Don't return `fg_color` fallback when default is `None`** — that's how old code made all buttons white.

**Migration in `appearance.py:load_custom_themes`:** detect old default-theme accents/names → wipe + re-create with v2 design. Custom user colors preserved.

## Theme Manager UI — `pyqt_ui/theme_panel.py`

- `ThemeSwatch(QWidget)` — custom paint with 5 color dots (bg_titlebar, surface, border, accent, text)
- 400×520, 4 cols × 3 rows for 12 themes
- **Instant apply** — no APPLY button
- 4-color picker (bg, accent, surface, text). "Auto" shows diagonal stripe + dashed border
- **Drag fix:** header-only (`mousePress y ≤ 46`) — clicking swatch with 1-2px drift no longer moves panel

## White-Icon Inversion

`invert_pixmap()` — RGB-invert preserving alpha (`QImage.invertPixels(InvertRgb)`).
`header_bar.py` + `bottom_bar.py` call `update_icon_theme(invert: bool)` from `main_window._apply_theme()` based on bg luminance:
- Dark bg → white icons (keep)
- Light bg (Snow/Cream/Mint) → invert to dark

---

# Settings — Dual UI

**ACTIVE UI:** `pyqt_ui/settings_panel.py` (PyQt6)
- Add toggles via `_add_toggle()`. Auto-saves on change.
- Thai section labels: "ตั้งค่าอื่นๆ" / "ทดสอบการแปลรูปแบบต่างๆ" / "ปุ่มลัด"
- Modern iOS-style `ToggleSwitch`: 44×22 → 52×26 (v1.8.0 +20% scale), 16px sliding knob, 160ms OutCubic animation. Drop-in API (`isChecked()`, `toggled` signal).

**LEGACY UI:** `settings.py` Tkinter — backend stays here; DO NOT add new toggle UI.

**Backend:** `Settings` class — `get()`, `set()`, `save_settings()`, `set_logs_settings(**kwargs)`.

## Restart App (v1.8.10)

Footer button below APPLY. Countdown 3..2..1 on button text in `settings_panel.py`. After countdown calls `self.main_app.restart_app()`.

**`MagicBabelApp.restart_app()`** (in `MBB.py`, right before `exit_program()`):
1. Re-entry guard via `self._restarting` flag — clicking twice during countdown doesn't spawn 2 children
2. Build cmdline:
   - Frozen `.exe`: `[sys.executable, "--from-restart"]`, cwd = `os.path.dirname(sys.executable)`
   - Dev `.py`: `[sys.executable, os.path.abspath(__file__), "--from-restart"]`, cwd = MBB.py's folder
3. `subprocess.Popen(cmd, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, close_fds=True, stdin/out/err=DEVNULL, cwd=cwd)`
4. Call `self.exit_program()` which closes windows, saves settings, releases mutex (via process death), then `sys.exit(0)`
5. If spawn raises before exit_program → clear `_restarting` + show `QMessageBox.critical` so user can retry manually

**`--from-restart`** cmdline flag is the bridge between old/new process. The new process's `_try_acquire_singleton(is_restart=True)` polls every 50ms up to 1.5s waiting for the old process's mutex to release, then acquires it. Singleton lock stays unbroken — a THIRD instance launched during the restart window still sees the lock and gets blocked.

## Single-Instance Lock (Windows Mutex, v1.8.10)

Defined at top of `if __name__ == "__main__":` in `MBB.py`, BEFORE `QApplication` / `Tk()` / API key dialog.

**Mechanism:** `kernel32.CreateMutexW(None, False, "MBB_Dalamud_SingleInstance_v1")`. Windows auto-releases on process exit (incl. kill/crash) — no cleanup code needed. Handle kept in module-scope `_mbb_singleton_mutex` so GC doesn't close it early.

**Normal launch:** single `CreateMutexW` attempt. If `GetLastError() == ERROR_ALREADY_EXISTS (183)` → show native `user32.MessageBoxW` ("MBB กำลังเปิดอยู่แล้ว · กรุณาปิดหน้าต่างเดิมก่อนเปิดใหม่") with `MB_ICONINFORMATION | MB_TOPMOST` → `sys.exit(0)`.

**Restart launch (`--from-restart` in sys.argv):** polls `CreateMutexW` 30× at 50ms intervals (1.5s total). Acquires when old process releases. On timeout, proceeds unlocked (best-effort — old process hung; user's next manual launch will still work normally since orphaned mutex names are cleaned up by the OS).

**Why MessageBox not Tk/Qt dialog:** the check runs before any GUI framework is loaded. `user32.MessageBoxW` is native Win32, zero dependencies, modal, topmost. Fits an "early bailout" perfectly.

**Failure modes (mutex skipped, app starts anyway):** non-Windows build, restricted permissions, ctypes import failure. Logged as `[single-instance] mutex check skipped: <error>`. Best-effort — duplicate detection is opt-in protection, not a hard requirement.

---

# Splash Screen — `MBB.py`

Tkinter Toplevel + PIL rendering, max 1280×720, aspect-preserved, centered on screen.

**Visual (v1.8.14, redesigned 2026-05-20 via [docs/manual/prototype.html](docs/manual/prototype.html)):**
- PIL rounded corner mask via `ImageDraw.rounded_rectangle` + `transparentcolor="black"` (no border)
- Corner radius: `max(14, new_width // 48)` — subtle (~22px at 1080 wide). Halved from old `max(28, w//24)` ≈ 45px per design review.
- Image fallback chain: `assets/MBBvisual.jpg` → `MBBvisual.png` → `MBBvisual.jpeg` → `MBBvisual_mar26.png` → `MBBvisual_legacy.png` (project currently ships `.jpg`)
- **Bottom-center group: `[meteor icon] [4px gap] [version text]`, no background bar**
  - Meteor icon (`assets/mbb_meteor.png`) loaded at height `max(60, font_size × 3.7)` ≈ 88px at font 24, width auto (preserves ~3:2 meteor aspect)
  - Icon vertical-centered on text vertical-center — overflows top/bottom so meteor trail keeps its dynamic shape
  - Icon compositing: cyan halo (silhouette filled `#00e5ff` alpha 140, blur 8) + dark drop shadow (silhouette `(0,0,0,210)` offset (1,2), blur 4) + sharp icon on top
- **Version text** (drawn into image via PIL): bright cyan `#00e5ff` (matches landing/manual theme), font Anuphan size `max(22, new_width // 44)` ~24px at 1080 wide
  - **Dark drop-shadow halo** (replaces removed dissolve bar): 2-layer Gaussian (radii 18/6, alphas 150/200, offsets (0,0)/(0,2))
  - **Cyan glow**: 3-layer Gaussian (radii 12/6/2, alphas 90/140/200)
  - Sharp top: 1px dark `(0,0,0,230)` offset (1,2) + cyan `#00e5ff` at (text_x, text_y)
- Bottom margin: `max(36, new_height × 0.07)`
- Group horizontally centered: `group_left = (new_w − (icon_w + gap + text_w)) // 2`
- Antialiased rounded edges fade to black → `transparentcolor` catches them → minor dark fringe at corners is acceptable (Tkinter `transparentcolor` is 1-bit; pixels not exactly `#000` aren't transparent)

**Timing:** fade-in 400ms (20 steps × 20ms, blocking) → min 5s hold → fade-out 500ms (non-blocking QTimer chain in `_fade_splash_step`).

**Imports needed at top of MBB.py:** `from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter`.

**Diagnostic log line on success:** `[splash] Loaded <path> · size=WxH · corner_r=N · version=vX.Y.Z`

---

# Updater UI — `updater/updater.py`

640×620 window. Logo `mbb_meteor.png` (154×100 subsample), `MBB Updater` 24pt + subtitle 12pt.

**Visual states:**
- Checking: animated rotating-arc spinner (Canvas 28×28, 40ms redraw) + animated dots ("ตรวจสอบ.", "..", "...")
- Final: colored badge (green/cyan/amber/red) + icon + label

**Behavior:**
- 404 from GitHub → green "✓ เวอร์ชั่นของคุณเป็นเวอร์ชั่นล่าสุด" (positive framing)
- Auto-hide "Update Now" when on latest → only "ปิด" remains
- Dev-mode short-circuit: `.py` skips Stage 1 (copy-to-temp + relaunch), goes to Stage 2 with auto-target `dist_test/MBB`
- `_resolve_asset(name)` 3-path: `sys._MEIPASS` → repo dev → installed `_internal/`. Rejects absolute paths + `..` (path traversal guard)
- `WM_DELETE_WINDOW` → `_on_close` cancels spinner/dots timers (avoid TclError on shutdown)
- `_start_spinner` + `_start_dots_animation` cancel previous `after_id` before starting (defensive)

---

# Gemini Models

Updated 2026-05-20 after deprecation sweep. Removed `gemini-3.1-flash-lite-preview` (shutdown 2026-05-25), `gemini-2.0-flash` (shutdown 2026-06-01), `gemini-2.5-pro` (cost-ineffective for translation), and `gemini-3.5-flash` (added then removed same day — tested slow + over-reasoned translations; waiting for `gemini-3.5-flash-lite` instead). Old `gemini-1.5-*` display-name shim in `translator_gemini.get_current_parameters` also deleted.

Ordered cheap → premium so budget users pick the top option, quality seekers scan to the bottom:

| Model | Input $/1M | Output $/1M | Speed | Shutdown | Notes |
|-------|-----------|-------------|-------|----------|-------|
| `gemini-2.5-flash-lite` | $0.10 | $0.40 | mid | **2026-10-16** | Cheapest option; budget pick — but has the earliest deprecation among the three |
| `gemini-3.1-flash-lite` | $0.25 | $1.50 | ~382 tok/s (fastest of the three) | 2027-05-07 | **Default** (changed 2026-05-20 after user testing — better translation quality than 3.5 Flash at ~17× lower cost, longest runway before next migration) |
| `gemini-2.5-flash` | $0.30 | $2.50 | ~232 tok/s | 2026-10-16 | Mid-tier alternative |

**Why `gemini-3.1-flash-lite` is default (not the cheapest):** user benchmarked all three on FFXIV cutscenes 2026-05-20. 3.1 Flash-Lite scored noticeably higher on translation quality + character voice consistency than 2.5 Flash-Lite, and was *faster* than `gemini-3.5-flash` (which over-reasoned and produced flatter Thai). Cost is 2.5× the cheapest — but absolute cost stays under $1/day for heavy 6-hour sessions, and 3.1 has a 7-month-longer deprecation runway. The cheaper 2.5 family will need re-migration before October 2026 anyway, so anchoring the default to 3.1 saves a future round-trip.

**5 files to update when changing the model list:**
- `settings.py` (`VALID_MODELS` + 5 default-string sites incl. `get_displayed_model` / `get_api_parameters` / build-config block)
- `pyqt_ui/model_panel.py` (`AVAILABLE_MODELS` + `_load_current` fallback + `_reset_defaults`)
- `translator_gemini.py` (default `self.model_name` 3 sites + `valid_models` list in `set_api_parameters`)
- `model.py` (legacy Tkinter `model_var` default + combobox values + `_load_current` fallback)
- `appearance.py` (legacy combobox in `create_api_parameter_form`)

**Fallback for users on old saved settings:** [settings.py:1027-1033](python-app/settings.py#L1027-L1033) `get_api_parameters` validates `saved_model` against `VALID_MODELS` and falls back to `DEFAULT_API_PARAMETERS["model"]` with a warning log. Means upgrading users who had `gemini-3.1-flash-lite-preview` saved will silently snap to `gemini-2.5-flash-lite` on next launch — no manual migration required.

Guide: `docs/GEMINI_MODELS_GUIDE.md` (may lag behind this table — trust CLAUDE.md).

---

# Test Messages — `pyqt_ui/settings_panel.py`

3 buttons in Settings → real Gemini pipeline → renders on TUI. Curated FFXIV-flavored lines (v1.8.9 — replaced generic placeholders).

| Pool | ChatType | Count | Speakers |
|------|----------|-------|----------|
| `_TEST_DIALOG` | 61 | 10 | Tataru, Alphinaud, Alisaie, Thancred, Y'shtola, G'raha Tia, Estinien, Urianger, Krile, Wuk Lamat |
| `_TEST_BATTLE` | 68 | 6 | Zenos, Nidhogg, Estinien (dragoon voice), Emet-Selch, Sephiroth, ??? |
| `_TEST_CUTSCENE` | 71 | 4-6 | narration only (`speaker=""`) — 4 cinematic moods |

Cutscene is narration per FFXIV convention — characters speaking use ChatType 61.

```python
def _inject_test_dialog(self):
    speaker, message = random.choice(self._TEST_DIALOG)
    self._inject_test_message("dialogue", speaker, message, 61)
```

---

# Build & Distribution

## PyQt6 PINNED at 6.9.0

> Qt 6.10+ has a frameless+translucent rendering regression. Do NOT upgrade casually.
> See `BUILD_PROTOCOL.md` for full protocol.

## PyInstaller

- `python-app/mbb.spec` (main)
- `python-app/updater/updater.spec` (updater)
- Build dir: `dist_test/` (NOT `python-app/dist/`)
- Uses system Python 3.11

## Post-Build Copy (mbb.spec)

After COLLECT, copies out of `_internal/`:
- `_internal/npc.json` → `MBB/npc.json` (user-editable, visible)
- `_internal/npc_images/` → `MBB/npc_images/` (user data)

```
MBB/
├── MBB.exe
├── npc.json          ← user-editable, visible
├── npc_images/       ← user data, visible
└── _internal/
    ├── npc.json      (fallback)
    ├── npc_images/   (fallback)
    └── ... (Python runtime)
```

## Frozen-Mode npc.json — CRITICAL RULE (v1.8.7)

**Any code touching `npc.json` MUST use `get_npc_file_path()`.**

`resource_path()` resolves to `sys._MEIPASS/npc.json` (immutable bundled snapshot) — fine for static assets (fonts, icons) but WRONG for npc.json (user writes via NPC Manager → resolver must point to exe-level file).

Bug history: `text_corrector.load_npc_data()` used `resource_path()` → after NPC Manager save → reload → re-read bundled snapshot → new char missing → unknown-purple on TUI. Bug invisible in dev (single npc.json).

**Verification:** `grep -rn 'resource_path.*npc' python-app/` → must return zero matches.

`load_npc_data` calls `ensure_npc_file_exists()` before reading (resilience for fresh installs).

## Version Bump

`python bump_version.py patch|minor|major|X.Y.Z` updates 8 files. **Never edit version strings by hand.**

---

# Hard-Won Rules — Critical Patterns

## Tkinter Threading

- `winfo_exists()`, `attributes()`, `update()`, `destroy()` — **main thread ONLY**
- Thread-based animation → use `root.after()` recursive chain instead
- Tkinter + PyQt6 hybrid shutdown sometimes crashes with `PyEval_RestoreThread` GIL error — known harmless

## PyQt6 Gotchas

1. **QSS overrides setFont** — apply via `font-family` QSS rule, or pre-render to QPixmap with QPainter
2. **`QGraphicsDropShadowEffect` rasterizes children** — sibling overlap pattern avoids ghost outlines (Polaroid)
3. **Hover Enter/Leave flickers on overlapping siblings** — use timer-based geometry polling (60-80ms)
4. **`QTimer.singleShot(0, ...)` from worker thread silently no-ops** — fires on calling thread. Use `pyqtSignal` (auto-queued connection) for cross-thread results
5. **`QtFontManager` is lazy** — runs on Settings/Font panel open. Components needing custom fonts before that should call `QFontDatabase.addApplicationFont()` themselves (idempotent)
6. **App-level `eventFilter` receives events from background threads** (e.g. global keyboard hook) — wrap callback bodies in try/except + log; exception propagating to Qt's C++ side silently terminates app
7. **QSS-styled QPushButton custom paintEvent is unreliable** — `setObjectName` + cascaded QSS routes painting through `QStyleSheetStyle::drawControl`, which may paint over a subclass `paintEvent` override that called `super().paintEvent` first. Symptom: `QPainter` shapes drawn in subclass paintEvent are invisible. Fix: use a **child `QFrame` with inline `setStyleSheet`** (background-color + border-radius) as the visual element. Child widgets composite on top of the parent's QSS-painted surface and are immune to this. See `_DotIndicator` in `pyqt_ui/npc_manager_panel.py` for the working pattern.

## Win32 + Tkinter Don'ts

- **`WM_NCLBUTTONDOWN` modal resize from Tk callback** = `PyEval_RestoreThread` GIL fatal (`SendMessageW` blocks main thread inside modal loop; Tk window proc fires WM_PAINT/WM_SIZE back to NULL Python thread state)
- **`SetWindowRgn` during drag** = jank (`CreateRoundRectRgn` + redraw + `update_idletasks()` is expensive). Re-apply only at `stop_resize()`
- **`transparentcolor` is 1-bit color-key** — no alpha gradient; partial-alpha pixels render as opaque squares

## MBB.py Attribute Names

| Use | NEVER use |
|-----|-----------|
| `self.translated_logs_instance` | ~~`self.translated_logs`~~ |
| `self.settings_ui` | ~~`self.settings_panel`~~ |
| `self.info_label` → `control_panel.lbl_status_info` | — |
| `self.conversation_logger` (always-on, never None) | — |

FontPanel ref is `_font_panel` (private).

---

# C# Bridge — `DalamudMBBBridge.cs`

Single-file Dalamud plugin (1,137 lines after v1.8.13 dead-code cleanup, down from 1,903). Captures FFXIV native text via addon lifecycle hooks → enqueues `TextHookData` → named pipe → Python.

## Active handlers (8)

| Handler | Addon / Source | Event(s) registered | ChatType in Python |
|---------|---------------|--------------------|--------------------|
| `OnChatMessage` | `ChatGui.ChatMessage` (non-Talk types) | event subscription | 61 (dialogue), filtered: 27/3 (player chat) |
| `OnTerritoryChanged` | `IClientState.TerritoryChanged` | event subscription | `system` (zone-change reset) |
| `OnTalkAddonPreReceive` | `Talk` | PreRefresh | 61 |
| `OnBattleTalkAddon` | `_BattleTalk` | PreSetup + PostSetup | 68 |
| `OnTalkSubtitleAddon` | `TalkSubtitle` | PreSetup + PreRefresh | 71 |
| `OnSelectStringAddon` | `SelectString` | PostSetup + PreRefresh | 0x0045/0x0046 |
| `OnSelectIconStringAddon` | `SelectIconString` | PostSetup + PreRefresh | 0x0045/0x0046 (backup) |
| `OnCutSceneSelectStringAddon` | `CutSceneSelectString`, `_CutSceneSelectString` | PostSetup + PostRefresh | 0x0045/0x0046 (cutscene choices like "Skip cutscene?") |

Removed in v1.8.13 (dead code): `OnCutsceneDiagnostic`, `OnCutsceneAddonTest` + 2 extract helpers, `OnCutsceneAddon` (legacy), `OnChoiceAddon`, `OnChoiceAddonOld`, `OnIconChoiceAddon`, `OnUniversalAddonEvent`, `OnUniversalAddonDetector`, two `potentialCutsceneAddons` 12-element arrays with 48 spurious registrations. Don't reintroduce these — they were exploratory scaffolding that became log spam in production.

## TalkSubtitle (cutscene) — Echoglossian pattern (v1.8.12)

Unwrap AtkValues from BOTH `AddonSetupArgs` AND `AddonRefreshArgs`. Echoglossian-verified pattern:

```csharp
AtkValue* atkValuesPtr = null;
if (args is AddonSetupArgs setupArgs && setupArgs.AtkValues != null)
    atkValuesPtr = (AtkValue*)setupArgs.AtkValues;
else if (args is AddonRefreshArgs refreshArgs && refreshArgs.AtkValues != null)
    atkValuesPtr = (AtkValue*)refreshArgs.AtkValues;

if (atkValuesPtr != null
    && atkValuesPtr[0].Type == AtkValueType.String   // ← MANDATORY type check
    && atkValuesPtr[0].String.Value != null)
{
    var text = MemoryHelper.ReadSeStringAsString(
        out _, (nint)atkValuesPtr[0].String.Value);
    // ...
}
```

The FIRST cinematic line of a cutscene arrives via PreRefresh's AtkValues, not PreSetup's. Code that handles only `AddonSetupArgs` silently drops the first line of every cutscene. Reference: `TalkSubtitleHandler.cs` at https://github.com/lokinmodar/Echoglossian (NativeUI/AddonHandlers/Talk).

## Native safety (v1.8.11 game-crash incident)

`AtkValue` is a **union** type. Reading `.String.Value` when `.Type != AtkValueType.String` returns a garbage pointer → `MemoryHelper.ReadSeStringAsString` dereferences in native code → **access violation crashes the game**. C# `try/catch` does NOT catch native AVs.

Hard rules:
- **Always** `if (atkValue.Type == AtkValueType.String && atkValue.String.Value != null)` BEFORE reading.
- **Never** register `PostUpdate` / `PreDraw` for text capture — they fire every frame (60Hz+) and any per-frame heavy iteration + unsafe pointer read = instant crash. Use them ONLY for native text replacement (which we don't do at all).
- **Never** iterate text nodes `0..N` speculatively. Stick to known good IDs (TalkSubtitle = 2, 3, 4 per Echoglossian).
- Captured in memory: [[feedback-dalamud-native-safety]].

# Plugin Manifest

- `DalamudMBBBridge/` (flat — was `dalamud-plugin/DalamudMBBBridge/`)
- DLL: `DalamudMBBBridge/bin/Release/DalamudMBBBridge.dll` (`<AppendRuntimeIdentifierToOutputPath>false</...>`)
- Manifest: name **Magicite Babel Bridge**, repo URL `iarcanar/MBB_Dalamud`, `OpenMainUi` registered
- Commands: `/mbb`, `/mbb launch`, `/mbb status`, `/mbb help`
- **Build rule:** `python bump_version.py patch` MUST run BEFORE every `dotnet build -c Release` (so version + DLL mtime change visibly for deployment verification). Captured in memory: [[feedback-bump-version-every-build]].

---

# Roadmap (Deferred)

| Item | Trigger | Memory |
|------|---------|--------|
| Phase A.5 — auto cloud-sync check on startup | After Phase A release cadence validates UX | `project_cloud_npc_sync_plan.md` |
| Phase B — encryption + private repo | After paid tier strategy | same |
| Phase C — paid tier gate | After Phase B | same |
| **v1.9.0 TUI module split** — `TUI_dialog` / `TUI_battle` / `TUI_cutscene` / `TUI_choice` separate modules | If more shared-state bugs in `translated_ui.py` | `project_tui_split_plan_v190.md` |
| Phase 2 file split — `tui_fade_system` / `tui_resize_system` / `tui_auto_hide` (~1100 more lines extractable) | When ready for mixin/delegation pattern | — |
| Custom repository setup (`pluginmaster.json`) | Phase 2 of distribution | — |
| PyInstaller one-click install | Phase 3 of distribution | — |

---

# Reference

- **Landing page:** `docs/index.html` (Tailwind + glass-morphism, cinematic banner). Maintenance guide: `docs/WEBSITE_GUIDE.md`
- **Build protocol:** `BUILD_PROTOCOL.md`
- **Gemini models:** `docs/GEMINI_MODELS_GUIDE.md`
- **NPC release pipeline:** `scripts/build_npc_release.py`
- **Cloud npc data repo:** [iarcanar/MBB_NPCData](https://github.com/iarcanar/MBB_NPCData)
- **Memory (AI agent persistent notes):** `C:\Users\Welcome\.claude\projects\c--MBB-Dalamud\memory\`

---

**Older changelogs (v1.8.0 → v1.8.9 details)** live in git history:
```bash
git log --oneline CLAUDE.md      # CLAUDE.md edit history
git log --oneline -- python-app/ # general project history
git show <commit>:CLAUDE.md      # any old version of this doc
```
