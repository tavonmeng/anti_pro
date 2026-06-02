"""客户资料信息抽取服务。"""

import json
import re
from app.config import settings
from app.services.ai_client import post_chat_completion
from app.services.memory_sanitizer import sanitize_document_memory_data
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger


logger = get_module_logger("ai")


EMPTY_EXTRACTION = {
    "company_info": {
        "name": "",
        "description": "",
        "city_intro": "",
        "city_positioning": "",
        "business_context": "",
        "audience_profile": "",
        "media_value": "",
        "advantages": [],
    },
    "screen_resources": [],
    "past_cases": [],
    "important_notes": [],
}


def empty_extraction() -> dict:
    return json.loads(json.dumps(EMPTY_EXTRACTION, ensure_ascii=False))


async def extract_customer_knowledge(document_text: str | list[str], filename: str = "") -> dict:
    """用 LLM 从客户资料文本中抽取 Agent Memory 可用信息。"""
    chunks = _normalize_document_chunks(document_text)
    if not settings.AI_API_KEY or not chunks:
        return empty_extraction()

    results = []
    total_chunks = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        extracted = await _extract_customer_knowledge_chunk(
            chunk,
            filename=filename,
            chunk_index=index,
            total_chunks=total_chunks,
        )
        if _has_extraction(extracted):
            results.append(extracted)

    return merge_extractions(results) if results else empty_extraction()


async def _extract_customer_knowledge_chunk(
    document_text: str,
    *,
    filename: str,
    chunk_index: int,
    total_chunks: int,
) -> dict:
    model = settings.DOCUMENT_EXTRACT_MODEL or settings.AI_MODEL_NAME

    system_prompt = (
        "你是客户画像资料分析 Agent。请从客户上传的中文资料中抽取可写入 Agent Memory 的关键信息。\n"
        "只返回严格 JSON，不要解释，不要 markdown。\n\n"
        "返回 schema：\n"
        "{\n"
        '  "company_info": {"name": "", "description": "", "city_intro": "", "city_positioning": "", "business_context": "", "audience_profile": "", "media_value": "", "advantages": []},\n'
        '  "screen_resources": [\n'
        '    {"city": "", "district": "", "business_district": "", "location": "", "media_position": "", "location_intro": "", "surrounding_landmarks": "", "name": "", "type": "", "size": "", "area": "", "resolution": "", "specs": "", "play_frequency": "", "play_time": "", "daily_traffic": "", "holiday_traffic": "", "audience_profile": "", "media_advantages": [], "viewing_path": "", "highlights": "", "notes": "", "source": {"page": ""}}\n'
        "  ],\n"
        '  "past_cases": [\n'
        '    {"title": "", "brand": "", "city": "", "location": "", "year": "", "content_type": "", "highlights": "", "source": {"page": ""}}\n'
        "  ],\n"
        '  "important_notes": [{"note": "", "source": {"page": ""}}]\n'
        "}\n\n"
        "抽取重点：\n"
        "1. 尽量完整抽取媒体资料里的所有有业务价值的信息，不只抽参数。包括城市介绍、城市定位、商圈背景、位置介绍、周边地标、目标受众/人群画像、媒体优势、传播价值、投放规则、播放时间、播放频次、客流/接触人次、案例等。\n"
        "2. 严禁抽取或输出任何价格、报价、刊例价、制作费、费用、成本、预算金额、含税/未税等敏感价格信息；遇到这些内容直接忽略，不要放进任何字段、notes 或 important_notes。\n"
        "3. 屏幕资源必须尽量完整保留媒体资料里的非价格原始字段，不要只抽屏幕名。尤其遇到这些标签时必须逐项抽取：媒体位置、播放频次、媒体规格、尺寸、面积、分辨率、播放时间、日媒体接触人次、人流量、客流量、节假日客流。\n"
        "4. 字段映射规则：媒体位置填 location 和 media_position；行政区填 district；播放频次填 play_frequency；播放时间填 play_time；日媒体接触人次填 daily_traffic；节假日接触人次填 holiday_traffic；长宽高/面积填 size 和 area；分辨率填 resolution。\n"
        "5. 城市整体介绍、城市消费力、交通枢纽、商业氛围、核心商圈等属于 company_info 的 city_intro / business_context / media_value；如果是某块屏所在点位的介绍，放到对应 screen_resources[].location_intro / surrounding_landmarks / media_advantages / audience_profile。\n"
        "6. specs 要汇总屏幕物理规格和分辨率，例如“长40.32m*高13.44m=542㎡，分辨率6048*2016”；notes 只保留无法归入独立字段的补充说明/投放规则，不要把商圈、周边、受众、媒体优势、播放频次、播放时间、接触人次重复塞进 notes。\n"
        "7. 如果文本类似“媒体位置 庐阳区淮河路步行街银泰中心北侧 / 播放频次 15s/60次/天 / 媒体规格 长40.32m*高13.44m=542㎡ 分辨率：6048*2016 / 播放时间 10：00~23：00 / 刊例价 300000元/周 / 日媒体接触人次 100万人次/天”，必须忽略刊例价，只把非价格内容放进同一条 screen_resources。\n"
        "8. 对“位置介绍/项目优势/媒体优势/资源亮点/周边介绍/城市介绍”这类段落不要忽略，要压缩成短句保留。不要为了结构化而丢掉解释性文字。\n"
        "9. 同一条资源内不要重复输出同一信息；字段里已有的内容不要在 notes 中反复复述多遍。\n"
        "10. 案例要优先输出户外屏幕/裸眼3D/商圈LED案例；普通公司新闻或非屏幕案例不要优先输出。\n"
        "11. 不要编造资料中没有的信息；没有就留空字符串或空数组。\n"
        "12. 每条资源、案例、备注都尽量标注来源页码。来源文本里有【来源：第X页】或【来源：第X页幻灯片】。不要输出源文件名。\n"
    )

    try:
        chunk_prefix = ""
        if total_chunks > 1:
            chunk_prefix = f"这是长文档的第 {chunk_index}/{total_chunks} 段。只抽取本段中明确出现的信息，后续系统会合并去重。\n\n"
        data = await post_chat_completion(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"文件名：{filename}\n\n{chunk_prefix}资料文本：\n{document_text}"},
                ],
                "response_format": {"type": "json_object"},
                "enable_thinking": False,
            },
            timeout=settings.DOCUMENT_EXTRACT_TIMEOUT,
        )
        content = data["choices"][0]["message"]["content"].strip()
        parsed = _parse_json(content)
        return normalize_extraction(parsed, filename)
    except Exception as exc:
        log_business_event(
            logger,
            "document_extract_failed",
            level="warning",
            filename=filename,
            model=model,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            text_length=len(document_text or ""),
            error_type=exc.__class__.__name__,
            error=_exception_message(exc),
        )
        return empty_extraction()


def merge_extractions(items: list[dict]) -> dict:
    result = empty_extraction()
    for item in items:
        normalized = normalize_extraction(item)
        company = normalized.get("company_info") or {}
        if company.get("name"):
            result["company_info"]["name"] = company["name"]
        if company.get("description"):
            current = result["company_info"].get("description") or ""
            if len(company["description"]) > len(current):
                result["company_info"]["description"] = company["description"]
        for key in ("city_intro", "city_positioning", "business_context", "audience_profile", "media_value"):
            if company.get(key):
                current = result["company_info"].get(key) or ""
                if len(company[key]) > len(current):
                    result["company_info"][key] = company[key]
        result["company_info"]["advantages"] = _merge_unique_strings(
            result["company_info"].get("advantages") or [],
            company.get("advantages") or [],
        )
        result["screen_resources"] = _merge_objects(
            result["screen_resources"],
            normalized.get("screen_resources") or [],
            keys=["city", "location", "name", "type"],
        )
        result["past_cases"] = _merge_objects(
            result["past_cases"],
            normalized.get("past_cases") or [],
            keys=["brand", "title", "city"],
        )
        result["important_notes"] = _merge_objects(
            result["important_notes"],
            normalized.get("important_notes") or [],
            keys=["note"],
        )
    return result


def normalize_extraction(data: dict, filename: str = "") -> dict:
    """规范化抽取结构，保证前端审核页稳定。"""
    if not isinstance(data, dict):
        return empty_extraction()

    result = empty_extraction()
    company = data.get("company_info") or {}
    if isinstance(company, dict):
        result["company_info"]["name"] = str(company.get("name") or "")
        result["company_info"]["description"] = str(company.get("description") or "")
        for key in ("city_intro", "city_positioning", "business_context", "audience_profile", "media_value"):
            result["company_info"][key] = str(company.get(key) or "")
        advantages = company.get("advantages") or []
        if isinstance(advantages, str):
            advantages = [advantages]
        result["company_info"]["advantages"] = [str(x) for x in advantages if str(x).strip()]

    result["screen_resources"] = _normalize_screen_resources(_normalize_list(data.get("screen_resources"), filename))
    result["past_cases"] = _normalize_list(data.get("past_cases"), filename)
    result["important_notes"] = _normalize_list(data.get("important_notes"), filename, note_mode=True)
    return sanitize_document_memory_data(result)


def _normalize_screen_resources(items: list[dict]) -> list[dict]:
    normalized = []
    for raw in items:
        item = dict(raw)
        item.pop("list_price", None)
        media_position = str(item.get("media_position") or "").strip()
        if media_position and not item.get("location"):
            item["location"] = media_position

        specs_parts = [
            item.get("type"),
            item.get("size"),
            item.get("area"),
            item.get("resolution") and f"分辨率{item.get('resolution')}",
        ]
        item["specs"] = _merge_text_fragments(item.get("specs"), specs_parts)

        item["notes"] = _clean_screen_notes(item)
        normalized.append(item)
    return normalized


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
            "page": source.get("page") or "",
        }
        items.append(item)
    return items


def _normalize_document_chunks(document_text: str | list[str]) -> list[str]:
    if isinstance(document_text, str):
        chunks = [document_text]
    else:
        chunks = document_text or []
    return [str(chunk).strip() for chunk in chunks if str(chunk or "").strip()]


def _has_extraction(data: dict) -> bool:
    company = data.get("company_info") or {}
    return bool(
        company.get("name")
        or company.get("description")
        or company.get("advantages")
        or data.get("screen_resources")
        or data.get("past_cases")
        or data.get("important_notes")
    )


def _merge_unique_strings(existing: list, incoming: list) -> list:
    merged = []
    for value in list(existing or []) + list(incoming or []):
        text = str(value).strip()
        if text and text not in merged:
            merged.append(text)
    return merged


def _merge_objects(existing: list, incoming: list, keys: list[str]) -> list:
    merged = list(existing or [])
    seen = {_object_key(item, keys) for item in merged if isinstance(item, dict)}
    for item in incoming:
        if not isinstance(item, dict):
            continue
        key = _object_key(item, keys)
        if key and key in seen:
            continue
        merged.append(item)
        if key:
            seen.add(key)
    return merged


def _object_key(item: dict, keys: list[str]) -> str:
    return "|".join(str(item.get(k) or "").strip().lower() for k in keys if str(item.get(k) or "").strip())


def _merge_text_fragments(existing, fragments: list) -> str:
    values = []
    for value in [existing, *fragments]:
        for text in _split_text_fragments(str(value or "")):
            if text and text not in values:
                values.append(text)
    return "，".join(values)


def _split_text_fragments(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"[，；]\s*", text or "")
        if part.strip()
    ]


def _clean_screen_notes(item: dict) -> str:
    structured_prefixes = (
        "位置介绍", "商圈", "周边", "播放频次", "播放时间", "刊例价",
        "日媒体接触人次", "节假日接触人次", "受众", "媒体优势", "观看动线",
    )
    fragments = []
    for text in _split_text_fragments(str(item.get("notes") or "")):
        if any(text.startswith(prefix) for prefix in structured_prefixes):
            continue
        if text and text not in fragments:
            fragments.append(text)
    return "，".join(fragments)


def _exception_message(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail:
        return str(detail)
    message = str(exc)
    return message or exc.__class__.__name__


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
