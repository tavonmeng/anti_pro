"""阿里云 OSS 文件存储服务

Bucket 权限设置为 **私有（private）**，通过签名 URL 提供有限时效的访问。
OSS_ENABLED=False 时自动回退到本地磁盘存储（开发环境）。
"""

import os
from typing import Mapping
from urllib.parse import unquote, urlparse, urlunparse

from app.config import settings
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.retry import RetryableExternalError, retry_sync
from app.utils.timezone import beijing_now


logger = get_module_logger("order")


def _is_retryable_status(status_code: int) -> bool:
    return status_code in (408, 429) or status_code >= 500


def _raise_for_oss_status(operation: str, status_code: int) -> None:
    message = "OSS %s 失败，状态码: %d" % (operation, status_code)
    if _is_retryable_status(status_code):
        raise RetryableExternalError(message)
    raise RuntimeError(message)


def _is_retryable_oss_exception(exc: BaseException) -> bool:
    if isinstance(exc, RetryableExternalError):
        return True
    if isinstance(exc, RuntimeError) and "状态码" in str(exc):
        return False
    return True


# ============ OSS 客户端初始化 ============

_oss_bucket = None


def _oss_endpoint() -> str:
    endpoint = (settings.OSS_ENDPOINT or "").strip()
    if endpoint and not endpoint.startswith(("http://", "https://")):
        endpoint = "https://" + endpoint
    return endpoint


def _oss_public_endpoint() -> str:
    endpoint = (settings.OSS_PUBLIC_ENDPOINT or "").strip()
    if not endpoint:
        endpoint = (settings.OSS_ENDPOINT or "").strip().replace("-internal", "")
    if endpoint and not endpoint.startswith(("http://", "https://")):
        endpoint = "https://" + endpoint
    return endpoint


def _rewrite_to_public_endpoint(url: str) -> str:
    public_endpoint = _oss_public_endpoint()
    if not public_endpoint:
        return url

    public_host = urlparse(public_endpoint).netloc
    if not public_host:
        return url

    parsed = urlparse(url)
    if not parsed.netloc:
        return url

    bucket_name = settings.OSS_BUCKET_NAME
    if bucket_name and parsed.netloc.startswith(f"{bucket_name}."):
        public_netloc = f"{bucket_name}.{public_host}"
    else:
        public_netloc = public_host
    return urlunparse(parsed._replace(netloc=public_netloc))


def _get_bucket():
    """懒加载 OSS Bucket 实例（进程级单例）"""
    global _oss_bucket
    if _oss_bucket is not None:
        return _oss_bucket

    import oss2
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    _oss_bucket = oss2.Bucket(auth, _oss_endpoint(), settings.OSS_BUCKET_NAME)
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
    bucket = _get_bucket()

    headers = {}
    if content_type:
        headers["Content-Type"] = content_type

    def _upload():
        result = bucket.put_object(object_key, data, headers=headers)
        if result.status != 200:
            _raise_for_oss_status("upload_bytes", result.status)
        return result

    retry_sync(
        _upload,
        logger=logger,
        event="oss_upload_bytes",
        attempts=settings.OSS_RETRY_ATTEMPTS,
        fields={"object_key": object_key, "size": len(data), "content_type": content_type},
        should_retry=_is_retryable_oss_exception,
    )

    return object_key


def upload_file(object_key: str, file_path: str, content_type: str = "") -> str:
    """
    从本地临时文件上传到 OSS，避免大文件在应用进程中整块占用内存。
    """
    bucket = _get_bucket()

    headers = {}
    if content_type:
        headers["Content-Type"] = content_type

    def _upload():
        result = bucket.put_object_from_file(object_key, file_path, headers=headers)
        if result.status != 200:
            _raise_for_oss_status("upload_file", result.status)
        return result

    retry_sync(
        _upload,
        logger=logger,
        event="oss_upload_file",
        attempts=settings.OSS_RETRY_ATTEMPTS,
        fields={
            "object_key": object_key,
            "file_path": file_path,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else None,
            "content_type": content_type,
        },
        should_retry=_is_retryable_oss_exception,
    )

    return object_key


def get_signed_url(
    object_key: str,
    expires: int = 3600,
    response_params: Mapping[str, str] | None = None,
) -> str:
    """
    生成带签名的临时访问 URL（私有 Bucket 专用）。

    Args:
        object_key: OSS 对象路径
        expires: URL 有效期（秒），默认 1 小时

    Returns:
        带签名的完整 HTTPS URL
    """
    bucket = _get_bucket()
    params = dict(response_params or {}) or None
    url = bucket.sign_url("GET", object_key, expires, params=params, slash_safe=True)

    # sign_url 默认返回 http，强制改 https
    if url.startswith("http://"):
        url = "https://" + url[7:]

    return _rewrite_to_public_endpoint(url)


def extract_object_key(url_or_key: str) -> str:
    """从本系统 OSS URL 或 object_key 中提取对象路径。

    历史数据里有些文件只保存了带签名的完整 URL。签名过期后必须从 URL
    反推出 object_key，再重新签名。
    """
    if not url_or_key:
        return ""

    value = str(url_or_key).strip()
    if not value:
        return ""

    if not value.startswith(("http://", "https://")):
        return "" if value.startswith("/") else value

    parsed = urlparse(value)
    if not parsed.netloc or not parsed.path:
        return ""

    host = parsed.netloc.split("@")[-1].split(":")[0]
    bucket_name = settings.OSS_BUCKET_NAME
    endpoint = settings.OSS_ENDPOINT or ""
    endpoint_host = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}").netloc
    public_endpoint = _oss_public_endpoint()
    public_endpoint_host = urlparse(public_endpoint).netloc if public_endpoint else ""
    object_path = unquote(parsed.path.lstrip("/"))
    if not object_path:
        return ""

    if bucket_name and endpoint_host:
        if host == f"{bucket_name}.{endpoint_host}":
            return object_path
        if host == endpoint_host and object_path.startswith(f"{bucket_name}/"):
            return object_path[len(bucket_name) + 1:]

    if bucket_name and public_endpoint_host:
        if host == f"{bucket_name}.{public_endpoint_host}":
            return object_path
        if host == public_endpoint_host and object_path.startswith(f"{bucket_name}/"):
            return object_path[len(bucket_name) + 1:]

    if bucket_name and host.startswith(f"{bucket_name}.") and ".aliyuncs.com" in host:
        return object_path

    return ""


def delete_object(object_key: str) -> bool:
    """删除 OSS 上的对象"""
    try:
        bucket = _get_bucket()
        retry_sync(
            lambda: bucket.delete_object(object_key),
            logger=logger,
            event="oss_delete_object",
            attempts=settings.OSS_RETRY_ATTEMPTS,
            fields={"object_key": object_key},
            should_retry=_is_retryable_oss_exception,
        )
        log_business_event(logger, "oss_object_deleted", object_key=object_key)
        return True
    except Exception as e:
        log_business_event(logger, "oss_object_delete_failed", level="warning", object_key=object_key, error=str(e))
        return False


def download_object_to_file(object_key: str, file_path: str):
    """下载 OSS 私有对象到本地临时文件。"""
    bucket = _get_bucket()

    def _download():
        result = bucket.get_object(object_key)
        with open(file_path, "wb") as f:
            while True:
                chunk = result.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

    retry_sync(
        _download,
        logger=logger,
        event="oss_download_object",
        attempts=settings.OSS_RETRY_ATTEMPTS,
        fields={"object_key": object_key, "target": file_path},
        should_retry=_is_retryable_oss_exception,
    )


def download_object_bytes(object_key: str) -> bytes:
    """下载 OSS 私有对象并返回 bytes。适合 PDF 这类小型归档文件。"""
    bucket = _get_bucket()

    def _download() -> bytes:
        result = bucket.get_object(object_key)
        chunks = []
        while True:
            chunk = result.read(1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)

    return retry_sync(
        _download,
        logger=logger,
        event="oss_download_object",
        attempts=settings.OSS_RETRY_ATTEMPTS,
        fields={"object_key": object_key},
        should_retry=_is_retryable_oss_exception,
    )


# ============ 工具方法 ============

def build_object_key(prefix: str, user_id: str, filename: str) -> str:
    """
    构建 OSS 对象路径（含时间戳防重名）。

    示例: site_photos/user-abc123/20260429_143052_photo.jpg
    """
    timestamp = beijing_now().strftime("%Y%m%d_%H%M%S")
    clean_prefix = (prefix or "uploads").strip().strip("/")
    clean_user_id = (user_id or "").strip().strip("/").replace("\\", "_").replace("/", "_")
    clean_filename = os.path.basename((filename or "upload").replace("\\", "/")).strip() or "upload"
    safe_name = "%s_%s" % (timestamp, clean_filename)
    if clean_user_id:
        return "%s/%s/%s" % (clean_prefix, clean_user_id, safe_name)
    return "%s/%s" % (clean_prefix, safe_name)


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


def upload_file_and_sign(
    file_path: str,
    prefix: str,
    user_id: str,
    filename: str,
    content_type: str = "",
    sign_expires: int = 3600,
) -> dict:
    """
    上传本地文件并返回签名 URL。

    适用于 UploadFile 已流式落到临时文件后的大文件上传路径。
    """
    object_key = build_object_key(prefix, user_id, filename)
    upload_file(object_key, file_path, content_type)
    signed_url = get_signed_url(object_key, sign_expires)

    return {
        "object_key": object_key,
        "url": signed_url,
        "filename": filename,
        "size": os.path.getsize(file_path),
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

    if url_or_key.startswith("http://") or url_or_key.startswith("https://"):
        object_key = extract_object_key(url_or_key)
        return get_signed_url(object_key, expires) if object_key else url_or_key

    # 本地路径（/uploads/...），在 OSS 模式下不应该出现，但安全起见原样返回
    if url_or_key.startswith("/"):
        return url_or_key

    # 是 OSS object_key，生成签名 URL
    return get_signed_url(url_or_key, expires)


def sign_file_url_fields(file_item: dict, expires: int = 3600) -> dict:
    """Refresh common browser-facing URL fields on a file metadata dict."""
    if not isinstance(file_item, dict):
        return file_item

    object_key = file_item.get("object_key") or file_item.get("objectKey")
    if not object_key:
        object_key = extract_object_key(
            file_item.get("url") or file_item.get("file_url") or file_item.get("href") or ""
        )

    if object_key:
        signed_url = maybe_sign_url(object_key, expires)
        file_item["object_key"] = object_key
        if "objectKey" in file_item:
            file_item["objectKey"] = object_key
        if "url" in file_item or not any(file_item.get(key) for key in ("file_url", "href")):
            file_item["url"] = signed_url
        if "file_url" in file_item:
            file_item["file_url"] = signed_url
        if "href" in file_item:
            file_item["href"] = signed_url
        return file_item

    for key in ("url", "file_url", "href"):
        if file_item.get(key):
            file_item[key] = maybe_sign_url(file_item[key], expires)
    return file_item
