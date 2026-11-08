import argparse
import json
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Settings
from .repository import ReportStore
from .service import run_once
from .mailer import send_report


def main():
    parser = argparse.ArgumentParser(description="酒店营销建议服务（不执行营销动作）")
    parser.add_argument("command", choices=["init-db", "run", "schedule", "latest", "send-email"])
    parser.add_argument("--run-key", help="补发指定运行记录，不重新调用模型")
    parser.add_argument("--retry-email", action="store_true", help="确认收件箱后重试failed邮件，可能重复投递")
    parser.add_argument("--dry-run", action="store_true", help="只查询和保存指标，不调用OpenAI")
    parser.add_argument("--force", action="store_true", help="手动重跑，可能再次产生API费用")
    args = parser.parse_args()
    if args.force and args.command != "run":
        parser.error("--force 仅用于 run")
    if args.command == "send-email" and (not args.run_key or args.dry_run):
        parser.error("send-email 需要 --run-key，且不能使用 --dry-run")
    if args.command != "send-email" and (args.run_key or args.retry_email):
        parser.error("--run-key 和 --retry-email 仅用于 send-email")
    logging.basicConfig(level=logging.INFO)
    try:
        settings = Settings.load()
        if args.command == "init-db":
            ReportStore.initialize()
            result = {"status": "initialized", "tables": ["a_marketing_reports", "a_report_emails"]}
        elif args.command == "send-email":
            result = {"email_status": send_report(settings, args.run_key, retry=args.retry_email)}
        elif args.command == "latest":
            result = ReportStore(settings.hotel).latest()
        elif args.command == "run":
            result = run_once(settings, dry_run=args.dry_run, force=args.force)
        else:
            attempted_day = None
            while True:
                now = datetime.now(ZoneInfo(settings.timezone))
                if now.hour >= settings.hour and attempted_day != now.date():
                    attempted_day = now.date()
                    try:
                        outcome = run_once(settings, dry_run=args.dry_run, now=now)
                        logging.info("Scheduled analysis: %s", outcome["status"])
                    except Exception as exc:
                        logging.error("Scheduled job failed: %s; check report/email status before retrying", type(exc).__name__)
                time.sleep(30)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.error("Cannot complete analysis (%s). Check configuration, database and API access.", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
