"""真实价格历史分析入口：读取数据库、调用 AI、保存报告并发送邮件。

从项目根目录运行：
    .venv/Scripts/python backend/test_marketing_history.py

读取项目根目录 .env，需要 OPENAI_MODEL、OPENAI_API_KEY、数据库连接配置，
以及 MARKETING_EMAIL_ENABLED=true 和完整的 SMTP/收发件邮箱配置。
每次直接运行都会创建新报告、真实调用 API 并发送邮件。
导入此模块或执行 unittest discover 不会触发外部调用。
原离线测试已移至 test_marketing_history_unit.py。
"""

import json
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from marketing.config import Settings
from marketing.repository import ReportStore
from marketing.service import run_once


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    settings = Settings.load()
    if not settings.model:
        raise ValueError("请在 .env 中设置 OPENAI_MODEL")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError("请在 .env 中设置 OPENAI_API_KEY")
    if not settings.email_enabled:
        raise ValueError("此入口会发送真实邮件，请在 .env 中设置 MARKETING_EMAIL_ENABLED=true")
    # 在调用 AI 前校验邮件配置，避免生成报告后才发现不能发信。
    settings.validate_email()

    now = datetime.now(ZoneInfo(settings.timezone))
    print(
        f"酒店：{settings.hotel}\n模型：{settings.model}"
        f"\n分析时间：{now.isoformat()}"
        f"\n历史回看：{settings.history_days}天"
        f"\n收件人：{settings.email_to}"
        "\n开始读取真实报价、调用 AI 并发送报告……",
        flush=True,
    )
    ReportStore.initialize()
    # 每次手动运行使用独立报告键；复用正式流程的存储、证据校验和邮件状态记录。
    result = run_once(settings, force=True, now=now)
    print(f"\n报告：{result['run_key']}\n报告状态：{result['status']}", flush=True)
    snapshot = result["payload"]["snapshot"]
    print(
        f"市场报价分组：{len(snapshot['groups'])}"
        f"\n历史价格分组：{len(snapshot['price_history'])}"
        f"\n本店比价分组：{len(snapshot['self_price_comparisons'])}",
        flush=True,
    )
    print("\nAI分析结果（待人工审核）：", flush=True)
    print(json.dumps(result["payload"]["advice"], ensure_ascii=False, indent=2), flush=True)
    if result["email_status"] != "sent":
        print(f"邮件未发送：{result['email_status']}", file=sys.stderr, flush=True)
        return 1
    print(f"\n邮件已由 SMTP 接受：{settings.email_to}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
