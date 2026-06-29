# แผน Migration: Dialogue TUI → PyQt6

**โปรเจค:** MBB_Dalamud · `python-app/`
**เป้าหมาย:** ย้าย dialogue mode (ChatType 61) จาก Tkinter → PyQt6 ให้เป็นมาตรฐานเดียวกับ cutscene/battle และปลดล็อกพื้นหลังแบบฟุ้ง (feathered)
**สถานะ:** เอกสารวางแผน + โครงโค้ดเริ่มต้น (ยังไม่ wire เข้าโปรแกรมจริง)

---

## 1. บริบทสถาปัตยกรรม (ทำไมถึงคุ้ม)

ข้อเท็จจริงที่ตรวจจากโค้ดจริง:

- **PyQt6 เป็น event loop หลักอยู่แล้ว** — `MBB.py` รัน `QApplication` เป็น host. Tkinter ถูก embed ผ่าน `QTimer` poll `root.update()` ทุก 16ms ไม่ใช่ `mainloop()` ของ Tk เอง
- cutscene/battle = `dissolve_overlay.py` (PyQt6 native, translucent, ฟุ้งแนวนอนแล้ว)
- dialogue = Tkinter ที่ถูก Qt อุ้มไว้ — เป็นหนี้สถาปัตยกรรม จ่ายดอกทุก frame

**ผลลัพธ์ที่คาดหวังหลัง migrate:**
- ลบสะพาน Tk↔Qt (`_tk_callback_queue`, poll 16ms, จัดการ 2 window/timer system)
- พื้นหลังฟุ้งเนียนแบบ per-pixel alpha "ฟรี" (ไม่ต้อง Pillow bake / Win32 / ขอบหยัก)
- 3 mode ใช้ paint engine เดียว ปรับสไตล์ที่เดียว

---

## 2. Interface Contract (สัญญาที่ห้ามเพี้ยน)

`MBB.py` ผูกกับ dialogue ผ่าน **interface แคบ** — ถ้า class ใหม่รักษาสัญญานี้ครบ MBB.py แทบไม่ต้องแก้

### 2.1 Constructor (14 อาร์กิวเมนต์ — ต้องรับครบ)

```python
def __init__(
    self,
    root,                          # เดิม tk.Tk — ใหม่ใช้เป็น QWidget parent หรือ None
    toggle_translation,            # Callable
    stop_translation,              # Callable
    previous_dialog_callback,      # Callable
    toggle_main_ui,                # Callable
    toggle_ui,                     # Callable
    settings,                      # Settings instance
    switch_area,                   # Callable
    logging_manager,               # Any
    character_names=None,          # Optional[set]
    main_app=None,
    font_settings=None,
    toggle_npc_manager_callback=None,
    on_close_callback=None,
):
```

> หมายเหตุ `root`: เดิมเป็น `tk.Tk`. ในเวอร์ชัน Qt ให้ยอมรับพารามิเตอร์นี้ไว้ (รับ `qt_app` หรือ parent `QWidget` แทน) เพื่อไม่ต้องแก้ลำดับ args ที่ MBB.py เรียก

### 2.2 Public methods ที่ MBB.py เรียก (signature ต้องเหมือนเดิม)

| Method | Signature | หน้าที่ |
|---|---|---|
| `update_text` | `(text, is_lore_text=False, force_choice_mode=False, chat_type=61)` | แสดงข้อความแปล (หัวใจหลัก) |
| `update_font` | `(font_name)` | เปลี่ยน font family |
| `adjust_font_size` | `(size)` | เปลี่ยนขนาด font |
| `update_character_names` | `(new_names)` | อัปเดต set ชื่อตัวละคร (สีฟ้า/ม่วง) |
| `update_translation_status` | `(...)` | สถานะการแปล |
| `show_feedback_message` | `(message, bg_color, x_offset, y_offset, duration, font_size)` | toast แจ้งเตือน |
| `reset_fade_timer_for_user_activity` | `(activity_name="user_activity")` | reset fade timer |
| `handle_translation_toggle` | `(...)` | toggle แปล |
| `force_show_tui` | `()` | บังคับแสดง |
| `force_check_overflow` | `()` | เช็คข้อความล้น |
| `close_window` | `()` | ปิดหน้าต่าง |
| `clear_displayed_text` | `()` | ล้างข้อความ |

### 2.3 Attributes ที่ MBB.py เข้าถึงตรงๆ (ต้องมี)

| Attribute | เดิมเป็น | ใหม่ (Qt) |
|---|---|---|
| `.state` | `UIState` | คงไว้เหมือนเดิม |
| `.root` | `tk.Tk` | map ไปเป็น `self` (QWidget) หรือ proxy ที่มี `.deiconify/.withdraw/.winfo_*` |
| `.dissolve_overlay` | PyQt overlay | คงไว้ (ไม่แตะ) |
| `.choice_overlay` | PyQt overlay | คงไว้ (ไม่แตะ) |
| `._closing_from_f9` | bool flag | คงไว้ |
| `.previous_dialog_callback` | Callable | คงไว้ |

> **จุดเสี่ยงสูงสุด:** `.root` ถูกเรียก `.deiconify()`, `.withdraw()`, `.winfo_x/y/width/height()`, `.geometry()` จาก MBB.py และจาก dissolve_overlay เวลาสลับ mode. ทางออก: สร้าง **shim object** ที่ map คำสั่ง Tk เหล่านี้ไปเป็น Qt (`show()/hide()/x()/y()/width()/height()/move()`) — ดู §4

---

## 3. ขอบเขตงาน (วัดจากโค้ดจริง)

`translated_ui.py` = 8,359 บรรทัด แต่ส่วนมากเป็น logic ไม่ใช่ UI

| Tkinter API | จำนวนจุด | แทนด้วย |
|---|---|---|
| `root.after` / `after_cancel` | 82 | `QTimer` / `QTimer.singleShot` |
| `.winfo_*` (x/y/width/height/exists) | 136 | `.x()/.y()/.width()/.height()` + `isVisible()` |
| `.bind(...)` | 28 | Qt events / signals |
| `.pack` / `.place` | ~23 | `QVBoxLayout` / `QHBoxLayout` |
| `tk.Button/Frame/Canvas` | ~22 | `QPushButton` / `QWidget` / `paintEvent` |
| `-alpha` / `-transparentcolor` | 8 | `WA_TranslucentBackground` + paint alpha |

**ประเมินบรรทัด Qt ใหม่:** 2,000–2,500 บรรทัด

### สิ่งที่ต้อง port (dialogue มี แต่ overlay ไม่มี)

- [ ] ปุ่ม rail แนวตั้งขวา (×, lock, color picker, font, chat/log)
- [ ] drag ย้ายหน้าต่าง + จำตำแหน่งต่อ mode → **มีแม่แบบใน overlay แล้ว**
- [ ] resize handle + จำขนาด → **มีแม่แบบ `_ResizeGrip` ใน overlay**
- [ ] custom scrollbar + mouse wheel (ข้อความยาวเกิน)
- [ ] color/alpha picker (`TUI_BG.png`)
- [ ] คลิกชื่อ → เปิด NPC Manager (`toggle_npc_manager_callback`)
- [ ] name color logic (ฟ้า `#38bdf8` / ม่วง `#a855f7` ถ้ามี `?`) → logic ตรงไปตรงมา
- [ ] overflow arrow (ลูกศรล่างขวาเมื่อข้อความยาว)
- [ ] fade / dissolve → **มีแม่แบบ `QPropertyAnimation` ใน overlay**

---

## 4. กลยุทธ์: RootShim (กุญแจลดความเสี่ยง)

ปัญหาใหญ่สุดคือ `.root` ถูกเรียกด้วยคำสั่ง Tkinter จากหลายที่ (MBB.py + overlay) ตอนสลับ mode

**ทางออก:** แทนที่จะแก้ทุก call site ให้สร้าง `RootShim` — object บางๆ ที่ครอบ QWidget แล้ว map คำสั่ง Tk → Qt:

```python
class RootShim:
    """แปลคำสั่ง Tk ที่ MBB.py/overlay เรียก → Qt บน QWidget จริง"""
    def __init__(self, widget):
        self._w = widget
    def deiconify(self):  self._w.show()
    def withdraw(self):   self._w.hide()
    def winfo_x(self):    return self._w.x()
    def winfo_y(self):    return self._w.y()
    def winfo_width(self):  return self._w.width()
    def winfo_height(self): return self._w.height()
    def winfo_exists(self):  return 1 if self._w else 0
    def winfo_ismapped(self): return 1 if self._w.isVisible() else 0
    def geometry(self, spec=None):
        if spec is None:
            return f"{self._w.width()}x{self._w.height()}+{self._w.x()}+{self._w.y()}"
        # parse "WxH+X+Y" → setGeometry
    # ... ครอบเฉพาะที่ถูกเรียกจริง (ดูรายการจาก grep)
```

ทำให้ MBB.py และ dissolve_overlay **เรียก `.root.withdraw()` ได้เหมือนเดิม** โดยไม่ต้องแก้ — ลดผิวสัมผัส migration ลงมาก

---

## 5. ลำดับงาน (แนะนำทำตามนี้)

### Phase 0 — เตรียม (ทำใน VS Code)
- [ ] อ่านไฟล์ `translated_ui_qt.py` (โครงที่ให้มา) ทำความเข้าใจ skeleton
- [ ] รัน standalone demo (`__main__` block) ดูพื้นหลังฟุ้ง + drag + resize ทำงาน

### Phase 1 — Paint + Window (หัวใจฟุ้ง)
- [ ] ยืนยัน `paintEvent` วาด `QRadialGradient` ฟุ้งรอบทิศ + toggle box/diffuse ได้
- [ ] drag / resize / geometry save ผ่าน `tui_positions` + `tui_geometries` (sync กับ overlay)

### Phase 2 — Controls
- [ ] rail ปุ่มแนวตั้ง wire กับ callbacks (close/lock/color/font/log)
- [ ] color/alpha picker
- [ ] scrollbar + overflow arrow + คลิกชื่อ→NPC Manager

### Phase 3 — Integration
- [ ] ใส่ `RootShim` ครอบ
- [ ] สลับ import ใน MBB.py: `Translated_UI` → `TranslatedUIQt`
- [ ] ทดสอบสลับ mode dialogue ↔ cutscene ↔ battle ↔ choice ไป-กลับ (จุดเปราะสุด)
- [ ] ทดสอบ fade / auto-hide / previous dialog

### Phase 4 — ทำความสะอาด
- [ ] ลบ `_tk_callback_queue` + QTimer poll `root.update()` ใน MBB.py (สะพานที่ไม่ต้องใช้แล้ว)
- [ ] ลบ Tkinter imports ที่ไม่ใช้

---

## 6. จุดเสี่ยง & ข้อควรระวัง

| ความเสี่ยง | ความรุนแรง | การลด |
|---|---|---|
| สลับ mode ไป-กลับแล้ว window หาย/ค้าง | 🔴 สูง | RootShim + ทดสอบ matrix ทุกคู่ mode |
| ปุ่ม interactive เพี้ยนจากเดิม | 🟡 กลาง | dialogue คือ mode ที่ผู้ใช้แตะเยอะสุด — เทสต์ทุกปุ่ม |
| geometry keys ไม่ sync กับ overlay | 🟡 กลาง | ใช้ key เดียวกัน: `tui_positions["dialog"]`, `tui_geometries["dialog"]` |
| font rich-text (`*italic*`) | 🟢 ต่ำ | port `RichTextFormatter` ทีหลังได้ |
| timer 82 จุด แปลงตกหล่น | 🟡 กลาง | grep หา `after(` ทุกจุด แปลงทีละอัน |

---

## 7. settings keys ที่ dialogue ใช้ (ต้องอ่าน/เขียนคีย์เดิม)

```
bg_color, bg_alpha, font, font_size, typing_speed,
tui_positions, tui_geometries, tui_colors, tui_alphas,
tui_auto_hide_icons, enable_battle_chat_mode,
enable_previous_dialog
```

> mode name ของ dialogue ในคีย์เหล่านี้คือ `"dialog"` (ไม่ใช่ `"dialogue"`)

---

## 8. ไฟล์ที่ให้มาในเซสชันนี้

1. `migration_plan.md` — เอกสารนี้
2. `translated_ui_qt.py` — โครง PyQt6 TUI ใหม่ (skeleton พร้อม paint ฟุ้ง + drag + resize + rail + RootShim) รันเดี่ยวได้ด้วย `python translated_ui_qt.py`

**ทั้งสองไฟล์เป็นจุดเริ่ม ไม่ใช่ของเสร็จ** — เอาไปต่อใน VS Code ตาม Phase 1–4
