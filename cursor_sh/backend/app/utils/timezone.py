"""统一系统时间。

业务主要面向北京时间用户，数据库写入、JSON 业务字段和 API 返回统一使用
Asia/Shanghai（UTC+08:00）。
"""

from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def beijing_now() -> datetime:
    """返回带 +08:00 时区信息的当前北京时间。"""
    return datetime.now(BEIJING_TZ)


def beijing_now_iso() -> str:
    """返回当前北京时间 ISO 字符串。"""
    return beijing_now().isoformat()


def ensure_beijing(dt: datetime | None) -> datetime | None:
    """将数据库/业务时间规范为北京时间。

    历史数据或部分数据库驱动可能返回无时区 datetime。系统现在约定数据库内
    无时区时间也按北京时间解释，避免前端再按 UTC 二次偏移。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(BEIJING_TZ)


def beijing_iso(dt: datetime | None, fallback: str | None = None) -> str | None:
    """将 datetime 输出为北京时间 ISO 字符串。"""
    normalized = ensure_beijing(dt)
    if normalized is None:
        return fallback
    return normalized.isoformat()
