#!/usr/bin/env python3
"""Smoke-test an Aliyun OSS AccessKey for the staging bucket.

The credential file can use the format:

AccessKey ID
<id>

AccessKey Secret
<secret>

The script never prints the secret. By default it creates a small object,
reads it back, signs a URL, then deletes the object.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _read_credentials(path: Path) -> tuple[str, str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    key_id = ""
    key_secret = ""

    for index, line in enumerate(lines):
        normalized = line.lower().replace(" ", "").replace("_", "")
        if normalized in {"accesskeyid", "accesskey"} and index + 1 < len(lines):
            key_id = lines[index + 1].strip()
        elif normalized == "accesskeysecret" and index + 1 < len(lines):
            key_secret = lines[index + 1].strip()

    if not key_id and lines:
        key_id = lines[0]
    if not key_secret and len(lines) > 1:
        key_secret = lines[1]

    if not key_id or not key_secret:
        raise ValueError(f"could not parse AccessKey ID/Secret from {path}")

    return key_id, key_secret


def _endpoint(value: str) -> str:
    value = value.strip()
    if value and not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Test staging_user Aliyun OSS permissions")
    parser.add_argument("--credentials", default="/root/workspace/staging_user.txt", help="AccessKey txt path")
    parser.add_argument("--bucket", default=os.getenv("OSS_BUCKET_NAME", ""), help="OSS bucket name")
    parser.add_argument("--endpoint", default=os.getenv("OSS_ENDPOINT", ""), help="OSS endpoint")
    parser.add_argument("--prefix", default="diagnostics/staging_user", help="temporary object prefix")
    parser.add_argument("--read-only", action="store_true", help="only call get_bucket_info")
    args = parser.parse_args()

    if not args.bucket:
        raise SystemExit("missing --bucket or OSS_BUCKET_NAME")
    if not args.endpoint:
        raise SystemExit("missing --endpoint or OSS_ENDPOINT")

    try:
        import oss2
    except ImportError as exc:
        raise SystemExit("oss2 is not installed; run inside anti-pro-backend container or install requirements") from exc

    key_id, key_secret = _read_credentials(Path(args.credentials))
    masked_id = key_id[:6] + "..." + key_id[-4:] if len(key_id) > 10 else "***"

    auth = oss2.Auth(key_id, key_secret)
    bucket = oss2.Bucket(auth, _endpoint(args.endpoint), args.bucket)

    print(f"credential_id={masked_id}")
    print(f"bucket={args.bucket}")
    print(f"endpoint={args.endpoint}")

    info = bucket.get_bucket_info()
    print(f"get_bucket_info=ok name={info.name}")

    if args.read_only:
        return 0

    object_key = f"{args.prefix.rstrip('/')}/ak-smoke-{int(time.time())}.txt"
    body = f"staging_user oss smoke test {int(time.time())}\n".encode("utf-8")

    put_result = bucket.put_object(object_key, body, headers={"Content-Type": "text/plain"})
    print(f"put_object=status:{put_result.status} key={object_key}")
    if put_result.status != 200:
        return 1

    downloaded = bucket.get_object(object_key).read()
    print(f"get_object=ok bytes={len(downloaded)} matches={downloaded == body}")
    if downloaded != body:
        return 1

    signed_url = bucket.sign_url("GET", object_key, 300)
    print(f"sign_url=ok scheme={signed_url.split(':', 1)[0]} expires=300")

    delete_result = bucket.delete_object(object_key)
    print(f"delete_object=status:{delete_result.status}")
    return 0 if delete_result.status in (200, 204) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error={type(exc).__name__}: {exc}", file=sys.stderr)
        raise
