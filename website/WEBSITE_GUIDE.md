# Magicite Babel — Dalamud Edition: Website Development Guide

**Version:** 2.0
**Website Version:** v1.7.8
**Last Updated:** 2026-03-06
**File:** `website/index.html` (single-file, self-contained)

---

## 1. Technology Stack

| Technology | Source | Usage |
|-----------|--------|-------|
| **Tailwind CSS** | CDN (cdn.tailwindcss.com) | Layout, spacing, colors |
| **Lucide Icons** | CDN (cdn.jsdelivr.net/npm/lucide@latest) | All icons sitewide |
| **Google Fonts: Kanit** | fonts.googleapis.com | Primary Thai + English font |
| **Cloudinary** | res.cloudinary.com/docoo51xb | All image hosting |
| **Vanilla JS** | ES6+ | Slideshow, modal, glitch, compare toggle, nav buttons |

> **No build tools.** Open `index.html` directly in browser to preview.
> `lucide.createIcons()` must be called after DOM ready to render SVG icons.

---

## 2. Design System

### 2.1 Color Palette

| Role | Value | Usage |
|------|-------|-------|
| Body BG | `#060d1a` | Main background |
| Hero gradient | `135deg, #0f1b47 → #1e1745` | Hero + alternating sections |
| Dark section | `.dark-section` class | Alternating sections |
| Indigo primary | `#6366f1` / `rgba(99,102,241,x)` | Buttons, active states, glows |
| Purple accent | `#8b5cf6` | Secondary gradients |
| Cyan accent | `#38bdf8` | TUI speaker name color |
| Text primary | `#e2e8f0` | Body text |
| Text dim | `rgba(148,163,184,x)` | Captions, secondary |
| Glass white | `rgba(255,255,255,0.07)` | Glass panel backgrounds |

### 2.2 Typography System

| Class | Style | Usage |
|-------|-------|-------|
| `.eyebrow` | `0.68rem, weight 600, tracking 0.22em, uppercase, #818cf8` | Section micro-label above h2/h3 |
| `.grad-text` | `linear-gradient(135deg, #a5b4fc, #818cf8)` → `-webkit-background-clip: text` | Gradient keyword in headings |
| `.hero-tag` | Pill badge, `rgba(255,255,255,0.04)`, 0.72rem | Feature tags in hero section |
| **H2 sections** | `text-3xl md:text-4xl font-bold .section-title text-white` | Section headings |
| **H3 hero text** | `text-2xl md:text-3xl font-bold text-white` | Card/block headings |
| **Body** | Kanit 300-400, `text-gray-300`, `leading-relaxed` | Descriptions |
| **Captions** | `text-xs`, `text-gray-400` | Sub-labels, notes |

**Pattern for section headings:**
```html
<p class="eyebrow text-center">Subtitle · Context</p>
<h2 class="text-3xl md:text-4xl font-bold text-center section-title text-white">
    คำ<span class="grad-text">เด่น</span>
</h2>
```

### 2.3 Glass Morphism Classes

| Class | Style | Usage |
|-------|-------|-------|
| `.glass-panel` | `backdrop-filter:blur(16px)`, `rgba(255,255,255,0.07→0.02)` gradient, border `rgba(255,255,255,0.11)` | Section containers, installation steps |
| `.glass-inner` | `rgba(255,255,255,0.05)`, border `rgba(255,255,255,0.08)` | Sub-cards inside glass-panel |
| `.glass-inner-purple` | `rgba(139,92,246,0.1)`, border `rgba(139,92,246,0.2)` | Purple-tinted sub-cards |
| `.card` | Same as glass-panel + `hover:translateY(-4px)` + glow | Feature grid cards |

### 2.4 Image Hover System

**No border frames** — images have transparent backgrounds.

```css
.image-container { position: relative; overflow: hidden; }
.image-container:hover { filter: drop-shadow(0 0 18px rgba(99,102,241,0.35)); }
/* drop-shadow() traces actual PNG shape, not bounding box */

/* Cyber scan-line sweep on hover */
.image-container::after {
    content: ''; position: absolute; top: -110%; ...
    background: linear-gradient(to bottom, transparent, rgba(99,102,241,0.09), ...);
}
.image-container:hover::after { top: 155%; }
```

### 2.5 Feature Icon Circles

```css
.feature-icon { border-radius:50%; width:52px; height:52px; backdrop-filter:blur(8px); }
.feature-icon.hook   { background: indigo gradient;  box-shadow: indigo glow }
.feature-icon.npc    { background: violet gradient }
.feature-icon.context { background: blue gradient }
.feature-icon.glass  { background: cyan gradient }
.feature-icon.speed  { background: amber gradient }
.feature-icon.install { background: pink gradient }
.feature-icon.zone   { background: red gradient }
.feature-icon.log    { background: teal gradient }
```

---

## 3. Page Structure (Section Order)

| # | Section | Background | Key Content |
|---|---------|-----------|-------------|
| 1 | Cinematic Banner | `#060d1a` | Full-width banner + logo + glitch effect |
| 2 | Hero | `hero-gradient` | 2-col: text left (right-aligned) + UI composite image right |
| 3 | Stats bar | `dark-section` | 4 stat cards: < 1s, Text Hook, 290+, 1-Click |
| 4 | How It Works | `hero-gradient` | Flow diagram (Dalamud→Hook→Gemini→TUI) |
| 5 | Slideshow | `dark-section` | 6-slide gallery + glass tab bar with Lucide icons |
| 6 | Features Grid | `dark-section` | 8 feature cards (2→3 col grid) |
| 7 | UI Showcase | `hero-gradient` | Unified glass-panel: Main/TUI/LOG/NPC/Settings |
| 8 | Installation | `dark-section` | Unified glass-panel: 4 steps with dividers |
| 9 | Download + Requirements | `hero-gradient` | System requirements + download CTA |
| 10 | Legal / FAQ | `dark-section` | Disclaimer + FAQ |
| 11 | Footer | `bg-slate-900` | Links + copyright + Discord |

---

## 4. Hero Section

**Layout:** 2-column `lg:flex-row`
- **Left** (`lg:w-1/2`, `items-end text-right`): eyebrow, h1 (`clamp(3rem,7vw,5.5rem)`), `.grad-text` on "Babel", `.hero-tag` pills, description, CTA buttons
- **Right** (`lg:w-1/2`): UI composite image (`UI_element01_iiaw1c.png`), `position:relative; right:-20px`, `drop-shadow` filter

```html
<h1 style="font-size:clamp(3rem,7vw,5.5rem);">
    Magicite<br>
    <span style="background:linear-gradient(135deg,#a5b4fc,#818cf8);-webkit-background-clip:text;...">Babel</span>
</h1>
```

---

## 5. Unified Container Pattern

Installation and UI Showcase use **one single `glass-panel`** instead of separate floating cards.

```html
<div class="glass-panel overflow-hidden">
    <!-- Step/Block 1 -->
    <div class="p-6 md:p-10 border-b border-white/[0.055]">
        ...content...
    </div>
    <!-- Step/Block N (last — no border-b) -->
    <div class="p-6 md:p-10">
        ...content...
    </div>
</div>
```

**Border between steps:** `border-b border-white/[0.055]` (last block has no border)

---

## 6. Slideshow

**6 slides** (added Mini Mode as slide 6):

| Slide | Tab Icon | Tab Label | Content |
|-------|----------|-----------|---------|
| 1 | `message-circle` | แปล 1 | Dialogue translation |
| 2 | `message-square` | แปล 2 | Dialogue continued |
| 3 | `list-checks` | ตัวเลือก | NPC + options |
| 4 | `clapperboard` | Cutscene | Cutscene mode |
| 5 | `brain` | Context | Wide-context system |
| 6 | `sidebar-close` | Mini Mode | Mini UI auto-show/hide |

**Tab bar:** glass morphism — `backdrop-filter:blur(20px)`, pill-shaped tabs, active state `rgba(99,102,241,0.17)` + indigo border + glow

---

## 7. Interactive Components

### Compare Toggle (UI Showcase — Block 1)

```js
// MUST be defined at top of <script>, BEFORE DOMContentLoaded
function switchCompare(mode, el) {
    document.querySelectorAll('.compare-img').forEach(img => img.classList.add('hidden-img'));
    document.querySelectorAll('.compare-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('compare-' + mode).classList.remove('hidden-img');
    el.classList.add('active');
}
```

> **Critical:** If defined inside `DOMContentLoaded`, inline `onclick` cannot reach it.

### Nav Jump Buttons (Fixed bottom-right)

Two buttons (up ↑ + down ↓), glass style, appear after scroll 200px:

```js
const onScroll = () => {
    const show = window.pageYOffset > 200;
    jUp.classList.toggle('show', show);
    jDown.classList.toggle('show', show);
};
jDown.addEventListener('click', () => window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'}));
```

### Image Modal (Lightbox)

- Trigger: click any `.zoomable-image`
- Close: backdrop click, X button, Escape key

### Slideshow

- `currentSlide(n)` → sets active slide + updates `.thumbnail.active`
- Keyboard: ArrowLeft / ArrowRight

---

## 8. Image Assets (Cloudinary)

### Active in use

| Asset | URL fragment | Section |
|-------|-------------|---------|
| Banner | `v1772760917/mbb_banner01_tmaxtu.png` | Cinematic banner |
| Logo | `v1772761009/mbb_LOGO_vkk21r.png` | Banner overlay |
| Icon/Favicon | `v1772761010/mbb_icon_swlthg.png` | `<link rel="icon">` |
| UI Composite | `v1772803961/UI_element01_iiaw1c.png` | Hero right column |
| Main UI | `v1772802695/Main_ui_vxwl64.png` | UI Showcase block 1 |
| Compare Main | `v1772801199/compare_main_ui_f4xqk2.png` | Compare toggle |
| Compare Mini | `v1772801199/compare_mini_ui_rky4e9.png` | Compare toggle |
| TUI | `v1772797987/TUI_urktwy.png` | UI Showcase block 2 |
| LOG | `v1772797987/logs_history_fapgly.png` | UI Showcase block 3 |
| NPC Manager | `v1772797988/NPC_manager_rvzmmh.png` | UI Showcase block 4 |
| Settings+Font | `v1772797987/setting_and_fonts_offxss.png` | UI Showcase block 5 |
| Checkmark | `v1772807395/checkmark_wxykjt.png` | NPC Manager — green checkmark demo |
| Miqo'te icon | `v1749997680/512px_icon_wqknxl.ico` | Installation section |

### Slideshow slides (active)

| Slide | URL fragment |
|-------|-------------|
| Slide 1 | `v1772792199/slide01_dialogue_kc2iw8.png` |
| Slide 2 | `v1772792199/slide02_dialogue2_dtmmep.png` |
| Slide 3 | `v1772792199/slide03_choices_xt4wjr.png` |
| Slide 4 | `v1772792199/slide04_cutscene_f2yzwb.png` |
| Slide 5 | `v1772792199/slide05_context_hpqlm2.png` |
| Slide 6 | Pending placeholder |

### Pending Placeholders

| Name | Section | Notes |
|------|---------|-------|
| `dalamud_intro.png` | Installation step 1 | Dalamud/XIVLauncher screenshot |
| `install_step1.png` | Installation step 2 | MBB Installer window |
| `install_step2.png` | Installation step 3 | Dalamud Plugin Settings — MBB App Path |
| `install_step3.png` | Installation step 4 | MBB App with API Key field |
| Slide 6 image | Slideshow | Mini UI auto-show in game |

### Replacing a Placeholder

Find `<div class="img-placeholder">` with matching `ph-name`, replace entire div with:

```html
<div class="image-container rounded-xl overflow-hidden">
    <img src="CLOUDINARY_URL" alt="description" class="zoomable-image w-full rounded-xl shadow-lg">
</div>
```

---

## 9. NPC Manager Section — Key Features

| Feature | Description | Implementation note |
|---------|-------------|---------------------|
| Role customization | กำหนดโทนน้ำเสียงต่อตัวละคร | Before/after example box with gradient bg |
| Green checkmark | `checkmark_wxykjt.png` แสดงข้างชื่อตัวละครใน TUI | Image `width:100%` full-width in card |
| Quick add from TUI | คลิกชื่อสีฟ้าบน TUI → เปิด NPC Manager พร้อมกรอกชื่อ | Described in indigo box |
| Wide context | จำบทสนทนา 3-8 บรรทัด → สรรพนามสม่ำเสมอ | Secondary card |
| Zone Change | กดเมื่อดู cutscene ย้อนหลังไม่ต่อเนื่องกัน | เล่นเกมปกติไม่ต้องกด — auto detection |

---

## 10. Installation Section

**XIVLauncher download button:**
```html
<a href="https://github.com/goatcorp/FFXIVQuickLauncher/releases/latest/download/XIVLauncher-win-Setup.exe"
   class="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white ...">
    <i data-lucide="download" ...></i> ดาวน์โหลด XIVLauncher
</a>
```

**MBB Start behavior:** โปรแกรมเริ่มแปลอัตโนมัติทันที ไม่ต้องกด START — แค่เปิดโปรแกรม พร้อมแปลเลย

---

## 11. Version Update Checklist

เมื่ออัพเดต version (เช่น v1.7.8 → v1.8.0):

- [ ] **Banner version label** — `<span class="banner-version">v1.7.8</span>`
- [ ] **Hero subtitle** — version ใน paragraph
- [ ] **Download section** — `Magicite Babel - Dalamud v1.7.8`
- [ ] **`<title>` tag** — ถ้าระบุ version

---

## 12. Quality Gate

ก่อน publish:

- [ ] Cloudinary images โหลดทุกรูป (ไม่มี 404)
- [ ] Banner dissolve ซ้ายไม่มีขอบ
- [ ] Glitch effect ทำงาน (trigger หลัง 4-8 วินาที)
- [ ] Slideshow 6 slides + tabs ทำงาน
- [ ] Compare toggle (Main/Mini) สลับได้ — `switchCompare` อยู่ global scope
- [ ] Nav jump up/down ปรากฏหลัง scroll 200px
- [ ] Image modal เปิด-ปิดได้ (click + Escape)
- [ ] XIVLauncher download button ลิงก์ถูก
- [ ] Mobile responsive — ไม่มี horizontal scroll
- [ ] `lucide.createIcons()` ถูกเรียกหลัง DOMContentLoaded

---

## 13. Known Issues & Workarounds

| Issue | Cause | Fix |
|-------|-------|-----|
| `switchCompare` not found from onclick | Defined inside DOMContentLoaded | Move to top of `<script>`, before DOMContentLoaded |
| Lucide icons not rendering | `lucide.createIcons()` not called | Call inside DOMContentLoaded |
| `drop-shadow` not following PNG shape | Using `box-shadow` instead | Use `filter: drop-shadow()` on `.image-container` |
| Bottom controls in Logs not showing | Z-order issue | `setup_bottom_controls()` must be called after `setup_chat_area()` |

---

## 14. File Structure

```
website/
├── index.html          ← Single-file website (HTML + CSS + JS)
└── WEBSITE_GUIDE.md    ← This guide
```

---

## 15. Pending Content (ยังต้องเติม)

- [ ] ใส่รูปภาพจริงแทน placeholder ทั้ง 4 รูปใน Installation section
- [ ] ใส่รูปภาพ Slide 6 (Mini Mode in-game)
- [ ] เพิ่ม Custom Repository URL จริงใน Installation step 2 (เมื่อพร้อม)
- [ ] เพิ่ม MBB download link จริงใน Download section (เมื่อ Installer พร้อม)
- [ ] พิจารณาเพิ่ม OpenGraph meta tags สำหรับ social sharing
