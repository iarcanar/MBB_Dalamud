# 🧪 Installation Testing Guide

**Version:** 1.0.0
**Purpose:** Quick testing checklist for end-to-end installation

---

## ⚡ Quick Test (5 Minutes)

### Prerequisites
- ✅ Clean FFXIV with Dalamud installed
- ✅ Internet connection
- ✅ Gemini API key ready

---

### Step 1: Add Custom Repository ⏱️ 30 seconds

**Action:**
```
1. เปิดเกม FFXIV
2. พิมพ์: /xlsettings
3. ไปที่แท็บ "Experimental"
4. กด "+" ใน Custom Plugin Repositories
5. วาง URL:
   https://raw.githubusercontent.com/iarcanar/MBB_Dalamud/main/pluginmaster.json
6. กด "Save and Close"
```

**ตรวจสอบ:**
- [ ] URL ถูกบันทึกในรายการ
- [ ] ไม่มี error message

---

### Step 2: Install Plugin ⏱️ 1 minute

**Action:**
```
1. พิมพ์: /xlplugins
2. ค้นหา: "MBB Dalamud Bridge"
3. กด "Install"
4. รอติดตั้งเสร็จ
```

**ตรวจสอบ:**
- [ ] Plugin ปรากฏในรายการค้นหา
- [ ] Icon แสดงถูกต้อง (MBB logo)
- [ ] Description: "Real-time Thai translation for FFXIV"
- [ ] Author: "iarcanar"
- [ ] Version: "1.0.0"
- [ ] ติดตั้งสำเร็จ (ไม่มี error)
- [ ] Plugin อยู่ใน "Installed Plugins" list

---

### Step 3: Download Python App ⏱️ 1 minute

**Action:**
```
1. ไปที่: https://github.com/iarcanar/MBB_Dalamud/releases/latest
2. ดาวน์โหลด: MBB_v1.0.0.zip (72 MB)
3. แตกไฟล์ไปที่: C:\MBB\ (หรือที่ไหนก็ได้)
```

**ตรวจสอบ:**
- [ ] ไฟล์ดาวน์โหลดสำเร็จ (72 MB)
- [ ] แตกไฟล์ได้โดยไม่มี error
- [ ] โครงสร้างไฟล์ถูกต้อง:
  ```
  MBB/
  ├── MBB.exe
  ├── _internal/
  │   ├── fonts/
  │   ├── assets/
  │   └── NPC.json
  └── README.txt
  ```

---

### Step 4: Configure Plugin Path ⏱️ 2 minutes

**Action:**
```
1. ในเกม พิมพ์: /mbb
2. กด "Browse..."
3. เลือก: C:\MBB\MBB.exe
4. กด "Save Path"
5. กด "Launch Python App"
```

**ตรวจสอบ:**
- [ ] Config window เปิดขึ้นมา
- [ ] Browse dialog ทำงาน
- [ ] Path ถูกบันทึก
- [ ] หน้าต่าง MBB app เปิดขึ้นมา (Python app)
- [ ] ไม่มี error "file not found"

---

### Step 5: Set API Key ⏱️ 1 minute

**Action:**
```
1. ในหน้าต่าง MBB app
2. ไปที่ "Settings"
3. วาง Gemini API Key
4. กด "Save"
5. กลับไปหน้าหลัก
6. กด F9 (เริ่มแปล)
```

**ตรวจสอบ:**
- [ ] Settings panel เปิดได้
- [ ] API key ช่องรับ input
- [ ] บันทึกสำเร็จ
- [ ] F9 เริ่ม translation mode
- [ ] Status แสดง "Translating..."

---

### Step 6: Test Translation ⏱️ 30 seconds

**Action:**
```
1. เข้าเกมที่มี NPC dialogue
2. คุยกับ NPC
3. ดู MBB app
```

**ตรวจสอบ:**
- [ ] Text จากเกมปรากฏใน MBB app
- [ ] แปลเป็นภาษาไทยอัตโนมัติ
- [ ] ไม่มี lag/freeze
- [ ] Font แสดงภาษาไทยถูกต้อง

---

## 🔍 Advanced Testing (Optional)

### Hotkey Testing
- [ ] F9 - Start/Stop ทำงาน
- [ ] F10 - Clear screen ทำงาน
- [ ] F11 - Toggle Mini/Full UI ทำงาน

### Theme Testing
- [ ] Settings → Theme → เปลี่ยน theme ได้
- [ ] Themes: Cyberpunk, Ocean, Sunset, Forest, Royal, Rose
- [ ] สีเปลี่ยนถูกต้อง

### NPC Manager Testing
- [ ] เปิด NPC Manager ได้
- [ ] แก้ไข NPC data ได้
- [ ] บันทึกการเปลี่ยนแปลง

### Settings Persistence
- [ ] ปิด MBB app
- [ ] เปิดใหม่
- [ ] Settings ยังคงอยู่ (API key, theme, etc.)

---

## ❌ Common Issues & Solutions

### Issue 1: Plugin ไม่โผล่ใน /xlplugins
**Solution:**
- ตรวจสอบ custom repository URL
- กด "Refresh" ใน plugin installer
- Restart Dalamud

### Issue 2: "MBB.exe not found"
**Solution:**
- ตรวจสอบ path ใน /mbb
- แน่ใจว่าแตกไฟล์ครบทั้งโฟลเดอร์
- อย่าย้ายเฉพาะ MBB.exe (ต้องมี _internal folder ด้วย)

### Issue 3: Translation ไม่ทำงาน
**Solution:**
- ตรวจสอบ API key
- กด F9 เพื่อ start
- ตรวจสอบ internet connection
- ดู log ใน Python app

### Issue 4: Font ไทยไม่แสดง
**Solution:**
- ตรวจสอบ fonts/ folder มีไฟล์
- เปลี่ยน font ใน Settings
- Restart app

### Issue 5: App ไม่เปิด
**Solution:**
- แตกไฟล์ใหม่ (อาจเสียระหว่างดาวน์โหลด)
- ปิด antivirus
- รันเป็น administrator

---

## ✅ Success Criteria

**Pass** ถ้า:
1. ✅ Plugin ติดตั้งผ่าน custom repository
2. ✅ MBB.exe รันได้
3. ✅ API key บันทึกได้
4. ✅ แปลภาษาไทยได้
5. ✅ Hotkeys (F9/F10/F11) ทำงาน
6. ✅ Settings บันทึกหลังปิดเปิดใหม่

**Total Pass Time:** < 5 minutes

---

## 📊 Test Report Template

```
# MBB Installation Test Report

**Date:** [DATE]
**Tester:** [NAME]
**System:** Windows [VERSION]
**FFXIV Version:** [VERSION]

## Test Results

### Phase 1: Repository & Plugin
- [ ] Custom repository added
- [ ] Plugin appeared in installer
- [ ] Plugin installed successfully

### Phase 2: Python App
- [ ] MBB_v1.0.0.zip downloaded
- [ ] Files extracted correctly
- [ ] MBB.exe launched

### Phase 3: Configuration
- [ ] Path configured in /mbb
- [ ] API key set
- [ ] Translation working

### Issues Found
1. [Issue description]
2. [Issue description]

### Overall Status
- [ ] Pass - All tests successful
- [ ] Fail - [describe failures]

**Time Taken:** [X] minutes
```

---

**Next Steps After Testing:**
1. Report any issues on GitHub
2. Share feedback
3. Enjoy real-time Thai translation! 🎮✨

---

**Testing Guide Version:** 1.0.0
**Last Updated:** 2026-01-23
**Repository:** https://github.com/iarcanar/MBB_Dalamud
