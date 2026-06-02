"""将审核后的客户资料合并写入 UserMemory。"""

from app.models.user_memory import UserMemory
from app.services.memory_sanitizer import (
    sanitize_agent_notes,
    sanitize_document_memory_data,
    sanitize_screen_resources,
)
from app.utils.timezone import beijing_now_iso


def merge_document_knowledge(memory: UserMemory, reviewed_data: dict, document_meta: dict) -> dict:
    """合并资料抽取结果到 memory，返回更新字段。"""
    reviewed_data = sanitize_document_memory_data(reviewed_data or {})
    source = {
        "type": "document",
        "document_id": document_meta.get("document_id", ""),
    }

    company_info = sanitize_document_memory_data(dict(memory.company_info or {}))
    incoming_company = reviewed_data.get("company_info") or {}
    if incoming_company.get("name"):
        company_info["name"] = incoming_company["name"]
    if incoming_company.get("description"):
        current_desc = company_info.get("description") or ""
        if not current_desc or len(incoming_company["description"]) >= len(current_desc):
            company_info["description"] = incoming_company["description"]
    for key in ("city_intro", "city_positioning", "business_context", "audience_profile", "media_value"):
        if incoming_company.get(key):
            current_value = company_info.get(key) or ""
            if not current_value or len(incoming_company[key]) >= len(current_value):
                company_info[key] = incoming_company[key]
    if incoming_company.get("advantages"):
        company_info["advantages"] = _merge_unique_strings(
            company_info.get("advantages") or [],
            incoming_company.get("advantages") or [],
        )

    company_info["memory_source"] = "document"
    company_info["document_updated_at"] = beijing_now_iso()

    past_cases = company_info.get("past_cases") or []
    past_cases = _merge_objects(
        past_cases,
        _with_source(reviewed_data.get("past_cases") or [], source),
        keys=["brand", "title", "city"],
    )
    company_info["past_cases"] = past_cases[-30:]

    screen_resources = _merge_objects(
        sanitize_screen_resources(memory.screen_resources or []),
        _with_source(reviewed_data.get("screen_resources") or [], source),
        keys=["city", "location", "name", "type"],
    )

    agent_notes = sanitize_agent_notes(memory.agent_notes or "")
    notes = reviewed_data.get("important_notes") or []
    note_lines = []
    for item in notes:
        note = item.get("note") if isinstance(item, dict) else str(item)
        if note and note not in agent_notes:
            note_lines.append(f"- {note}")
    if note_lines:
        section = "\n【客户资料导入备注】\n%s" % "\n".join(note_lines)
        agent_notes = (agent_notes + "\n" + section).strip()
        agent_notes = sanitize_agent_notes(agent_notes)

    return {
        "company_info": company_info,
        "screen_resources": sanitize_screen_resources(screen_resources[-50:]),
        "agent_notes": agent_notes,
    }


def _with_source(items: list, base_source: dict) -> list:
    enriched = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        item_source = item.get("source") if isinstance(item.get("source"), dict) else {}
        item["source"] = {
            **base_source,
            **item_source,
            "type": "document",
        }
        sanitized = sanitize_document_memory_data(item)
        if isinstance(sanitized, dict):
            enriched.append(sanitized)
    return enriched


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
        key = _object_key(item, keys)
        if not key or key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return merged


def _object_key(item: dict, keys: list[str]) -> str:
    parts = [str(item.get(k) or "").strip().lower() for k in keys]
    return "|".join(p for p in parts if p)
