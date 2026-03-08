"""
Dalamud IMMEDIATE Handler - แสดงคำแปลทันทีเมื่อได้รับข้อความ
Display translations immediately when messages are received
"""

import logging
from typing import Dict, Any, Optional
import time
import threading

# 🎯 Text Hook Filtering - ALLOW LIST APPROACH (v1.5.4)
# Changed from Block List to Allow List for better control and simpler maintenance
# We ONLY translate what we explicitly want, everything else is blocked by default

ESSENTIAL_CHAT_TYPES = {
    # ✅ DIALOGUE - Main NPC conversations
    61,      # Talk addon dialogue (0x003D)
    68,      # Top chat bubble (0x0044) - แชทระหว่างคัทซีน/คำพูดประกอบระหว่าง gameplay ก่อนคัทซีน

    # ✅ CUTSCENE - Story cutscenes
    71,      # TalkSubtitle addon (0x0047)
}

# 🔴 DEPRECATED - No longer needed with Allow List approach
# Previously had 50+ blocked ChatTypes - now we just allow 2-3 types!

def should_translate_message(message_data):
    """
    Determine if a message should be translated based on ChatType filtering
    Using ALLOW LIST approach - only translate explicitly allowed types

    ตัดสินใจว่าข้อความควรถูกแปลหรือไม่ - ใช้ระบบ Allow List
    แปลเฉพาะ ChatType ที่อนุญาตเท่านั้น ที่เหลือปิดหมด
    """
    chat_type = message_data.get('ChatType', 0)
    message_type = message_data.get('Type', '')

    # 🎯 ALLOW LIST CHECK - Only translate if explicitly allowed
    if chat_type in ESSENTIAL_CHAT_TYPES:
        return True

    # 🎬 Special case: Cutscene type (may come from addon detection)
    if message_type in ['cutscene', 'dialogue', 'battle', 'choice']:
        return True

    # 🚫 DEFAULT: BLOCK ALL OTHER TYPES
    # This is the key change - we block by default instead of allow
    return False


class DalamudImmediateHandler:
    def __init__(self, translator=None, ui_updater=None, main_app=None):
        self.translator = translator
        self.ui_updater = ui_updater
        self.main_app = main_app  # 🔧 Reference to main app for force translate
        self.main_app_ref = main_app  # 🔧 CRITICAL FIX: Also store as main_app_ref for compatibility
        self.translated_logs = None  # เพิ่มการเก็บ reference ไปที่ translated_logs
        self.conversation_logger = None  # ConversationLogger สำหรับ wide-context dev


        # Control flags
        self.is_running = False
        self.is_translating = False

        # Timestamp filtering to prevent translating old messages
        # See: FIX_BACKLOG_TRANSLATION.md for detailed explanation
        self.translation_start_time = None  # Track when translation started

        # Translation cache for speed
        self.translation_cache = {}
        self.cache_max_size = 100

        # Store original text for force translate
        self.last_original_text = None  # Store last original text
        self.last_message_data = None   # Store last message data for force translate

        # Current translation tracking
        self.current_translation_thread = None
        self.translating_messages = set()  # Track messages being translated
        self.current_chat_type = None  # Track current chat type for display mode switching

        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_translated': 0,
            'cache_hits': 0,
            'immediate_displays': 0,
            'errors': 0
        }

        # Logger
        self.logger = logging.getLogger('DalamudImmediateHandler')

    def start(self):
        """Start the handler"""
        if self.is_running:
            return

        self.is_running = True
        self.logger.info("Dalamud IMMEDIATE Handler started - แสดงทันที!")

    def stop(self):
        """Stop the handler"""
        self.is_running = False
        self.is_translating = False
        self.logger.info("Dalamud IMMEDIATE Handler stopped")

    def set_translation_active(self, active: bool):
        """Set translation active state"""
        self.is_translating = active
        if active:
            # Record timestamp when translation starts to filter old messages
            import time
            self.translation_start_time = time.time()
            self.logger.info(f"Translation active: {active} - Start time: {self.translation_start_time}")
        else:
            self.translation_start_time = None
            self.logger.info(f"Translation active: {active}")

    def set_translator(self, translator):
        """Set the translator instance"""
        self.translator = translator
        self.logger.info("Translator set")

    def set_ui_updater(self, ui_updater):
        """Set the UI updater function"""
        self.ui_updater = ui_updater
        self.logger.info("UI updater set")

    def set_translated_logs(self, translated_logs):
        """Set the translated logs instance for history logging"""
        self.translated_logs = translated_logs
        self.logger.info("Translated logs instance set")

    def set_conversation_logger(self, conv_logger):
        """Set ConversationLogger for wide-context-translation development"""
        self.conversation_logger = conv_logger
        self.logger.info("ConversationLogger set")

    def process_message(self, message_data: Dict[str, Any]):
        """
        Process message with IMMEDIATE display
        แสดงคำแปลทันทีเมื่อได้รับข้อความ
        """
        # Input validation - ensure message_data is a dict
        if not isinstance(message_data, dict):
            self.logger.error(f"[SECURITY] Invalid message_data type: {type(message_data)}")
            return

        try:
            # 🔔 SYSTEM EVENT: zone_change etc. → log แล้ว return ทันที (ไม่แปล)
            if message_data.get('Type') == 'system':
                if self.conversation_logger:
                    msg = message_data.get('Message', '')
                    self.conversation_logger.log_system_event('zone_change', msg)
                return

            # 📝 CONVERSATION LOGGER: บันทึกเฉพาะ NPC dialogue/cutscene
            if self.conversation_logger:
                try:
                    log_chat_type = message_data.get('ChatType', 0)
                    if log_chat_type in (61, 68, 71, 0x0045, 0x0046):
                        self.conversation_logger.log_message(message_data)
                except Exception:
                    pass  # ห้ามให้ logger พัง translation pipeline

            # 🚫 TEXT HOOK FILTERING: Check if message should be translated
            chat_type = message_data.get('ChatType', 0)
            self.logger.info(f"[DEBUG FILTER] Checking ChatType {chat_type}")

            # 🚫 BLOCK BATTLE CHAT BY USER SETTING
            if chat_type == 68:
                enable_battle_chat = self.main_app_ref.settings.get("enable_battle_chat_mode", True)
                if not enable_battle_chat:
                    self.logger.info(f"[BLOCKED] Battle Chat (ChatType 68) - disabled in settings")
                    return  # ← EARLY EXIT - NO TRANSLATION, NO DISPLAY

            if not should_translate_message(message_data):
                self.logger.info(f"[FILTERED] ChatType {chat_type} blocked - not translating")
                return

            # 🕐 TIMESTAMP FILTERING: Skip old messages from before translation started
            # This prevents translating messages that were queued before pressing Start
            # See: FIX_BACKLOG_TRANSLATION.md for detailed explanation
            if self.translation_start_time:
                message_timestamp = message_data.get('Timestamp', 0)
                # Convert timestamp from milliseconds to seconds if needed
                if message_timestamp > 1000000000000:  # Likely in milliseconds
                    message_timestamp = message_timestamp / 1000

                if message_timestamp > 0 and message_timestamp < self.translation_start_time:
                    self.logger.info(f"[TIMESTAMP FILTER] Skipping old message from {message_timestamp} (before {self.translation_start_time})")
                    return

            # Create message text with input sanitization
            speaker = str(message_data.get('Speaker', '')).strip()[:100]  # Limit speaker name length
            message = str(message_data.get('Message', '')).strip()[:5000]  # Limit message length
            message_text = f"{speaker}: {message}" if speaker else message

            if not message_text.strip():
                return

            # 🔥 WARMUP MESSAGE FILTER: Skip warmup messages
            if speaker == "System" and ("Welcome to MagicBabel" in message or "MagicBabel Battle Chat Ready" in message):
                self.logger.info(f"[WARMUP] Processing warmup message (won't display errors)")
                # Continue processing for API warmup but don't show errors

            # IMPORTANT: Store original text and data BEFORE checking translation state
            # This ensures force translate always has text to work with
            self.last_original_text = message_text
            self.last_message_data = message_data

            # 📝 ORIGINAL TEXT DISPLAY: Send original text to MBB for status display
            if hasattr(self, 'main_app_ref') and self.main_app_ref:
                try:
                    # Update original text display on status line
                    self.main_app_ref.update_original_text_display(message_text)
                except Exception:
                    pass  # Silently ignore errors to avoid breaking translation flow

            # Force translate functionality has been removed - replaced by previous dialog system

            # Now check if we should process for translation
            if not self.is_running or not self.is_translating:
                return

            if not self.translator or not self.ui_updater:
                return

            self.stats['messages_received'] += 1
            cache_key = hash(message_text)

            self.logger.info(f"[รับข้อความ] #{self.stats['messages_received']}: {message_text[:50]}...")

            # Check cache first - if found, show IMMEDIATELY
            if cache_key in self.translation_cache:
                self.logger.info(f"[CACHE HIT] แสดงคำแปลจาก cache ทันที!")
                self.stats['cache_hits'] += 1
                self._show_immediately(self.translation_cache[cache_key], chat_type)
                return

            # Check if already translating this message
            if cache_key in self.translating_messages:
                self.logger.info(f"[กำลังแปล] ข้อความนี้กำลังแปลอยู่")
                return

            # Start immediate translation
            self.logger.info(f"[เริ่มแปล] เริ่มแปลข้อความใหม่...")
            self.translating_messages.add(cache_key)

            def translate_and_show_immediately():
                try:
                    start_time = time.time()

                    # Detect warmup message
                    is_warmup = (message_data.get('Speaker') == 'System' and
                                 'MagicBabel' in message_data.get('Message', ''))

                    if is_warmup:
                        self.logger.info("🔥 [WARMUP] Processing warmup through pipeline")

                    # Update status to show TRANSLATING
                    if hasattr(self, 'main_app_ref') and self.main_app_ref:
                        try:
                            self.main_app_ref._translating_in_progress = True
                            self.main_app_ref.safe_after(0, self.main_app_ref.update_info_label_with_model_color)
                        except Exception:
                            pass

                    # Translate — detect choice type and use dedicated method
                    is_choice = (message_data.get('Type', '') == 'choice')
                    if is_choice:
                        # Convert pipe format to newline format for translate_choice()
                        # C# sends: "What will you say? | Choice1 | Choice2"
                        # translate_choice() expects: "What will you say?\nChoice1\nChoice2"
                        choice_text = message_text.replace(" | ", "\n") if " | " in message_text else message_text
                        self.logger.info(f"🎯 [CHOICE] Using translate_choice() for: {choice_text[:80]}")
                        translated_text = self.translator.translate_choice(choice_text)
                    else:
                        # Wide-context: ดึง context จาก conversation logger
                        # Opt1: ลด context size — cutscene=4, dialogue=3, battle=skip
                        # Opt2: smart skip — battle ไม่ส่ง context (ประโยคสั้น standalone)
                        conversation_context = ""
                        if self.conversation_logger and chat_type != 68:
                            try:
                                ctx_messages = 4 if chat_type == 71 else 3
                                conversation_context = self.conversation_logger.get_recent_context(
                                    max_messages=ctx_messages, exclude_last=True
                                )
                            except Exception:
                                conversation_context = ""

                        translated_text = self.translator.translate(
                            message_text,
                            chat_type=chat_type,
                            conversation_context=conversation_context
                        )

                    translation_time = time.time() - start_time

                    if is_warmup:
                        self.logger.info(f"🔥 [WARMUP] First translation: {translation_time:.2f}s")
                    else:
                        self.logger.info(f"[แปลเสร็จ] ใช้เวลา {translation_time:.2f}s: {translated_text[:50]}...")

                    # 📝 CONVERSATION LOGGER: เติมคำแปลที่ได้
                    if self.conversation_logger:
                        try:
                            self.conversation_logger.update_translation(
                                message, translated_text
                            )
                        except Exception:
                            pass

                    # Cache result
                    self.translation_cache[cache_key] = translated_text
                    if len(self.translation_cache) > self.cache_max_size:
                        first_key = next(iter(self.translation_cache))
                        del self.translation_cache[first_key]

                    self.stats['messages_translated'] += 1

                    # CRITICAL: Show IMMEDIATELY if still translating
                    if self.is_translating and self.is_running:
                        self.logger.info(f"[แสดงทันที] แสดงคำแปลทันที (ChatType {chat_type})!")
                        self._show_immediately(translated_text, chat_type)

                        # *** ADD TO HISTORY: เพิ่มข้อความแปลจริงลงใน history สำหรับ Previous Dialog ***
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                if hasattr(self.main_app_ref, 'add_to_dialog_history'):
                                    # Extract speaker and message from original
                                    speaker = message_data.get('Speaker', 'Unknown')
                                    self.main_app_ref.add_to_dialog_history(
                                        original_text=message_text,
                                        translated_text=translated_text,
                                        speaker=speaker,
                                        chat_type=message_data.get('ChatType')
                                    )
                                    self.logger.info(f"📄 [REAL HISTORY] Added real translation for '{speaker}'")
                            except Exception as e:
                                self.logger.error(f"❌ [REAL HISTORY] Error adding to history: {e}")

                        # TUI AUTO-SHOW: Trigger directly after successful translation
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                if hasattr(self.main_app_ref, '_trigger_tui_auto_show'):
                                    self.main_app_ref._trigger_tui_auto_show()
                            except Exception:
                                pass

                        # 🔧 FORCE STATUS UPDATE: Update main UI status back to READY
                        if hasattr(self, 'main_app_ref') and self.main_app_ref:
                            try:
                                self.main_app_ref._translating_in_progress = False
                                self.main_app_ref.safe_after(0, self.main_app_ref.update_info_label_with_model_color)
                            except:
                                pass
                    else:
                        self.logger.warning(f"[ไม่แสดง] ระบบปิดแล้ว")

                except Exception as e:
                    self.stats['errors'] += 1
                    self.logger.error(f"Translation error: {e}")
                finally:
                    # Clean up tracking
                    self.translating_messages.discard(cache_key)

                    # 🔧 ENSURE CLEANUP: Always clear translating status on completion
                    if hasattr(self, 'main_app_ref') and self.main_app_ref:
                        try:
                            if hasattr(self.main_app_ref, '_translating_in_progress'):
                                self.main_app_ref._translating_in_progress = False
                                self.main_app_ref.safe_after(0, self.main_app_ref.update_info_label_with_model_color)
                        except:
                            pass

            # Start translation thread immediately
            thread = threading.Thread(
                target=translate_and_show_immediately,
                daemon=True,
                name=f"ImmediateTranslate-{time.time()}"
            )
            thread.start()

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Error processing message: {e}")

    def _show_immediately(self, text: str, chat_type: int = None):
        """แสดงข้อความทันทีใน UI โดย schedule ลง main thread"""
        try:
            self.stats['immediate_displays'] += 1
            self.logger.info(f"[UI UPDATE] แสดงใน UI (ChatType {chat_type}): {text[:50]}...")

            # Schedule UI update on main thread (Tkinter calls must be on main thread)
            if hasattr(self, 'main_app_ref') and self.main_app_ref and hasattr(self.main_app_ref, 'safe_after'):
                self.main_app_ref.safe_after(0, lambda: self._do_show_on_main_thread(text, chat_type))
            else:
                # Fallback: try direct call (will fail from bg thread with PyQt6)
                self._do_show_on_main_thread(text, chat_type)

        except Exception as e:
            self.logger.error(f"[UI ERROR] ไม่สามารถแสดง UI: {e}")

    def _do_show_on_main_thread(self, text: str, chat_type: int = None):
        """Actual UI update logic - must run on main thread."""
        try:
            if hasattr(self.ui_updater, '__call__'):
                self.ui_updater(text, chat_type)
                self.logger.info(f"[UI SUCCESS] เรียกฟังก์ชัน UI สำเร็จ (ChatType {chat_type})")
            else:
                self.ui_updater.update_text(text, chat_type=chat_type)
                self.logger.info(f"[UI SUCCESS] เรียกเมธอด update_text สำเร็จ (ChatType {chat_type})")

            # ส่งข้อมูลไปที่ translated_logs
            if self.translated_logs and hasattr(self.translated_logs, 'add_message'):
                try:
                    self.translated_logs.add_message(text)
                    self.logger.info(f"[LOGS SUCCESS] ส่งข้อมูลไป translated_logs สำเร็จ")
                except Exception as logs_error:
                    self.logger.error(f"[LOGS ERROR] ไม่สามารถส่งไป translated_logs: {logs_error}")

        except Exception as e:
            self.logger.error(f"[UI ERROR] ไม่สามารถแสดง UI: {e}")

    def force_sync(self):
        """
        Force sync - not needed for immediate mode but kept for compatibility
        ไม่จำเป็นในโหมดทันที แต่เก็บไว้เพื่อความเข้ากันได้
        """
        self.logger.info(f"[FORCE SYNC] ไม่จำเป็นในโหมดทันที")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'is_translating': self.is_translating,
            'cache_size': len(self.translation_cache),
            'translating_count': len(self.translating_messages)
        }

    def clear_cache(self):
        """Clear translation cache"""
        self.translation_cache.clear()
        self.translating_messages.clear()
        self.logger.info("Translation cache cleared")

    def force_clear_cache(self):
        """Clear cache specifically for force translate"""
        if self.last_original_text:
            cache_key = hash(self.last_original_text)
            if cache_key in self.translation_cache:
                del self.translation_cache[cache_key]
                self.logger.info(f"[FORCE CLEAR] Cleared cache for force translate")
            # Also remove from translating messages if present
            self.translating_messages.discard(cache_key)
        else:
            self.logger.warning("[FORCE CLEAR] No original text to clear cache for")

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'messages_received': 0,
            'messages_translated': 0,
            'cache_hits': 0,
            'immediate_displays': 0,
            'errors': 0
        }
        self.logger.info("Statistics reset")


# Factory function
def create_dalamud_immediate_handler(translator=None, ui_updater=None, main_app=None) -> DalamudImmediateHandler:
    """Create and configure a DalamudImmediateHandler instance"""
    handler = DalamudImmediateHandler(translator, ui_updater, main_app)
    return handler