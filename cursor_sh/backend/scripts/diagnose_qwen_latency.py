"""Measure Qwen/DashScope streaming latency through the configured API key.

Run from cursor_sh/backend:
    python scripts/diagnose_qwen_latency.py

The script reports:
    - headers: time until the provider accepts the stream
    - first_token: time until the first text delta arrives
    - total: time until the stream finishes
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv


def _load_env() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    load_dotenv(backend_dir / ".env")


async def main() -> None:
    _load_env()
    api_key = os.getenv("AI_API_KEY", "")
    base_url = os.getenv("AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
    model = os.getenv("AI_MODEL_NAME", "qwen-plus")
    timeout = float(os.getenv("AI_HTTP_TIMEOUT", "120"))

    if not api_key:
        raise SystemExit("AI_API_KEY is empty; configure cursor_sh/backend/.env first.")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个响应简洁的中文助手。"},
            {"role": "user", "content": "请用一句话回复：杭州裸眼3D项目第一步应该确认什么？"},
        ],
        "stream": True,
        "enable_thinking": os.getenv("AI_ENABLE_THINKING", "false").lower() in {"1", "true", "yes", "on"},
        "temperature": 0.2,
        "max_tokens": 80,
    }

    started = time.perf_counter()
    first_token_at: float | None = None
    first_reasoning_at: float | None = None
    token_count = 0
    reasoning_count = 0
    text_parts: list[str] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as response:
            headers_at = time.perf_counter()
            print(f"status={response.status_code}")
            print(f"headers={headers_at - started:.3f}s")
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if not data or data == "[DONE]":
                    continue
                chunk = json.loads(data)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta_payload = choices[0].get("delta") or {}
                reasoning = delta_payload.get("reasoning_content") or ""
                if reasoning:
                    if first_reasoning_at is None:
                        first_reasoning_at = time.perf_counter()
                        print(f"first_reasoning={first_reasoning_at - started:.3f}s")
                    reasoning_count += 1
                    continue
                delta = delta_payload.get("content") or ""
                if not delta:
                    continue
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                    print(f"first_token={first_token_at - started:.3f}s")
                token_count += 1
                text_parts.append(delta)

    finished = time.perf_counter()
    if first_token_at is None:
        print("first_token=not_received")
    print(f"total={finished - started:.3f}s")
    print(f"reasoning_chunks={reasoning_count}")
    print(f"chunks={token_count}")
    print(f"reply={''.join(text_parts).strip()}")


if __name__ == "__main__":
    asyncio.run(main())
