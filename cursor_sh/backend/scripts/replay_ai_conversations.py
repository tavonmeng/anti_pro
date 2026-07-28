"""Replay real AI conversation regressions against the configured model.

This runner intentionally exercises the same Router, Brief extractor, context
window, and Brief reply builder used by the application. It stores all replay
state in a temporary log directory, so it does not touch real user sessions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import tempfile
from typing import Any
from uuid import uuid4

from app.api.ai import ChatRequest, _build_requirement_llm_messages
from app.config import settings
from app.services.ai_brief_agent import sanitize_brief_agent_reply
from app.services.ai_brief_state import (
    create_empty_brief_state,
    load_agent_state,
    merge_brief_updates,
    save_agent_state,
    update_agent_state_from_message,
)
from app.services.ai_client import post_chat_completion
from app.services.ai_context import (
    agent_context_messages,
    append_agent_context_message,
    latest_user_context_message,
    sync_agent_context_window_from_history,
)
from app.services.ai_orchestrator import OrchestratorContext, decide_route


DEFAULT_CASES_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "ai_conversation_regressions.json"
)


def load_replay_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"No replay cases found in {path}")
    ids = [str(case.get("id") or "").strip() for case in cases]
    if any(not case_id for case_id in ids):
        raise ValueError(f"Every replay case must have an id in {path}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Replay case ids must be unique in {path}")
    return cases


def evaluate_expectations(
    result: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    route = result.get("route") or {}
    for key, value in (expected.get("route") or {}).items():
        if route.get(key) != value:
            failures.append(
                f"route.{key}: expected {value!r}, got {route.get(key)!r}"
            )

    brief_fields = result.get("brief_fields") or {}
    for field, value in (expected.get("brief_fields") or {}).items():
        if brief_fields.get(field) != value:
            failures.append(
                f"brief_fields.{field}: expected {value!r}, "
                f"got {brief_fields.get(field)!r}"
            )

    window_contents = [
        str(item.get("content") or "")
        for item in (result.get("window") or [])
    ]
    for content, count in (expected.get("window_content_counts") or {}).items():
        actual = window_contents.count(content)
        if actual != count:
            failures.append(
                f"window count for {content!r}: expected {count}, got {actual}"
            )

    reply = str(result.get("reply") or "")
    for pattern in expected.get("reply_forbidden_regex") or []:
        if re.search(pattern, reply, re.I | re.S):
            failures.append(f"reply matched forbidden pattern {pattern!r}")
    for pattern in expected.get("reply_required_regex") or []:
        if not re.search(pattern, reply, re.I | re.S):
            failures.append(f"reply did not match required pattern {pattern!r}")
    return failures


def _initial_agent_state(case: dict[str, Any]) -> dict[str, Any]:
    business_type = str(case.get("business_type") or "ai_3d_custom")
    brief_state = merge_brief_updates(
        create_empty_brief_state(business_type),
        case.get("initial_brief") or {},
        source_message_id="replay-seed",
    )
    return {
        "current_agent": case.get("current_agent"),
        "stage": case.get("stage") or "intent_routing",
        "business_type": business_type,
        "brief_state": brief_state,
        "agent_context_window": {"messages": []},
        "pending_evaluation": case.get("pending_evaluation"),
        "pending_creative_direction": case.get("pending_creative_direction"),
    }


async def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("kind") == "multi_turn_router":
        return await _run_multi_turn_router_case(case)

    case_id = str(case["id"])
    business_type = str(case.get("business_type") or "ai_3d_custom")
    session_id = f"replay-{case_id}-{uuid4().hex[:10]}"
    user_id = f"replay-user-{uuid4().hex[:10]}"
    current_message_id = f"{case_id}-current"
    history = list(case.get("history") or [])
    message = str(case.get("message") or "")

    state = _initial_agent_state(case)
    save_agent_state(session_id, user_id, state)
    state = load_agent_state(session_id, user_id, business_type)
    state = await sync_agent_context_window_from_history(state, history)
    state, _ = await append_agent_context_message(
        state,
        role="user",
        content=message,
        source_message_id=current_message_id,
    )
    route_history = agent_context_messages(
        state,
        exclude_source_message_id=current_message_id,
        fallback_history=history,
    )
    route = await decide_route(
        OrchestratorContext(
            session_id=session_id,
            message=latest_user_context_message(
                state,
                message,
                source_message_id=current_message_id,
            ),
            history=route_history,
            current_agent=case.get("current_agent"),
            stage=case.get("stage"),
            business_type=business_type,
            brief_state=state.get("brief_state"),
            pending_evaluation=state.get("pending_evaluation"),
            pending_creative_direction=state.get("pending_creative_direction"),
            has_attachments=bool(case.get("has_attachments")),
        )
    )
    state["current_agent"] = route.target_agent
    state["stage"] = route.stage
    save_agent_state(session_id, user_id, state)

    result: dict[str, Any] = {
        "id": case_id,
        "kind": case.get("kind") or "router",
        "model": settings.AI_MODEL_NAME,
        "route": route.to_dict(),
    }
    if case.get("kind") != "brief_turn":
        return result

    state = await update_agent_state_from_message(
        session_id=session_id,
        user_id=user_id,
        business_type=business_type,
        message=message,
        history=history,
        source_message_id=current_message_id,
        memory_hints={},
    )
    request = ChatRequest(
        session_id=session_id,
        message=message,
        history=history,
        business_type=business_type,
        user_message_id=current_message_id,
        assistant_message_id=f"{case_id}-assistant",
    )
    llm_messages = _build_requirement_llm_messages(
        request,
        agent_state=state,
    )
    completion = await post_chat_completion(
        {
            "model": settings.AI_MODEL_NAME,
            "messages": llm_messages,
            "temperature": settings.AI_REQUIREMENT_TEMPERATURE,
            "enable_thinking": False,
        },
        timeout=settings.AI_HTTP_TIMEOUT,
    )
    reply = sanitize_brief_agent_reply(
        completion["choices"][0]["message"]["content"],
        state,
    )
    brief_fields = {
        field: str(value.get("value") or "")
        for field, value in ((state.get("brief_state") or {}).get("fields") or {}).items()
        if isinstance(value, dict) and str(value.get("value") or "").strip()
    }
    result.update(
        {
            "brief_fields": brief_fields,
            "window": [
                {
                    "message_id": item.get("source_message_id"),
                    "role": item.get("role"),
                    "content": item.get("content"),
                }
                for item in (
                    (state.get("agent_context_window") or {}).get("messages") or []
                )
            ],
            "generation_last_two": llm_messages[-2:],
            "reply": reply,
        }
    )
    return result


async def _run_multi_turn_router_case(case: dict[str, Any]) -> dict[str, Any]:
    """Replay one conversation as a sequence of real Router decisions.

    Assistant turns are recorded fixture transcripts.  This keeps the replay
    focused on routing while preserving the state each sub-agent would leave
    behind (for example its pending-feedback status) for the next user turn.
    """
    case_id = str(case["id"])
    business_type = str(case.get("business_type") or "ai_3d_custom")
    session_id = f"replay-{case_id}-{uuid4().hex[:10]}"
    user_id = f"replay-user-{uuid4().hex[:10]}"
    turns = case.get("turns") or []
    if not isinstance(turns, list) or not turns:
        raise ValueError(f"multi_turn_router case {case_id} must include turns")

    state = _initial_agent_state(case)
    save_agent_state(session_id, user_id, state)
    state = load_agent_state(session_id, user_id, business_type)
    history = list(case.get("history") or [])
    state = await sync_agent_context_window_from_history(state, history)
    replay_turns: list[dict[str, Any]] = []

    for index, turn in enumerate(turns, start=1):
        message = str(turn.get("message") or "")
        current_message_id = f"{case_id}-turn-{index}"
        state, _ = await append_agent_context_message(
            state,
            role="user",
            content=message,
            source_message_id=current_message_id,
        )
        route_history = agent_context_messages(
            state,
            exclude_source_message_id=current_message_id,
            fallback_history=history,
        )
        route = await decide_route(
            OrchestratorContext(
                session_id=session_id,
                message=latest_user_context_message(
                    state,
                    message,
                    source_message_id=current_message_id,
                ),
                history=route_history,
                current_agent=state.get("current_agent"),
                stage=state.get("stage"),
                business_type=business_type,
                brief_state=state.get("brief_state"),
                pending_evaluation=state.get("pending_evaluation"),
                pending_creative_direction=state.get("pending_creative_direction"),
                has_attachments=bool(turn.get("has_attachments")),
            )
        )
        state["current_agent"] = route.target_agent
        state["stage"] = route.stage

        assistant = turn.get("assistant") or {}
        assistant_content = str(assistant.get("content") or "")
        if assistant_content:
            assistant_message_id = f"{case_id}-assistant-{index}"
            state, _ = await append_agent_context_message(
                state,
                role="assistant",
                content=assistant_content,
                source_message_id=assistant_message_id,
            )
            history.extend(
                [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": assistant_content},
                ]
            )
        else:
            history.append({"role": "user", "content": message})

        for key in ("pending_evaluation", "pending_creative_direction"):
            if key in assistant:
                state[key] = assistant[key]
        if "current_agent" in assistant:
            state["current_agent"] = assistant["current_agent"]
        if "stage" in assistant:
            state["stage"] = assistant["stage"]
        save_agent_state(session_id, user_id, state)

        turn_result = {
            "index": index,
            "message": message,
            "route": route.to_dict(),
        }
        failures = evaluate_expectations(
            {"route": route.to_dict()},
            turn.get("expected") or {},
        )
        turn_result["failures"] = failures
        replay_turns.append(turn_result)

    return {
        "id": case_id,
        "kind": "multi_turn_router",
        "model": settings.AI_MODEL_NAME,
        "turns": replay_turns,
        "route": replay_turns[-1]["route"],
        "window": [
            {
                "message_id": item.get("source_message_id"),
                "role": item.get("role"),
                "content": item.get("content"),
            }
            for item in ((state.get("agent_context_window") or {}).get("messages") or [])
        ],
    }


async def run_replays(
    cases: list[dict[str, Any]],
    *,
    selected_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not settings.AI_API_KEY:
        raise RuntimeError("AI_API_KEY is required for live conversation replay")

    original_log_dir = settings.LOG_DIR
    with tempfile.TemporaryDirectory(prefix="ai-conversation-replays-") as temp_dir:
        settings.LOG_DIR = temp_dir
        try:
            results = []
            for case in cases:
                case_id = str(case["id"])
                if selected_ids and case_id not in selected_ids:
                    continue
                result = await _run_case(case)
                failures = evaluate_expectations(result, case.get("expected") or {})
                for turn in result.get("turns") or []:
                    for failure in turn.get("failures") or []:
                        failures.append(f"turn {turn.get('index')}: {failure}")
                result["passed"] = not failures
                result["failures"] = failures
                results.append(result)
            return results
        finally:
            settings.LOG_DIR = original_log_dir


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": result["id"],
        "passed": result["passed"],
        "route": {
            "action": (result.get("route") or {}).get("action"),
            "intent": (result.get("route") or {}).get("intent"),
            "target_agent": (result.get("route") or {}).get("target_agent"),
            "reason": (result.get("route") or {}).get("reason"),
        },
        "brief_fields": result.get("brief_fields"),
        "reply": result.get("reply"),
        "turns": [
            {
                "index": turn.get("index"),
                "message": turn.get("message"),
                "route": {
                    "action": (turn.get("route") or {}).get("action"),
                    "intent": (turn.get("route") or {}).get("intent"),
                    "target_agent": (turn.get("route") or {}).get("target_agent"),
                },
                "failures": turn.get("failures"),
            }
            for turn in (result.get("turns") or [])
        ]
        or None,
        "failures": result.get("failures"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay real AI chat regressions against the configured model"
    )
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=DEFAULT_CASES_PATH,
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Run only the selected case id; repeat for multiple cases",
    )
    parser.add_argument(
        "--full-json",
        action="store_true",
        help="Print full window and generation payload evidence",
    )
    args = parser.parse_args()

    cases = load_replay_cases(args.cases_file)
    selected_ids = set(args.case_ids or [])
    known_ids = {str(case["id"]) for case in cases}
    unknown = sorted(selected_ids - known_ids)
    if unknown:
        parser.error(f"unknown case ids: {', '.join(unknown)}")

    results = asyncio.run(run_replays(cases, selected_ids=selected_ids or None))
    output = results if args.full_json else [_compact_result(item) for item in results]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    passed = sum(1 for item in results if item["passed"])
    print(f"\nAI replay summary: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
