#!/usr/bin/env python3
"""Send a one-off test email through Alibaba Mail SMTP."""

from __future__ import annotations

import argparse
import email.utils
import getpass
import os
import smtplib
import ssl
import sys
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


DEFAULT_USER = "support@uniquevisionx.com"
DEFAULT_RECIPIENT = "mht0228@163.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test email via Alibaba Mail SMTP.")
    parser.add_argument("--host", default=os.getenv("ALIYUN_SMTP_HOST", "smtp.qiye.aliyun.com"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ALIYUN_SMTP_PORT", "465")))
    parser.add_argument("--user", default=os.getenv("ALIYUN_SMTP_USER", DEFAULT_USER))
    parser.add_argument("--from-name", default=os.getenv("ALIYUN_SMTP_FROM_NAME", "Unique Vision AI"))
    parser.add_argument("--to", default=os.getenv("ALIYUN_SMTP_TO", DEFAULT_RECIPIENT))
    parser.add_argument("--subject", default=os.getenv("ALIYUN_SMTP_SUBJECT", "Unique Vision AI email test"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("ALIYUN_SMTP_TIMEOUT", "20")))
    parser.add_argument(
        "--with-test-attachment",
        action="store_true",
        help="Attach a small generated text file to verify attachment delivery.",
    )
    parser.add_argument(
        "--plain-port",
        action="store_true",
        help="Use a plain SMTP connection instead of SMTP over SSL. Intended for port 25/80 tests.",
    )
    return parser.parse_args()


def get_password() -> str:
    password = os.getenv("ALIYUN_SMTP_PASSWORD", "").strip()
    if password:
        return password
    return getpass.getpass("Alibaba Mail SMTP password/security password: ").strip()


def build_message(
    sender: str,
    from_name: str,
    recipient: str,
    subject: str,
    with_test_attachment: bool,
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(from_name, "utf-8")), sender))
    msg["To"] = recipient
    msg["Reply-To"] = sender
    msg["Message-Id"] = email.utils.make_msgid(domain=sender.split("@", 1)[-1])
    msg["Date"] = email.utils.formatdate(localtime=True)

    text = (
        "This is a test email from Unique Vision AI via Alibaba Mail SMTP.\n"
        "If you received this, SMTP authentication and delivery are working.\n"
    )
    html = """
    <html>
      <body>
        <p>This is a test email from <strong>Unique Vision AI</strong> via Alibaba Mail SMTP.</p>
        <p>If you received this, SMTP authentication and delivery are working.</p>
      </body>
    </html>
    """
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(text, "plain", "utf-8"))
    body.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(body)

    if with_test_attachment:
        content = (
            "Unique Vision AI Alibaba Mail SMTP attachment test\n"
            f"From: {sender}\n"
            f"To: {recipient}\n"
        ).encode("utf-8")
        attachment = MIMEApplication(content)
        attachment.add_header("Content-Disposition", "attachment", filename="uniquevisionx-email-test.txt")
        msg.attach(attachment)

    return msg


def send_email(args: argparse.Namespace, password: str) -> None:
    msg = build_message(args.user, args.from_name, args.to, args.subject, args.with_test_attachment)
    if args.plain_port:
        with smtplib.SMTP(args.host, args.port, timeout=args.timeout) as client:
            client.login(args.user, password)
            client.sendmail(args.user, [args.to], msg.as_string())
        return

    context = ssl.create_default_context()
    context.set_ciphers("DEFAULT")
    with smtplib.SMTP_SSL(args.host, args.port, timeout=args.timeout, context=context) as client:
        client.login(args.user, password)
        client.sendmail(args.user, [args.to], msg.as_string())


def main() -> int:
    args = parse_args()
    password = get_password()
    if not password:
        print("FAIL missing SMTP password/security password", file=sys.stderr)
        return 2

    try:
        send_email(args, password)
    except smtplib.SMTPAuthenticationError as exc:
        print(f"FAIL authentication error: {exc.smtp_code} {exc.smtp_error!r}", file=sys.stderr)
        return 1
    except smtplib.SMTPConnectError as exc:
        print(f"FAIL connection error: {exc.smtp_code} {exc.smtp_error!r}", file=sys.stderr)
        return 1
    except smtplib.SMTPRecipientsRefused as exc:
        print(f"FAIL recipients refused: {exc.recipients!r}", file=sys.stderr)
        return 1
    except smtplib.SMTPSenderRefused as exc:
        print(f"FAIL sender refused: {exc.smtp_code} {exc.smtp_error!r}", file=sys.stderr)
        return 1
    except smtplib.SMTPDataError as exc:
        print(f"FAIL data refused: {exc.smtp_code} {exc.smtp_error!r}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAIL {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1

    attachment_note = " with attachment" if args.with_test_attachment else ""
    print(f"OK sent test email{attachment_note} from {args.user} to {args.to} via {args.host}:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
