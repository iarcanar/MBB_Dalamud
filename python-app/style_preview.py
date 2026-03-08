"""
Style Preview v4 — ตัวอย่างรูปแบบข้อความแบบ realtime + font selector
รันแยก: python style_preview.py

กฎ:
1. Speaker known → ฟ้าหนา, ??? → ม่วงบาง
2. ชื่อตัวละครใน text → ฟ้าบาง (dialogue) / สี mode+หนา (cutscene/battle)
3. คำเฉพาะ/lore → latte+หนา (dialogue) / สี mode+หนา (cutscene/battle)
4. **highlight word** → ส้มอ่อน+หนา (ไม่ italic)
5. *italic* → FC Minimal, สีข้อความ
"""
import tkinter as tk
from tkinter import ttk
import os

# ── Default Style Config ──
STYLES = {
    "bg_color":        "#0a0a0f",
    "speaker":         "#38bdf8",   # Cyan — known speaker (bold)
    "speaker_unknown": "#a855f7",   # Purple — ??? speaker (thin)
    "dialogue":        "#ffffff",   # White — normal dialogue text
    "cutscene":        "#FFD700",   # Gold — cutscene text
    "battle":          "#FF6B00",   # Orange — battle text
    "lore":            "#D4C4A8",   # Latte — lore/place words (bold)
    "highlight":       "#FFB366",   # Light orange — **highlight words** (bold)
    "choice_header":   "#FFD700",   # Gold — choice header
    "choice_item":     "#e0e0e0",   # Light gray — choice items
    "shadow_color":    "#000000",
    "shadow_offset":   1,
}

# ── Bundled Font Names ──
BUNDLED_FONTS = [
    "Anuphan",
    "FC Minimal Medium",
    "Google Sans 17pt Medium",
]

# ── Sample Texts ──
SAMPLES = [
    {
        "label": "1. DIALOGUE — Speaker + Lore Word",
        "speaker": "Wuk Lamat",
        "text": "ที่นี่คือ Urqopacha สินะ... ข้าไม่เคยมาที่นี่มาก่อนเลยแฮะ",
        "mode": "dialogue",
        "characters": [],
        "lore": ["Urqopacha"],
    },
    {
        "label": "2. DIALOGUE — Character Name + Lore Word",
        "speaker": "Erenville",
        "text": "Y'shtola ว่าอย่างไร? เราควรมุ่งหน้าไป Yok Tural ตามแผน",
        "mode": "dialogue",
        "characters": ["Y'shtola"],
        "lore": ["Yok Tural"],
    },
    {
        "label": "3. DIALOGUE — Unknown Speaker (???) + Character Name",
        "speaker": "???",
        "text": "ขออภัยที่เสียมารยาท แต่...คุณคือ Wuk Lamat ใช่ไหม?",
        "mode": "dialogue",
        "characters": ["Wuk Lamat"],
        "lore": [],
    },
    {
        "label": "4. CUTSCENE — Narration + Lore (yellow mono)",
        "speaker": "",
        "text": "คงกระพันและเป็นนิรันดร์ มันอุบัติขึ้นจาก Urqopacha ร้อยขุนเขาแห่งกาลเวลา",
        "mode": "cutscene",
        "characters": [],
        "lore": ["Urqopacha"],
    },
    {
        "label": "5. CUTSCENE — Lore Word",
        "speaker": "",
        "text": "มีเพียง Valigarmanda ในตำนานเท่านั้นที่อาจหวังจะทำลายความสงบอันสง่างามของยอดเขาได้",
        "mode": "cutscene",
        "characters": [],
        "lore": ["Valigarmanda"],
    },
    {
        "label": "6. BATTLE — Speaker + Lore in text (orange mono)",
        "speaker": "Zoraal Ja",
        "text": "จงรับชะตากรรมของเจ้า! ดาบแห่ง Tuliyollal จะทำลายทุกสิ่ง!",
        "mode": "battle",
        "characters": [],
        "lore": ["Tuliyollal"],
    },
    {
        "label": "7. DIALOGUE — **Highlight Word** + *Italic with Lore*",
        "speaker": "Alphinaud",
        "text": "เราคง *ประเมินพ่อค้า Pelupelu ต่ำไปไม่ได้* เรื่องนี้ **สำคัญมาก** จริงๆ",
        "mode": "dialogue",
        "characters": [],
        "lore": ["Pelupelu"],
    },
    {
        "label": "8. CHOICE DIALOGUE",
        "speaker": "",
        "text": "What will you say?\n① สันติสุขจงมีแด่ Tural\n② ข้าจะต่อสู้เพื่อทุกคน\n③ ...",
        "mode": "choice",
        "characters": [],
        "lore": ["Tural"],
    },
]


class StylePreview(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MBB — Text Style Preview (v4)")
        self.configure(bg="#111118")
        self.geometry("1100x920+100+50")
        self.styles = dict(STYLES)

        # Load bundled fonts
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        for f in ["Anuphan.ttf", "FC Minimal.ttf", "Google Sans 17pt Medium.ttf"]:
            path = os.path.join(font_dir, f)
            if os.path.exists(path):
                try:
                    from ctypes import windll
                    windll.gdi32.AddFontResourceW(path)
                except Exception:
                    pass

        self._build_ui()
        self._render_all()

    # ── UI Build ──

    def _build_ui(self):
        ctrl_frame = tk.Frame(self, bg="#1a1a24")
        ctrl_frame.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(ctrl_frame, text="TEXT STYLE CONTROLS — v4",
                 font=("Consolas", 9, "bold"), fg="#888", bg="#1a1a24"
                 ).pack(anchor="w", padx=8, pady=(4, 2))

        # ── Font Selector Row ──
        font_frame = tk.Frame(ctrl_frame, bg="#1a1a24")
        font_frame.pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(font_frame, text="Font:", font=("Consolas", 9, "bold"),
                 fg="#aaa", bg="#1a1a24").pack(side="left", padx=(0, 6))

        self.font_var = tk.StringVar(value="Anuphan")
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var,
                                  values=BUNDLED_FONTS,
                                  font=("Consolas", 9), width=28)
        font_combo.pack(side="left", padx=(0, 12))
        font_combo.bind("<<ComboboxSelected>>", lambda e: self._render_all())
        font_combo.bind("<Return>", lambda e: self._render_all())

        tk.Label(font_frame, text="Size:", font=("Consolas", 9, "bold"),
                 fg="#aaa", bg="#1a1a24").pack(side="left", padx=(0, 6))

        self.font_size_var = tk.IntVar(value=20)
        size_spin = tk.Spinbox(font_frame, from_=10, to=40,
                               textvariable=self.font_size_var,
                               font=("Consolas", 9), width=4, bg="#222",
                               fg="#ddd", insertbackground="#ddd",
                               command=self._render_all)
        size_spin.pack(side="left")
        size_spin.bind("<Return>", lambda e: self._render_all())

        # ── Color Controls Grid ──
        grid = tk.Frame(ctrl_frame, bg="#1a1a24")
        grid.pack(fill="x", padx=8, pady=(0, 4))

        self.color_entries = {}
        controls = [
            ("speaker",         "Speaker (Known)"),
            ("speaker_unknown", "Speaker (???)"),
            ("dialogue",        "Dialogue Text"),
            ("highlight",       "**Highlight**"),
            ("lore",            "Lore/Places"),
            ("cutscene",        "Cutscene Text"),
            ("battle",          "Battle Text"),
            ("choice_header",   "Choice Header"),
            ("choice_item",     "Choice Items"),
            ("bg_color",        "Background"),
            ("shadow_color",    "Shadow"),
        ]

        for i, (key, label) in enumerate(controls):
            row, col = divmod(i, 4)
            f = tk.Frame(grid, bg="#1a1a24")
            f.grid(row=row, column=col, padx=4, pady=2, sticky="w")

            swatch = tk.Label(f, text="  ", bg=self.styles[key], width=2,
                              relief="solid", borderwidth=1)
            swatch.pack(side="left", padx=(0, 4))

            tk.Label(f, text=label, font=("Consolas", 8), fg="#aaa",
                     bg="#1a1a24", width=16, anchor="w").pack(side="left")

            entry = tk.Entry(f, font=("Consolas", 8), width=8, bg="#222",
                             fg="#ddd", insertbackground="#ddd", borderwidth=1,
                             relief="solid")
            entry.insert(0, self.styles[key])
            entry.pack(side="left", padx=(2, 0))
            entry.bind("<Return>",
                       lambda e, k=key, s=swatch: self._on_color_change(k, e.widget, s))
            entry.bind("<FocusOut>",
                       lambda e, k=key, s=swatch: self._on_color_change(k, e.widget, s))

            self.color_entries[key] = (entry, swatch)

        # Legend
        legend = tk.Frame(ctrl_frame, bg="#1a1a24")
        legend.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(legend, font=("Consolas", 7), fg="#666", bg="#1a1a24",
                 text=("Speaker: known=cyan bold, ???=purple thin  |  "
                       "Char=cyan thin  |  Lore=latte bold  |  "
                       "**highlight**=light orange bold  |  "
                       "Cutscene/Battle=mono-color")
                 ).pack(anchor="w")

        # Canvas
        canvas_frame = tk.Frame(self, bg="#111118")
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self.canvas = tk.Canvas(canvas_frame, bg=self.styles["bg_color"],
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    # ── Color Controls ──

    def _on_color_change(self, key, entry_widget, swatch):
        val = entry_widget.get().strip()
        if val.startswith("#") and len(val) in (4, 7):
            try:
                swatch.config(bg=val)
                self.styles[key] = val
                if key == "bg_color":
                    self.canvas.config(bg=val)
                self._render_all()
            except tk.TclError:
                pass

    # ── Font Builder ──

    def _build_fonts(self):
        """Build font tuples from current font_var and font_size_var."""
        name = self.font_var.get()
        size = self.font_size_var.get()
        return {
            "base":   (name, size),
            "bold":   (name, size, "bold"),
            "italic": (name, size),           # same font, no italic flag
        }

    # ── Rendering ──

    def _render_all(self):
        self.canvas.delete("all")
        y = 20
        fonts = self._build_fonts()
        label_font = ("Consolas", 10)

        for sample in SAMPLES:
            self.canvas.create_text(20, y, text=sample["label"],
                                    font=label_font, fill="#555", anchor="nw")
            y += 22

            if sample["mode"] == "choice":
                y = self._render_choice(y, sample["text"], fonts)
            else:
                y = self._render_dialogue(y, sample, fonts)

            y += 16

    def _render_dialogue(self, y, sample, fonts):
        x = 30
        shadow = self.styles["shadow_color"]
        so = self.styles["shadow_offset"]
        speaker = sample["speaker"]
        mode = sample["mode"]

        # ── Speaker name ──
        if speaker:
            if "?" in speaker:
                speaker_color = self.styles["speaker_unknown"]
                speaker_font = fonts["base"]       # ??? = thin
            else:
                speaker_color = self.styles["speaker"]
                speaker_font = fonts["bold"]       # known = bold

            speaker_text = f"{speaker}: "
            for dx, dy in [(-so,0),(so,0),(0,-so),(0,so),
                           (-so,-so),(so,-so),(-so,so),(so,so)]:
                self.canvas.create_text(x+dx, y+dy, text=speaker_text,
                                        font=speaker_font, fill=shadow, anchor="nw")
            self.canvas.create_text(x, y, text=speaker_text,
                                    font=speaker_font, fill=speaker_color, anchor="nw")
            temp_id = self.canvas.create_text(0, 0, text=speaker_text,
                                              font=speaker_font, anchor="nw")
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            x += bbox[2] - bbox[0]

        # ── Text segments ──
        segments = self._parse_text(sample["text"],
                                    sample.get("characters", []),
                                    sample.get("lore", []))
        y = self._render_segments(x, y, segments, mode, fonts)
        return y

    # ── Text Parser ──

    def _parse_text(self, text, characters, lore):
        """Parse text → segments with type tags for characters and lore separately."""
        tagged_names = ([(n, 'char') for n in characters] +
                        [(n, 'lore') for n in lore])
        tagged_names.sort(key=lambda x: len(x[0]), reverse=True)

        # Pass 1: split by **bold** and *italic* markers
        raw_segments = []
        i = 0
        while i < len(text):
            if text[i:i+2] == '**':
                end = text.find('**', i+2)
                if end != -1:
                    raw_segments.append(('highlight', text[i+2:end]))
                    i = end + 2
                    continue
            if text[i] == '*':
                end = text.find('*', i+1)
                if end != -1:
                    raw_segments.append(('italic', text[i+1:end]))
                    i = end + 1
                    continue
            next_bold = text.find('**', i)
            next_italic = text.find('*', i)
            if next_italic == next_bold:
                next_italic = -1
            end = len(text)
            if next_bold != -1:
                end = min(end, next_bold)
            if next_italic != -1:
                end = min(end, next_italic)
            raw_segments.append(('normal', text[i:end]))
            i = end

        # Pass 2: split by tagged names
        segments = []
        for style, seg_text in raw_segments:
            sub_segs = self._split_by_tagged_names(seg_text, tagged_names)
            for sub_type, sub_text in sub_segs:
                if sub_type == 'char':
                    segments.append(('char_name' if style == 'normal'
                                     else f'char_name_{style}', sub_text))
                elif sub_type == 'lore':
                    segments.append(('lore_word' if style == 'normal'
                                     else f'lore_word_{style}', sub_text))
                else:
                    segments.append((style, sub_text))

        return segments

    def _split_by_tagged_names(self, text, tagged_names):
        """Split text by names, preserving their tag (char/lore)."""
        if not tagged_names:
            return [('normal', text)]
        result = []
        remaining = text
        while remaining:
            earliest_pos = len(remaining)
            earliest_name = None
            earliest_tag = None
            for name, tag in tagged_names:
                pos = remaining.find(name)
                if pos != -1 and pos < earliest_pos:
                    earliest_pos = pos
                    earliest_name = name
                    earliest_tag = tag
            if earliest_name is None:
                result.append(('normal', remaining))
                break
            if earliest_pos > 0:
                result.append(('normal', remaining[:earliest_pos]))
            result.append((earliest_tag, earliest_name))
            remaining = remaining[earliest_pos + len(earliest_name):]
        return result

    # ── Segment Renderer ──

    def _render_segments(self, start_x, y, segments, mode, fonts):
        shadow = self.styles["shadow_color"]
        so = self.styles["shadow_offset"]
        x = start_x
        max_width = 1040
        size = self.font_size_var.get()
        line_height = size + 10

        for seg_type, seg_text in segments:
            font, color = self._resolve_style(seg_type, mode, fonts)

            # Measure
            temp_id = self.canvas.create_text(0, 0, text=seg_text,
                                              font=font, anchor="nw")
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            w = bbox[2] - bbox[0] if bbox else 0

            # Line wrap
            if x + w > max_width and x > start_x:
                x = start_x
                y += line_height

            # Shadow + text
            for dx, dy in [(-so,0),(so,0),(0,-so),(0,so),
                           (-so,-so),(so,-so),(-so,so),(so,so)]:
                self.canvas.create_text(x+dx, y+dy, text=seg_text,
                                        font=font, fill=shadow, anchor="nw")
            self.canvas.create_text(x, y, text=seg_text,
                                    font=font, fill=color, anchor="nw")
            x += w

        return y + line_height

    def _resolve_style(self, seg_type, mode, fonts):
        """Return (font, color) based on segment type and mode."""
        S = self.styles

        # ── Cutscene / Battle: mono-color ──
        if mode in ("cutscene", "battle"):
            mc = S["cutscene"] if mode == "cutscene" else S["battle"]
            if seg_type == 'normal':
                return fonts["base"], mc
            elif seg_type in ('char_name', 'lore_word',
                              'char_name_italic', 'lore_word_italic'):
                return fonts["bold"], mc
            elif seg_type in ('highlight', 'char_name_highlight',
                              'lore_word_highlight'):
                return fonts["bold"], mc
            elif seg_type == 'italic':
                return fonts["base"], mc
            return fonts["base"], mc

        # ── Dialogue mode ──
        if seg_type == 'normal':
            return fonts["base"], S["dialogue"]
        elif seg_type == 'char_name':
            # Character name → cyan THIN
            return fonts["base"], S["speaker"]
        elif seg_type == 'lore_word':
            # Lore/place → latte BOLD
            return fonts["bold"], S["lore"]
        elif seg_type in ('highlight', 'char_name_highlight',
                          'lore_word_highlight'):
            # **highlight word** → light orange BOLD
            return fonts["bold"], S["highlight"]
        elif seg_type == 'italic':
            # *italic* → same font, text color (no italic flag)
            return fonts["base"], S["dialogue"]
        elif seg_type == 'char_name_italic':
            # Char inside *...* → cyan thin (name wins)
            return fonts["base"], S["speaker"]
        elif seg_type == 'lore_word_italic':
            # Lore inside *...* → latte bold (lore wins)
            return fonts["bold"], S["lore"]

        return fonts["base"], S["dialogue"]

    # ── Choice Renderer ──

    def _render_choice(self, y, text, fonts):
        shadow = self.styles["shadow_color"]
        so = self.styles["shadow_offset"]
        x = 30
        lines = text.split("\n")

        header = lines[0] if lines else ""
        for dx, dy in [(-so,0),(so,0),(0,-so),(0,so)]:
            self.canvas.create_text(x+dx, y+dy, text=header,
                                    font=fonts["bold"], fill=shadow, anchor="nw")
        self.canvas.create_text(x, y, text=header,
                                font=fonts["bold"],
                                fill=self.styles["choice_header"], anchor="nw")
        size = self.font_size_var.get()
        y += size + 12

        for line in lines[1:]:
            if not line.strip():
                continue
            for dx, dy in [(-so,0),(so,0),(0,-so),(0,so)]:
                self.canvas.create_text(x+20+dx, y+dy, text=line,
                                        font=fonts["base"], fill=shadow, anchor="nw")
            self.canvas.create_text(x+20, y, text=line,
                                    font=fonts["base"],
                                    fill=self.styles["choice_item"], anchor="nw")
            y += size + 8

        return y


if __name__ == "__main__":
    app = StylePreview()
    app.mainloop()
