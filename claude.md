# MBB Dalamud - Custom Repository Project

## Project Information

**Version:** 1.7.8
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

**Developed by:** iarcanar
**Framework:** Dalamud Plugin + Python + Gemini AI
**License:** MIT
