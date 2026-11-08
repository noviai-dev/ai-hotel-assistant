"""SMTP delivery; no external email dependency and no credentials in reports."""
import hashlib
import json
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate

from .repository import ReportStore


def build_message(settings, report):
    """Deliver the AI-written body verbatim; keep structured data in the attachment."""
    payload = report["payload"]
    snapshot = payload.get("snapshot", {})
    advice = payload.get("advice", {})
    # Reports generated before email_body was introduced only have a summary.
    body = advice.get("email_body") or advice.get("summary")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("报告缺少 AI 邮件正文，不能发送空报告")
    msg = EmailMessage()
    msg["Subject"] = f"酒店营销日报 | {settings.hotel} | {snapshot.get('as_of', '')[:10]}"
    msg["From"], msg["To"] = settings.email_from, settings.email_to
    msg["Date"] = formatdate(localtime=False)
    digest = hashlib.sha256(report["run_key"].encode()).hexdigest()
    msg["Message-ID"] = f"<{digest}@{settings.email_from.rsplit('@', 1)[1]}>"
    msg.set_content(body)
    msg.add_attachment(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
                       maintype="application", subtype="json", filename="marketing-report.json")
    return msg


def send_report(settings, key, *, retry=False):
    if not settings.email_enabled:
        return "disabled"
    settings.validate_email()
    store = ReportStore(settings.hotel)
    report = store.get(key)
    if not report or report["status"] not in {"succeeded", "no_data"}:
        return "not_ready"
    message = build_message(settings, report)
    if not store.claim_email(key, settings.email_to, retry):
        return "already_claimed"
    try:
        context = ssl.create_default_context()
        if settings.smtp_security == "ssl":
            client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30, context=context)
        else:
            client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
        try:
            if settings.smtp_security == "starttls":
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message, from_addr=settings.email_from, to_addrs=[settings.email_to])
        finally:
            client.close()
    except Exception as exc:
        store.finish_email(key, "failed", type(exc).__name__)
        raise
    store.finish_email(key, "sent")
    return "sent"
