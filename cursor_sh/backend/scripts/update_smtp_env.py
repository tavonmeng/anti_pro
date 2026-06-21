#!/usr/bin/env python3
"""Update SMTP keys in a backend .env file without printing secrets."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path


SMTP_VALUES = {
    "SMTP_HOST": "smtp.qiye.aliyun.com",
    "SMTP_PORT": "465",
    "SMTP_USER": "support@uniquevisionx.com",
    "SMTP_FROM": "support@uniquevisionx.com",
    "SMTP_FROM_NAME": "Unique Vision AI",
    "SMTP_TIMEOUT": "20",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update backend SMTP .env settings.")
    parser.add_argument("env_file", help="Path to the backend .env file to update")
    return parser.parse_args()


def read_password() -> str:
    password = os.getenv("ALIYUN_SMTP_PASSWORD", "").strip()
    if password:
        return password
    return getpass.getpass("Alibaba Mail SMTP password/security password: ").strip()


def update_env(path: Path, values: dict[str, str]) -> None:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    seen: set[str] = set()
    updated: list[str] = []

    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            updated.append(line)
            continue

        key = line.split("=", 1)[0].strip()
        if key in values:
            updated.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            updated.append(line)

    for key, value in values.items():
        if key not in seen:
            updated.append(f"{key}={value}")

    content = "\n".join(updated) + ("\n" if original.endswith("\n") else "")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    path = Path(args.env_file)
    if not path.exists():
        print(f"FAIL env file not found: {path}")
        return 1

    password = read_password()
    if not password:
        print("FAIL missing SMTP password/security password")
        return 2

    values = dict(SMTP_VALUES)
    values["SMTP_PASSWORD"] = password
    update_env(path, values)
    print(f"OK updated SMTP settings in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
