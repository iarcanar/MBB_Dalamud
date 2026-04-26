"""
NPC Data Manager — pure data layer for npc.json
Separated from UI so the new PyQt6 NPC Manager panel can share with the legacy
Tkinter version (during transition) and any future UIs.

Data structure (from npc.json):
    main_characters: list[{firstName, lastName, gender, role, relationship}]
    npcs:            list[{name, role, description}]
    lore:            dict[term -> definition]
    character_roles: dict[name -> role_description]
    word_fixes:      dict[wrong -> correct]
    _game_info:      dict (game metadata)
"""
import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from npc_file_utils import get_npc_file_path

# ─── Image storage ───
# Avatars stored in npc_images/<section>/<filename>.png
# Each character entry's "image" field holds JUST the filename (portable, no full paths).
IMAGE_DIR_NAME = "npc_images"

log = logging.getLogger("npc-data")


# Zero-width characters that often sneak into game-hooked names
_ZWS = "​‌‍﻿"
_ZWS_TRANS = str.maketrans("", "", _ZWS)


def _clean_name(s: str) -> str:
    """Strip zero-width chars + outer whitespace from a name string."""
    if not isinstance(s, str):
        return ""
    return s.strip().translate(_ZWS_TRANS)


class NPCDataManager:
    """In-memory + persistent CRUD for npc.json.

    Usage:
        dm = NPCDataManager()                # auto-loads
        chars = dm.list_main_characters()
        dm.add_main_character({...})
        dm.save()                             # writes to disk
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or get_npc_file_path()
        self.data: Dict[str, Any] = {}
        self._dirty = False
        self.load()

    # ─────────────────────────── load / save ───────────────────────────

    def load(self) -> None:
        """Load npc.json into memory. Creates empty structure if file missing."""
        if not self.file_path or not os.path.exists(self.file_path):
            log.warning(f"npc.json not found at {self.file_path}; using empty data")
            self.data = {
                "main_characters": [],
                "npcs": [],
                "lore": {},
                "character_roles": {},
                "word_fixes": {},
                "_game_info": {},
            }
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            # Normalize: ensure all expected keys exist
            self.data.setdefault("main_characters", [])
            self.data.setdefault("npcs", [])
            self.data.setdefault("lore", {})
            self.data.setdefault("character_roles", {})
            self.data.setdefault("word_fixes", {})
            self.data.setdefault("_game_info", {})
            self._dirty = False
            log.info(
                f"Loaded npc.json: {len(self.data['main_characters'])} main, "
                f"{len(self.data['npcs'])} npcs, {len(self.data['lore'])} lore, "
                f"{len(self.data['character_roles'])} roles, "
                f"{len(self.data['word_fixes'])} word_fixes"
            )
        except Exception as e:
            log.error(f"Failed to load npc.json: {e}")
            self.data = {}

    def save(self, *, backup: bool = True) -> bool:
        """Write data back to npc.json. Creates a timestamped backup first."""
        if not self.file_path:
            return False
        if backup and os.path.exists(self.file_path):
            try:
                bdir = os.path.join(os.path.dirname(self.file_path), "backups")
                os.makedirs(bdir, exist_ok=True)
                bname = f"npc_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.file_path, os.path.join(bdir, bname))
            except Exception as e:
                log.warning(f"Backup failed (continuing): {e}")
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            self._dirty = False
            log.info(f"Saved npc.json")
            return True
        except Exception as e:
            log.error(f"Failed to save npc.json: {e}")
            return False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ─────────────────────────── images ───────────────────────────

    def get_image_dir(self, section: str = "main_characters") -> str:
        """Return absolute path to the image directory for a section.
        Auto-creates if missing."""
        if not self.file_path:
            return ""
        base = os.path.dirname(self.file_path)
        path = os.path.join(base, IMAGE_DIR_NAME, section)
        os.makedirs(path, exist_ok=True)
        return path

    def get_main_character_image_path(self, index: int) -> Optional[str]:
        """Returns absolute path to the character's avatar image, or None if not set."""
        chars = self.data.get("main_characters", [])
        if not (0 <= index < len(chars)):
            return None
        filename = chars[index].get("image", "").strip()
        if not filename:
            return None
        full = os.path.join(self.get_image_dir("main_characters"), filename)
        return full if os.path.exists(full) else None

    def set_main_character_image(self, index: int, src_image_path: str,
                                  size: int = 128) -> Optional[str]:
        """Optimize a raw image and assign it to a character.

        Args:
            index: character index in main_characters list
            src_image_path: path to raw input image
            size: avatar dimension (default 128px)

        Returns:
            Filename (without dir) on success, None on failure.
        """
        chars = self.data.get("main_characters", [])
        if not (0 <= index < len(chars)):
            return None
        # Compute target filename from character's full name
        from image_optimizer import optimize_avatar, safe_filename
        c = chars[index]
        name = (c.get("firstName", "") + "_" + c.get("lastName", "")).strip("_")
        if not name:
            return None
        filename = safe_filename(name)
        dst = os.path.join(self.get_image_dir("main_characters"), filename)
        if not optimize_avatar(src_image_path, dst, size=size):
            return None
        # Update entry's image field
        c["image"] = filename
        self._dirty = True
        return filename

    def remove_main_character_image(self, index: int) -> bool:
        """Remove avatar image from disk + clear entry's image field."""
        chars = self.data.get("main_characters", [])
        if not (0 <= index < len(chars)):
            return False
        c = chars[index]
        filename = c.get("image", "").strip()
        if filename:
            full = os.path.join(self.get_image_dir("main_characters"), filename)
            try:
                if os.path.exists(full):
                    os.remove(full)
            except Exception as e:
                log.warning(f"Failed to delete image {full}: {e}")
        if "image" in c:
            del c["image"]
            self._dirty = True
        return True

    # ─────────────────────────── main_characters ───────────────────────────

    def list_main_characters(self) -> List[Dict[str, str]]:
        return list(self.data.get("main_characters", []))

    def find_main_character(self, first_name: str, last_name: str = "") -> Optional[int]:
        """Returns index of matching character, or None."""
        first = _clean_name(first_name)
        last = _clean_name(last_name)
        for i, c in enumerate(self.data.get("main_characters", [])):
            if (_clean_name(c.get("firstName", "")) == first and
                _clean_name(c.get("lastName", "")) == last):
                return i
        return None

    def add_main_character(self, entry: Dict[str, str]) -> bool:
        first = _clean_name(entry.get("firstName", ""))
        if not first:
            return False
        if self.find_main_character(first, entry.get("lastName", "")) is not None:
            return False  # duplicate
        new_entry = {
            "firstName": first,
            "lastName": _clean_name(entry.get("lastName", "")),
            "gender": entry.get("gender", "Neutral"),
            "role": entry.get("role", "").strip(),
            "relationship": entry.get("relationship", "Neutral"),
            # Internal metadata — Unix timestamp, used by "เพิ่มล่าสุด" filter.
            # Only newly-added entries get this; legacy entries (no field) won't
            # appear in the recent-added filter (correct behavior).
            "_added_at": time.time(),
        }
        # Optional image field — only include if non-empty (keeps JSON clean)
        image = (entry.get("image") or "").strip()
        if image:
            new_entry["image"] = image
        self.data.setdefault("main_characters", []).append(new_entry)
        self._dirty = True
        return True

    def update_main_character(self, index: int, entry: Dict[str, str]) -> bool:
        chars = self.data.get("main_characters", [])
        if not (0 <= index < len(chars)):
            return False
        # Preserve existing image unless caller provides a new one
        current = chars[index]
        new_entry = {
            "firstName": _clean_name(entry.get("firstName", "")),
            "lastName": _clean_name(entry.get("lastName", "")),
            "gender": entry.get("gender", "Neutral"),
            "role": entry.get("role", "").strip(),
            "relationship": entry.get("relationship", "Neutral"),
        }
        # image: explicit "" means CLEAR; missing key means PRESERVE existing
        if "image" in entry:
            image = (entry.get("image") or "").strip()
            if image:
                new_entry["image"] = image
            # else: omit field (cleared)
        elif "image" in current:
            new_entry["image"] = current["image"]
        # Preserve _added_at across updates so "recently added" stays accurate
        if "_added_at" in current:
            new_entry["_added_at"] = current["_added_at"]
        chars[index] = new_entry
        self._dirty = True
        return True

    def delete_main_character(self, index: int) -> bool:
        chars = self.data.get("main_characters", [])
        if not (0 <= index < len(chars)):
            return False
        del chars[index]
        self._dirty = True
        return True

    # ─────────────────────────── npcs ───────────────────────────

    def list_npcs(self) -> List[Dict[str, str]]:
        return list(self.data.get("npcs", []))

    def find_npc(self, name: str) -> Optional[int]:
        name = _clean_name(name)
        for i, n in enumerate(self.data.get("npcs", [])):
            if _clean_name(n.get("name", "")) == name:
                return i
        return None

    def add_npc(self, entry: Dict[str, str]) -> bool:
        name = _clean_name(entry.get("name", ""))
        if not name or self.find_npc(name) is not None:
            return False
        self.data.setdefault("npcs", []).append({
            "name": name,
            "role": entry.get("role", "").strip(),
            "description": entry.get("description", "").strip(),
        })
        self._dirty = True
        return True

    def update_npc(self, index: int, entry: Dict[str, str]) -> bool:
        npcs = self.data.get("npcs", [])
        if not (0 <= index < len(npcs)):
            return False
        npcs[index] = {
            "name": _clean_name(entry.get("name", "")),
            "role": entry.get("role", "").strip(),
            "description": entry.get("description", "").strip(),
        }
        self._dirty = True
        return True

    def delete_npc(self, index: int) -> bool:
        npcs = self.data.get("npcs", [])
        if not (0 <= index < len(npcs)):
            return False
        del npcs[index]
        self._dirty = True
        return True

    # ─────────────────────────── lore (dict) ───────────────────────────

    def list_lore(self) -> List[tuple]:
        """Returns list of (term, definition) tuples sorted by term."""
        return sorted(self.data.get("lore", {}).items(), key=lambda x: x[0].lower())

    def set_lore(self, term: str, definition: str) -> bool:
        term = term.strip()
        if not term:
            return False
        self.data.setdefault("lore", {})[term] = definition.strip()
        self._dirty = True
        return True

    def delete_lore(self, term: str) -> bool:
        if term in self.data.get("lore", {}):
            del self.data["lore"][term]
            self._dirty = True
            return True
        return False

    # ─────────────────────────── character_roles (dict) ───────────────────────────

    def list_character_roles(self) -> List[tuple]:
        return sorted(self.data.get("character_roles", {}).items(), key=lambda x: x[0].lower())

    def set_character_role(self, name: str, description: str) -> bool:
        name = _clean_name(name)
        if not name:
            return False
        self.data.setdefault("character_roles", {})[name] = description.strip()
        self._dirty = True
        return True

    def delete_character_role(self, name: str) -> bool:
        if name in self.data.get("character_roles", {}):
            del self.data["character_roles"][name]
            self._dirty = True
            return True
        return False

    # ─────────────────────────── word_fixes (dict) ───────────────────────────

    def list_word_fixes(self) -> List[tuple]:
        return sorted(self.data.get("word_fixes", {}).items(), key=lambda x: x[0].lower())

    def set_word_fix(self, wrong: str, correct: str) -> bool:
        wrong = wrong.strip()
        # Refuse dangerous 1-2 char replacements that could corrupt valid text
        if not wrong or len(wrong) < 2:
            log.warning(f"Refusing tiny word_fix: {wrong!r}")
            return False
        self.data.setdefault("word_fixes", {})[wrong] = correct
        self._dirty = True
        return True

    def delete_word_fix(self, wrong: str) -> bool:
        if wrong in self.data.get("word_fixes", {}):
            del self.data["word_fixes"][wrong]
            self._dirty = True
            return True
        return False

    # ─────────────────────────── search across all sections ───────────────────────────

    def search(self, query: str, section: str = "main") -> List:
        """Filter entries in given section by case-insensitive substring match."""
        q = query.strip().lower()
        if not q:
            if section == "main":
                return self.list_main_characters()
            if section == "npcs":
                return self.list_npcs()
            if section == "lore":
                return self.list_lore()
            if section == "roles":
                return self.list_character_roles()
            if section == "fixes":
                return self.list_word_fixes()
            return []

        if section == "main":
            return [c for c in self.list_main_characters()
                    if q in _clean_name(c.get("firstName", "")).lower()
                    or q in _clean_name(c.get("lastName", "")).lower()
                    or q in c.get("role", "").lower()]
        if section == "npcs":
            return [n for n in self.list_npcs()
                    if q in _clean_name(n.get("name", "")).lower()
                    or q in n.get("role", "").lower()
                    or q in n.get("description", "").lower()]
        if section == "lore":
            return [(t, d) for t, d in self.list_lore()
                    if q in t.lower() or q in d.lower()]
        if section == "roles":
            return [(n, r) for n, r in self.list_character_roles()
                    if q in n.lower() or q in r.lower()]
        if section == "fixes":
            return [(w, c) for w, c in self.list_word_fixes()
                    if q in w.lower() or q in c.lower()]
        return []
