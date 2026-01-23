# UI Troubleshooting Guide - MBB Dalamud

**Version:** 1.0.0
**Date:** 2026-01-22
**Purpose:** คู่มือแก้ไขปัญหา UI ที่พบบ่อย โดยเฉพาะส่วนที่แก้ไขยาก

---

## ⚠️ ข้อควรระวัง: Game Info Label / Swap Button

### ปัญหาที่พบ
เมื่อพยายามแก้ไขความสูงของ label แสดงชื่อฐานข้อมูล ("ใช้: FFXIV") โดยการเพิ่ม padding หรือ font size **มักไม่ได้ผล** เพราะ:

1. **โครงสร้างซับซ้อน:** ไม่ใช่แค่ Label ธรรมดา แต่เป็นระบบที่ประกอบด้วย:
   - Container Frame (swap_container)
   - Border Frame (lbl_swap_border) สร้างกรอบสี
   - Label (lbl_swap) แสดงข้อความ
   - Spacer Frame เว้นระยะ
   - Button (btn_swap) ปุ่มเล็กด้านขวา

2. **การ pack() แบบ side=tk.LEFT:** วาง widget แนวนอน ทำให้ความสูงถูกควบคุมโดย widget ที่สูงที่สุด

3. **Parameter ที่ต้องตรงกัน:**
   - Label: `height=2` (จำนวนบรรทัด)
   - Button: `height=2` (ต้องเท่ากันเพื่อสมดุล)
   - Border padding: `padx=1, pady=1` (สร้างเอฟเฟกต์กรอบ)

---

### ✅ วิธีแก้ไขที่ถูกต้อง

**อย่าพยายามแก้เอง!** ให้ใช้โค้ดต้นฉบับจากโปรเจ็คเดิม:

**ที่ตั้งโค้ดต้นฉบับ:**
```
C:\Yariman_Babel\MbbDalamud_bridge\python-app\ui_components\control_panel.py
```

**Method ที่ต้องคัดลอก:**
```python
def _create_swap_button(self):
    """Create NPC data display label and swap button"""
    # ... (คัดลอกทั้งหมด 56 บรรทัด)
```

**ส่วนที่เกี่ยวข้องใน update_theme():**
```python
# Update swap label and border (lines 289-301)
if self.lbl_swap and self.lbl_swap.winfo_exists():
    # ...

# Update SWAP button (lines 322-331)
if self.btn_swap and self.btn_swap.winfo_exists():
    # ...
```

---

### 🔧 Parameters สำคัญที่ควบคุมรูปทรง

```python
# Label แสดงชื่อฐานข้อมูล
self.lbl_swap = tk.Label(
    border_frame,
    text="ใช้: FFXIV",
    font=("Nasalization Rg", 9, "bold"),  # ← ขนาดฟอนต์
    width=19,                              # ← ความกว้าง (ตัวอักษร)
    height=2,                              # ← ความสูง (บรรทัด) **สำคัญ!**
    anchor="center",
    justify="center"
)
self.lbl_swap.pack(padx=1, pady=1)  # ← padding สร้างกรอบ

# ปุ่มเล็ก
self.btn_swap = self.button_factory.create_button(
    swap_container,
    text="⇄",
    width=3,
    height=2  # ← ต้องเท่ากับ label!
)
```

**หากต้องการเปลี่ยนความสูง:**
1. เปลี่ยน `height=2` เป็น `height=3` ใน **ทั้ง label และ button**
2. ทดสอบทันทีว่ารูปทรงสมดุลหรือไม่
3. ปรับ `font size` และ `pady` container ถ้าจำเป็น

---

### 🚫 สิ่งที่ไม่ควรทำ

❌ **อย่าสร้าง Label ใหม่แทน** - จะทำให้สูญเสียโครงสร้างกรอบสี
❌ **อย่าเปลี่ยนเฉพาะ padding** - ไม่มีผล ต้องเปลี่ยน `height` parameter
❌ **อย่าใช้ Frame height** - ทำให้ยุ่งยากและไม่ flexible
❌ **อย่าลืม border frame** - ไม่งั้นไม่มีกรอบสี magenta

---

### 📋 Checklist การแก้ไข

ก่อนแก้ไข UI ส่วนนี้ ให้ตรวจสอบ:

- [ ] อ่านโค้ดต้นฉบับจากโปรเจ็คเดิมก่อน
- [ ] เข้าใจโครงสร้าง: Container → Border → Label + Spacer + Button
- [ ] ตรวจสอบว่า height ของ label และ button เท่ากัน
- [ ] ทดสอบบนหน้าจอจริง (ไม่ใช่แค่ดู log)
- [ ] ตรวจสอบ theme updates (magenta color, border)

---

## 🎨 โครงสร้าง UI ที่ถูกต้อง

```
swap_container (Frame, bg=transparent)
├── border_frame (Frame, bg=magenta, highlightbackground=magenta)
│   └── lbl_swap (Label, width=19, height=2, "ใช้: FFXIV")
│       └── padx=1, pady=1 (สร้างกรอบสี)
├── spacer (Frame, width=5)
└── btn_swap (Button, width=3, height=2, "⇄")
```

**Visual:**
```
┌───────────────────────┐ ← swap_container
│ ┌──────────────────┐  │
│ │┌────────────────┐│  │ ← border_frame (magenta)
│ ││                ││  │
│ ││  ใช้: FFXIV    ││ [⇄] ← btn_swap
│ ││                ││  │
│ │└────────────────┘│  │ ← lbl_swap
│ └──────────────────┘  │
└───────────────────────┘
```

---

## 🔍 วิธีดีบัก

### ถ้า Label สูงไม่พอ:
1. ตรวจสอบ `height=2` ใน Label
2. ตรวจสอบ `height=2` ใน Button (ต้องเท่ากัน!)
3. ตรวจสอบ font size (ควรเป็น 9pt)
4. ดู pady ของ container (ค่าเริ่มต้น: 3)

### ถ้า Label สูงเกินไป:
1. ลด height เหลือ 1 (แต่ไม่แนะนำ)
2. ลด font size
3. ลด pady ของ container

### ถ้ากรอบสีหาย:
1. ตรวจสอบ `border_frame` ถูกสร้างหรือไม่
2. ตรวจสอบ `bg=magenta_color, highlightbackground=magenta_color`
3. ตรวจสอบ `padx=1, pady=1` ใน label.pack()

### ถ้าปุ่มไม่อยู่ด้านขวา:
1. ตรวจสอบ `side=tk.LEFT` ใน button.pack()
2. ตรวจสอบ spacer frame อยู่ระหว่าง label และ button
3. ตรวจสอบลำดับ pack: border_frame → spacer → button

---

## 📝 ตัวอย่างโค้ดที่ถูกต้อง (Minimal)

```python
def _create_swap_button(self):
    bg_color = self.appearance.bg_color

    # 1. Container
    swap_container = tk.Frame(self.frame, bg=bg_color, bd=0, highlightthickness=0)
    swap_container.pack(pady=3, anchor="center")

    # 2. Border frame (สร้างกรอบสี)
    magenta = self.appearance.get_theme_color("secondary", "#FF00FF")
    border_frame = tk.Frame(
        swap_container, bg=magenta, bd=0,
        highlightthickness=1, highlightbackground=magenta, highlightcolor=magenta
    )
    border_frame.pack(side=tk.LEFT)

    # 3. Label แสดงชื่อ
    self.lbl_swap = tk.Label(
        border_frame, text="ใช้: FFXIV",
        font=("Nasalization Rg", 9, "bold"),
        fg=magenta, bg="#0a0a0f", relief="flat", bd=0,
        width=19, height=2, anchor="center", justify="center"
    )
    self.lbl_swap.pack(padx=1, pady=1)  # สร้างกรอบ

    # 4. Spacer
    spacer = tk.Frame(swap_container, bg=bg_color, width=5)
    spacer.pack(side=tk.LEFT)

    # 5. ปุ่มเล็ก
    self.btn_swap = self.button_factory.create_button(
        swap_container, text="⇄", command=lambda: None,
        style="utility", width=3, height=2
    )
    self.btn_swap.pack(side=tk.LEFT)

    # 6. เก็บ references
    self.lbl_swap_border = border_frame
```

---

## 📚 ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | บรรทัด | จุดประสงค์ |
|------|--------|-----------|
| `ui_components/control_panel.py` | 33-36 | Widget declarations |
| `ui_components/control_panel.py` | 103-157 | `_create_swap_button()` method |
| `ui_components/control_panel.py` | 194-205 | `set_swap_text()` method |
| `ui_components/control_panel.py` | 231-244 | Theme updates (swap label) |
| `ui_components/control_panel.py` | 252-265 | Theme updates (swap button) |
| `MBB.py` | 2343-2351 | โหลดและแสดงชื่อเกม |
| `MBB.py` | 2392 | Backward compatibility reference |
| `MBB.py` | 2404-2405 | Tooltips |

---

## 🔄 Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-22 | 1.0.0 | Initial guide created after OCR cleanup |

---

## 💡 Tips

1. **เมื่อไม่แน่ใจ → อ้างอิงโค้ดเดิม** จาก `C:\Yariman_Babel\MbbDalamud_bridge`
2. **ทดสอบบนหน้าจอจริง** ไม่ใช่แค่ดู log
3. **แก้ทีละนิด** แล้วทดสอบทันที
4. **เก็บ backup** ก่อนแก้ไขโครงสร้าง UI
5. **อย่าลืม theme updates** เมื่อเพิ่ม widget ใหม่

---

**จัดทำโดย:** Claude Code
**โปรเจ็ค:** MBB Dalamud Custom Repository
**License:** MIT
