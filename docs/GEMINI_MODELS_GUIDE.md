# Gemini Models Guide — MBB Dalamud Development Reference

> สรุปโมเดล Gemini ที่รองรับใน MBB พร้อมคำแนะนำการใช้งานสำหรับนักพัฒนา

## โมเดลที่รองรับ (v1.7.8+)

| Model ID | Generation | Tier | สถานะ |
|----------|-----------|------|-------|
| `gemini-3.1-flash-lite-preview` | 3.1 | Lite | **NEW** — แนะนำสำหรับ MBB |
| `gemini-2.5-flash` | 2.5 | Standard | Default ปัจจุบัน |
| `gemini-2.5-flash-lite` | 2.5 | Lite | ทางเลือกประหยัด |
| `gemini-2.5-pro` | 2.5 | Pro | คุณภาพสูงสุด ช้ากว่า |
| `gemini-2.0-flash` | 2.0 | Standard | Legacy — ยังใช้ได้ |

## Gemini 3.1 Flash-Lite — ทำไมถึงเหมาะกับ MBB

### ความเร็ว (Latency)
- **TTFT (Time to First Token)** เร็วกว่า 2.5 Flash ถึง **2.5x**
- **Output speed** เร็วขึ้น **45%** เทียบกับรุ่นพี่
- เหมาะกับ Battle text (ChatType 68) ที่ต้องการความเร็วสูงสุด
- Glass Mode overlay แทบไม่มี delay

### ตรรกะและบริบท (Reasoning & Context)
- คะแนน GPQA สูงกว่าโมเดลที่ใหญ่กว่า — แยกแยะบริบทประโยคยาวได้ดี
- รักษาบุคลิกตัวละคร (สรรพนาม, honorifics) ได้แม่นยำ
- เข้ากันได้กับ Wide-Context system (Rule 10: Context Consistency)

### ราคา
- **Input**: $0.25 / 1M tokens (~8.5 บาท / 1M tokens)
- **Output**: $1.50 / 1M tokens (~51 บาท / 1M tokens)
- MBB ใช้ ~1,050-1,270 tokens/request → ประมาณ **0.0003-0.0004 บาท/ประโยค**
- Free tier ของ Google AI Studio: เพียงพอสำหรับ 2-4 ชม./วัน

### Thinking Levels (ฟีเจอร์ใหม่ — ยังไม่ implement)
- โมเดลรองรับการปรับระดับการคิด: Fast / Standard / Deep
- **แนวทางอนาคต**: ปรับตาม ChatType
  - Dialogue (61) / Battle (68): **Fast** — เน้นความเร็ว
  - Cutscene (71): **Deep** — เรียบเรียงสละสลวยขึ้น

## ไฟล์ที่เกี่ยวข้อง (ต้องแก้เมื่อเพิ่ม/ลบโมเดล)

| ไฟล์ | ตำแหน่ง | สิ่งที่ต้องแก้ |
|------|---------|--------------|
| [settings.py](../python-app/settings.py) | `VALID_MODELS` dict (~line 45) | เพิ่ม entry ใน dict |
| [model_panel.py](../python-app/pyqt_ui/model_panel.py) | `AVAILABLE_MODELS` list (~line 20) | เพิ่มใน list |
| [translator_gemini.py](../python-app/translator_gemini.py) | `valid_models` list (~line 309) | เพิ่มใน validation list |
| [model.py](../python-app/model.py) | `values=[...]` (~line 373) | Legacy UI — เพิ่มใน combobox values |

### Default Values ในแต่ละไฟล์

| ไฟล์ | Default | หมายเหตุ |
|------|---------|---------|
| `settings.py` `DEFAULT_API_PARAMETERS` | `gemini-2.5-flash` | default สำหรับ settings ใหม่ |
| `translator_gemini.py` fallback | `gemini-2.0-flash-lite` | fallback ถ้าไม่มี settings |
| `model_panel.py` `_reset_defaults()` | `gemini-2.5-flash` | ปุ่ม Reset ใน UI |

## Model Change Flow

```
User เลือกโมเดลใน ModelPanel (PyQt6)
    ↓
ModelPanel._on_apply()
    ↓
settings.set_api_parameters(model="gemini-3.1-flash-lite-preview")
    ↓
settings.validate_model_parameters() ← เช็คกับ VALID_MODELS
    ↓
settings.save_settings() → settings.json
    ↓
main_app.update_api_settings()
    ↓
translator.update_model_parameters(model="...") ← เช็คกับ valid_models list
    ↓
genai.GenerativeModel(model_name=...) ← สร้าง model instance ใหม่
```

## Token Budget ต่อ Request (v2 prompt)

| ส่วน | Tokens โดยประมาณ |
|------|-----------------|
| System prompt (v2 optimized) | ~490 |
| Recent context (Wide-Context) | ~150-400 |
| Character names + lore | ~180 |
| Dialogue text | ~200 |
| **รวม** | **~1,020-1,270** |

## คำแนะนำสำหรับผู้ใช้

### เลือกโมเดลตามการใช้งาน

| สถานการณ์ | โมเดลแนะนำ |
|-----------|-----------|
| เล่นทั่วไป ต้องการเร็ว+ถูก | `gemini-3.1-flash-lite-preview` |
| ต้องการคุณภาพสูง (MSQ/Cutscene) | `gemini-2.5-flash` หรือ `gemini-2.5-pro` |
| Free tier ใช้หมดเร็ว | `gemini-3.1-flash-lite-preview` (ราคาถูกที่สุด) |
| ระบบเก่า/ต้องการความเสถียร | `gemini-2.0-flash` |

## Model Validation & Fallback

`settings.py` `get_api_parameters()` มี validation:
- ถ้า model ที่บันทึกไว้ใน settings.json ไม่อยู่ใน `VALID_MODELS` → fallback เป็น default อัตโนมัติ
- ป้องกันกรณี Google เปลี่ยนชื่อ model (เช่น ลบ `-preview` ออก)
- Log warning เพื่อ debug

---

*อัพเดตล่าสุด: มีนาคม 2026*
