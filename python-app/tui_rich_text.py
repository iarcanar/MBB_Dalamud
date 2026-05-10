"""
tui_rich_text.py — Rich Text Formatting System for the TUI

Extracted verbatim from translated_ui.py (lines 927-1126) to keep that file
manageable. Do NOT modify the class body without also updating the call sites
in translated_ui.py.

Contents:
    RichTextFormatter — parses *italic* / **bold** markers and (optionally)
    detects character names within plain text, returning segment dicts
    consumable by the Tkinter Canvas renderer in translated_ui.py.

Public methods (all preserved as-is):
    - parse_rich_text(text)                        -> list[dict]
    - parse_rich_text_with_names(text, names=None) -> list[dict]
    - get_font_tuple(base_font_tuple, font_style)  -> tuple
    - has_rich_text_markers(text)                  -> bool
    - _split_text_by_names(text, sorted_names)     -> list[tuple]  (internal)

The class operates on plain strings and returns plain Python data structures.
The only external dependencies are the standard library plus
`resource_path` from resource_utils (used to resolve the bundled italic font).
"""

import re
import logging

from resource_utils import resource_path


class RichTextFormatter:
    """Rich Text Formatting System for TUI supporting *italic* text with font switching"""

    def __init__(self):
        self.italic_font_path = resource_path("fonts/FC Minimal.ttf")
        self.italic_font_name = "FC Minimal"  # ชื่อฟอนต์จริงจาก metadata

        # Dynamic italic fonts list (can be updated by external tools)
        self.italic_fonts = [
            "FC Minimal Medium",     # First choice - รองรับภาษาไทยและ italic
            "FC Minimal",            # Second choice - รองรับภาษาไทย
            "Times New Roman",       # Fallback - Windows standard
            "Arial",
            "Calibri",
            "Georgia",
            "Verdana"
        ]

    def parse_rich_text(self, text: str) -> list:
        """
        Parse text with *italic* and **bold** markers into segments with font information

        Args:
            text: Text with formatting markers like "This is *italic* and **bold** text"

        Returns:
            List of dicts with 'text' and 'font_style' keys
            Example: [
                {'text': 'This is ', 'font_style': 'normal'},
                {'text': 'italic', 'font_style': 'italic'},
                {'text': ' and ', 'font_style': 'normal'},
                {'text': 'bold', 'font_style': 'bold'},
                {'text': ' text', 'font_style': 'normal'}
            ]
        """
        logging.info(f"🔍 PARSE_RICH_TEXT: Input text = '{text}'")
        segments = []
        current_pos = 0

        import re
        # Find all patterns in order of appearance
        # **text** for bold (must be checked first to avoid conflict with *text*)
        bold_pattern = r'\*\*([^*]+)\*\*'
        # *text* for italic
        italic_pattern = r'\*([^*]+)\*'

        # Combine patterns and find all matches
        all_matches = []

        # Find bold patterns first
        for match in re.finditer(bold_pattern, text):
            all_matches.append({
                'start': match.start(),
                'end': match.end(),
                'text': match.group(1),
                'style': 'bold',
                'full_match': match.group(0)
            })

        # Find italic patterns (but exclude those already captured by bold)
        for match in re.finditer(italic_pattern, text):
            # Check if this match overlaps with any bold match
            overlaps = False
            for bold_match in all_matches:
                if (match.start() >= bold_match['start'] and match.end() <= bold_match['end']):
                    overlaps = True
                    break

            if not overlaps:
                all_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(1),
                    'style': 'italic',
                    'full_match': match.group(0)
                })

        # Sort matches by position
        all_matches.sort(key=lambda x: x['start'])

        logging.info(f"🔍 PARSE_RICH_TEXT: Found {len([m for m in all_matches if m['style'] == 'italic'])} italic and {len([m for m in all_matches if m['style'] == 'bold'])} bold patterns")

        for i, match in enumerate(all_matches):
            # Add normal text before the current pattern
            if match['start'] > current_pos:
                normal_text = text[current_pos:match['start']]
                if normal_text:
                    segments.append({
                        'text': normal_text,
                        'font_style': 'normal'
                    })

            # Add formatted text
            segments.append({
                'text': match['text'],
                'font_style': match['style']
            })

            current_pos = match['end']

        # Add remaining normal text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                segments.append({
                    'text': remaining_text,
                    'font_style': 'normal'
                })

        # If no patterns found, return the whole text as normal
        if not segments:
            segments.append({
                'text': text,
                'font_style': 'normal'
            })

        return segments

    def get_font_tuple(self, base_font_tuple, font_style: str):
        """
        Get appropriate font tuple based on style

        Args:
            base_font_tuple: Tuple like ("Anuphan", 20)
            font_style: 'normal', 'italic', 'bold', or 'name'

        Returns:
            Font tuple for tkinter
        """
        font_family, font_size = base_font_tuple

        if font_style == 'italic':
            return ("FC Minimal Medium", font_size, "italic")
        elif font_style == 'bold':
            return (font_family, font_size, "bold")
        elif font_style == 'name':
            return base_font_tuple  # Names use base font (normal weight)
        else:
            return base_font_tuple

    def has_rich_text_markers(self, text: str) -> bool:
        """Check if text contains rich text formatting markers (*italic* or **bold**)"""
        return '*' in text

    def parse_rich_text_with_names(self, text: str, names=None) -> list:
        """Parse text for *italic*, **bold**, and character names.
        Returns segments with font_style: 'normal', 'bold', 'italic', 'name'."""
        segments = self.parse_rich_text(text)
        if not names:
            return segments

        sorted_names = sorted([n for n in names if len(n) >= 2], key=len, reverse=True)
        if not sorted_names:
            return segments

        result = []
        for segment in segments:
            style = segment['font_style']
            if style in ('normal', 'italic'):
                sub_segs = self._split_text_by_names(segment['text'], sorted_names)
                for sub_type, sub_text in sub_segs:
                    if sub_type == 'name':
                        result.append({'text': sub_text, 'font_style': 'name'})
                    else:
                        result.append({'text': sub_text, 'font_style': style})
            else:
                result.append(segment)

        return result

    def _split_text_by_names(self, text: str, sorted_names: list) -> list:
        """Split text by character names with word boundary check."""
        if not sorted_names:
            return [('normal', text)]
        result = []
        remaining = text
        while remaining:
            earliest_pos = len(remaining)
            earliest_name = None
            for name in sorted_names:
                pos = remaining.find(name)
                if pos != -1 and pos < earliest_pos:
                    is_word = True
                    if pos > 0 and (remaining[pos - 1].isalnum() or remaining[pos - 1] == "'"):
                        is_word = False
                    end_pos = pos + len(name)
                    if end_pos < len(remaining) and (remaining[end_pos].isalnum() or remaining[end_pos] == "'"):
                        is_word = False
                    if is_word:
                        earliest_pos = pos
                        earliest_name = name
            if earliest_name is None:
                result.append(('normal', remaining))
                break
            if earliest_pos > 0:
                result.append(('normal', remaining[:earliest_pos]))
            result.append(('name', earliest_name))
            remaining = remaining[earliest_pos + len(earliest_name):]
        return result
