#!/usr/bin/env python3
"""Check runtime service connectivity for a deployed backend env."""

from __future__ import annotations

import asyncio
import email.message
import os
import smtplib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


async def check_database() -> CheckResult:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async def query() -> int:
            async with engine.connect() as conn:
                return (await conn.execute(text("SELECT 1"))).scalar_one()

        value = await asyncio.wait_for(query(), timeout=8)
        return CheckResult("database", value == 1, f"connected to {settings.DB_HOST}/{settings.DB_NAME}")
    finally:
        await engine.dispose()


async def check_audit_database() -> CheckResult:
    if not settings.LOG_DB_ENABLED:
        return CheckResult("audit_database", True, "skipped because LOG_DB_ENABLED=false")
    engine = create_async_engine(settings.AUDIT_DATABASE_URL, pool_pre_ping=True)
    try:
        async def query() -> int:
            async with engine.connect() as conn:
                return (await conn.execute(text("SELECT 1"))).scalar_one()

        value = await asyncio.wait_for(query(), timeout=8)
        return CheckResult("audit_database", value == 1, "connected")
    finally:
        await engine.dispose()


async def check_oss() -> CheckResult:
    if not settings.OSS_ENABLED:
        return CheckResult("oss", True, "skipped because OSS_ENABLED=false")
    import oss2

    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
    info = await asyncio.to_thread(bucket.get_bucket_info)
    return CheckResult("oss", True, f"bucket={info.name}")


async def check_ai() -> CheckResult:
    if not settings.AI_API_KEY:
        return CheckResult("ai", False, "AI_API_KEY is empty")
    url = settings.AI_BASE_URL.rstrip("/") + "/models"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"})
    if resp.status_code >= 400:
        return CheckResult("ai", False, f"HTTP {resp.status_code}")
    return CheckResult("ai", True, "models endpoint reachable")


async def check_sms_config() -> CheckResult:
    if not settings.SMS_ENABLED:
        return CheckResult("sms", True, "skipped because SMS_ENABLED=false")
    missing = [
        key
        for key, value in {
            "SMS_ACCESS_KEY_ID": settings.SMS_ACCESS_KEY_ID,
            "SMS_ACCESS_KEY_SECRET": settings.SMS_ACCESS_KEY_SECRET,
            "SMS_SIGN_NAME": settings.SMS_SIGN_NAME,
            "SMS_TEMPLATE_CODE": settings.SMS_TEMPLATE_CODE,
        }.items()
        if not value
    ]
    if missing:
        return CheckResult("sms", False, "missing " + ",".join(missing))
    phone = os.getenv("CHECK_SMS_PHONE", "").strip()
    if phone:
        from app.services.sms_service import send_sms_verify_code

        result = await asyncio.wait_for(send_sms_verify_code(phone), timeout=20)
        if result.get("success"):
            return CheckResult("sms", True, f"sent to {phone[:3]}****{phone[-4:]}")
        return CheckResult("sms", False, str(result))

    import alibabacloud_dysmsapi20170525  # noqa: F401

    return CheckResult("sms", True, "sdk import ok; send test requires a phone number")


async def check_email() -> CheckResult:
    recipient = os.getenv("CHECK_EMAIL_TO", "").strip()
    if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASSWORD]):
        return CheckResult("email", False, "missing SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD")
    if not recipient:
        return CheckResult("email", True, "smtp config present; send test requires CHECK_EMAIL_TO")

    def send() -> None:
        msg = email.message.EmailMessage()
        msg["Subject"] = "Anti Pro staging email check"
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = recipient
        msg.set_content("This is a staging email connectivity check.")
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)

    await asyncio.wait_for(asyncio.to_thread(send), timeout=max(settings.SMTP_TIMEOUT + 5, 10))
    return CheckResult("email", True, f"sent to {recipient}")


async def run_check(name: str, func: Callable[[], Awaitable[CheckResult]]) -> CheckResult:
    try:
        return await func()
    except Exception as exc:
        return CheckResult(name, False, exc.__class__.__name__ + ": " + str(exc))


async def main() -> int:
    checks: list[tuple[str, Callable[[], Awaitable[CheckResult]]]] = [
        ("database", check_database),
        ("audit_database", check_audit_database),
        ("oss", check_oss),
        ("ai", check_ai),
        ("sms", check_sms_config),
        ("email", check_email),
    ]
    results = [await run_check(name, func) for name, func in checks]
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status} {result.name}: {result.message}")
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
