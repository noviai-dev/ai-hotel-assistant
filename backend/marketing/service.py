import logging
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from .advisor import generate
from .repository import ReportStore, load_snapshot
from .mailer import send_report

logger = logging.getLogger(__name__)


def run_once(settings, *, dry_run=False, force=False, now=None):
    now = now or datetime.now(ZoneInfo(settings.timezone))
    store = ReportStore(settings.hotel)
    mode = "preview" if dry_run else "live"
    key = f"{settings.hotel}:{now.date()}:{mode}"
    if force:
        key += f":{uuid4()}"
    if not store.claim(key):
        return {"run_key": key, "status": "already_exists",
                "email_status": send_report(settings, key) if not dry_run else "disabled"}
    payload = {"model": settings.model, "prompt_version": "1", "review_status": "pending"}
    try:
        snapshot = load_snapshot(settings, now)
        payload["snapshot"] = snapshot
        if not snapshot["groups"]:
            status = "no_data"
        elif dry_run:
            status = "preview"
        else:
            payload.update(generate(settings, snapshot))
            status = "succeeded"
        store.save(key, status, payload)
    except Exception as exc:
        # Do not persist upstream messages which may include credentials or raw data.
        payload["error_type"] = type(exc).__name__
        store.save(key, "failed", payload)
        logger.error("Analysis failed (%s); run=%s", type(exc).__name__, key)
        raise
    # Email failure must not overwrite a successfully generated report.
    email_status = send_report(settings, key) if not dry_run else "disabled"
    return {"run_key": key, "status": status, "payload": payload, "email_status": email_status}
