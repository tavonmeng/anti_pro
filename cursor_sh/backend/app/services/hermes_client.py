"""Hermes Agent API Server client."""

from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.config import settings


class HermesClient:
    """Small wrapper around Hermes' OpenAI-compatible API server."""

    def __init__(self) -> None:
        self.base_url = (settings.HERMES_API_BASE_URL or "").rstrip("/")
        self.timeout = float(settings.HERMES_HTTP_TIMEOUT or 180.0)

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{path}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.HERMES_API_KEY:
            headers["Authorization"] = f"Bearer {settings.HERMES_API_KEY}"
        return headers

    def _ensure_enabled(self) -> None:
        if not settings.HERMES_AGENT_ENABLED:
            raise HTTPException(status_code=503, detail="Hermes Agent 未启用")
        if not self.base_url:
            raise HTTPException(status_code=503, detail="Hermes API 地址未配置")

    def _model_name(self) -> str:
        return settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME

    async def get_capabilities(self) -> dict[str, Any]:
        self._ensure_enabled()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self._url("/capabilities"), headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Hermes Agent 响应超时")
        except httpx.HTTPStatusError as exc:
            raise _to_http_exception(exc, "Hermes Agent capabilities 获取失败")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Hermes Agent 暂时不可用")

    async def health(self) -> dict[str, Any]:
        self._ensure_enabled()
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 10.0)) as client:
                response = await client.get(self._url("/health"), headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Hermes Agent 健康检查超时")
        except httpx.HTTPStatusError as exc:
            raise _to_http_exception(exc, "Hermes Agent 健康检查失败")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Hermes Agent 暂时不可用")

    async def create_run(
        self,
        *,
        input_text: str,
        session_id: str,
        instructions: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a Hermes run for a long creative workflow."""
        self._ensure_enabled()
        payload: dict[str, Any] = {
            "model": self._model_name(),
            "input": input_text,
            "session_id": session_id,
            "instructions": instructions,
        }
        if conversation_history:
            payload["conversation_history"] = conversation_history
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self._url("/runs"), headers=self._headers(), json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Hermes Agent 创建运行超时")
        except httpx.HTTPStatusError as exc:
            raise _to_http_exception(exc, "Hermes Agent 创建运行失败")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Hermes Agent 暂时不可用")

    async def get_run(self, hermes_run_id: str) -> dict[str, Any]:
        self._ensure_enabled()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self._url(f"/runs/{hermes_run_id}"), headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Hermes Agent 运行状态查询超时")
        except httpx.HTTPStatusError as exc:
            raise _to_http_exception(exc, "Hermes Agent 运行状态查询失败")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Hermes Agent 暂时不可用")

    async def stop_run(self, hermes_run_id: str) -> dict[str, Any]:
        self._ensure_enabled()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self._url(f"/runs/{hermes_run_id}/stop"), headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Hermes Agent 停止运行超时")
        except httpx.HTTPStatusError as exc:
            raise _to_http_exception(exc, "Hermes Agent 停止运行失败")
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Hermes Agent 暂时不可用")


def _to_http_exception(exc: httpx.HTTPStatusError, fallback_detail: str) -> HTTPException:
    status_code = exc.response.status_code if exc.response is not None else 502
    if status_code in {401, 403}:
        return HTTPException(status_code=502, detail="Hermes Agent 鉴权失败，请检查 HERMES_API_KEY")
    if status_code == 404:
        return HTTPException(status_code=502, detail=f"{fallback_detail}: endpoint 不存在")
    if status_code == 429:
        return HTTPException(status_code=429, detail="Hermes Agent 请求繁忙，请稍后再试")
    detail = fallback_detail
    try:
        body = exc.response.json()
        detail = body.get("detail") or body.get("error") or fallback_detail
    except Exception:
        pass
    return HTTPException(status_code=502, detail=detail)
