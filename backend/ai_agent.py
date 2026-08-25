"""
AI Agent — bóc tách thông số kỹ thuật từ mô tả đơn hàng gốm.
Dùng Google Gemini 1.5 Flash; fallback sang regex nếu không có API key.
"""
import json
import re
from typing import Any, Dict

from config import GEMINI_API_KEY


def parse_order(description: str) -> Dict[str, Any]:
    """Entry-point: chọn Gemini hoặc regex tùy cấu hình."""
    if GEMINI_API_KEY:
        try:
            return _gemini_parse(description)
        except Exception as exc:
            print(f"[AI] Gemini error ({exc}), switching to regex fallback")
    return _regex_parse(description)


# ── Gemini ──────────────────────────────────────────────────────────────────

def _gemini_parse(description: str) -> Dict[str, Any]:
    import google.generativeai as genai  # lazy import

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-3.6-flash")

    prompt = f"""Bạn là AI chuyên phân tích đơn hàng xưởng gốm sứ Việt Nam.
Phân tích đơn hàng sau và trả về JSON thuần (không markdown, không giải thích):

Đơn hàng: "{description}"

Trả về JSON với đúng cấu trúc này:
{{
  "product_name": "tên sản phẩm gốm (ví dụ: Bình gốm họa tiết sen)",
  "quantity": <số_lượng_integer>,
  "height_cm": <chiều_cao_float_hoặc_null>,
  "glaze_type": "loại men (men lam / men trắng / men nâu / men xanh / men ngọc / ...)",
  "pattern": "họa tiết (sen / chim / trúc / cá / hoa / ... hoặc null)",
  "firing_temp_c": <nhiệt_độ_nung_integer>,
  "firing_duration_h": <thời_gian_nung_giờ_float>,
  "clay_kg_estimate": <ước_tính_tổng_kg_đất_sét_float>,
  "priority": <1_khẩn_cấp | 2_bình_thường | 3_thấp>,
  "deadline_days": <số_ngày_integer>,
  "notes": "ghi chú kỹ thuật"
}}

Quy tắc:
- priority 1 nếu deadline <= 3 ngày; 3 nếu deadline > 14 ngày; còn lại là 2
- clay_kg_estimate: bình cao ~2kg/cái, tô/bát ~0.3kg, đĩa ~0.5kg, bình nhỏ ~0.8kg
- firing_duration_h: 1280°C → 10h; 1200°C → 7h; 900°C → 5h (ước tính)"""

    resp = model.generate_content(prompt)

    # ── Log token usage ──────────────────────────────────────────────────────
    if hasattr(resp, "usage_metadata") and resp.usage_metadata:
        u = resp.usage_metadata
        input_tok  = getattr(u, "prompt_token_count", 0) or 0
        output_tok = getattr(u, "candidates_token_count", 0) or 0
        total_tok  = getattr(u, "total_token_count", input_tok + output_tok) or 0
        # Giá Gemini 1.5 Flash: $0.075/1M input, $0.30/1M output (tính USD)
        cost_usd = (input_tok * 0.075 + output_tok * 0.30) / 1_000_000
        print(
            f"[Gemini] tokens — input: {input_tok} | output: {output_tok} "
            f"| total: {total_tok} | ~${cost_usd:.6f} USD"
        )
    # ────────────────────────────────────────────────────────────────────────

    text = resp.text.strip()
    # Loại bỏ markdown fence nếu model trả về
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return json.loads(text)


# ── Regex fallback ───────────────────────────────────────────────────────────

def _regex_parse(description: str) -> Dict[str, Any]:
    desc_lower = description.lower()

    qty_m = re.search(r"(\d+)\s*(cái|chiếc|bình|tô|bát|đĩa|ly|chén|ấm|lọ)", description, re.IGNORECASE)
    temp_m = re.search(r"(\d{3,4})\s*°?c", description, re.IGNORECASE)
    height_m = re.search(r"cao\s*(\d+)\s*cm", description, re.IGNORECASE)
    days_m = re.search(r"(\d+)\s*ngày", description, re.IGNORECASE)

    quantity = int(qty_m.group(1)) if qty_m else 100
    temp = int(temp_m.group(1)) if temp_m else 1200
    height = float(height_m.group(1)) if height_m else None
    days = int(days_m.group(1)) if days_m else 7

    clay_per = 2.0 if height and height > 25 else (0.8 if height and height > 15 else 0.4)

    glaze = "men trắng"
    for g in ("men lam", "men nâu", "men xanh", "men ngọc", "men đỏ"):
        if g in desc_lower:
            glaze = g
            break

    pattern = None
    for p in ("sen", "trúc", "chim", "cá", "hoa", "rồng", "phượng"):
        if p in desc_lower:
            pattern = p
            break

    dur = 10.0 if temp >= 1280 else (7.0 if temp >= 1200 else 5.0)

    return {
        "product_name": description[:60].strip(),
        "quantity": quantity,
        "height_cm": height,
        "glaze_type": glaze,
        "pattern": pattern,
        "firing_temp_c": temp,
        "firing_duration_h": dur,
        "clay_kg_estimate": round(quantity * clay_per, 1),
        "priority": 1 if days <= 3 else (3 if days > 14 else 2),
        "deadline_days": days,
        "notes": f"[Regex parsed] {description[:120]}",
    }
