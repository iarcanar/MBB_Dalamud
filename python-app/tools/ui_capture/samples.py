"""Sample content fed into each UI for the capture (offline — no Gemini).

Kept here so the look of the captured art is easy to tweak in one place.
Speakers are real essential characters so the TUI/overlay styles them correctly.
"""

# Speaker names the dialog TUI should recognise + style (cyan known-speaker).
CHARACTER_NAMES = {
    "Y'shtola", "Alphinaud", "Alisaie", "Thancred", "Estinien",
    "Wuk Lamat", "G'raha Tia", "Krile", "Urianger", "Emet-Selch",
}

# Dialogue TUI (ChatType 61) — "Speaker: dialogue" format.
DIALOG = "Y'shtola: ในที่สุดเราก็มาถึงจุดนี้... อย่าประมาทศัตรูที่อยู่เบื้องหน้านะ"

# Battle overlay (ChatType 68).
BATTLE_SPEAKER = "Zenos"
BATTLE_TEXT = "เจ้าคือผู้ที่ข้าตามหามาตลอด... มาเถิด ให้เราเต้นรำกันอีกครั้ง!"

# Cutscene overlay (ChatType 71) — narration, no speaker.
CUTSCENE_TEXT = "แสงดาวสาดส่องเหนือผืนนภา ราวกับว่าทั้งจักรวาลกำลังเฝ้ามองชะตากรรมของพวกเขา"

# Choice overlay (ChatType 70).
CHOICE_HEADER = "คุณจะพูดว่าอย่างไร?"
CHOICE_OPTIONS = [
    "• ข้าพร้อมจะสู้เคียงข้างเจ้า",
    "• ขอเวลาคิดสักครู่",
    "• เรื่องนี้มันเกินกำลังของข้า",
]

# Translated Logs — a short conversation as it would appear in history.
LOG_MESSAGES = [
    "Alphinaud: เราต้องรีบไปยังเมืองหลวงก่อนที่ทุกอย่างจะสายเกินไป",
    "Alisaie: พี่ชายพูดถูก ฉันจะไปด้วย ไม่ว่าอันตรายแค่ไหน",
    "Y'shtola: ระวังตัวด้วย พลังที่เรารู้สึกได้นั้นไม่ธรรมดาเลย",
    "Estinien: หึ... ในที่สุดก็ได้เวลาที่น่าสนใจเสียที",
    "Thancred: อย่าได้ประมาท ศัตรูครั้งนี้ต่างจากที่เคยเจอมา",
]
