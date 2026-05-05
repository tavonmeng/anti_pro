"""阿里云 OSS 文件存储服务

Bucket 权限设置为 **私有（private）**，通过签名 URL 提供有限时效的访问。
OSS_ENABLED=False 时自动回退到本地磁盘存储（开发环境）。
"""

import os
import time
from datetime import datetime
from typing import Optional

from app.config import settings


# ============ OSS 客户端初始化 ============

_oss_bucket = None


def _get_bucket():
    """懒加载 OSS Bucket 实例（进程级单例）"""
    global _oss_bucket
    if _oss_bucket is not None:
        return _oss_bucket

    import oss2
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    _oss_bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
    return _oss_bucket


# ============ 核心方法 ============

def upload_bytes(data: bytes, object_key: str, content_type: str = "") -> str:
    """
    上传字节数据到 OSS。

    Args:
        data: 文件的字节内容
        object_key: OSS 中的完整路径，如 site_photos/user123/20260429_photo.jpg
        content_type: MIME 类型，如 image/jpeg

    Returns:
        object_key（与入参相同，方便链式调用）
    """
    import oss2
    bucket = _get_bucket()

    headers = {}
    if content_type:
        headers["Content-Type"] = content_type

    result = bucket.put_object(object_key, data, headers=headers)
    if result.status != 200:
        raise RuntimeError("OSS 上传失败，状态码: %d" % result.status)

    return object_key


def get_signed_url(object_key: str, expires: int = 3600) -> str:
    """
    生成带签名的临时访问 URL（私有 Bucket 专用）。

    Args:
        object_key: OSS 对象路径
        expires: URL 有效期（秒），默认 1 小时

    Returns:
        带签名的完整 HTTPS URL
    """
    bucket = _get_bucket()
    url = bucket.sign_url("GET", object_key, expires, slash_safe=True)

    # sign_url 默认返回 http，强制改 https
    if url.startswith("http://"):
        url = "https://" + url[7:]

    return url


def delete_object(object_key: str) -> bool:
    """删除 OSS 上的对象"""
    try:
        bucket = _get_bucket()
        bucket.delete_object(object_key)
        return True
    except Exception as e:
        print("OSS 删除失败: %s" % str(e))
        return False


def download_object_to_file(object_key: str, file_path: str):
    """下载 OSS 私有对象到本地临时文件。"""
    bucket = _get_bucket()
    result = bucket.get_object(object_key)
    with open(file_path, "wb") as f:
        while True:
            chunk = result.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


# ============ 工具方法 ============

def build_object_key(prefix: str, user_id: str, filename: str) -> str:
    """
    构建 OSS 对象路径（含时间戳防重名）。

    示例: site_photos/user-abc123/20260429_143052_photo.jpg
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "%s_%s" % (timestamp, filename)
    if user_id:
        return "%s/%s/%s" % (prefix, user_id, safe_name)
    return "%s/%s" % (prefix, safe_name)


def upload_and_sign(
    data: bytes,
    prefix: str,
    user_id: str,
    filename: str,
    content_type: str = "",
    sign_expires: int = 3600,
) -> dict:
    """
    上传文件并返回签名 URL（一步到位的便捷方法）。

    Returns:
        {
            "object_key": "site_photos/user123/20260429_photo.jpg",
            "url": "https://bucket.oss-cn-hangzhou.../site_photos/...?签名参数",
            "filename": "photo.jpg",
            "size": 12345,
        }
    """
    object_key = build_object_key(prefix, user_id, filename)
    upload_bytes(data, object_key, content_type)
    signed_url = get_signed_url(object_key, sign_expires)

    return {
        "object_key": object_key,
        "url": signed_url,
        "filename": filename,
        "size": len(data),
    }


def maybe_sign_url(url_or_key: str, expires: int = 3600) -> str:
    """
    智能判断并签名 URL。

    - 如果 OSS 未启用，原样返回（本地路径如 /uploads/xxx）
    - 如果是已经带 http 的完整 URL，原样返回（已签名或外部链接）
    - 如果是 OSS object_key（不以 / 或 http 开头），生成签名 URL

    用于 API 返回数据库中存储的文件路径时，自动处理签名。
    """
    if not url_or_key:
        return url_or_key

    if not settings.OSS_ENABLED:
        return url_or_key

    # 已经是完整 URL（已签名或外部链接），不处理
    if url_or_key.startswith("http://") or url_or_key.startswith("https://"):
        return url_or_key

    # 本地路径（/uploads/...），在 OSS 模式下不应该出现，但安全起见原样返回
    if url_or_key.startswith("/"):
        return url_or_key

    # 是 OSS object_key，生成签名 URL
    return get_signed_url(url_or_key, expires)
