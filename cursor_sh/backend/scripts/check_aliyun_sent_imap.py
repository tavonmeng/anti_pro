#!/usr/bin/env python3
"""Check Alibaba Mail IMAP folders for recently sent test messages."""

from __future__ import annotations

import argparse
import getpass
import imaplib
import os
import re
import sys
from email.header import decode_header
from email.parser import BytesParser
from email.policy import default


DEFAULT_USER = "support@uniquevisionx.com"
DEFAULT_TARGET = "mht0228@163.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search Alibaba Mail IMAP folders for test messages.")
    parser.add_argument("--host", default=os.getenv("ALIYUN_IMAP_HOST", "imap.qiye.aliyun.com"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ALIYUN_IMAP_PORT", "993")))
    parser.add_argument("--user", default=os.getenv("ALIYUN_IMAP_USER", DEFAULT_USER))
    parser.add_argument("--target", default=os.getenv("ALIYUN_IMAP_TARGET", DEFAULT_TARGET))
    return parser.parse_args()


def get_password() -> str:
    password = os.getenv("ALIYUN_IMAP_PASSWORD", "").strip()
    if password:
        return password
    return getpass.getpass("Alibaba Mail IMAP password/security password: ").strip()


def parse_mailbox_name(line: bytes) -> bytes | None:
    # LIST returns: (<flags>) "<delimiter>" "<mailbox name>"
    match = re.search(rb'\) (?:"[^"]*"|NIL) (.+)$', line)
    if not match:
        return None
    name = match.group(1).strip()
    if name.startswith(b'"') and name.endswith(b'"'):
        name = name[1:-1].replace(br'\"', b'"').replace(br'\\', b'\\')
    return name


def decode_value(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for payload, charset in decode_header(value):
        if isinstance(payload, bytes):
            parts.append(payload.decode(charset or "utf-8", "replace"))
        else:
            parts.append(payload)
    return "".join(parts)


def search_folder(imap: imaplib.IMAP4_SSL, mailbox: bytes, target: str) -> list[str]:
    status, _ = imap.select(mailbox, readonly=True)
    if status != "OK":
        return []

    status, data = imap.search(None, "ALL")
    if status != "OK" or not data or not data[0]:
        return []

    found = []
    ids = data[0].split()[-50:]
    for msg_id in ids:
        status, fetched = imap.fetch(msg_id, "(BODY.PEEK[HEADER])")
        if status != "OK" or not fetched:
            continue
        for item in fetched:
            if not isinstance(item, tuple):
                continue
            message = BytesParser(policy=default).parsebytes(item[1])
            subject = decode_value(message.get("Subject"))
            sender = decode_value(message.get("From"))
            recipient = decode_value(message.get("To"))
            date = decode_value(message.get("Date"))
            if target.lower() not in recipient.lower():
                continue
            found.append(f"date={date} from={sender} to={recipient} subject={subject}")
    return found


def main() -> int:
    args = parse_args()
    password = get_password()
    if not password:
        print("FAIL missing IMAP password/security password", file=sys.stderr)
        return 2

    with imaplib.IMAP4_SSL(args.host, args.port) as imap:
        imap.login(args.user, password)
        status, boxes = imap.list()
        if status != "OK":
            print("FAIL could not list mailboxes", file=sys.stderr)
            return 1

        print("MAILBOXES")
        mailboxes: list[bytes] = []
        for box in boxes or []:
            print(box.decode("utf-8", "replace"))
            name = parse_mailbox_name(box)
            if name:
                mailboxes.append(name)

        print("\nMATCHES")
        total = 0
        for mailbox in mailboxes:
            try:
                matches = search_folder(imap, mailbox, args.target)
            except Exception as exc:
                print(f"SKIP {mailbox!r}: {exc.__class__.__name__}: {exc}")
                continue
            if not matches:
                continue
            print(f"FOLDER {mailbox.decode('utf-8', 'replace')}")
            for match in matches:
                print("  " + match)
                total += 1

        imap.logout()
    print(f"\nFOUND {total} message(s) addressed to {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
