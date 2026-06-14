"""LLM-backed evaluator tool for creative agent runs.

The tool keeps evaluation inputs compact and returns a normalized score object.
It is intentionally independent from the Hermes prompt flow so backend-driven
runs can audit exactly when evaluation happened and what it returned.
"""

import json
import re
import time
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.services.ai_client import post_chat_completion


CORE_RUBRIC = [
    {"key": "goal_fit", "name": "目标匹配度", "max": 10},
    {"key": "visual_impact", "name": "视觉冲击力", "max": 15},
    {"key": "naked_eye_3d_fit", "name": "裸眼3D适配度", "max": 15},
]
CORE_RUBRIC_MAX = sum(item["max"] for item in CORE_RUBRIC)
RUBRIC_VERSION = "backend_core_v1"

BRIEF_KEEP_KEYS = {
    "project_name",
    "campaign_name",
    "brand",
    "product",
    "theme",
    "theme_concept",
    "creative_goal",
    "objective",
    "content",
    "resource_background",
    "audience_scene",
    "media_positioning",
    "media_specs",
    "media_size",
    "screen_size",
    "resolution",
    "duration",
    "city_location",
    "media_location",
    "art_direction",
    "style",
    "brand_tone",
    "target_group",
    "target_audience",
    "hard_constraints",
    "special_requirements",
    "prohibited_content",
    "deadline",
    "timeline",
}

IDEA_KEEP_KEYS = {
    "title",
    "name",
    "core_concept",
    "creative_concept",
    "concept",
    "big_idea",
    "spatial_mechanism",
    "naked_eye_3d_mechanism",
    "story_outline",
    "script",
    "timed_script",
    "production_notes",
    "style_reference",
    "execution_notes",
    "risk_notes",
    "risks",
    "tags",
}


async def score_ideas_tool(
    *,
    brief: dict[str, Any],
    ideas: list[dict[str, Any]],
    target_score: int = 85,
    model_name: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Score creative ideas with a compact LLM call and strict normalized output."""

    compact_brief = compact_brief_for_evaluator(brief)
    compact_ideas = [compact_idea_for_evaluator(item, index) for index, item in enumerate(ideas)]
    core_target_score = normalize_core_target_score(target_score)
    started = time.monotonic()
    model = model_name or settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME

    payload = {
        "rubric": CORE_RUBRIC,
        "target_score": core_target_score,
        "brief": compact_brief,
        "ideas": compact_ideas,
        "output_schema": {
            "scores": [
                {
                    "idea_index": 0,
                    "scores": {
                        "goal_fit": {"score": 0, "max": 10, "reason": "一句话扣分或加分原因"},
                        "visual_impact": {"score": 0, "max": 15, "reason": "一句话扣分或加分原因"},
                        "naked_eye_3d_fit": {"score": 0, "max": 15, "reason": "一句话扣分或加分原因"},
                    },
                    "core_issues": ["最关键问题，不超过3条"],
                    "recommendations": ["下一轮最该改什么，不超过3条"],
                    "risk_flags": ["明显风险，不超过2条"],
                    "summary": "一句话综合判断",
                }
            ]
        },
    }
    response = await post_chat_completion(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个创意评分工具 score_ideas。只评估目标匹配度、视觉冲击力、裸眼3D适配度三项。"
                        "必须输出严格 JSON object，不要 Markdown，不要解释前后缀。所有字符串值用简体中文。"
                        "每个 reason、summary、recommendation 都要短，避免复述完整方案。"
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": 0.15,
        },
        timeout=timeout if timeout is not None else float(settings.HERMES_HTTP_TIMEOUT or settings.AI_HTTP_TIMEOUT or 120.0),
    )
    output_text = _extract_chat_completion_text(response)
    parsed = _parse_json_output(output_text)
    if not parsed:
        raise HTTPException(status_code=502, detail="Evaluator tool 未返回可解析 JSON")

    normalized = normalize_score_result(
        parsed,
        idea_count=len(compact_ideas),
        target_score=core_target_score,
    )
    normalized["tool_name"] = "score_ideas"
    normalized["rubric_version"] = RUBRIC_VERSION
    normalized["target_score"] = core_target_score
    normalized["raw_target_score"] = target_score
    normalized["model"] = model
    normalized["duration_ms"] = int((time.monotonic() - started) * 1000)
    normalized["compact_input"] = {
        "brief_keys": sorted(compact_brief.keys()),
        "idea_count": len(compact_ideas),
        "input_chars": len(json.dumps(payload, ensure_ascii=False)),
    }
    return normalized


def normalize_core_target_score(target_score: int) -> int:
    value = _to_int(target_score) or CORE_RUBRIC_MAX
    if value > CORE_RUBRIC_MAX:
        value = round(value / 100 * CORE_RUBRIC_MAX)
    return max(0, min(CORE_RUBRIC_MAX, value))


def compact_brief_for_evaluator(brief: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in (brief or {}).items():
        if key in BRIEF_KEEP_KEYS or _looks_relevant_brief_key(key):
            cleaned = _compact_value(value, max_text=600)
            if cleaned not in ("", None, [], {}):
                compact[key] = cleaned
    return compact


def compact_idea_for_evaluator(idea: dict[str, Any], index: int = 0) -> dict[str, Any]:
    compact: dict[str, Any] = {"idea_index": index}
    for key, value in (idea or {}).items():
        if key in IDEA_KEEP_KEYS:
            cleaned = _compact_value(value, max_text=900)
            if cleaned not in ("", None, [], {}):
                compact[key] = cleaned
    if "title" not in compact:
        compact["title"] = str(idea.get("name") or f"方案 {index + 1}")[:120]
    return compact


def normalize_score_result(
    parsed: dict[str, Any],
    *,
    idea_count: int,
    target_score: int,
) -> dict[str, Any]:
    raw_scores = parsed.get("scores") or parsed.get("evaluations") or parsed.get("reviews") or []
    if isinstance(raw_scores, dict):
        raw_scores = raw_scores.get("items") or raw_scores.get("scores") or [raw_scores]
    if not isinstance(raw_scores, list):
        raw_scores = []

    by_index: dict[int, dict[str, Any]] = {}
    for position, item in enumerate(raw_scores):
        if not isinstance(item, dict):
            continue
        index = _selected_index(item.get("idea_index"), idea_count)
        if index is None:
            index = _selected_index(item.get("index"), idea_count)
        if index is None:
            index = position if position < idea_count else None
        if index is None:
            continue
        by_index[index] = _normalize_one_score(item, index=index, target_score=target_score)

    scores = [
        by_index.get(index) or _empty_score(index, "评分工具未返回该方案的评分")
        for index in range(idea_count)
    ]
    best_index = 0
    best_score = -1
    for item in scores:
        score = int(item.get("total_score") or 0)
        if score > best_score:
            best_score = score
            best_index = int(item.get("idea_index") or 0)

    target_reached = best_score >= target_score
    return {
        "scores": scores,
        "best_index": best_index,
        "best_score": max(0, best_score),
        "target_reached": target_reached,
        "continue_recommendation": "stop" if target_reached else "iterate",
        "compact_score_matrix": [
            {
                "idea_index": item["idea_index"],
                "total_score": item["total_score"],
                "goal_fit": item["scores"]["goal_fit"]["score"],
                "visual_impact": item["scores"]["visual_impact"]["score"],
                "naked_eye_3d_fit": item["scores"]["naked_eye_3d_fit"]["score"],
            }
            for item in scores
        ],
    }


def _normalize_one_score(item: dict[str, Any], *, index: int, target_score: int) -> dict[str, Any]:
    raw_dimensions = item.get("scores") or item.get("score_table") or item.get("dimensions") or {}
    if isinstance(raw_dimensions, list):
        raw_dimensions = {
            _dimension_key(dim.get("key") or dim.get("name") or dim.get("dimension")): dim
            for dim in raw_dimensions
            if isinstance(dim, dict)
        }
    scores: dict[str, dict[str, Any]] = {}
    total = 0
    for rubric in CORE_RUBRIC:
        key = rubric["key"]
        raw_value = raw_dimensions.get(key) if isinstance(raw_dimensions, dict) else None
        if raw_value is None and isinstance(raw_dimensions, dict):
            raw_value = raw_dimensions.get(rubric["name"])
        score = _score_value(raw_value)
        score = max(0, min(int(rubric["max"]), score if score is not None else 0))
        total += score
        reason = ""
        if isinstance(raw_value, dict):
            reason = _text_value(raw_value.get("reason") or raw_value.get("why") or raw_value.get("comment"))
        scores[key] = {
            "score": score,
            "max": int(rubric["max"]),
            "reason": reason[:160],
        }
    explicit_total = _to_int(item.get("total_score") or item.get("score") or item.get("total"))
    total_score = max(0, min(CORE_RUBRIC_MAX, explicit_total if explicit_total is not None else total))
    return {
        "idea_index": index,
        "scores": scores,
        "total_score": total_score,
        "grade": _grade(total_score),
        "core_issues": _short_list(item.get("core_issues") or item.get("issues") or item.get("problems"), 3),
        "recommendations": _short_list(
            item.get("recommendations") or item.get("optimization_suggestions") or item.get("suggestions"),
            3,
        ),
        "risk_flags": _short_list(item.get("risk_flags") or item.get("risks"), 2),
        "summary": _text_value(item.get("summary") or item.get("overall_judgement") or item.get("judgement"))[:220],
        "target_reached": total_score >= target_score,
    }


def _empty_score(index: int, message: str) -> dict[str, Any]:
    return {
        "idea_index": index,
        "scores": {
            item["key"]: {"score": 0, "max": item["max"], "reason": message}
            for item in CORE_RUBRIC
        },
        "total_score": 0,
        "grade": "D",
        "core_issues": [message],
        "recommendations": ["重新调用评分工具"],
        "risk_flags": [],
        "summary": message,
        "target_reached": False,
    }


def _compact_value(value: Any, *, max_text: int) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text[:max_text] if len(text) > max_text else text
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        items = [_compact_value(item, max_text=max(120, max_text // 2)) for item in value[:8]]
        return [item for item in items if item not in ("", None, [], {})]
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, child in value.items():
            if _drop_key(key):
                continue
            cleaned = _compact_value(child, max_text=max(120, max_text // 2))
            if cleaned not in ("", None, [], {}):
                compact[key] = cleaned
            if len(compact) >= 20:
                break
        return compact
    return str(value)[:max_text]


def _looks_relevant_brief_key(key: str) -> bool:
    normalized = key.lower()
    return any(
        token in normalized
        for token in (
            "brief",
            "brand",
            "creative",
            "media",
            "screen",
            "audience",
            "style",
            "constraint",
            "requirement",
            "scene",
            "location",
        )
    )


def _drop_key(key: str) -> bool:
    normalized = key.lower()
    return any(
        token in normalized
        for token in (
            "raw",
            "url",
            "oss",
            "signature",
            "token",
            "password",
            "secret",
            "photo",
            "image",
            "file",
            "attachment",
        )
    )


def _parse_json_output(output_text: str) -> dict[str, Any]:
    text = (output_text or "").strip()
    if not text:
        return {}
    value = _try_parse_json_value(text)
    if value is not None:
        return value if isinstance(value, dict) else {"items": value}
    fences = re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    for fence in fences:
        value = _try_parse_json_value(fence.group(1).strip())
        if value is not None:
            return value if isinstance(value, dict) else {"items": value}
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        value = _try_parse_json_value(text[start : end + 1])
        if value is not None:
            return value if isinstance(value, dict) else {"items": value}
    return {}


def _try_parse_json_value(text: str) -> Any:
    try:
        return json.loads((text or "").strip())
    except json.JSONDecodeError:
        return None


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = [
                    _text_value(item.get("text") or item.get("content"))
                    for item in content
                    if isinstance(item, dict)
                ]
                return "\n".join(item for item in parts if item).strip()
        text = choices[0].get("text")
        if text:
            return _text_value(text)
    return ""


def _selected_index(value: Any, length: int) -> int | None:
    idx = _to_int(value)
    if idx is None:
        return None
    if 0 <= idx < length:
        return idx
    if 1 <= idx <= length:
        return idx - 1
    return None


def _dimension_key(value: Any) -> str:
    raw = _text_value(value)
    alias_map = {
        "目标匹配度": "goal_fit",
        "goal fit": "goal_fit",
        "视觉冲击力": "visual_impact",
        "visual impact": "visual_impact",
        "裸眼3d适配度": "naked_eye_3d_fit",
        "裸眼3D适配度": "naked_eye_3d_fit",
        "3d fit": "naked_eye_3d_fit",
    }
    return alias_map.get(raw) or alias_map.get(raw.lower()) or raw


def _score_value(value: Any) -> int | None:
    if isinstance(value, dict):
        return _to_int(value.get("score") or value.get("value"))
    return _to_int(value)


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return int(round(float(match.group(0))))
    return None


def _short_list(value: Any, limit: int) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [_text_value(item)[:180] for item in items[:limit] if _text_value(item)]


def _grade(score: int) -> str:
    if score >= 36:
        return "A"
    if score >= 32:
        return "B"
    if score >= 28:
        return "C"
    return "D"


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value).strip()
