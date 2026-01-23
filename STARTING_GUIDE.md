# 🚀 คู่มือเริ่มต้นใช้งาน MBB Dalamud Bridge v1.5.2

<div align="center">

🎮 **การแปลภาษาไทยแบบเรียลไทม์สำหรับ Final Fantasy XIV**

[![Version](https://img.shields.io/badge/Version-1.5.2-blue.svg)](#)
[![FFXIV](https://img.shields.io/badge/FFXIV-Compatible-green.svg)](#)
[![Dalamud](https://img.shields.io/badge/Dalamud-Plugin-purple.svg)](#)

</div>

---

## 📦 ขั้นตอนการติดตั้งครั้งแรก

### 🗂️ **ขั้นตอนที่ 1: แตกไฟล์**
1. 📥 ดาวน์โหลดไฟล์ `MbbDalamud_bridge.RAR`
2. 📁 แตกไฟล์ลงใน **ไดรฟ์ C:** โดยตรง
   ```
   📂 C:\MbbDalamud_bridge\
   ```

### 🎮 **ขั้นตอนที่ 2: เปิด Final Fantasy XIV**
เปิดเกมส์ FFXIV ผ่าน XIVLauncher (สามารถเปิดก่อนหรือหลังก็ได้)

### 🔌 **ขั้นตอนที่ 3: ติดตั้ง Plugin**

1. **📋 เรียกหน้าต่าง Plugin Manager:**
   - พิมพ์คำสั่ง: `/xlplugins` ในแชท
   - หรือเปิดผ่าน XIVLauncher Settings

2. **⚙️ เข้าแท็บ Experimental:**
   - คลิกแท็บ **"Experimental"**
   - ค้นหาช่อง **"Add Plugin Repository"**

3. **📋 Copy Path Plugin:**
   ```
   🗂️ C:\MbbDalamud_bridge\dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64\DalamudMBBBridge.dll
   ```

4. **➕ เพิ่ม Plugin:**
   - วาง Path ลงในช่อง
   - กดปุ่ม **"+"** เพื่อเพิ่ม
   - กดไอคอน **💾 Save** เพื่อบันทึก

### 🔄 **ขั้นตอนที่ 4: เปิดใช้งาน Plugin**

1. **🔍 ค้นหา Plugin:**
   - เปิดแท็บ **"Dev Plugin"**
   - ค้นหา **"Mbb Dalamud v1.5.2"**

2. **🟢 เปิดใช้งาน:**
   - เปิดสวิตซ์เพื่อเริ่มใช้งาน Plugin
   - ตรวจสอบสถานะ ✅ **Enabled**

---

## 🎯 คำสั่งในเกมส์ FFXIV

### 📋 **คำสั่งหลัก:**

| คำสั่ง | หน้าที่ | 📝 คำอธิบาย |
|--------|---------|-------------|
| `/mbb` | 🏠 **หน้าต่างหลัก** | เรียกหน้าต่างดูสถานะและตั้งค่า |
| `/mbb launch` | 🚀 **เริ่มแปล** | รันโปรแกรมแปลภาษาทันที |

---

## ⚙️ การตั้งค่า Path ครั้งแรก

### 🔧 **ขั้นตอนการกำหนด Path:**

1. **📂 เรียกหน้าต่างตั้งค่า:**
   ```bash
   /mbb
   ```

2. **📁 ใส่ Path ของไฟล์หลัก:**
   - ค้นหาช่อง **"MBB Path Configuration"**
   - ใส่ Path ต่อไปนี้:
   ```
   🗂️ C:\MbbDalamud_bridge\MbbDalamud_bridge\python-app\MBB.py
   ```

3. **💾 บันทึกและเริ่มใช้งาน:**
   - กดปุ่ม **"Save Path"**
   - กดปุ่ม **"🚀 Start Program"**

### 🔍 **Path ทางเลือก:**
หากไฟล์ไม่อยู่ในตำแหน่งเริ่มต้น ลองใช้ Path เหล่านี้:

```
📂 C:\MbbDalamud_bridge\python-app\MBB.py
📂 C:\Yariman_Babel\MbbDalamud_bridge\python-app\MBB.py
📂 C:\MBB\MBB.py
```

---

## 🎮 การใช้งานหลังติดตั้ง

### ✅ **ขั้นตอนการใช้งานปกติ:**

1. **🎯 เปิดเกมส์ FFXIV**
2. **🚀 เริ่มแปลภาษา:**
   ```bash
   /mbb launch
   ```
3. **📊 ตรวจสอบสถานะ:**
   ```bash
   /mbb
   ```
4. **🎊 เพลิดเพลินกับการเล่นเกมส์พร้อมคำแปลภาษาไทย!**

### 🔄 **คุณสมบัติหลัก:**
- 🎯 **Real-time Translation** - แปลข้อความในเกมส์แบบเรียลไทม์
- 🧠 **Smart Character Database** - ฐานข้อมูลตัวละคร FFXIV กว่า 500+ ตัว
- 🎨 **Modern UI** - อินเทอร์เฟซสมัยใหม่ปรับแต่งได้
- ⚡ **High Performance** - ประสิทธิภาพสูงไม่กระทบการเล่นเกมส์

---

## 🛠️ การแก้ไขปัญหาเบื้องต้น

### ❌ **ปัญหาที่อาจพบ:**

| ปัญหา | 🔧 วิธีแก้ไข |
|-------|-------------|
| **🚫 ไม่พบไฟล์ MBB.py** | ตรวจสอบ Path และใช้ปุ่ม Browse เพื่อค้นหาไฟล์ |
| **🔴 Connection Failed** | ตรวจสอบ Firewall และรันโปรแกรม MBB.py ก่อน |
| **⚠️ Plugin ไม่ทำงาน** | ตรวจสอบว่า Plugin เปิดใช้งานแล้วใน Dev Plugin Tab |

### 📞 **การสนับสนุน:**
- 📝 **Documentation:** อ่านไฟล์ `README.md` สำหรับข้อมูลเพิ่มเติม
- 🏗️ **Build Info:** ดูไฟล์ `BUILD_PROTOCOL.md` สำหรับข้อมูลการ Build
- 🧠 **Lore System:** ศึกษาไฟล์ `LORE_SYSTEM.md` สำหรับระบบฐานข้อมูลตัวละคร

---

<div align="center">

## 🎉 **พร้อมใช้งานแล้ว!**

**สนุกกับการเล่น FFXIV พร้อมคำแปลภาษาไทยคุณภาพสูง** 🇹🇭

---

**📅 Last Updated:** September 21, 2025
**🏷️ Version:** 1.5.2
**✅ Status:** Ready to Use

</div>