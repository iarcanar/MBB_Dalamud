# 🌐 MBB — Magicite Babel Bridge

**FFXIV ↔ Thai real-time translator** ขับเคลื่อนด้วย Gemini AI

**Version:** 1.8.2

---

## 📦 สิ่งที่คุณต้องมี

ก่อนเริ่มติดตั้ง:
- ✅ **FFXIV** ติดตั้งและเล่นได้ปกติ
- ✅ **XIVLauncher** (พร้อม Dalamud) — [ดาวน์โหลด](https://goatcorp.github.io/)
- ✅ **Gemini API key** ฟรี — [สมัครที่นี่](https://aistudio.google.com/app/apikey) (ใช้บัญชี Google)
- ✅ **Windows 10/11** 64-bit

---

## 📥 ดาวน์โหลด

ไฟล์เดียวจบ:

```
MBB-1.8.2-Full.rar  (~80-100 MB)
```

ดาวน์โหลดจาก: [ลิงก์เว็บไซต์/Release page]

---

## 🚀 ขั้นตอนติดตั้ง (4 ขั้น — ทำครั้งเดียว)

### ① แตกไฟล์

แตก `MBB-1.8.2-Full.rar` ไปวางที่ใดก็ได้บนเครื่องคุณ เช่น
- `D:\MBB\`
- `C:\Games\MBB\`
- `Documents\MBB\`

> **ห้ามวางใน Program Files** เพราะ Windows จำกัดสิทธิ์เขียนไฟล์ (settings/log จะ save ไม่ได้)

โครงสร้างหลังแตกไฟล์:
```
MBB\
├── MBB.exe                    ← โปรแกรมหลัก
├── _internal\                 ← Python runtime (ห้ามลบ)
├── plugin\                    ← Dalamud plugin
│   ├── DalamudMBBBridge.dll
│   ├── DalamudMBBBridge.json
│   └── icon.png
├── settings.json
└── ...
```

---

### ② ติดตั้ง Dalamud Plugin

เปิด FFXIV เข้าเกมจนถึงหน้า lobby/character select ก็ได้, แล้ว:

1. เปิด chat พิมพ์: **`/xlsettings`**
2. คลิกแท็บ **"Experimental"**
3. หา **"Dev Plugin Locations"**
4. คลิก **"+"** เพิ่มแถวใหม่
5. คลิก **"..."** browse → เลือก folder **`plugin\`** ที่อยู่ในโฟลเดอร์ MBB ที่แตกไว้

   ตัวอย่าง: `D:\MBB\plugin`

6. คลิก **"Save and Close"**
7. พิมพ์ **`/xlplugins`** → คลิก **"Scan Dev Plugins"** (ปุ่มล่าง)

ถ้าสำเร็จ จะเห็น plugin ชื่อ **"Magicite Babel Bridge"** ในรายการ (ที่แท็บ "Dev Tools")

---

### ③ ตั้งค่า Path ของ MBB.exe

ใน FFXIV chat:

1. พิมพ์ **`/mbb`**
2. หาส่วน **"📁 MBB Path Configuration"**
3. คลิก **"Browse..."** → ไปที่ folder MBB → เลือกไฟล์ **`MBB.exe`**
4. คลิก **"Save Path"**

ถ้าตั้งถูก จะแสดงสถานะปกติ (ไม่มีคำว่า "File not found")

---

### ④ เปิด MBB ครั้งแรก + ใส่ API Key

1. กด **"Launch MBB Application"** ในหน้าต่าง `/mbb`
   - หรือ double-click `MBB.exe` ในโฟลเดอร์ก็ได้
2. ครั้งแรกจะมีหน้าต่างขอ **Gemini API Key**
   - วาง API key ที่สมัครไว้ → กด OK
   - Key จะถูกเก็บใน `C:\Users\<ชื่อคุณ>\AppData\Local\MBB_Dalamud\.env`
3. โปรแกรม MBB เปิดขึ้น
4. กลับไปใน FFXIV → พิมพ์ **`/mbb status`** → ควรเห็น **"Connected"**

---

## 🎮 วิธีใช้งาน

### ปุ่มลัดเริ่มต้น
- **F9** — เริ่ม/หยุด แปล
- **F10** — ซ่อน/แสดง UI แปล (TUI)

### เริ่มแปล
1. เปิด MBB.exe
2. กด F9 (หรือคลิกปุ่ม Start ใน MBB)
3. คุยกับ NPC ในเกม → คำแปลภาษาไทยจะปรากฏที่ TUI overlay ทันที

### Commands ใน FFXIV chat
| คำสั่ง | ผล |
|---|---|
| `/mbb` | เปิดหน้าต่าง config |
| `/mbb launch` | เปิด MBB.exe จาก path ที่ตั้งไว้ |
| `/mbb status` | ตรวจสถานะการเชื่อมต่อ |
| `/mbb help` | ดูคำสั่งทั้งหมด |

> **Tip:** เพิ่มคำสั่งเหล่านี้ใน FFXIV Macro Editor เพื่อกดจาก hotbar ได้สะดวก

---

## ❓ Troubleshooting

### Plugin ไม่โผล่หลัง Scan Dev Plugins
- ตรวจ path ที่ใส่ใน Dev Plugin Locations ต้องเป็น **folder `plugin\`** ไม่ใช่ DLL ตรงๆ
- Restart Dalamud (`/xlrestart`)

### `/mbb status` แสดง "Not Connected"
- เช็คว่า MBB.exe เปิดอยู่ (ดูที่ taskbar)
- ใน MBB.exe → Settings → ติ๊ก **"Dalamud Mode"**
- กด F9 เริ่มแปล

### MBB.exe ปิดตัวเอง / ไม่เปิด
- เช็คว่าวาง folder MBB **ไม่ใช่ใน Program Files**
- ลอง run as administrator
- ดู log ที่ `MBB_errors.log` ใน folder MBB
- โพสต์ log ใน Discord support เพื่อขอความช่วยเหลือ

### "API key invalid"
- ตรวจ key ที่ [aistudio.google.com](https://aistudio.google.com/app/apikey)
- ลบ `.env` ที่ `C:\Users\<ชื่อ>\AppData\Local\MBB_Dalamud\.env` แล้วเปิด MBB.exe ใหม่ จะถามอีกครั้ง

### คำแปลช้า / ติดๆขัดๆ
- เช็คอินเทอร์เน็ต (Gemini API ต้อง online)
- เปลี่ยน model เป็น `gemini-2.5-flash-lite` ใน Settings (เร็วสุด)
- ลด `max_tokens` ใน Settings (default 500 → ลองใช้ 300)

### Dalamud บอก "outdated API level"
- รอเวอร์ชั่นใหม่ของ MBB หรือ
- ตรวจว่า Dalamud อัพเดตล่าสุด — ถ้าใหม่กว่า MBB อาจต้องรอ release ถัดไป

---

## 🔄 อัพเดต MBB เวอร์ชั่นใหม่

1. ปิด MBB.exe + ปิด FFXIV
2. ลบ folder MBB เก่า (เก็บ `settings.json` ไว้ก่อน)
3. แตก rar เวอร์ชั่นใหม่ที่ path เดิม
4. คัดลอก `settings.json` กลับเข้ามา
5. เปิด FFXIV → `/xlplugins` → "Scan Dev Plugins"
6. เริ่มใช้งานได้ทันที (Path + API key เดิมยังใช้ได้)

---

## 📞 Support

- **Discord:** [link]
- **GitHub Issues:** [link]
- **Author:** iarcanar

---

## 📜 License & Credits

- **MBB** by iarcanar — MIT License
- **Translation engine:** Google Gemini AI
- **Plugin framework:** [Dalamud](https://github.com/goatcorp/Dalamud) by goatcorp
- **Bundled fonts:** Anuphan, FC Minimal, Caveat (OFL)
- ตัวละคร + ฉาก FFXIV เป็นทรัพย์สินของ Square Enix — โครงการนี้เป็น fan tool ที่ไม่มีส่วนเกี่ยวข้องกับ Square Enix

---

**Magicite Babel Bridge v1.8.2** — แปล FFXIV เป็นภาษาไทยแบบ real-time
