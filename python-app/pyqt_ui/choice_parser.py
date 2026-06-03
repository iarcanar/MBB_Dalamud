"""
Choice text parser — extracts (header, choices_list) from raw choice
dialogue text.

This module was extracted from translated_ui._handle_choice_text (Tkinter
era). The parsing logic is preserved byte-for-byte — only the canvas
rendering portion was dropped. ChoiceOverlay (PyQt6) calls this then
renders the result.

Input formats handled:
  1. Pipe-separated (current C# output):
       "What will you say? | Choice1 | Choice2 | Choice3"
  2. Newline-separated (fallback):
       "What will you say?\\nChoice1\\nChoice2\\nChoice3"
  3. Numbered list:
       "Header\\n1. A 2. B 3. C"
  4. Bulleted list:
       "Header\\n• A • B • C"

Processing steps:
  - Header detection (Thai keywords / "?" / short line)
  - Long-line splitting (>100 chars + 2+ punctuation)
  - Unwanted header filter (strips repeated "คุณจะพูดว่าอย่างไร" prefix)
  - Similarity dedup (>70% word overlap)
  - Bullet prefix application ("• ")
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("choice-parser")

# Headers to strip if they leak into a choice (translator sometimes
# duplicates the prompt into the first choice).
_UNWANTED_HEADERS = [
    "ท่านจะว่าอย่างไร",
    "จะว่าอย่างไรดี",
    "ท่านจะพูดอะไร",
    "คุณจะว่าอย่างไร",
    "พูดอะไรดี",
    "What will you say",
    "คุณจะพูดว่าอย่างไร",
    "ท่านจะพูดว่าอย่างไร",
    "ท่านจะกล่าวว่าอย่างไร",
    "คุณจะกล่าวว่าอย่างไร",
    "เจ้าจะกล่าวว่าอย่างไร",
    "จะกล่าวว่าอย่างไร",
]

# Substantive Thai connectors — a remainder containing these is a
# sentence fragment, not a tail-end stub. We keep the full choice.
_SUBSTANCE_WORDS = ["การ", "เรา", "จะ", "ไม่", "ให้", "ได้", "มา", "ไป"]

# Heuristic header signals in Thai dialogue.
_HEADER_KEYWORDS = ["พูด", "ว่า", "ไร", "ดี", "อะไร", "จะ", "คุณ", "ท่าน"]

_DEFAULT_HEADER_TH = "คุณจะพูดว่าอย่างไร?"

_BULLET_CHARS = "•◆○□■★☆-*"


def parse_choice_text(text: str) -> tuple[str, list[str]]:
    """Parse choice dialogue text into (header, formatted_choices).

    Returns:
        header: display header (e.g. "What will you say?" or Thai equivalent)
        formatted_choices: list of choice strings, each already prefixed
            with "• " when no bullet/number prefix exists. Empty list if
            no choices could be parsed.
    """
    header = ""
    choices_text = ""
    processed_text = text.strip()

    # ─── 1. Format detection ───
    if " | " in text:
        # Pipe-separated (current C# output)
        parts = [p.strip() for p in text.split(" | ")]
        if len(parts) >= 2:
            header_text = parts[0]
            choice_texts = parts[1:]

            english_headers = [
                "What will you say?",
                "What will you say",
                "Whatwill you say?",
                "What willyou say?",
            ]
            display_header = header_text
            for pattern in english_headers:
                if pattern.lower() in header_text.lower():
                    display_header = "What will you say?"
                    log.info(f"[CHOICE-PARSE] Normalized English header")
                    break

            header = display_header
            choices_text = "\n".join(choice_texts)
            log.info(f"[CHOICE-PARSE] pipe format → header={header!r} n={len(choice_texts)}")
    else:
        # Newline-separated fallback
        processed_text = processed_text.replace("<NL>", "\n")
        processed_text = processed_text.replace("\r\n", "\n")
        processed_text = processed_text.replace("\r", "\n")
        processed_text = re.sub(r"\n+", "\n", processed_text)

        lines = processed_text.split("\n")
        if len(lines) >= 2:
            first_line = lines[0].strip()
            remaining_lines = lines[1:]
            # Short line OR contains "?" OR Thai header keyword → header
            if (
                "?" in first_line
                or any(word in first_line for word in _HEADER_KEYWORDS)
                or len(first_line.split()) <= 8
            ):
                header = first_line
                choices_text = "\n".join(remaining_lines)
            else:
                header = _DEFAULT_HEADER_TH
                choices_text = processed_text
        else:
            header = _DEFAULT_HEADER_TH
            choices_text = processed_text

    # ─── 2. Clean leading whitespace ───
    choices_text = choices_text.lstrip("\n").lstrip()

    # ─── 3. Split into individual choices ───
    choices: list[str] = []

    if "\n" in choices_text:
        raw_choices = [c.strip() for c in choices_text.split("\n") if c.strip()]

        # Split long lines on sentence boundaries if they contain ≥2 punctuation
        processed_choices: list[str] = []
        for choice in raw_choices:
            if (
                len(choice) > 100
                and choice.count("!") + choice.count("?") + choice.count(".") >= 2
            ):
                sub_choices = re.split(r"(?<=[.!?])\s+", choice)
                valid = [s.strip() for s in sub_choices if 10 <= len(s.strip()) <= 150]
                if len(valid) > 1:
                    processed_choices.extend(valid)
                    log.info(f"[CHOICE-PARSE] split long choice into {len(valid)}")
                else:
                    processed_choices.append(choice)
            else:
                processed_choices.append(choice)
        choices = processed_choices

    elif re.search(r"\d+\.", choices_text):
        numbered = re.split(r"(?=\d+\.)", choices_text)
        choices = [c.strip() for c in numbered if c.strip()]

    elif re.search(rf"[{re.escape(_BULLET_CHARS)}]", choices_text):
        bullet = re.split(rf"(?=[{re.escape(_BULLET_CHARS)}])", choices_text)
        choices = [c.strip() for c in bullet if c.strip()]

    elif choices_text:
        choices = [choices_text]

    if not choices:
        choices = [processed_text] if processed_text else []
        if processed_text:
            header = _DEFAULT_HEADER_TH

    # ─── 4. Filter unwanted-header leak + dedup ───
    filtered: list[str] = []
    seen: set[str] = set()
    header_lower = header.lower().strip()

    for choice in choices:
        cleaned = choice.strip()
        should_skip = False

        if cleaned.lower().strip() == header_lower:
            should_skip = True
        else:
            for unwanted in _UNWANTED_HEADERS:
                if cleaned.lower().startswith(unwanted.lower()):
                    remainder = cleaned[len(unwanted):].strip()
                    if len(remainder) <= 5:
                        should_skip = True
                        break
                    elif remainder.startswith(("?", ":", "!", ".")):
                        should_skip = True
                        break
                    elif len(remainder) > 15 or any(
                        w in remainder for w in _SUBSTANCE_WORDS
                    ):
                        # Substantive sentence — keep full original
                        break
                    else:
                        # Tail-end stub — strip the unwanted prefix
                        cleaned = remainder.lstrip("?:!. ").strip()
                        break

        if should_skip or not cleaned:
            continue

        # Similarity dedup (word overlap)
        choice_words = set(cleaned.lower().split())
        is_dupe = False
        for existing in seen:
            existing_words = set(existing.lower().split())
            if choice_words and existing_words:
                overlap = len(choice_words & existing_words)
                similarity = overlap / max(len(choice_words), len(existing_words))
                if similarity > 0.7:
                    is_dupe = True
                    break
        if is_dupe:
            continue

        filtered.append(cleaned)
        seen.add(cleaned)

    choices = filtered if filtered else choices

    # ─── 5. Apply bullet prefix ───
    formatted: list[str] = []
    for choice in choices:
        stripped = choice.strip()
        has_prefix = any(stripped.startswith(c) for c in _BULLET_CHARS)
        if not has_prefix and re.match(r"^\d+[\.\)\-]", stripped):
            has_prefix = True
        if not has_prefix:
            formatted.append(f"• {choice}")
        else:
            formatted.append(choice)

    log.info(f"[CHOICE-PARSE] result: header={header!r} choices={len(formatted)}")
    return header, formatted
