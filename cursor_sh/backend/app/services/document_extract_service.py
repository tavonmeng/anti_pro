"""客户资料信息抽取服务。"""

import json
import re
from app.config import settings


EMPTY_EXTRACTION = {
    "company_info": {
        "name": "",
        "description": "",
        "advantages": [],
    },
    "screen_resources": [],
    "past_cases": [],
    "important_notes": [],
}


def empty_extraction() -> dict:
    return json.loads(json.dumps(EMPTY_EXTRACTION, ensure_ascii=False))


async def extract_customer_knowledge(document_text: str, filename: str = "") -> dict:
    """用 LLM 从客户资料文本中抽取 Agent Memory 可用信息。"""
    if not settings.AI_API_KEY or not document_text.strip():
        return empty_extraction()

    import httpx

    system_prompt = (
        "你是客户画像资料分析 Agent。请从客户上传的中文资料中抽取可写入 Agent Memory 的关键信息。\n"
        "只返回严格 JSON，不要解释，不要 markdown。\n\n"
        "返回 schema：\n"
        "{\n"
        '  "company_info": {"name": "", "description": "", "advantages": []},\n'
        '  "screen_resources": [\n'
        '    {"city": "", "location": "", "name": "", "type": "", "size": "", "resolution": "", "daily_traffic": "", "highlights": "", "source": {"filename": "", "page": ""}}\n'
        "  ],\n"
        '  "past_cases": [\n'
        '    {"title": "", "brand": "", "city": "", "location": "", "year": "", "content_type": "", "highlights": "", "source": {"filename": "", "page": ""}}\n'
        "  ],\n"
        '  "important_notes": [{"note": "", "source": {"filename": "", "page": ""}}]\n'
        "}\n\n"
        "抽取重点：\n"
        "1. 优先抽取户外屏幕、商圈 LED、城市 LED、裸眼3D大屏、地标屏、数字户外 OOH 相关信息。\n"
        "2. 屏幕资源要尽量包含城市、商圈/点位、屏幕名称、屏幕类型、尺寸、分辨率、客流和亮点。\n"
        "3. 案例要优先输出户外屏幕/裸眼3D/商圈LED案例；普通公司新闻或非屏幕案例不要优先输出。\n"
        "4. 不要编造资料中没有的信息；没有就留空字符串或空数组。\n"
        "5. 每条资源、案例、备注都尽量标注来源页码。来源文本里有【来源：第X页】或【来源：第X页幻灯片】。\n"
        f"6. source.filename 固定填：{filename}\n"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AI_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"文件名：{filename}\n\n资料文本：\n{document_text}"},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=45.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            parsed = _parse_json(content)
            return normalize_extraction(parsed, filename)
    except Exception as exc:
        print(f"[DocumentExtract] 抽取失败: {exc}")
        return empty_extraction()


def normalize_extraction(data: dict, filename: str = "") -> dict:
    """规范化抽取结构，保证前端审核页稳定。"""
    if not isinstance(data, dict):
        return empty_extraction()

    result = empty_extraction()
    company = data.get("company_info") or {}
    if isinstance(company, dict):
        result["company_info"]["name"] = str(company.get("name") or "")
        result["company_info"]["description"] = str(company.get("description") or "")
        advantages = company.get("advantages") or []
        if isinstance(advantages, str):
            advantages = [advantages]
        result["company_info"]["advantages"] = [str(x) for x in advantages if str(x).strip()]

    result["screen_resources"] = _normalize_list(data.get("screen_resources"), filename)
    result["past_cases"] = _normalize_list(data.get("past_cases"), filename)
    result["important_notes"] = _normalize_list(data.get("important_notes"), filename, note_mode=True)
    return result


def _normalize_list(value, filename: str, note_mode: bool = False) -> list:
    if not isinstance(value, list):
        return []
    items = []
    for raw in value:
        if isinstance(raw, str):
            raw = {"note": raw} if note_mode else {"title": raw}
        if not isinstance(raw, dict):
            continue
        item = {k: v for k, v in raw.items() if k != "source"}
        source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
        item["source"] = {
            "type": "document",
            "filename": source.get("filename") or filename,
            "page": source.get("page") or "",
        }
        items.append(item)
    return items


def _parse_json(content: str) -> dict:
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if code_match:
        content = code_match.group(1)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        obj_match = re.search(r"\{[\s\S]*\}", content)
        if obj_match:
            return json.loads(obj_match.group(0))
        raise
