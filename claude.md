# MBB Dalamud — Project Reference

**Version:** 1.8.21 · **Build:** 04032026-02
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
| **HTML manual** (derived view) | `docs/manual/` (6 pages) | Onboarding new contributors · visual reference for layout math / data flow / cloud sync (SVG diagrams + UI screenshots) · understanding new subsystems faster than reading prose · sharing the project externally |

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
3. HTML pages carry a `Snapshot derived from CLAUDE.md · last synced YYYY-MM-DD · vX.Y.Z` banner — keep it honest. Update the date in the 5 hand-maintained pages when you re-sync (find-replace). `library.html` is regenerated (its banner is auto-stamped), and its shared-CSS link is cache-busted by `manual.css` mtime — bump nothing by hand there.
4. **HTML drift risk:** if banner date lags 2+ versions, treat HTML as suspect; trust this file.

**HTML file inventory** (`docs/manual/`):
- `index.html` — overview, project structure, data flow SVG, ChatType routing, build pipeline
- `ui.html` — Main Window layout math, Mini UI, TUI dialog/choice, DissolveOverlay 3 dispatcher rules, Translated Logs, Glass Mode
- `npc-translation.html` — NPC Manager + Polaroid patterns, Cloud Sync flow, Translation engine, 3-layer name preservation, Wide-context, NPC database
- `styling.html` — Theme system (12 palettes), Font dual storage, Settings, Splash, Updater
- `reference.html` — Gemini models (3-model matrix, re-synced v1.8.21), test messages, Hard-Won Rules, plugin manifest, roadmap
- `library.html` — **Asset / Visual Library (new v1.8.21)** — categorised gallery of every real project asset (SVG icons · PNG UI icons · status · brand/art · fonts · NPC avatars). **Auto-generated** by `scripts/gen_asset_library.py` (scans `python-app/assets`, `assets/icons`, `fonts`, `npc_images`); re-run it instead of hand-editing. Served from repo root so it can reference `python-app/…`.
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

## Pipeline Hardening (v1.8.19 — FLOWFIX_1-8)

Full pipeline audit batch, 2026-06-10. Every change carries a `FLOWFIX_n` marker comment with a REVERT note — `grep -rn FLOWFIX_` to locate all sites. Details live in each subsystem's section; this is the index:

| # | Fix | Where |
|---|-----|-------|
| 1 | Error results ("⚠…") are NOT cached and NOT fed into wide-context — a transient API blip no longer poisons a line for the whole session, nor leaks error text into future prompts. Still displayed. | `dalamud_immediate_handler.py` |
| 2 | `translate_choice()` API calls (block + per-choice fallback) get `timeout=30` + full generation/safety config — a hung choice request was leaking its thread AND the pre-flight `_choice_overlay_active` flag (TUI hidden forever). | `translator_gemini.py` |
| 3 | Per-surface display ordering: monotonic `_msg_seq` per arrival; a slow OLD result completing after a NEWER one is dropped (`[SEQ-SKIP]` log) instead of overwriting it. Surfaces tracked separately (tui / dissolve / choice) so cross-surface lines never suppress each other. Stale-skip returns True (the newer message owns the overlay flag — rolling back would re-trigger the v1.8.10 flash bug). | `dalamud_immediate_handler.py` |
| 4 | C#: `OnChatMessage` allowlist {61,68,71,70} · queue cap 200 (drop-oldest) · sliding dedup window · hot-path logs demoted | `DalamudMBBBridge.cs` |
| 5 | C#: `OnSelectIconStringAddon` ChatType `0x0047`→`0x0046` (icon choices were landing on the cutscene overlay) | `DalamudMBBBridge.cs` |
| 6 | Battle overlay position FORCED every show: x centered, y = 15% screen height (heals stale saved positions) | `pyqt_ui/dissolve_overlay.py` |
| 7 | Dialogue keep-alive at translation START — closes the ~1s window where auto-fade/hide blanked the TUI mid-translation | handler + `translated_ui.py` |
| 8 | Overlay chain-memory (`_tk_was_visible_before_*`) preservation, 4 guards (8a-d) — rapid mode switching no longer leaves the dialog TUI invisible | handler + `translated_ui.py` |

**Deferred from the same audit** (quality-path, need dedicated translation testing): retry doesn't raise `max_output_tokens` on truncation · API-fallback path skips name-restoration layers · nested-bracket marking (`[[Y'shtola] Rhul]`) when first+full names both match · WMI process-check on the ImGui draw thread.

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

# PyQt6 TUI Migration (Mini UI + Dialogue) — 2026-06-18

Mini UI and the dialogue TUI were rewritten Tkinter → PyQt6 (the dialogue's whole
point: a **feathered/diffuse background** — Tk's 1-bit `transparentcolor` can't do
per-pixel alpha). New files:

| File | Role |
|------|------|
| `mini_ui_qt.py` | PyQt6 Mini UI — **default-on, in-place** (MBB.py imports it; Tk `mini_ui.py` kept only for git-revert) |
| `pyqt_ui/translated_ui_qt.py` | PyQt6 dialogue TUI (`TranslatedUIQt`) — **opt-in behind a feature flag**; Tk `translated_ui.py` stays the default |
| `pyqt_ui/tk_compat.py` | `TkWindowShim` — a Tk-method shim over a QWidget, shared by both |

## Feature flag — dialogue backend
MBB.py construction (~line 3263) branches on:
```python
_use_qt_dialogue = (os.environ.get("MBB_QT_DIALOGUE") == "1"
                    or bool(self.settings.get("use_qt_dialogue", False)))
```
- **OFF (default):** legacy Tk `Translated_UI` (unchanged — safe revert).
- **ON:** `TranslatedUIQt`; `self.translated_ui_window` = `translated_ui.root` (a `TkWindowShim`) so MBB's ~20 direct Tk calls on that window keep working untouched. `_ui_args`/`_ui_kwargs` are shared by both branches.
Test a session: launch with `MBB_QT_DIALOGUE=1`. Persist: `use_qt_dialogue: true` in settings. Standalone preview: `python pyqt_ui/translated_ui_qt.py` (has a sys.path bootstrap).

## `tk_compat.py` — `TkWindowShim`
Plain **wrapper** over a QWidget (NOT a QWidget mixin — a Tk-style `geometry()`
would clash with `QWidget.geometry()`). Implements ONLY the Tk methods MBB.py
calls: `winfo_exists / state / withdraw / deiconify / lift / geometry (read+write)
/ attributes("-topmost") / winfo_x/y/width/height / winfo_children / destroy /
update_idletasks`. `state()` returns "normal"/"withdrawn" from `isVisible()`.
Used as Mini UI's `.mini_ui` and the dialogue's `.root`.

## What the Qt dialogue ports
- **Feathered diffuse bg** (cached pixmap; stacked rounded-rects, ease-in alpha
  ramp). Tunables: `FEATHER_PX=30`, `EDGE_FALLOFF=1.8`, `BG_RADIUS=16`.
- **Rich text reuses Tk `RichTextFormatter`** (Tk-free) → identical segmentation;
  rendered via `QTextDocument` (Thai wrap + per-segment HTML: italic=FC Minimal,
  `**highlight**`=#FFB366, name=cyan/purple).
- **Typewriter matches Tk `type_writer_effect`** — batch 5 Thai / 4 long / 3
  default at `TYPE_BASE_MS=15` + punctuation pauses (NOT the slow 50ms
  `_continue_typing_animation`). ⚠️ if it feels slow it regressed to 1 char/tick.
- **Speaker name + tapered dissolving underline** (centred on the name, clamped
  in-bounds). Tunables: `NAME_LINE_TAPER=0.44`, `NAME_LINE_EXTRA_CHARS=4`,
  `NAME_LINE_ALPHA=130`.
- **Hover icon rail** (close/lock/color/fadeout/log) — same PNG icons as Tk:
  - **Lock 3-mode** (circular): `normal.png` bg+drag · `lock.png` hide-bg (text +
    painted dark outline) + locked · `BG_lock.png` bg + locked.
  - **Colour/transparency modal** (`_ColorAlphaModal`): step-lock **50/80/92/100%**
    + bg-colour pick, live + saved.
  - **Fade-out + auto-hide** (10s idle → fade → hide; fadeout button toggles +
    toast). Logs `[TUIQT] auto-hide ...`.
  - **log button** → `main_app.toggle_translated_logs()` (NOT `toggle_ui`, which
    swaps Main/Mini — a bug that bit during P5).
  - **Click the speaker name** → `toggle_npc_manager_callback(name)`.
- **Dispatcher + FLOWFIX_8 chain-memory** in `_dispatch` (a `pyqtSignal` slot, so
  the translator thread's `update_text` marshals onto the UI thread): 68/71 →
  dissolve, 70/pipe → choice, 61 → dialogue; exits the active overlay on
  switch-back. `self.hide()/show()` replace `root.withdraw()/deiconify()`; the
  `_tk_was_visible_before_*` memory survives overlay→overlay chains so the
  dialogue restores every time. Verified by a full mode-switch matrix.

## Status / enabling / revert
Mini UI shipped (default). Dialogue behind the flag — **production-tested in the
real app 2026-06-18 (user-confirmed working)**; real-FFXIV-game text capture still
pending. **Enable:** `MBB_QT_DIALOGUE=1` (session) or `use_qt_dialogue: true` in
settings.json (persistent — settings.json is **gitignored**, so the **repo default
stays Tk**). **Revert:** `use_qt_dialogue: false`. **A packaged exe needs a rebuild
to include the migration** (the changes live in the dev source; an old
`dist_test/MBB.exe` won't have them). **Deferred:** remove the 16ms `tk_poll_timer`
(MBB.py:7076-7078) once the flag is default AND Mini UI is Qt (only the transient
splash stays Tk); ui_capture mini recipe tk→qt.

---

# Mini UI — `mini_ui.py` → now PyQt6 (`mini_ui_qt.py`)

> **Migrated to PyQt6 (2026-06-18, default-on).** `mini_ui_qt.py` is what MBB.py
> imports now (see the PyQt6 TUI Migration section above). The Tk details below
> describe the original `mini_ui.py`, kept only for git-revert — the Qt version
> replaces the Win32 corners with a `paintEvent`, monitor-detect with
> `QGuiApplication.screenAt`, and destroy-rebuild theming with a live re-theme.

Tkinter Toplevel, 50×176, frameless (`overrideredirect`), always-on-top.
Snapped to left edge of screen, vertically aligned with main window.

**Asymmetric rounded corners (Win32):** `CreateRoundRectRgn` with ellipse=10 (~5px) → right side rounded, left side flush with screen edge.

> Don't increase corner radius — region clipping cuts highlight border at top-right/bottom-right.

**Highlight border:** flashes white 1.2s on show (`highlightthickness=2 #e0e0e0` → `1 #2a2a2a`).

**Theme change:** destroy + rebuild (Tkinter color baking). Snapshot/restore position around rebuild.

**Light theme:** white-line icons auto-invert via PIL `_invert_rgb_keep_alpha()` + luminance check.

---

# TUI — Dialog & Choice Mode (Tkinter, `translated_ui.py`)

> **A PyQt6 alternative exists** (`pyqt_ui/translated_ui_qt.py`, opt-in via the
> `MBB_QT_DIALOGUE` flag — see the PyQt6 TUI Migration section above). This
> section documents the **default** Tk renderer.

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
| Battle | center (**forced** every show) | `round(sh × 0.15)` (**forced** every show — FLOWFIX_6 v1.8.19, see DissolveOverlay section) |
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

## Battle Position — forced top 15% (v1.8.19, FLOWFIX_6)

`show_for_mode("battle")` **overrides** saved `tui_positions["battle"]` every show: `x` centered, `y = geo.y() + int(screen_h × BATTLE_TOP_FRACTION)` (= 0.15). Saved **size** stays user-tunable.

Rationale: a stale/corrupted saved position (real incident — battle saved at screen-center by an old spurious save) silently overrode the sensible near-top default, which only applied when NO saved value existed. Forcing on every show self-heals bad saved values and scales across resolutions. Same pattern as the cutscene width force above.

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

**Fix:** in `dalamud_immediate_handler.py` `process_message`, right before `thread.start()` (after all early-return gates + cache check), if `chat_type ∈ {68, 71, 70}` — pre-flight:

1. Set `translated_ui._dissolve_active = True` synchronously on the bridge thread (atomic Python attribute write — GIL covers it).
2. Schedule `ui.root.withdraw()` on the Tk main thread via `safe_after(0, ...)`. The withdraw callback also sets `_tk_was_visible_before_dissolve` based on actual `root.state()`.
3. Mark `was_pre_flighted = True` in the outer closure so the thread's `finally` block can reset on failure.

**Cleanup (in thread `finally`):**
- If `was_pre_flighted` AND `_translation_displayed=False` (`_show_immediately` was never called), reset `_dissolve_active=False`. Otherwise a translation failure leaves TUI hidden forever — next dialogue's auto-show stays blocked.

**Placement notes:** pre-flight must be AFTER all early returns (cache hit calls `_show_immediately` synchronously; "already translating" defers to the in-flight thread). Pre-flighting before those would leak `_dissolve_active=True` without a thread to clean up.

**v1.8.18 — extended to choice (ChatType 70):** the pre-flight block is now generalized over `{68, 71, 70}`. For 70 it arms `_choice_overlay_active` (not `_dissolve_active`) and the withdraw callback sets `_tk_was_visible_before_choice` (the choice overlay's own restore flag — distinct from dissolve's `_tk_was_visible_before_dissolve`); the `finally` cleanup resets whichever flag was armed via a `_preflight_flag` variable. Without it the first choice flashed stale dialogue for ~1s exactly like battle/cutscene did pre-v1.8.10. 68/71 behaviour is byte-identical to before.

**v1.8.19 — chain-memory rule (FLOWFIX_8) — CRITICAL:** `_tk_was_visible_before_*` is the ONLY memory deciding whether the Tk root comes back when overlays exit. **Never write `False` to it while another overlay already owns the withdrawn root.** Real incident: rapid battle→cutscene→choice switching — each later pre-flight saw the root "already withdrawn" (hidden by the PREVIOUS overlay) and clobbered the memory to False → the next dialogue rendered into a withdrawn window (invisible until manual TUI button). Four guards now enforce this (all marked `FLOWFIX_8a-d`, grep-able):
- **8a** handler pre-flight: captures `_overlay_was_active` BEFORE arming its flag; the withdraw callback writes `False` only when NO chain was active (root hidden by the user, not by an overlay).
- **8b/8c** both dispatcher routes capture `_chain_owned_root` at entry; their "already withdrawn → mark False" branches preserve the memory when chain-owned. 8c also re-withdraws when the root is `normal` even if `_choice_overlay_active` was pre-armed (dissolve→choice transition: `_exit_dissolve_overlay` deiconifies AFTER the pre-flight withdraw ran).
- **8d** safety net in `show_tui_on_new_translation`: deiconifies on REAL window state (`root.state() != "normal"`), not just `is_window_hidden` — gated to fire only for non-overlay messages with no overlay active (choice/battle/cutscene types pass through it before routing).

**v1.8.19 — dialogue keep-alive (FLOWFIX_7):** the TUI's 3-layer fade-race defense cancels timers at DISPLAY time (`update_text`) — leaving the ~1s translation window unprotected: a 10s auto-fade/hide firing mid-translation blanked the dialog until the result arrived ("dialog vanishes for a moment"). The handler now schedules `translated_ui.keep_alive_for_incoming()` on the Tk thread the moment a ChatType-61 translation thread starts (same placement as the overlay pre-flight — only when a thread will actually run; cache hits have no race window). It cancels fade/hide timers + bumps activity + restores alpha if mid-fade, but never deiconifies a hidden window (auto-show gate stays in MBB).

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

**v1.8.18 fix:** `_open_at_tab` fills the search box with the **registry-stored** key (the matched entry's `firstName` / `name`), NOT the raw TUI name. Previously a full "First Last" TUI name that matched a first-token-only registry entry was fed to `dm.search` (forward-substring) → the row was filtered OUT → the tab switched but the list was empty and no row selected (the opposite of the intended auto-select). Passing the registry key guarantees the row re-appears so selection-by-index works.

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
- Capped at 20 (token control). **v1.8.18:** names ACTUALLY PRESENT in the line are ordered FIRST, then essentials pad to the cap. Previously the ~19 always-on essentials filled the cap and crowded out detected side-characters — a line naming 2+ non-essential NPCs lost all but one from preservation (nondeterministic, set ordering). Detected-first guarantees in-line names are never dropped.
- Essential (20): Y'shtola, Alphinaud, Alisaie, Wuk Lamat, Estinien, G'raha Tia, Thancred, Urianger, Krile, Emet-Selch, Hythlodaeus, Venat, Meteion, Zenos, Koana, Zoraal Ja, Gulool Ja, Sphene, Otis

---

# Wide-Context Translation (always-on, v1.7.8+)

Inject recent Thai translations into Gemini prompt for consistency (pronouns, honorifics, transliteration).

## Flow

```
ConversationLogger.log_message()         (always-on, in-memory)
ConversationLogger.update_translation()
        ↓
ConversationLogger.get_recent_context()  cutscene=4, dialogue=3, battle=SKIP (no context — short standalone lines)
        ↓
dalamud_immediate_handler.py
        ↓
translator_gemini.translate(conversation_context="...")
```

## get_recent_context()

- Source: `_current_conv['messages']` (same conversation)
- Uses `translated` field only (don't send EN — Gemini may copy)
- Skip if no `translated` or `chattype_group == 'other'`
- Max **50 chars** per entry (truncate at 47 + `...` — reduced from 80 to save tokens; verified in code 2026-06-10)
- `exclude_last=True` (avoid dup with "Text to translate")
- Strips dup speaker prefix
- **Pronoun memory block appended** — session-scoped `_pronoun_lock`: first detected first-person pronoun per speaker (priority list, ข้าพเจ้า before ข้า) locked + appended as `[Speakers' established pronouns — MUST keep consistent]`. Survives conversation-boundary resets, unlike the recent-dialogue window.

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

# Token Usage Tracking & Trial Limit (v1.8.19+)

Counts cumulative Gemini token usage to power a **free-trial usage cap** for distributed trial packs.

## Source of truth — real tokens, not estimates

The pre-v1.8.19 code estimated tokens via `words × 1.3`. Since `google-generativeai` **v0.8.5** exposes **`response.usage_metadata`** (`prompt_token_count` / `candidates_token_count` / `total_token_count`), `translator_gemini.py` now reads the **real** counts (matches Google billing). Word-based estimate kept ONLY as fallback if `usage_metadata` is absent (SDK change safety).

## `usage_tracker.py` — `UsageTracker`

Owned by `TranslatorGemini` (`self.usage_tracker`, created in `__init__` when `settings` present; `None` otherwise). API:
- `is_over_limit()` — `trial_limit > 0 AND total_tokens >= trial_limit`
- `remaining()` — tokens left, or `None` when unlimited
- `add(in, out, model)` — accumulate one **real** API call (ignores 0-token / cache-hit calls); debounced flush every `FLUSH_EVERY=5` calls
- `flush()` — persist to the active backend (Phase-2 secure store, else settings.json); called on debounce + `MBB.exit_program`
- `snapshot()` — dict for UI

## Counting rules (CRITICAL)

- **Cache hits are NOT counted** — they never hit Gemini. The quota guard sits AFTER the cache-return in `translate()` ([translator_gemini.py](python-app/translator_gemini.py), after both speaker/general branches) so cached lines still render even when over limit.
- Recorded at every real `generate_content`: main path (inline, also drives the token log line), retry path, fallback path, and `translate_choice` — via `self._record_usage(response)` helper (no-op if tracker off / no usage_metadata).
- Analyze methods (`analyze_translation_quality` / `analyze_custom_prompt`) are dev-only and intentionally NOT counted.

## Enforcement

When over limit, `translate()` / `translate_choice()` return `_trial_limit_message()` (Thai "ใช้โควต้าทดลองครบแล้ว…") instead of calling the API → renders on TUI like any translation.

## Persistence

Counter fields (identical in both backends): `total_tokens / input_tokens / output_tokens / total_requests / per_model / first_use_at` (+ `seq` in the secure store).
- **Primary = Phase-2 secure store** (below) when `cryptography` is available; **fallback = plaintext `settings.json["usage_stats"]`** otherwise (schema + `ensure_default_values` migration in `settings.py`, mirrors `logs_ui`).
- `trial_limit` is **not** a persisted gate value — it ALWAYS comes from the `trial_config` build constant (see Phase 2). Any `trial_limit` key left in settings.json is display-only / ignored.
- Debounced write (≤4 calls can be lost on crash — acceptable for a soft gate).

## UI — Model Panel (`pyqt_ui/model_panel.py`)

"การใช้งาน Token (Trial Usage)" card (layout details in the redesign section below): `QLabel` (used / limit / %) + `QProgressBar` (chunk green <80% / amber 80-99% / red full) + per-model breakdown line. Reads `main_app.translator.usage_tracker.snapshot()`. Refreshes on `showEvent` + 5s `QTimer` (stopped in `hideEvent`). When `trial_limit=0` shows "ใช้ไป N tokens · M ครั้ง (ไม่จำกัด)" with empty bar. Token counts abbreviated via `_fmt_tokens()`: `<1000` as-is, `1000–99999` → `12.3k`, `≥100000` → `100k` (request count keeps `,` grouping).

## Phase 2 — medium-grade anti-tamper (`secure_usage_store.py`, implemented)

For real community release. `UsageTracker` auto-selects a backend:
- **Secure (Phase 2):** used whenever `cryptography` imports (real builds). `SecureUsageStore` stores the counter as a **Fernet** blob (AES-128-CBC + HMAC-SHA256) — encrypted (number hidden) + authenticated (edits fail to verify). Key = `SHA256(embedded_app_secret + Windows MachineGuid)` → a blob from machine A can't decrypt on machine B. **Dual store**: file `%LOCALAPPDATA%/MBB_Dalamud/.usage` + registry `HKCU\Software\MBB_Dalamud\u` — deleting one heals from the other. **Anti-rollback**: monotonic `seq`, `load()` takes `max(seq)` so an old backup of one store is overridden. **Fail-closed only under an active cap**: a store exists but nothing decrypts → status `tamper`. **Tamper locks translation ONLY when `trial_limit > 0`** — `is_over_limit()` short-circuits to `False` when the cap is 0, so on a full/dev build an unreadable store (MachineGuid changed after OS reinstall, partial write, etc.) does NOT punish a legit user: it silently resets + re-seeds and keeps translating. Trial users who are genuinely locked recover via the dev reset. Empty machine → `fresh` (start 0, migrates any Phase-1 plaintext counter once).
- **Settings (Phase 1 fallback):** plaintext `settings.json` when `cryptography` absent. `trial_limit` here is STILL the build constant (NOT read from settings.json) — so breaking the crypto import to fall back can't lift the cap.

**`trial_limit` source (security-critical):** ALWAYS the build constant `usage_tracker.TRIAL_LIMIT` (0 = unlimited; set > 0 when packaging a trial) in BOTH backends — never read from an editable file, so a user can't raise their own cap. Dev-only env override `MBB_TRIAL_LIMIT` is honoured ONLY in non-frozen runs (ignored in a release exe).

**Dev reset path (REQUIRED):** MachineGuid changes on OS reinstall → both stores fail to decrypt → a legit user is falsely locked. Recover with `python secure_usage_store.py --reset` (or `SecureUsageStore().clear()`), which wipes file + registry → next launch is `fresh`.

**Untouched by Phase 2:** the translate guard + Model Panel UI — they only call `is_over_limit()/snapshot()/add()`. Swapping the backend was the whole point of Phase 1's seam.

## Trial lockdown + Model Panel redesign (`trial_config.py`)

`trial_config.py` centralizes ALL build-time trial toggles (one place to flip when packaging):
`TRIAL_PACK` (master) · `TRIAL_TOKEN_LIMIT` (read by `usage_tracker`) · `LOCK_MODEL` · `LOCK_PARAMETERS` (both default to `TRIAL_PACK`) · `FORCED_MODEL="gemini-3.1-flash-lite"` · `FORCED_PARAMS={max_tokens:500, temperature:0.8, top_p:0.9}`. Trial build = set `TRIAL_PACK=True` + `TRIAL_TOKEN_LIMIT=N`, rebuild. Added to `mbb.spec` hiddenimports.

**Model Panel** (`pyqt_ui/model_panel.py`, 420×772 — bumped to settings-panel scale in v1.8.21; card-based: API Key · Model · Parameters · Trial Usage):
- **Locked** (`LOCK_MODEL`/`LOCK_PARAMETERS`): model shown as a read-only pill (no dropdown — selection hidden); parameter sliders **stay visible but disabled** (view-only, title gets "🔒 ล็อก (แสดงอย่างเดียว)"), set to `FORCED_PARAMS` regardless of settings so the user/dev can SEE the tuned values without changing them; RESET/APPLY footer hidden only when BOTH locked. Editing (dropdown + draggable sliders + APPLY) is the dev/full build (`TRIAL_PACK=False`). `_on_apply`/`_reset_defaults`/`_load_current` guard `_model_combo is None` and read `FORCED_PARAMS` when `LOCK_PARAMETERS`.
- **`_reset_defaults` now uses `FORCED_PARAMS`** (temperature 0.8) — fixes the old inconsistency where reset wrote 0.7 but the load default was 0.8.

**v1.8.21 UI polish pass** (model panel brought up to the settings-panel scale + slider rework — user-tested 2026-06-29):
- **Scale parity:** header 44→52 / title 11→13pt / card titles 9→11pt / param labels 9→10pt / hints 8→9pt (the 8pt hints were the "too small" complaint vs the +20% settings panel); **accent-tinted hover** on every button (was a faint `bg_medium` bump); RESET/APPLY `min-width 96` + `padding 22px` (text was cramped).
- **Magnet sliders** (`_MagnetSlider` + module-level `PARAM_SPECS`): each slider runs in **step-index units** (0..n, every integer = one snap stop → inherent magnet, no custom snap logic). UI ranges are **deliberately narrower than the backend validators** (settings.py `set_api_parameters`: 100–2000 / 0.0–1.0) so a user can't drag into a quality-degrading value — Max Tokens **400–1200/step100/rec500** · Temperature **0.50–1.00/0.05/0.80** · Top P **0.80–1.00/0.05/0.90** (`rec` = recommended = `FORCED_PARAMS`). Out-of-band saved values snap into the band on load (`_real_to_idx` clamp; e.g. temp 0.3→0.5, top_p 0.5→0.8). **RESET = restore recommended** (not just "defaults").
- **Slider is FULLY self-painted** — `_MagnetSlider.paintEvent` does NOT call `super()`. Styling only a QSlider's subcontrols via QSS leaves the widget + the unstyled `::add-page` as a **default grey block** that `background: transparent` can't suppress (real incident, 2 rounds of user feedback). Self-paint draws a thin theme-blended track (`bg_deeper`) + **uniform small snap pips** (recommended pip = accent colour, SAME size as the rest — uniformity was an explicit ask) + an accent handle. Drag still works (it's in the event handlers, not paint). See PyQt6 Gotcha #8.
- **Model combo:** the selected model shows **centred + bold** via an editable-read-only `QLineEdit` (a plain QComboBox can't centre its display text); clicking the text (not just the arrow) opens the popup (`eventFilter` on the lineEdit); the down-arrow is the **chevron SVG** baked per-theme to a tinted PNG (`qt_icons.save_tinted_png` → QSS `image:url`, since QSS can't tint a raw asset itself).

**SVG icon infra** (`pyqt_ui/qt_icons.py`, new v1.8.21): `load_icon/load_pixmap(name, color)` render `assets/icons/<name>.svg` via `QSvgRenderer` → `styles.tint_pixmap()` to the theme colour (alpha preserved → opacity-0.4 sub-paths become a soft second tone), so **one asset works on every theme** — no per-theme variants. `save_tinted_png()` bakes a PNG for QSS `image:url` targets. Both return `None` on failure → callers keep their emoji-glyph fallback. Strip `style="fill:var(--fillg)"` from authored SVGs (Qt can't resolve the CSS var → blank). Icons in use: `folder`(settings open-log btn) · `reload`(settings restart menu) · `eye_open`/`eye_close`/`edit`/`save`(model API-key buttons, theme-tinted, swapped by state in `_update_key_icons`) · `chevron`(model combo arrow) · `lock`(saved, **trial-only, not wired**). Still-glyph: `⋮` settings kebab. **`PyQt6.QtSvg` must be added to `mbb.spec` hiddenimports before the next frozen build** (dev runs fine; not yet done).

**Inline API-key card** (always shown, both modes): masked key (`AIza••••3xQ` / `mask_key()`) + **eye(open/close) / edit / save SVG icons** (`pyqt_ui/qt_icons.py`, tinted to theme; emoji 👁/✎/💾 fallback) inline + green/red status dot + "เปิด Google AI Studio" link. Save → `api_key_manager.save_key()` (.env) → `MBB.reload_api_key()` → `TranslatorGemini.reload_api_key()` rebuilds the live model with the new key **without restart** (caches + usage_tracker preserved). No more startup-only key entry.

**`api_key_manager.py` refactor:** key logic extracted to module fns `get_current_key()` / `mask_key()` / `validate_format()` / `save_key()` — shared by both the startup `APIKeyDialog` and the inline editor (no dup). **`validate_format` relaxed**: Google issues non-`AIza` keys too (e.g. `AQ.…`); the old strict `AIza`-prefix check would reject valid newer keys (and falsely red-dot a working key). Now: non-empty, no whitespace, ≥20 chars. **`save_key` is atomic + non-destructive**: it preserves any other lines in `.env` (replaces only the `GEMINI_API_KEY` line, collapses duplicates) and writes via temp+`os.replace` so a mid-write crash can't truncate `.env`. The raw key is never logged — only `mask_key()` output is shown.

**Dead code purge (v1.8.19):** `model.py` (Tkinter `ModelSettings`), legacy Tkinter `translated_logs.py`, `api_manager.py`, `translation_logger.py` deleted (zero imports, verified) + their `mbb.spec` hiddenimports lines removed. Recover from git history if ever needed.

**Threat coverage (honest, from the 2026-06-04 security audit):** defeats casual resets — notepad/settings.json edits, deleting or write-blocking ONE store (the other heals), copying another machine's file (machine-bound key → fails closed). Does NOT defeat — restoring BOTH stores from an early backup, deleting BOTH (→ fresh reset), write-blocking BOTH (counter can't persist), or binary RE of the embedded secret. These are accepted at medium tier; closing them needs Phase 3 = server-side grant. Build: `cryptography` in requirements + `mbb.spec` hiddenimports; embedded secret XOR-obfuscated in `secure_usage_store.py` (`_S1`/`_S2`) — regenerate per public build if desired.

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
- **Button hover (v1.8.19+):** every button has a *visible* hover. FONT/MODEL/HOTKEY + test buttons use **accent-tinted** hover (`rgba(accent,0.16)` bg + accent border + `accent_light` text) + `:pressed` (`rgba(accent,0.30)`) — the old `bg_medium`/`border_active` hover was ~5% lightness = invisible. `accent_rgb` derived once in `_apply_theme` via `QColor(p['accent'])`.
- **Shortcuts = READ-ONLY info card (v1.8.19+), NOT buttons:** the "ปุ่มลัด" section is an info display (`#settings_shortcut_card`, subtle bg+border, visually distinct from the clickable rows above). Two rows via `_make_shortcut_info_row(label,value)` → description left + **keycap** right (`#settings_shortcut_val`: accent text, `bg_deeper` bg, thick `border-bottom` = 3D key look). Panel height bumped 624→676→**708** (708 in v1.8.21 for the test card).
  - **Labels reflect REAL behavior:** "เปิด / ปิด UI" (ALT+H → `toggle_ui`), "โชว์ / ซ่อน TUI" (F9 → `toggle_translated_ui`). F9 is NOT "start/stop translation" (that's the control-panel button) — the old "เริ่ม/หยุด" label was wrong.
  - **Live refresh:** `_refresh_shortcut_display()` updates the keycaps; `_ensure_hotkey_panel` wraps HotkeyPanel's save-callback so changing a key via HOTKEY updates the card *immediately* (not just on reopen). Default unified to `alt+h` everywhere (was mixed `alt+l`/`alt+h` across `settings.py` default_settings, settings_panel, hotkey_panel).
- **Test-injection zone = distinct dashed card (v1.8.21):** the "ทดสอบการแปลรูปแบบต่างๆ" buttons (Dialog/Battle/Cutscene/Choice) are wrapped in `#settings_test_card` — `bg_deeper` bg + **1px dashed border** + a dim caption — so the dev/test injectors read as a separate zone from the real settings above (user request "make the test zone look different"). Log-path readability: dropped the 📁 emoji + the hardcoded white-@45% inline colour → theme-aware `#settings_log_path { color: text_dim }` at 9pt (was 8pt); the open-folder button gets the **folder SVG** icon (`qt_icons`); restart menu item gets the **reload SVG** icon.

**LEGACY UI:** `settings.py` Tkinter — backend stays here; DO NOT add new toggle UI.

**Backend:** `Settings` class — `get()`, `set()`, `save_settings()`, `set_logs_settings(**kwargs)`.

## Restart App — behind ⋮ kebab (v1.8.19+)

Footer is `[APPLY (stretch)] [⋮]`. APPLY stays put; **RESTART moved into a `⋮` kebab overflow menu** to its right (`_show_more_menu` → `QMenu` item with the **reload SVG** icon + "รีสตาร์ทโปรแกรม" — 🔄 glyph fallback — hover red = destructive) — rare + destructive, tucked away to prevent misclicks (user request 2026-06-21). The old standalone `_restart_btn` was removed; countdown 3..2..1 now shows on `_status_label`, and `_more_btn` + `_apply_btn` disable during it. After countdown calls `self.main_app.restart_app()`.

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

# Splash Screen — `MBB.py` (PyQt6, migrated 2026-06-21)

**PyQt6 translucent `QWidget`** (was a Tkinter Toplevel until 2026-06-21). The migration was for a **modern feathered drop shadow**: Tk's `-transparentcolor` is a 1-bit colour key (partial-alpha pixels render as opaque squares) so a soft floating-card shadow was impossible there; Qt's `WA_TranslucentBackground` keeps per-pixel alpha. `QApplication` already exists when the splash builds (created in `__main__` before `MagicBabelApp`), so Qt is available. PIL still renders the whole frame onto an **oversized RGBA canvas** → `QPixmap` → `QLabel` on a frameless translucent `QWidget` (`FramelessWindowHint | WindowStaysOnTopHint | Tool`, same flags as the overlays).

**Visual (v1.8.19+, user request 2026-06-21):**
- **Square (sharp) edges** — rounded mask removed; image pasted straight (`canvas.paste(image, (ox, oy), image)`).
- **Modern drop shadow** — `SHADOW_PAD = 64` transparent border around the image; two stacked feathered PIL blurs (ambient blur 34/α90/Δy 14 + contact blur 16/α110/Δy 6) = Windows-11/macOS floating-card look. This is the whole reason for the Qt move.
- Image fallback chain unchanged: `assets/MBBvisual.jpg` → `.png` → `.jpeg` → `_mar26.png` → `_legacy.png` (ships `.jpg`).
- **Bottom-center group `[meteor icon] [6px gap] [version text]`** — meteor (`mbb_meteor.png`, height `max(60, font×3.7)`, cyan halo `#00e5ff` α130 + dark shadow + sharp) unchanged.
- **Version text: WHITE `#FFFFFF`, font Segoe UI Light** (`C:/Windows/Fonts/segoeuil.ttf` → Semilight → bundled Google Sans → Anuphan). Modern/thin/clean. The old cyan glow is replaced by a soft dark shadow (blur 7/α130 + blur 3/α170) for legibility on the bright sky — no glow.
- All element coords are offset by `(ox, oy) = (SHADOW_PAD, SHADOW_PAD)` (canvas is bigger than the image).

**Lifecycle:**
- `show_splash()` returns `(QWidget, None)` (was `(toplevel, photo)`); on error `(None, None)`. `_complete_startup` guards `if hasattr(self,"splash") and self.splash` + `.isVisible()`, so a failed splash skips straight to `_finish_startup_tasks`.
- **Fade-in is a blocking pump** — `for i in range(21): setWindowOpacity(i/20); self.qt_app.processEvents(); time.sleep(0.02)`. The Qt event loop isn't running yet inside `__init__`, so pump manually (mirrors the old Tk `update()`/sleep loop). Runs before `bind_events` + `tk_poll_timer` → no re-entrancy.
- **Fade-out** `_fade_splash_step`: QTimer chain → `setWindowOpacity` down → `close()` + `deleteLater()` + `self.splash = None`.
- QImage→QPixmap uses `qimg.copy()` to detach from the `tobytes()` buffer (avoids dangling-buffer).

**Splash is built BEFORE `self.settings`** (splash ~782, `Settings()` ~787), so the **`enable_starting_key_visual` toggle** ("เริ่มโปรแกรมด้วยภาพ artwork") is honoured via a **direct `json.load("settings.json")`** at the top of `show_splash` — `False` → early-return `(None, None)` + log `[splash] skipped`; missing/unreadable → default True (show). It was DEAD before v1.8.19 (the Tk version's "checked inside show_splash" comment was stale, never real code — splash always showed); re-wired + tested both ways 2026-06-21. `splash_skip_date` still has no live checkbox.

**Imports at top of MBB.py:** `from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter` (ImageTk still used by other UI — not orphaned).

**Diagnostic log:** `[splash] Loaded <path> · size=WxH · square edges · version=vX.Y.Z`

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

**4 files to update when changing the model list** (was 5 — `model.py` deleted v1.8.19):
- `settings.py` (`VALID_MODELS` + 5 default-string sites incl. `get_displayed_model` / `get_api_parameters` / build-config block)
- `pyqt_ui/model_panel.py` (`AVAILABLE_MODELS` + `_load_current` fallback + `_reset_defaults`)
- `translator_gemini.py` (default `self.model_name` 3 sites + `valid_models` list in `set_api_parameters`)
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

**v1.8.18 frozen-mode robustness** (fixes the real-world "settings don't save" / "npc.json not read" / unexplained NPC Manager crashes seen only in the packaged exe):
- **Atomic npc.json write** — `npc_data_manager.save()` writes to `npc.json.tmp` → `flush()` + `os.fsync()` → `os.replace()` (atomic on NTFS). A mid-write crash (incl. the Tk+Qt GIL fatal) can no longer leave npc.json truncated/corrupt. Timestamped backup in `backups/` still made first.
- **Loader `.get()` hardening** — `text_corrector` + `translator_gemini` `load_npc_data()` read every key via `.get(k, default)`, so an incomplete/partial npc.json degrades to an empty-but-functional state instead of raising `KeyError` → "Failed to load NPC data".
- **CWD normalization** — `os.chdir(get_app_dir())` at the very top of `MBB.py`'s `__main__` (before splash/Settings). Relative opens (`settings.json`, `font_settings.json`, logs/) resolve against the exe dir on every launch path. The Dalamud launcher already sets `WorkingDirectory`, but a direct desktop-shortcut/Explorer/script launch could leave CWD elsewhere → settings silently written to the wrong folder (= the "doesn't save via exe" symptom).
- **Stub schema fix** — `ensure_npc_file_exists()`'s default stub now matches the real schema (`main_characters/npcs/lore/character_roles/word_fixes/_game_info`); the old stub omitted keys → `KeyError` on a fresh/incomplete install.

## Version Bump

`python bump_version.py patch|minor|major|X.Y.Z` updates 8 files. **Never edit version strings by hand.**

---

# Hard-Won Rules — Critical Patterns

## Tkinter Threading

- `winfo_exists()`, `attributes()`, `update()`, `destroy()` — **main thread ONLY**
- Thread-based animation → use `root.after()` recursive chain instead
- Tkinter + PyQt6 hybrid shutdown sometimes crashes with `PyEval_RestoreThread` GIL error — known harmless
- **`keyboard` global-hotkey callbacks run on the keyboard listener thread** — touching ANY Tk/Qt widget from them is a GIL-fatal crash (NO Python traceback — the process just dies). Wrap on registration: `keyboard.add_hotkey(key, lambda: self.safe_after(0, self.handler))` — `safe_after` enqueues to `_tk_callback_queue`, drained by the 16ms `tk_poll_timer` on the main thread. **v1.8.19 incident:** `toggle_ui` (ALT+H) + `toggle_translated_ui` (F9) crashed *instantly* once `use_qt_dialogue=True` made the TUI a real Qt widget — they called widget ops cross-thread (`hide_and_stop_translation` for WASD already marshalled itself internally, so it was fine). Also v1.8.19: `toggle_ui` now just **delegates to `toggle_mini_ui()`** (the MINI-button handler) so hotkey + button never diverge — old inline `toggle_ui` used a stale `last_mini_ui_pos` and dropped the mini UI at screen-center instead of snapping left. ⚠️ Testing caveat: `keyboard.send()` / Win32 `keybd_event` **injected** keys do NOT trigger MBB's `keyboard` hook (filtered) — global hotkeys can only be verified by a **physical** keypress. Memory: [[feedback-hotkey-callback-marshal-main-thread]].

## PyQt6 Gotchas

1. **QSS overrides setFont** — apply via `font-family` QSS rule, or pre-render to QPixmap with QPainter
2. **`QGraphicsDropShadowEffect` rasterizes children** — sibling overlap pattern avoids ghost outlines (Polaroid)
3. **Hover Enter/Leave flickers on overlapping siblings** — use timer-based geometry polling (60-80ms)
4. **`QTimer.singleShot(0, ...)` from worker thread silently no-ops** — fires on calling thread. Use `pyqtSignal` (auto-queued connection) for cross-thread results
5. **`QtFontManager` is lazy** — runs on Settings/Font panel open. Components needing custom fonts before that should call `QFontDatabase.addApplicationFont()` themselves (idempotent)
6. **App-level `eventFilter` receives events from background threads** (e.g. global keyboard hook) — wrap callback bodies in try/except + log; exception propagating to Qt's C++ side silently terminates app
7. **QSS-styled QPushButton custom paintEvent is unreliable** — `setObjectName` + cascaded QSS routes painting through `QStyleSheetStyle::drawControl`, which may paint over a subclass `paintEvent` override that called `super().paintEvent` first. Symptom: `QPainter` shapes drawn in subclass paintEvent are invisible. Fix: use a **child `QFrame` with inline `setStyleSheet`** (background-color + border-radius) as the visual element. Child widgets composite on top of the parent's QSS-painted surface and are immune to this. See `_DotIndicator` in `pyqt_ui/npc_manager_panel.py` for the working pattern.
8. **A QSS-styled QSlider shows a default grey block** — when you style only a QSlider's *subcontrols* (`::groove`/`::handle`/`::sub-page`) via QSS, `QStyleSheetStyle` still draws the widget background AND any **unstyled** subcontrol (notably `::add-page`, the part after the handle) as a tall **default grey block**. `QSlider#x { background: transparent }` does **NOT** suppress it — Qt falls back to the default fill (a solid colour like `#ffff00` test *does* apply, but `transparent` specifically doesn't). Fix: **fully self-paint** — override `paintEvent` and do NOT call `super().paintEvent`; draw the track + ticks + handle yourself (geometry via `QStyleOptionSlider` + `style().subControlRect(...)` + `QStyle.sliderPositionFromValue`). Drag/keyboard still work (they live in the event handlers, not paint). Real incident (2 rounds of "still a grey block" feedback): see `_MagnetSlider` in `pyqt_ui/model_panel.py`. Memory: [[feedback-qslider-self-paint]].

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

## v1.8.19 hardening (FLOWFIX_4/5 — C# side)

- **`OnChatMessage` is now ALLOWLIST-based**: `AllowedChatTypes = {61, 68, 71, 70}` (static readonly), everything else dropped at source. Replaced the old ~70-entry denylist `HashSet` that was rebuilt on EVERY message and leaked emotes/FC/system chat to Python. Enforces the project hard rule "capture only what MBB renders". Talk (0x003D) still excluded inside (handled by the Talk addon hook).
- **Queue cap**: `EnqueueHookData()` wraps all 9 enqueue sites — drops oldest past `MaxQueuedMessages = 200`. The queue only drains while the pipe is connected; uncapped it grew for hours and blasted the whole stale backlog at Python on connect.
- **Sliding dedup window**: `IsUniqueMessage` refreshes the stored timestamp when it BLOCKS a duplicate — a persistently re-firing addon (SelectString PreRefresh while the user hovers choices >4s) no longer re-sends the same choice every ~4s. Its per-call `Log.Info` lines demoted to `Log.Debug` (framework-thread I/O during combat spam).
- **`OnSelectIconStringAddon` ChatType fixed `0x0047`→`0x0046`** (FLOWFIX_5) — icon choices were mis-routed to the cutscene DissolveOverlay instead of ChoiceOverlay.

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

**Dispose (v1.8.18 fix):** `TalkSubtitle`'s PreSetup + PreRefresh listeners MUST be unregistered in `Dispose()` — they were leaked until v1.8.18, so after a plugin reload the next cutscene fired the handler on a disposed instance → crash. Every addon listener registered in init needs a matching `Dispose()` unregister (verify the register ↔ dispose lists stay symmetric).

## Native safety (v1.8.11 game-crash incident)

`AtkValue` is a **union** type. Reading `.String.Value` when `.Type != AtkValueType.String` returns a garbage pointer → `MemoryHelper.ReadSeStringAsString` dereferences in native code → **access violation crashes the game**. C# `try/catch` does NOT catch native AVs.

Hard rules:
- **Always** `if (atkValue.Type == AtkValueType.String && atkValue.String.Value != null)` BEFORE reading — **where the addon actually reports a String type.** ⚠️ **Exception — the `Talk` addon (dialogue, 61):** at PreRefresh it hands back a *readable* String pointer at `AtkValues[0]` (message) / `[1]` (speaker), but its `.Type` is **NOT** `AtkValueType.String`. Applying the strict `== String` gate there early-returns on **every** line → all NPC dialogue silently stops being captured (v1.8.17 regression → reverted v1.8.18). `OnTalkAddonPreReceive` must **null-check the pointer only, no type gate**. TalkSubtitle (71) is the opposite (its `[0].Type` IS String → keeps the gate). The gate is for union *safety*; don't blanket-apply it to an addon whose Type field isn't String — log the real `.Type` first if unsure. Memory: [[feedback-talk-addon-no-type-guard]].
- **Never** register `PostUpdate` / `PreDraw` for text capture — they fire every frame (60Hz+) and any per-frame heavy iteration + unsafe pointer read = instant crash. Use them ONLY for native text replacement (which we don't do at all).
- **Never** iterate text nodes `0..N` speculatively. Stick to known good IDs (TalkSubtitle = 2, 3, 4 per Echoglossian).
- **Capture ONLY the addon types MBB renders** — dialogue (61), battle (68), cutscene (71), choice (70); filter everything else. The online-game hook floods messages; widening the net = disaster. Never add broad/speculative hooks without user sign-off. Memory: [[feedback-capture-only-used-types]].
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
| **Token trial — Phase 3 server-side grant** (true enforcement, resists binary RE) | Only if Phase 2 medium-tier proves insufficient | `project_token_trial_phase2_encryption.md` |
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
