"""
gen_asset_library.py — generate docs/manual/library.html (the Asset / Visual
Library page) by scanning the real project asset folders. Re-run whenever the
assets change:  python scripts/gen_asset_library.py

Scans:  python-app/assets/*.png · assets/icons/*.svg · fonts/*.ttf ·
        npc_images/main_characters/*  → a categorised, de-cluttered gallery
that matches the manual's cyberpunk styling (classes in assets/manual.css).
"""
import os
import html
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "python-app")
ASSETS = os.path.join(APP, "assets")
ICONS = os.path.join(ASSETS, "icons")
FONTS = os.path.join(APP, "fonts")
NPC = os.path.join(APP, "npc_images", "main_characters")
OUT = os.path.join(ROOT, "docs", "manual", "library.html")

# Relative prefix from docs/manual/ to python-app/ (served from repo root or file://)
REL = "../../python-app"

# ── PNG categorisation ──
# Brand/art split into CURRENT assets (shown with an "in use" dot) vs superseded
# LEGACY variants. MBBvisual is the splash and ships as .jpg (not .png).
# TUI_BG.png is the colour-picker button ICON, not brand → it stays in UI icons.
BRAND_CURRENT = ["MBBvisual", "mbb_meteor"]
BRAND_LEGACY = ["MBBvisual_mar26", "MBBvisual_legacy", "YBB_logo", "mbb_pixel"]
BRAND_NOTE = {
    "MBBvisual": "splash ปัจจุบัน (fallback → _mar26 / _legacy)",
    "mbb_meteor": "splash meteor + โลโก้ main window",
}
STATUS = ["good", "bad", "error", "confirm", "liked", "unlike",
          "green_pin", "pin_gold", "red_icon", "black_icon"]

# SVG → where it's used (Thai)
SVG_USE = {
    "folder":    "Settings · ปุ่มเปิดโฟลเดอร์ log",
    "reload":    "Settings · เมนูรีสตาร์ท",
    "eye_open":  "Model · เผย API Key",
    "eye_close": "Model · ซ่อน API Key",
    "edit":      "Model · แก้ไข API Key",
    "save":      "Model · บันทึก API Key",
    "chevron":   "Model · ลูกศร dropdown",
    "lock":      "Model · พารามิเตอร์ล็อก (trial)",
}

# Font → role (Thai)
FONT_ROLE = {
    "Anuphan": "ฟอนต์หลัก Thai — TUI / Logs default",
    "Caveat": "ลายมือ — ชื่อใน Polaroid",
    "FC Minimal": "italic segments ใน rich text",
    "Google Sans 17pt Medium": "UI accent",
    "Pacifico": "decorative",
}


def _list(folder, exts):
    if not os.path.isdir(folder):
        return []
    out = [f for f in sorted(os.listdir(folder), key=str.lower)
           if os.path.splitext(f)[1].lower() in exts]
    return out


def _resolve(stem):
    """Actual filename for a brand stem (any common image ext), or None.
    Brand assets may be .jpg (MBBvisual) not just .png."""
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        if os.path.exists(os.path.join(ASSETS, stem + ext)):
            return stem + ext
    return None


def _is_legacy(stem):
    return stem.endswith("_old") or stem.endswith("_legacy")


def tile(src, name, sub="", legacy=False, big=False, used=False):
    """One gallery tile: swatch + filename (+ optional sub note / legacy tag /
    'in use' dot when the asset is referenced by the current code)."""
    cls = "asset-tile" + (" big" if big else "")
    badges = ""
    if used:
        badges += '<span class="asset-inuse" title="อ้างอิงในโค้ดเวอร์ชันล่าสุด"></span>'
    if legacy:
        badges += '<span class="asset-legacy">legacy</span>'
    sub_html = f'<div class="asset-sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<figure class="{cls}" data-name="{html.escape(name.lower())}">'
            f'<div class="asset-swatch">{badges}'
            f'<img loading="lazy" src="{src}" alt="{html.escape(name)}"></div>'
            f'<figcaption class="asset-name">{html.escape(name)}</figcaption>'
            f'{sub_html}</figure>')


def _code_blob():
    """Concatenate all SOURCE python-app *.py so we can detect asset references.
    Skips dist/ + build/ + __pycache__ — those are stale build-output copies
    that would falsely mark superseded assets as 'in use'."""
    import glob
    skip = (os.sep + "dist" + os.sep, os.sep + "build" + os.sep,
            os.sep + "__pycache__" + os.sep)
    blob = []
    for pyf in glob.glob(os.path.join(APP, "**", "*.py"), recursive=True):
        if any(s in pyf for s in skip):
            continue
        try:
            with open(pyf, "r", encoding="utf-8", errors="ignore") as fh:
                blob.append(fh.read())
        except Exception:
            pass
    return "\n".join(blob)


def grid(tiles, search=False):
    sid = ' data-searchable="1"' if search else ""
    return f'<div class="asset-grid"{sid}>\n' + "\n".join(tiles) + "\n</div>"


def build():
    pngs = [os.path.splitext(f)[0] for f in _list(ASSETS, {".png"})]
    svgs = [os.path.splitext(f)[0] for f in _list(ICONS, {".svg"})]
    fonts = [f for f in _list(FONTS, {".ttf"})]
    avatars = _list(NPC, {".png", ".webp", ".jpg", ".jpeg"})

    status = [p for p in STATUS if p in pngs]
    brand_stems = set(BRAND_CURRENT) | set(BRAND_LEGACY)
    categorised = brand_stems | set(status)
    ui_icons = [p for p in pngs if p not in categorised]

    code = _code_blob()
    def _used(p):
        return f"{p}.png" in code   # literal filename ref = confirmed in use

    # ── SVG section (all wired in v1.8.21 → in use) ──
    svg_tiles = [tile(f"{REL}/assets/icons/{s}.svg", f"{s}.svg",
                      SVG_USE.get(s, ""), big=True, used=True) for s in svgs]

    # ── PNG UI icons ──
    ui_tiles = [tile(f"{REL}/assets/{p}.png", f"{p}.png",
                     legacy=_is_legacy(p), used=_used(p)) for p in ui_icons]

    # ── Status / colored ──
    status_tiles = [tile(f"{REL}/assets/{p}.png", f"{p}.png", used=_used(p))
                    for p in status]

    # ── Brand & art — current (notes + in-use dot), then legacy (superseded) ──
    brand_tiles = []
    for s in BRAND_CURRENT:
        fn = _resolve(s)
        if fn:
            brand_tiles.append(tile(f"{REL}/assets/{fn}", fn,
                                    BRAND_NOTE.get(s, ""), big=True, used=True))
    for s in BRAND_LEGACY:
        fn = _resolve(s)
        if fn:
            brand_tiles.append(tile(f"{REL}/assets/{fn}", fn, "เลิกใช้แล้ว / fallback",
                                    big=True, legacy=True, used=False))

    # ── Fonts (@font-face + sample) ──
    faces, font_tiles = [], []
    for i, fn in enumerate(fonts):
        stem = os.path.splitext(fn)[0]
        fam = f"lib-font-{i}"
        faces.append(f"@font-face{{font-family:'{fam}';"
                     f"src:url('{REL}/fonts/{quote(fn)}');font-display:swap;}}")
        role = FONT_ROLE.get(stem, "")
        font_tiles.append(
            f'<figure class="font-tile" data-name="{html.escape(fn.lower())}">'
            f'<div class="font-sample" style="font-family:\'{fam}\'">'
            f'ก ข ค Aa Bb · MBB 123</div>'
            f'<figcaption class="asset-name">{html.escape(fn)}</figcaption>'
            f'<div class="asset-sub">{html.escape(role)}</div></figure>')

    # ── NPC avatars (collapsible) ──
    av_tiles = [
        f'<figure class="avatar-tile" data-name="{html.escape(a.lower())}">'
        f'<img loading="lazy" src="{REL}/npc_images/main_characters/{quote(a)}" '
        f'alt="{html.escape(a)}"><figcaption>{html.escape(os.path.splitext(a)[0])}'
        f'</figcaption></figure>'
        for a in avatars]

    icon_pngs = ui_icons + status
    counts = dict(svg=len(svgs), ui=len(ui_icons), status=len(status),
                  brand=len(brand_tiles), fonts=len(fonts), avatars=len(avatars),
                  inuse=len(svgs) + sum(1 for p in icon_pngs if _used(p)),
                  icons_total=len(svgs) + len(icon_pngs))
    return render(svg_tiles, ui_tiles, status_tiles, brand_tiles,
                  font_tiles, av_tiles, faces, counts)


def render(svg, ui, status, brand, fonts, avatars, faces, c):
    face_css = "\n".join(faces)
    summary_cards = "".join([
        f'<div class="card compact"><h3>{n}</h3>'
        f'<p style="color:var(--text-dim);font-size:13px;margin:0">{d}</p></div>'
        for n, d in [
            (f"{c['svg']} SVG", "ไอคอน themed (assets/icons/) — v1.8.21"),
            (f"{c['ui']} PNG", "UI icons (assets/) — white, auto-invert"),
            (f"{c['status']} Status", "good / bad / error / pin …"),
            (f"{c['brand']} Brand", "splash · logo · meteor"),
            (f"{c['fonts']} Fonts", "bundled .ttf (fonts/)"),
            (f"{c['avatars']} Avatars", "npc_images/main_characters/"),
        ]])

    av_grid = "\n".join(avatars)
    # Cache-bust the shared CSS by its mtime so edits show up on reload.
    css_v = int(os.path.getmtime(os.path.join(
        ROOT, "docs", "manual", "assets", "manual.css")))
    return TEMPLATE.format(
        css_v=css_v,
        face_css=face_css,
        summary=summary_cards,
        inuse=c["inuse"],
        icons_total=c["icons_total"],
        svg_grid=grid(svg),
        ui_grid=grid(ui, search=True),
        status_grid=grid(status),
        brand_grid=grid(brand),
        font_grid='<div class="font-grid">' + "\n".join(fonts) + "</div>",
        av_count=c["avatars"],
        av_grid=av_grid,
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MBB Manual — Asset Library</title>
    <link rel="icon" type="image/png" href="../web_assets/mbb_icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&family=Kanit:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/manual.css?v={css_v}">
    <style>
{face_css}
    </style>
</head>
<body>
<div class="bg-particles" aria-hidden="true"></div>
<div class="manual-shell">
    <header class="manual-header">
        <a href="index.html" class="brand">
            <span class="dot"></span>
            <span>MBB <strong style="color:#a5b4fc">Manual</strong></span>
            <span class="tag" style="margin-left:8px">v1.8.21</span>
        </a>
        <button class="hamburger" aria-label="Toggle nav">&#8801;</button>
        <nav>
            <a href="https://mbb-ffxiv.vercel.app" target="_blank" rel="noopener">Landing</a>
            <a href="index.html">Overview</a>
            <a href="ui.html">UI Systems</a>
            <a href="npc-translation.html">NPC + Translation</a>
            <a href="styling.html">Theme + Settings</a>
            <a href="reference.html">Reference</a>
            <a href="library.html" class="active">Assets</a>
            <a href="https://github.com/iarcanar/MBB_Dalamud" target="_blank" style="color:#94a3b8">GitHub &#8599;</a>
        </nav>
    </header>

    <div class="sync-banner">
        <span class="sync-dot"></span>
        Auto-generated · v1.8.21
        <a href="https://github.com/iarcanar/MBB_Dalamud" target="_blank">Repo &#8599;</a>
    </div>

    <aside class="manual-sidebar">
        <div class="group">
            <div class="group-title"><span class="group-icon"></span>Asset Library</div>
            <ul>
                <li><a href="library.html#svg"><span class="lead">&#9656;</span>SVG Icons</a></li>
                <li><a href="library.html#ui"><span class="lead">&#9656;</span>PNG UI Icons</a></li>
                <li><a href="library.html#status"><span class="lead">&#9656;</span>Status / Colored</a></li>
                <li><a href="library.html#brand"><span class="lead">&#9656;</span>Brand &amp; Art</a></li>
                <li><a href="library.html#fonts"><span class="lead">&#9656;</span>Fonts</a></li>
                <li><a href="library.html#avatars"><span class="lead">&#9656;</span>NPC Avatars</a></li>
            </ul>
        </div>
        <div class="group">
            <div class="group-title"><span class="group-icon"></span>Back to manual</div>
            <ul>
                <li><a href="index.html"><span class="lead">&#183;</span>Overview</a></li>
                <li><a href="ui.html"><span class="lead">&#183;</span>UI Systems</a></li>
                <li><a href="reference.html"><span class="lead">&#183;</span>Reference</a></li>
            </ul>
        </div>
    </aside>

    <main class="manual-content">
        <div class="breadcrumb">
            <a href="https://mbb-ffxiv.vercel.app" target="_blank" rel="noopener">MBB</a><span class="sep">/</span>
            <a href="index.html">Manual</a><span class="sep">/</span>
            <span class="here">Asset Library</span>
        </div>

        <div class="hero-row">
            <div class="hero-card">
                <div class="page-eyebrow">Visual Library</div>
                <h1>Asset Library</h1>
                <p>ไฟล์ภาพ ไอคอน และฟอนต์ทั้งหมดที่โปรเจ็คใช้จริง — แยกตามหมวดตามโครงสร้างโฟลเดอร์ <code>python-app/</code>. หน้านี้ <strong>generate อัตโนมัติ</strong>จากโฟลเดอร์จริง (ไม่ตกหล่น ไม่ค้างของเก่า).</p>
            </div>
            <div class="card" style="padding:20px">
                <div class="card-eyebrow">Summary</div>
                <div class="card-grid" style="margin:0;gap:10px;grid-template-columns:repeat(2,1fr)">
{summary}
                </div>
            </div>
        </div>

        <div class="lib-legend">
            <span class="lib-legend-item"><span class="asset-inuse"></span> ใช้งานบนเวอร์ชันล่าสุด ({inuse}/{icons_total} ไอคอน)</span>
            <span class="lib-legend-item"><span class="asset-legacy">legacy</span> ไฟล์รุ่นเก่า</span>
        </div>

        <section class="doc-section">
            <h2 class="section-head" id="svg">SVG Icons <span class="tag">assets/icons/</span></h2>
            <p>ไอคอน vector ใหม่ (v1.8.21) — โหลดผ่าน <code>pyqt_ui/qt_icons.py</code> แล้ว <strong>tint สีตามธีม</strong> อัตโนมัติ (asset เดียวใช้ได้ทุกธีม). แสดงด้วยสีขาวบนพื้นเข้มตามต้นฉบับ.</p>
{svg_grid}
        </section>

        <section class="doc-section">
            <h2 class="section-head" id="ui">PNG UI Icons <span class="tag">assets/</span></h2>
            <p>ไอคอน UI สีขาว (auto-invert บนธีมสว่าง) ใช้ใน TUI / Mini UI / overlays. พิมพ์ค้นหาเพื่อกรอง:</p>
            <input class="asset-search" type="search" placeholder="ค้นหาไอคอน… (เช่น lock, scale, fade)" oninput="filterAssets(this)">
{ui_grid}
        </section>

        <section class="doc-section">
            <h2 class="section-head" id="status">Status / Colored <span class="tag">assets/</span></h2>
            <p>ไอคอนที่มีสีในตัว (สถานะ / pin / like) — ไม่ invert ตามธีม.</p>
{status_grid}
        </section>

        <section class="doc-section">
            <h2 class="section-head" id="brand">Brand &amp; Art <span class="tag">assets/</span></h2>
            <p>ภาพแบรนด์และอาร์ตเวิร์ก — splash (ปัจจุบัน + รุ่นเก่า/fallback), โลโก้, meteor. <span style="color:var(--text-faint)">เรียงตัวที่ใช้งานก่อน แล้วตามด้วย legacy.</span></p>
{brand_grid}
        </section>

        <section class="doc-section">
            <h2 class="section-head" id="fonts">Fonts <span class="tag">fonts/</span></h2>
            <p>ฟอนต์ที่ bundle มากับโปรเจ็ค — PyQt6 ต้อง <code>QFontDatabase.addApplicationFont()</code> (จัดการโดย <code>QtFontManager</code>). ตัวอย่าง render จริง:</p>
{font_grid}
        </section>

        <section class="doc-section">
            <h2 class="section-head" id="avatars">NPC Avatars <span class="tag">{av_count} files</span></h2>
            <p>ภาพตัวละครใน <code>npc_images/main_characters/</code> (512px WebP, แสดงใน NPC Manager + speaker icon). คลิกเพื่อกาง:</p>
            <details class="asset-details">
                <summary>แสดง avatars ทั้งหมด ({av_count})</summary>
                <div class="avatar-grid">
{av_grid}
                </div>
            </details>
        </section>

        <nav class="page-nav">
            <a href="reference.html" class="prev"><span class="nav-dir">&#8592; Prev</span><span class="nav-title">Reference</span></a>
            <a href="index.html" class="next"><span class="nav-dir">Next &#8594;</span><span class="nav-title">Overview</span></a>
        </nav>
    </main>

    <footer class="manual-footer">
        &copy; 2026 MBB Dalamud · Asset Library auto-generated · <a href="https://mbb-ffxiv.vercel.app" target="_blank" rel="noopener">&#8592; Landing</a>
    </footer>
</div>

<script src="assets/manual.js"></script>
<script>
function filterAssets(input) {{
    var q = input.value.trim().toLowerCase();
    var grid = input.parentElement.querySelector('[data-searchable]');
    if (!grid) return;
    grid.querySelectorAll('.asset-tile').forEach(function(t) {{
        t.style.display = (!q || t.dataset.name.indexOf(q) !== -1) ? '' : 'none';
    }});
}}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    page = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {OUT} ({len(page)} bytes)")
