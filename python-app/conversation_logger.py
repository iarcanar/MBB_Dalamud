"""
Conversation Logger — บันทึกบทสนทนาแบบมีโครงสร้าง สำหรับ wide-context-translation

ระบบ ALWAYS-ON สำหรับ in-memory context (ช่วยรักษาความสม่ำเสมอของคำแปล)
Disk logging เปิด/ปิดแยกต่างหากผ่าน Settings UI → "Conversation Log" toggle (debug mode)

จุดประสงค์:
- ติดตาม active speakers และบทสนทนาแบบ in-memory เสมอ
- ส่ง recent context ให้ Gemini ก่อนแปล → สรรพนาม/honorific คงที่
- Export เป็น JSON (เฉพาะเมื่อ disk_logging=True)

ไฟล์ output: AppData/Local/MBB_Dalamud/logs/conversations/conv_YYYYMMDD_HHMMSS.json
"""

import os
import json
import time
import atexit
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from resource_utils import get_user_data_dir, get_app_dir



# --- Conversation boundary heuristics ---

# ถ้าเงียบนานกว่านี้ (วินาที) → ถือว่าบทสนทนาเดิมจบแล้ว
CONVERSATION_GAP_SECONDS = 45

# Speaker limit ต่อ conversation (เพิ่มจาก 5→8 เพื่อรองรับ quest ที่มี NPC หลายตัว)
CONVERSATION_MAX_SPEAKERS = 8

# Thai first-person pronouns sorted by specificity (longest/rarest first so
# 'ข้าพเจ้า' matches before 'ข้า', 'หม่อมฉัน' before 'ฉัน', etc.). Used to
# lock each speaker's pronoun on first translation — prevents pronoun drift
# across long scenes (e.g. Vauthry vs Crystal Exarch where 'ข้า' flipped to
# 'ฉัน' mid-conversation in observed logs).
_PRONOUN_PRIORITY = (
    'หม่อมฉัน', 'ข้าพเจ้า', 'กระผม', 'ดิฉัน',
    'ข้า', 'ผม', 'ฉัน', 'หนู', 'เรา',
)

# ChatType ที่ถือว่าเป็นคนละ "โหมด" → เปลี่ยน conversation
# เช่น จาก Talk (61) → Cutscene (71) = บทสนทนาใหม่
CHATTYPE_GROUPS = {
    'dialogue': {61},           # Talk addon — บทสนทนา NPC ปกติ
    'battle':   {68},           # BattleTalk — คำพูดระหว่าง combat/gameplay
    'cutscene': {71, 0x0045},   # TalkSubtitle + cutscene addons
    'choice':   {0x0046},       # SelectString — ตัวเลือกของผู้เล่น
}

def _get_chattype_group(chat_type: int) -> str:
    """ระบุกลุ่มของ ChatType"""
    for group_name, types in CHATTYPE_GROUPS.items():
        if chat_type in types:
            return group_name
    return 'other'


class ConversationLogger:
    """บันทึกและจัดกลุ่มบทสนทนาจากเกม — always-on in-memory context + optional disk logging"""

    def __init__(self, base_path: Optional[str] = None, enabled: bool = True,
                 disk_logging: bool = False):
        # Logs land NEXT TO the program (project folder in dev, exe dir in
        # frozen build) — keeps them easy to find without digging through
        # %LOCALAPPDATA%. Old logs at AppData are not migrated automatically
        # — they stay where they are; new sessions write to the new path.
        if base_path is None:
            base_path = get_app_dir()

        self.log_dir = os.path.join(base_path, "logs", "conversation_logs")
        self.enabled = enabled
        self.disk_logging = disk_logging  # True = save JSON to disk (debug mode)
        self.logger = logging.getLogger("ConversationLogger")

        # --- Session state ---
        self.session_id: Optional[str] = None
        self.session_start: Optional[float] = None
        self.session_file: Optional[str] = None

        # --- Conversation tracking ---
        self.conversations: List[Dict[str, Any]] = []
        self._current_conv: Optional[Dict[str, Any]] = None
        self._last_message_time: float = 0
        self._last_chattype_group: str = ''
        self._message_count: int = 0

        # --- Abrupt-close safety ---
        # atexit hook runs on normal process exit + sys.exit + unhandled
        # exceptions. Doesn't fire on SIGKILL / taskkill /F — that's covered
        # by per-chunk auto-flush in _close_current_conversation.
        self._atexit_registered = False

        # --- Pronoun lock (session-scoped) ---
        # Maps speaker name → first-person pronoun observed in their first
        # translated line. Injected into context so Gemini keeps the same
        # pronoun for that speaker across all subsequent messages in the
        # session, even past conversation chunk boundaries.
        self._pronoun_lock: Dict[str, str] = {}

        # สร้าง directory เฉพาะเมื่อ disk_logging เปิด
        if self.disk_logging:
            os.makedirs(self.log_dir, exist_ok=True)

    # ========================================
    # Session lifecycle
    # ========================================

    def set_disk_logging(self, enabled: bool):
        """เปิด/ปิด disk logging — เรียกเมื่อ user toggle ใน Settings"""
        self.disk_logging = enabled
        if enabled:
            os.makedirs(self.log_dir, exist_ok=True)
        self.logger.info(f"[ConvLog] Disk logging {'ENABLED' if enabled else 'DISABLED'}")

    def get_log_dir(self) -> str:
        """Absolute path to the disk-logging directory.
        UI uses this to show the path + open the folder."""
        return self.log_dir

    def start_session(self):
        """เริ่ม session ใหม่ — เรียกเมื่อกดปุ่ม Start Translation"""
        if not self.enabled:
            return

        now = time.time()
        self.session_id = datetime.fromtimestamp(now).strftime("%Y%m%d_%H%M%S")
        self.session_start = now
        # สร้าง file path เฉพาะเมื่อ disk_logging เปิดอยู่
        if self.disk_logging:
            self.session_file = os.path.join(
                self.log_dir, f"conv_{self.session_id}.json"
            )
        else:
            self.session_file = None
        self.conversations = []
        self._current_conv = None
        self._last_message_time = 0
        self._last_chattype_group = ''
        self._message_count = 0
        self._pronoun_lock = {}

        mode = "disk+memory" if self.disk_logging else "memory-only"
        self.logger.info(f"[ConvLog] Session started: {self.session_id} ({mode})")

        # Register atexit hook ONCE per logger lifetime — fires on normal
        # process exit (sys.exit, return from main, unhandled exception)
        # so users who close MBB without pressing Stop still get a save.
        # Per-chunk auto-flush covers the SIGKILL case for older chunks.
        if not self._atexit_registered:
            atexit.register(self._atexit_handler)
            self._atexit_registered = True

    def _atexit_handler(self):
        """Last-resort save on abrupt process exit. Guarded — safe to call
        when session already ended (no-op)."""
        try:
            if self.session_id and self.disk_logging:
                self.logger.info("[ConvLog] atexit triggered — flushing session")
                self.end_session()
        except Exception as e:
            # Never raise from atexit
            try:
                self.logger.error(f"[ConvLog] atexit handler error: {e}")
            except Exception:
                pass

    def end_session(self):
        """จบ session — เรียกเมื่อกดปุ่ม Stop Translation"""
        if not self.session_id:
            return

        # ปิด conversation สุดท้าย
        self._close_current_conversation()

        # เขียนไฟล์ JSON เฉพาะเมื่อ disk_logging เปิด
        if self.disk_logging:
            self._save_to_file()

        self.logger.info(
            f"[ConvLog] Session ended: {self.session_id} | "
            f"{len(self.conversations)} conversations, {self._message_count} messages"
        )
        self.session_id = None

    # ========================================
    # Message logging — จุดเชื่อมหลัก
    # ========================================

    def log_message(self, message_data: Dict[str, Any],
                    translated_text: Optional[str] = None):
        """
        บันทึกข้อความจากเกม พร้อม metadata

        เรียกจาก dalamud_immediate_handler.process_message()
        สามารถเรียกอีกครั้งภายหลังพร้อม translated_text เมื่อแปลเสร็จ

        Args:
            message_data: dict จาก Dalamud bridge
                {Type, Speaker, Message, Timestamp, ChatType}
            translated_text: คำแปล (ถ้ามี — จะเติมภายหลังได้)
        """
        if not self.session_id:
            return

        now = time.time()
        speaker = str(message_data.get('Speaker', '')).strip()
        message = str(message_data.get('Message', '')).strip()
        chat_type = message_data.get('ChatType', 0)
        msg_type = message_data.get('Type', '')
        chattype_group = _get_chattype_group(chat_type)

        if not message:
            return

        # --- ตรวจจับ conversation boundary ---
        should_start_new = self._should_start_new_conversation(
            now, chattype_group, speaker
        )

        if should_start_new:
            self._close_current_conversation()
            self._start_new_conversation(now, chattype_group)

        # --- สร้าง message entry ---
        entry = {
            'seq': self._current_conv['message_count'],
            'time': round(now, 3),
            'relative_time': round(now - self._current_conv['start_time'], 2),
            'speaker': speaker,
            'message': message,
            'chat_type': chat_type,
            'chattype_group': chattype_group,
            'msg_type': msg_type,
        }

        if translated_text:
            entry['translated'] = translated_text

        self._current_conv['messages'].append(entry)
        self._current_conv['message_count'] += 1

        # อัพเดท active speakers
        if speaker and speaker not in ('', '???'):
            speakers = self._current_conv['speakers']
            if speaker not in speakers:
                speakers.append(speaker)
            self._current_conv['speaker_count'] = len(speakers)

        # อัพเดท chattype_group ของ conversation เป็น 'mixed' เมื่อมีหลายประเภทปน
        if (chattype_group != 'other'
                and self._current_conv['chattype_group'] != chattype_group
                and self._current_conv['chattype_group'] != 'mixed'):
            self._current_conv['chattype_group'] = 'mixed'

        self._last_message_time = now
        self._last_chattype_group = chattype_group
        self._message_count += 1

    def update_translation(self, original_message: str, translated_text: str):
        """
        เติมคำแปลให้ข้อความที่บันทึกไว้แล้ว + lock สรรพนามครั้งแรกของแต่ละ speaker

        เรียกหลังจาก translate() เสร็จ — match ด้วย original message text
        """
        if not self._current_conv:
            return

        # ค้นหาข้อความล่าสุดที่ตรงกัน (ย้อนจากท้าย)
        for msg in reversed(self._current_conv['messages']):
            if msg['message'] == original_message and 'translated' not in msg:
                msg['translated'] = translated_text

                # Lock first-time pronoun for this speaker (session-scoped).
                # Once locked, all later translations for this speaker get
                # the pronoun memory injected → consistent voice.
                speaker = (msg.get('speaker') or '').strip()
                if (speaker and speaker != '???'
                        and speaker not in self._pronoun_lock):
                    pron = self._detect_first_person_pronoun(translated_text)
                    if pron:
                        self._pronoun_lock[speaker] = pron
                        self.logger.info(
                            f"[ConvLog] Pronoun lock: {speaker} -> {pron}"
                        )
                return

    @staticmethod
    def _detect_first_person_pronoun(text: str) -> Optional[str]:
        """Scan translated text for the speaker's first-person pronoun.

        Returns the first match from _PRONOUN_PRIORITY (longest/most specific
        first), or None if none found. Heuristic — works because Thai dialogue
        typically uses one self-referential pronoun per utterance, and the
        priority order resolves overlaps (ข้าพเจ้า before ข้า, etc.)."""
        if not text:
            return None
        # Strip the leading "Speaker: " prefix if present so we don't match
        # the speaker's NAME accidentally.
        if ':' in text:
            text = text.split(':', 1)[1]
        for p in _PRONOUN_PRIORITY:
            if p in text:
                return p
        return None

    def _format_pronoun_memory(self) -> str:
        """Format locked pronouns as a context hint block for Gemini. Empty
        string when no locks yet (early in session)."""
        if not self._pronoun_lock:
            return ""
        lines = [f"- {speaker}: {pron}"
                 for speaker, pron in self._pronoun_lock.items()]
        return ("[Speakers' established pronouns — MUST keep consistent]\n"
                + "\n".join(lines))

    def log_system_event(self, event_type: str, details: str = ''):
        """
        บันทึก system event — เตรียมไว้สำหรับ scene/zone change detection

        Args:
            event_type: ประเภท event เช่น 'zone_change', 'cutscene_start',
                       'cutscene_end', 'duty_start', 'duty_end'
            details: รายละเอียดเพิ่มเติม เช่น ชื่อ zone
        """
        if not self.session_id:
            return

        now = time.time()

        # System event → จบ conversation เดิมเสมอ
        self._close_current_conversation()

        # บันทึก event เป็น marker ระหว่าง conversations (เฉพาะ disk_logging mode)
        if self.disk_logging:
            event = {
                'type': 'system_event',
                'event_type': event_type,
                'details': details,
                'time': round(now, 3),
            }
            self.conversations.append(event)

        self.logger.info(f"[ConvLog] System event: {event_type} — {details}")

    # ========================================
    # Conversation boundary detection
    # ========================================

    def _should_start_new_conversation(
        self, now: float, chattype_group: str, speaker: str
    ) -> bool:
        """ตรวจสอบว่าควรเริ่ม conversation ใหม่หรือไม่"""

        # ยังไม่มี conversation → เริ่มใหม่แน่นอน
        if self._current_conv is None:
            return True

        # 1. Time gap — เงียบนานเกินไป
        gap = now - self._last_message_time
        if gap > CONVERSATION_GAP_SECONDS:
            self.logger.debug(
                f"[ConvLog] New conv: time gap {gap:.0f}s > {CONVERSATION_GAP_SECONDS}s"
            )
            return True

        # 2. [REMOVED] ChatType group change ไม่ถือเป็น boundary อีกต่อไป
        #    เพราะในเกมมักมี dialogue + battle + cutscene เกิดขึ้นต่อเนื่อง
        #    context ควรไหลข้ามประเภทได้ (boundary จริงคือ time gap + zone change เท่านั้น)

        # 3. ถ้า speaker เกิน CONVERSATION_MAX_SPEAKERS คน → conversation ใหม่
        #    (เพิ่มเป็น 8 เพื่อรองรับ quest ที่มี NPC หลายตัวพูดพร้อมกัน)
        if (speaker and speaker not in ('', '???')
                and speaker not in self._current_conv['speakers']
                and len(self._current_conv['speakers']) >= CONVERSATION_MAX_SPEAKERS):
            self.logger.debug(
                f"[ConvLog] New conv: speaker limit reached ({CONVERSATION_MAX_SPEAKERS}), new speaker '{speaker}'"
            )
            return True

        return False

    def _start_new_conversation(self, start_time: float, chattype_group: str):
        """สร้าง conversation ใหม่"""
        self._current_conv = {
            'conv_id': len(self.conversations),
            'start_time': round(start_time, 3),
            'end_time': None,
            'duration': None,
            'chattype_group': chattype_group,
            'speakers': [],
            'speaker_count': 0,
            'message_count': 0,
            'messages': [],
        }

    def _close_current_conversation(self):
        """ปิด conversation ปัจจุบันและเพิ่มเข้า list.
        Auto-flushes to disk if disk_logging is on — so abrupt MBB close
        only loses the in-flight chunk, not earlier closed chunks."""
        if self._current_conv is None:
            return
        if self._current_conv['message_count'] == 0:
            # ไม่มีข้อความ → ไม่บันทึก
            self._current_conv = None
            return

        self._current_conv['end_time'] = round(self._last_message_time, 3)
        self._current_conv['duration'] = round(
            self._last_message_time - self._current_conv['start_time'], 2
        )
        self.conversations.append(self._current_conv)
        self._current_conv = None

        # Auto-flush each closed chunk — protects against abrupt close (crash,
        # taskkill /F, power loss). Cheap because chunks close every ~1-2 min
        # at typical FFXIV dialogue pace.
        if self.disk_logging:
            try:
                self._save_to_file()
            except Exception as e:
                self.logger.error(f"[ConvLog] Auto-flush error: {e}")

    # ========================================
    # File I/O
    # ========================================

    def _save_to_file(self):
        """เขียน session ลงไฟล์ JSON แบบ atomic (temp + replace).
        Atomic write prevents partial/corrupt files if the process dies
        mid-write — readers always see either the previous valid file
        or the new complete one, never a half-written file."""
        if not self.session_file or not self.conversations:
            return

        session_data = {
            'session_id': self.session_id,
            'session_start': self.session_start,
            'session_start_human': datetime.fromtimestamp(
                self.session_start
            ).strftime("%Y-%m-%d %H:%M:%S"),
            'total_conversations': sum(
                1 for c in self.conversations if c.get('conv_id') is not None
            ),
            'total_messages': self._message_count,
            'total_system_events': sum(
                1 for c in self.conversations if c.get('type') == 'system_event'
            ),
            'conversations': self.conversations,
        }

        tmp_path = self.session_file + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # force OS to flush to disk
            os.replace(tmp_path, self.session_file)  # atomic on Windows + POSIX
            self.logger.info(f"[ConvLog] Saved to {self.session_file}")
        except Exception as e:
            self.logger.error(f"[ConvLog] Save error: {e}")
            # Best-effort cleanup of orphaned temp file
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def save_incremental(self):
        """บันทึกทันทีระหว่างเล่น — เรียกได้ตอนไหนก็ได้ (เฉพาะเมื่อ disk_logging เปิด)"""
        if not self.session_id or not self.disk_logging:
            return

        temp_conv = self._current_conv
        if temp_conv and temp_conv['message_count'] > 0:
            snapshot = dict(temp_conv)
            snapshot['end_time'] = round(self._last_message_time, 3)
            snapshot['duration'] = round(
                self._last_message_time - snapshot['start_time'], 2
            )
            self.conversations.append(snapshot)
            try:
                self._save_to_file()
            finally:
                self.conversations.pop()  # ลบ snapshot ออกเสมอ แม้ save ล้มเหลว
        else:
            self._save_to_file()

    # ========================================
    # Query / stats
    # ========================================

    def get_stats(self) -> Dict[str, Any]:
        """สถิติ session ปัจจุบัน"""
        conv_count = sum(
            1 for c in self.conversations if c.get('conv_id') is not None
        )
        current_speakers = (
            len(self._current_conv['speakers'])
            if self._current_conv else 0
        )
        return {
            'session_id': self.session_id,
            'conversations': conv_count,
            'messages': self._message_count,
            'current_speakers': current_speakers,
            'enabled': self.enabled,
            'disk_logging': self.disk_logging,
        }

    def get_recent_context(self, max_messages: int = 3, exclude_last: bool = True) -> str:
        """
        สร้าง context string จากข้อความล่าสุดใน conversation ปัจจุบัน
        สำหรับ inject เข้า translation prompt เพื่อรักษาความสม่ำเสมอ

        Args:
            max_messages: จำนวนข้อความสูงสุดที่ดึง — handler ส่งตาม chat type (cutscene=4, dialogue=3, battle=skip)
            exclude_last: ตัดข้อความล่าสุดออก (เพราะเป็นข้อความที่กำลังแปล)

        Returns:
            str: formatted context หรือ "" ถ้าไม่มี
        """
        if not self.session_id:
            return ""
        if not self._current_conv or not self._current_conv.get('messages'):
            return ""

        messages = self._current_conv['messages']
        if exclude_last and len(messages) > 0:
            messages = messages[:-1]

        if not messages:
            return ""

        # กรองเอาเฉพาะ dialogue/cutscene/battle ที่มีคำแปลแล้ว
        relevant = []
        for msg in messages:
            if msg.get('chattype_group') == 'other':
                continue  # skip player chat
            translated = msg.get('translated')
            if not translated:
                continue  # skip ข้อความที่ยังไม่มีคำแปล
            relevant.append(msg)

        if not relevant:
            return ""

        # เอาแค่ N ข้อความล่าสุด
        recent = relevant[-max_messages:]

        lines = []
        for msg in recent:
            speaker = msg.get('speaker', '')
            text = msg['translated']

            # ตัดข้อความยาวเกิน 50 chars (ลดจาก 80 เพื่อลด token — pronoun/honorific ยังไม่โดนตัด)
            if len(text) > 50:
                text = text[:47] + "..."

            # ลบ speaker prefix ที่ซ้ำ (translated อาจมี "Speaker: ..." อยู่แล้ว)
            if speaker and text.startswith(f"{speaker}:"):
                text = text[len(speaker) + 1:].strip()

            if speaker:
                lines.append(f"{speaker}: {text}")
            else:
                lines.append(text)

        # Append pronoun memory block (session-scoped, persists across
        # conversation chunks unlike the recent-dialogue window).
        recent_block = "\n".join(lines)
        pronoun_block = self._format_pronoun_memory()
        if pronoun_block:
            return f"{recent_block}\n\n{pronoun_block}"
        return recent_block

    def list_session_files(self) -> List[str]:
        """รายชื่อ session files ทั้งหมด"""
        if not os.path.exists(self.log_dir):
            return []
        files = [
            f for f in os.listdir(self.log_dir)
            if f.startswith('conv_') and f.endswith('.json')
        ]
        files.sort(reverse=True)
        return files
