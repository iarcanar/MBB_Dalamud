# MBB Website Improvement Plan

> ประเมินจากโครงสร้างเว็บปัจจุบัน (`docs/index.html`) — มีนาคม 2026

---

## สิ่งที่ทำได้ดีแล้ว

- เนื้อหาครบถ้วน — Hero, How it Works, Gallery, Features, UI Showcase, Installation, FAQ, Footer
- Flow เรียงลำดับสมเหตุสมผล คนอ่านเข้าใจว่าโปรแกรมทำอะไร ติดตั้งยังไง
- Selling points แข็ง: NPC Manager 290+ ตัว, Wide-Context, 1-sec translation

---

## สิ่งที่ปรับปรุงแล้ว

### 1. Hero Section หนักเกินไป ✅
- **ปัญหา:** มี badge, subtitle, tagline, bullet, description, CTA ยัดกันหมด
- **แก้ไข:** ลดเหลือ 1 headline ("Magicite Babel") + 1 subtitle + 1 CTA ("เริ่มใช้งาน")
- **Mobile:** จัดกึ่งกลาง (`items-center text-center`), desktop ยัง right-aligned
- **ผลลัพธ์:** whitespace เพิ่ม ดูมืออาชีพขึ้น

### 2. Screenshot Gallery → Bento Grid ✅
- **ปัญหา:** Carousel engagement ต่ำ
- **แก้ไข:** เปลี่ยนเป็น 3-col bento grid (2 รูปใหญ่ span 2 cols + 5 รูปปกติ)
- **Caption style:** Frosted glass pill badge (`backdrop-filter: blur(12px)`) + indigo dot indicator — สีเดียวกันทุกรูป (`#c7d2fe`)
- **เดิม:** gradient overlay + สีต่างกัน (cyan/yellow/purple/emerald) — กระจัดกระจาย

### 3. Feature Cards → 2 Tier ✅
- **ปัญหา:** 8 ฟีเจอร์เรียงแบบ flat
- **แก้ไข:** 3 primary large cards (Text Hook, NPC Manager, Wide-Context) + 5 secondary compact cards
- **ผลลัพธ์:** visual hierarchy ชัดเจน สื่อว่าอะไรสำคัญที่สุด

### 4. Installation → Accordion Stepper ✅
- **ปัญหา:** 4 ขั้นตอนเปิดหมด หน้ายาวมาก
- **แก้ไข:** Accordion stepper — คลิก header เปิดทีละขั้น
- **CSS:** `max-height` transition, chevron rotate, step-num scale effect
- **JS:** `toggleStep()` — เปิดขั้นที่คลิก ปิดขั้นอื่น, Step 1 เปิดเริ่มต้น

### 5. Typography & Spacing ✅
- **แก้ไข:** Noto Sans Thai (body) + Kanit (headings), `line-height: 1.75` body, `1.2` headings
- **ผลลัพธ์:** ข้อความไทยอ่านง่ายขึ้น ไม่แน่นเกินไป

### 6. CTA รวมให้ชัดเจน ✅
- **แก้ไข:** CTA หลัก "เริ่มใช้งาน" ทั้ง Hero และ Download section → ลิงก์ไป `#install`
- **เดิม:** "ติดตั้งเลย", "ดาวน์โหลด" กระจายหลายจุด

### 7. Color Palette ✅
- **ตรวจสอบ:** สีที่ใช้มี semantic meaning ชัดเจน — indigo (primary), emerald (success), yellow (warning)
- **ผลลัพธ์:** คงไว้ตามเดิม ไม่ลดเหลือสีเดียว เพราะแต่ละสีสื่อความหมายต่างกัน

### 8. Mobile Responsiveness ✅ (partial)
- **Hero:** centered text+CTA บน mobile, right-aligned บน desktop
- **How it Works:** 5 steps แนวตั้ง → compact 2x2 grid + 1 centered, ไม่มีลูกศร
- **Stats:** ลดขนาด font+padding, ซ่อน sub-text บน mobile
- **UI image:** ลบ offset `right:-20px` บน mobile

### 9. Gemini Model Reference ✅
- อัพเดตทุกจุดจาก "Gemini 2.0 Flash" → **"Gemini 3.1 Flash Lite"**
- Hero subtitle, Feature card, Installation Step 4, FAQ 2 จุด
- คงชื่อ "Gemini AI" / "Gemini API Key" ไว้ (ชื่อ service ไม่ใช่ชื่อ model)

---

## สิ่งที่ยังไม่ได้ทำ

### Demo Video
- **สถานะ:** ยังไม่มี video
- **แผน:** Embedded video สั้น 30-60 วินาที โชว์การทำงานจริง วางไว้ใต้ Hero
- **Priority:** สูง — ภาพเคลื่อนไหวขายได้ดีกว่า screenshot

### Social Proof
- **สถานะ:** ยังไม่มี
- **แผน:** GitHub badge + stars count + community link
- **Priority:** ปานกลาง

### Mobile Responsiveness (เหลือ)
- **สถานะ:** แก้ไข Hero, How it Works, Stats แล้ว
- **เหลือ:** ตรวจ Gallery grid, Feature cards, UI Showcase, Installation accordion, Download section บน mobile
- **Priority:** ปานกลาง

---

## สรุปการเปลี่ยนแปลง CSS/JS ที่เพิ่ม

| Component | CSS Class | หน้าที่ |
|-----------|-----------|--------|
| Gallery badge | `.gallery-badge`, `.badge-dot` | Frosted glass pill caption ที่มุมล่างซ้ายรูป |
| Accordion | `.accordion-step`, `.accordion-header`, `.accordion-body` | Stepper เปิด/ปิดทีละขั้น |
| Compact flow | `.flow-step-compact` | 2x2 grid flow diagram สำหรับ mobile |
| Hero UI image | `.hero-ui-img` | Responsive offset (desktop only) |

| JS Function | หน้าที่ |
|-------------|--------|
| `toggleStep(headerEl)` | เปิด/ปิด accordion step |

---

*สร้าง: มีนาคม 2026*
*อัพเดตล่าสุด: มีนาคม 2026*
*สถานะ: ดำเนินการแล้วส่วนใหญ่ — เหลือ demo video, social proof, mobile check ส่วนที่เหลือ*
