# Installation Guide - Magicite Babel Dalamud Bridge v1.5.28

## 1. ติดตั้ง Python

**เวอร์ชันที่แนะนำ:** Python 3.11.x หรือ 3.12.x (64-bit)

### ดาวน์โหลด:
- [Python 3.12.8 (Windows 64-bit)](https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe)
- [Python Downloads Page](https://www.python.org/downloads/)

### การติดตั้ง:
1. รัน installer
2. **สำคัญ:** เลือก "Add Python to PATH"
3. เลือก "Install Now" หรือ "Customize installation"
4. รอจนเสร็จ

---

## 2. ติดตั้ง Dependencies

### วิธีที่ 1: ใช้ไฟล์ Batch (แนะนำ)
1. ดับเบิลคลิก `install_dependencies.bat` ในโฟลเดอร์โปรเจค
2. รอจนติดตั้งเสร็จ

### วิธีที่ 2: ติดตั้งเอง
```cmd
cd python-app
pip install -r requirements_full.txt
```

---

## 3. ตั้งค่า Dalamud Plugin

### Path ไฟล์ DLL:
```
dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64\DalamudMBBBridge.dll
```

### วิธีติดตั้ง Plugin:
1. เปิด Dalamud Settings (พิมพ์ `/xlsettings`)
2. ไปที่ **Experimental** tab
3. ใน **Dev Plugin Locations** เพิ่ม path:
   ```
   C:\Yariman_Babel\MbbDalamud_bridge\dalamud-plugin\DalamudMBBBridge\bin\Release\win-x64
   ```
4. กด **Save and Close**
5. พิมพ์ `/xlplugins` แล้วเปิดใช้งาน **Mgicite Babel**

---

## 4. วิธีใช้งาน

### เริ่มต้นใช้งาน:
1. **เปิดเกม FFXIV** ผ่าน XIVLauncher
2. **ในเกม** พิมพ์ `/mbb launch` เพื่อเปิดโปรแกรมแปล
3. **TUI จะแสดงอัตโนมัติ** เมื่อมีข้อความ

### คำสั่งในเกม:
| คำสั่ง | การทำงาน |
|--------|---------|
| `/mbb` | เปิด/ปิดหน้าต่างตั้งค่า Plugin |
| `/mbb launch` | เปิดโปรแกรมแปลภาษา |
| `/mbb stop` | หยุดโปรแกรมแปลภาษา |

### Hotkeys:
| ปุ่ม | การทำงาน |
|------|---------|
| `ALT+H` | ซ่อน/แสดง TUI |
| `F9` | เริ่ม/หยุด การแปล |

---

## 5. ทดสอบการทำงาน

1. เปิด **Settings** ใน TUI
2. กดปุ่ม **Dialog**, **Battle**, หรือ **Cutscene** ใน Test Hook section
3. TUI ควรแสดงข้อความทดสอบที่แปลแล้ว

---

## Troubleshooting

### ปัญหา: Plugin ไม่แสดงใน Dalamud
- ตรวจสอบ path ของ DLL ว่าถูกต้อง
- ตรวจสอบว่า build DLL สำเร็จ (ไม่มี error)

### ปัญหา: โปรแกรมแปลไม่เริ่มทำงาน
- ตรวจสอบว่าติดตั้ง Python และ dependencies ครบ
- ตรวจสอบ Console output ใน Dalamud

### ปัญหา: ไม่มีการแปล
- ตรวจสอบ API Key ใน Settings > Screen/API
- ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต