"""SMTP delivery; no external email dependency and no credentials in reports."""
import hashlib
import json
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate

from .repository import ReportStore


def build_message(settings, report):
    payload = report["payload"]
    snapshot = payload.get("snapshot", {})
    advice = payload.get("advice", {})
    lines = [f"酒店：{settings.hotel}", f"报告：{report['run_key']}",
             f"数据时点：{snapshot.get('as_of', '')}", "状态：待人工审核", "",
             advice.get("summary", "没有符合条件的近期报价，本日未生成营销建议。")]
    for i, item in enumerate(advice.get("recommendations", []), 1):
        lines += ["", f"{i}. {item['title']}"]
        for label, key in [("行动", "action"), ("客群", "audience"), ("渠道", "channel"),
                           ("时间", "timing"), ("验证方式", "validation"), ("置信度", "confidence")]:
            lines.append(f"{label}：{item[key]}")
        lines += ["证据：" + ", ".join(item["evidence_ids"]), "约束：" + "；".join(item["constraints"])]
    lines += ["", "数据限制：", *snapshot.get("limitations", []), *advice.get("missing_data", [])]
    msg = EmailMessage()
    msg["Subject"] = f"酒店营销日报 | {settings.hotel} | {snapshot.get('as_of', '')[:10]}"
    msg["From"], msg["To"] = settings.email_from, settings.email_to
    msg["Date"] = formatdate(localtime=False)
    digest = hashlib.sha256(report["run_key"].encode()).hexdigest()
    msg["Message-ID"] = f"<{digest}@{settings.email_from.rsplit('@', 1)[1]}>"
    msg.set_content("\n".join(lines))
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
