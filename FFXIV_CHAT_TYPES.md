# FFXIV Chat Types Reference — MBB Development Guide

> **วัตถุประสงค์:** คู่มืออ้างอิง ChatType ทั้งหมดในเกม FFXIV สำหรับพัฒนาระบบกรองข้อความ
> **แหล่งข้อมูล:** Dalamud XivChatType enum + ข้อมูลจาก Log Filters ในเกม + การทดสอบจริง
> **อัปเดตล่าสุด:** 2026-02-27

---

## 1. Dalamud XivChatType Enum — ค่าทางการ

ค่าจาก [`Dalamud/Game/Text/XivChatType.cs`](https://github.com/goatcorp/Dalamud/blob/master/Dalamud/Game/Text/XivChatType.cs)

| Value | Hex | Enum Name | คำอธิบาย |
|-------|-----|-----------|---------|
| 0 | 0x00 | None | ไม่มีประเภท |
| 1 | 0x01 | Debug | Debug messages |
| 2 | 0x02 | Urgent | ข้อความด่วน |
| 3 | 0x03 | Notice | ข้อความแจ้งเตือน |
| 10 | 0x0A | Say | พูดทั่วไป (ผู้เล่น) |
| 11 | 0x0B | Shout | ตะโกน |
| 12 | 0x0C | TellOutgoing | กระซิบ (ส่งออก) |
| 13 | 0x0D | TellIncoming | กระซิบ (รับเข้า) |
| 14 | 0x0E | Party | ปาร์ตี้ |
| 15 | 0x0F | Alliance | พันธมิตร |
| 16-23 | 0x10-17 | Ls1-Ls8 | Linkshell 1-8 |
| 24 | 0x18 | FreeCompany | Free Company |
| 27 | 0x1B | NoviceNetwork | เครือข่ายมือใหม่ |
| 28 | 0x1C | CustomEmote | อิโมทกำหนดเอง |
| 29 | 0x1D | StandardEmote | อิโมทมาตรฐาน |
| 30 | 0x1E | Yell | ตะโกนดัง |
| 32 | 0x20 | CrossParty | ปาร์ตี้ข้ามเซิร์ฟเวอร์ |
| 36 | 0x24 | PvPTeam | ทีม PvP |
| 37 | 0x25 | CrossLinkShell1 | Cross-world Linkshell 1 |
| 56 | 0x38 | Echo | Echo (ข้อความส่วนตัว) |
| 57 | 0x39 | SystemMessage | ข้อความระบบ |
| 58 | 0x3A | SystemError | ข้อผิดพลาดระบบ |
| 59 | 0x3B | GatheringSystemMessage | ข้อความระบบเก็บของ |
| 60 | 0x3C | ErrorMessage | ข้อความแสดงข้อผิดพลาด |
| **61** | **0x3D** | **NPCDialogue** | **บทสนทนา NPC (Talk addon)** |
| **68** | **0x44** | **NPCDialogueAnnouncements** | **ประกาศ NPC / คำพูดระหว่าง gameplay** |
| 71 | 0x47 | RetainerSale | แจ้งเตือนขายของ Retainer |
| 101-107 | 0x65-6B | CrossLinkShell2-8 | Cross-world Linkshell 2-8 |

> **หมายเหตุ:** Enum นี้ไม่ครอบคลุมทุก ChatType ที่เกมส่งจริง — ค่าที่มากกว่า 107
> ส่วนใหญ่เป็น combat/system messages ที่ไม่มีชื่อใน enum (ดูหมวด 3)

---

## 2. In-Game Log Filter Categories — หมวดหมู่จากเมนูในเกม

### 2A. System Messages (ข้อความระบบ)

| หมวด (In-Game) | ChatType(s) | หมายเหตุ |
|----------------|-------------|---------|
| System Messages | 57 | เปลี่ยนอาชีพ, เปลี่ยนอุปกรณ์, ข้อความระบบทั่วไป |
| Own Battle System Messages | 2092, 2729, 2221, 2874 | ผู้เล่นโจมตี/คริติคอล/ดูดเลือด/ชนะ |
| Others' Battle System Messages | 4139, 4777, 12457 | สมาชิกปาร์ตี้/ศัตรูโจมตี |
| Gathering System Messages | 59 | ข้อความระบบเก็บของ |
| Error Messages | 58, 60 | ข้อผิดพลาดต่างๆ |
| Echo | 56 | ข้อความ Echo ส่วนตัว |
| Novice Network Notifications | 27 (system) | ประกาศเครือข่ายมือใหม่ |
| Free Company Announcements | 24 (system) | ประกาศ FC |
| PvP Team Announcements | 36 (system) | ประกาศทีม PvP |
| Retainer Sale Notifications | 71 | แจ้งเตือน Retainer ขายของสำเร็จ |
| **NPC Dialogue** | **61** | **บทสนทนา NPC หลัก — แปลโดย MBB** |
| **NPC Dialogue (Announcements)** | **68** | **ประกาศ/คำพูด NPC — แปลโดย MBB** |
| Loot Notices | 69 (est.) | แจ้งเตือนของดรอป |
| Own Progression Messages | 70 (est.) | ข้อความเลเวลอัป/ความก้าวหน้าตัวเอง |
| Others' Progression Messages | — | ข้อความเลเวลอัปของผู้อื่น |
| Others' Loot Messages | — | ข้อความได้ของของผู้อื่น |
| Synthesis Messages | — | ข้อความคราฟต์ |
| Gathering Messages | — | ข้อความเก็บของ |
| Fishing Messages | — | ข้อความตกปลา |
| Recruitment Notifications | — | ข้อความรับสมัคร Party Finder |
| Sign Messages | — | ข้อความ Sign/Waymark |
| Random Number Messages | — | ผลลัพธ์ /random |
| Orchestrion Track Messages | — | แจ้งเพลง Orchestrion |
| Message Book Alert | — | แจ้งเตือน Message Book |
| Alarm Notifications | — | ข้อความนาฬิกาปลุก |

> **"—"** = ChatType ที่แน่ชัดยังไม่ได้ทดสอบ ต้อง enable ใน C# debug log แล้วตรวจสอบ

### 2B. Chat (แชทผู้เล่น)

| หมวด (In-Game) | ChatType | Hex | หมายเหตุ |
|----------------|----------|-----|---------|
| Say | 10 | 0x0A | พูดทั่วไป |
| Yell | 30 | 0x1E | ตะโกนดัง |
| Shout | 11 | 0x0B | ตะโกน (พื้นที่กว้าง) |
| Tell | 12, 13 | 0x0C-0D | กระซิบ (ส่ง/รับ) |
| Party | 14 | 0x0E | ปาร์ตี้ |
| Alliance | 15 | 0x0F | พันธมิตร |
| Free Company | 24 | 0x18 | FC แชท |
| PvP Team | 36 | 0x24 | ทีม PvP |
| Novice Network | 27 | 0x1B | เครือข่ายมือใหม่ |
| Cross-world Linkshell 1 | 37 | 0x25 | CWLS 1 |
| Cross-world Linkshell 2-8 | 101-107 | 0x65-6B | CWLS 2-8 |
| Linkshell 1-8 | 16-23 | 0x10-17 | LS 1-8 |
| Standard Emotes | 29 | 0x1D | อิโมทมาตรฐาน |
| Custom Emotes | 28 | 0x1C | อิโมทกำหนดเอง |

---

## 3. Extended ChatTypes — ค่าที่พบจากการทดสอบจริง

ChatTypes เหล่านี้ไม่อยู่ใน XivChatType enum แต่เกมส่งมาจริง (ส่วนใหญ่เป็น combat)

### 3A. Combat Messages (ถูก Block ใน C#)

| Value | คำอธิบาย | ตัวอย่าง |
|-------|---------|---------|
| 2091-2092 | Player actions | "You use a bowl of mesquite soup" |
| 2105 | Equipment messages | "Ceremonial bangle of aiming unequipped" |
| 2221 | HP absorption | "You absorb X HP" |
| 2729 | Critical hits | "Critical! You hit X for Y damage" |
| 2735 | Status effects | "suffers the effect of" |
| 2857 | Combat damage | "You hit Necron for X damage" |
| 2874 | Victory messages | "You defeat X" |
| 4139 | Ability casting | "Krile begins casting" |
| 4398 | Status gained | "gains the effect of" |
| 4400 | Status lost | "loses the effect of" |
| 4777 | Damage taken | "Necron takes X damage" |
| 9001 | Striking dummy damage | "The striking dummy takes X damage" |
| 9002 | Combat immunity | "The striking dummy is unaffected" |
| 9007 | Status application | "suffers the effect of" |
| 10283 | Spell interruption | "begins casting, is interrupted" |
| 10929 | Status recovery | "recovers from the effect of" |
| 12331 | NPC/Monster casting | "begins casting, casts" |
| 12457 | Enemy damage to player | "Necron hits you for X damage" |
| 13105 | Status recovery (alt) | "recovers from the effect of" |

### 3B. Cutscene/Dialogue — ค่าพิเศษ

| Value | Hex | คำอธิบาย | สถานะใน MBB |
|-------|-----|---------|------------|
| **61** | **0x3D** | NPC Talk dialog (main dialogue box) | ✅ ESSENTIAL — แปล |
| **68** | **0x44** | NPC chat during gameplay/cutscene | ✅ ESSENTIAL — แปล |
| **71** | **0x47** | Cutscene subtitle text | ✅ ESSENTIAL — แปล |

> **ข้อสังเกต ChatType 71:** Dalamud enum ระบุว่าเป็น `RetainerSale` แต่จากการทดสอบจริง
> พบว่ามี **cutscene subtitle** มาด้วย เช่น "Or was it a gift─the terminal's parting miracle?"
> เดิม block ไว้ แล้ว remove ออกเมื่อค้นพบว่ามี story text (v1.4.8.1)

---

## 4. MBB Filter Architecture — สถาปัตยกรรมการกรอง 2 ชั้น

### ชั้นที่ 1: C# Plugin (DalamudMBBBridge.cs)

```
ข้อความเข้ามา → [DEBUG-FILTER] log → blockedTypes check → ส่งต่อ / ทิ้ง
```

- **Block List** approach — block เฉพาะ combat/system spam
- ข้อความที่ไม่ถูก block จะถูกส่งผ่าน named pipe ไปยัง Python
- ChatType 0x003D (61) ถูก **exclude จาก chat handler** เพราะมี dedicated Talk addon handler

### ชั้นที่ 2: Python (dalamud_immediate_handler.py)

```
ข้อความจาก pipe → ESSENTIAL_CHAT_TYPES check → แปล / ทิ้ง
```

- **Allow List** approach — แปลเฉพาะ 3 ประเภท: `{61, 68, 71}`
- ทุกอย่างอื่นถูกปฏิเสธโดยอัตโนมัติ

### Flow Diagram

```
FFXIV Game
    │
    ├─ Talk Addon (0x3D/61) ──→ OnTalkAddonPreReceive() ──→ Pipe ──→ Python ✅
    │
    └─ Chat Message (all others)
         │
         ├─ blockedTypes? ──→ DROP (combat spam)
         │
         └─ NOT blocked ──→ Pipe ──→ Python
                                      │
                                      ├─ ChatType ∈ {61,68,71}? ──→ TRANSLATE ✅
                                      │
                                      └─ อื่นๆ ──→ DROP (Python allow list)
```

---

## 5. ChatTypes ที่อาจเป็นประโยชน์ในอนาคต

| Value | ชื่อ | เหตุผลที่อาจเป็นประโยชน์ |
|-------|------|------------------------|
| 57 | SystemMessage | ตรวจจับ zone change ("You arrive at ...") |
| 56 | Echo | ข้อความ quest objective / duty info |
| 10 | Say | แปลแชทผู้เล่น (ถ้าต้องการ) |
| 29 | StandardEmote | ตรวจจับ emote ที่มีข้อความ |
| 3 | Notice | ตรวจจับ duty/instance entry |

> **ChatType 57 สำหรับ Zone Change:**
> ปัจจุบันถูก block ใน C# (line 296) — ถ้าต้องการใช้เพื่อตรวจจับการเปลี่ยนพื้นที่
> ต้อง unblock แล้วกรองที่ Python side แทน หรือใช้ Dalamud `IClientState.TerritoryChanged` event

---

## 6. Legacy Blocked Types (Safety Block)

ค่าเหล่านี้ถูก block ไว้ตั้งแต่ v1.4 โดยไม่มี comment อธิบาย — เก็บไว้เผื่อเจอปัญหา

```
2091, 2110, 2218, 2219, 2220, 2222, 2224, 2233, 2235, 2240, 2241, 2242,
2265, 2266, 2267, 2283, 2284, 2285, 2317, 2318, 2730, 2731, 3001,
8235, 8745, 8746, 8747, 8748, 8749, 8750, 8752, 8754,
10409, 10410, 10411, 10412, 10413
```

---

*Reference: [Dalamud XivChatType Source](https://github.com/goatcorp/Dalamud/blob/master/Dalamud/Game/Text/XivChatType.cs)*
*Reference: [Dalamud API Docs](https://dalamud.dev/api/Dalamud.Game.Text/Enums/XivChatType/)*
