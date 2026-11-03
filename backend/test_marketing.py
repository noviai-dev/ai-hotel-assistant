"""读取项目 .env，使用真实 PostgreSQL 和大模型生成并可邮件发送营销建议。

从项目根目录运行：
    .venv/Scripts/python backend/test_marketing.py

这是实际调用 API 的集成测试，不使用 mock。普通 unittest discover 会跳过，
直接运行此文件才启用。运行会保存已验证的建议；启用邮件配置后发送邮件。
"""

import json
import os
import sys
import unittest
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from marketing.advisor import Advice, generate
from marketing.config import Settings
from marketing.mailer import send_report
from marketing.repository import ReportStore, load_snapshot


class MarketingAdviceTest(unittest.TestCase):
    live_enabled = False

    def test_generate_marketing_advice(self):
        if not self.live_enabled:
            self.skipTest("真实调用请直接运行：python backend/test_marketing.py")

        # 加载项目根目录 .env，已有进程环境变量优先。
        settings = Settings.load()
        self.assertTrue(settings.model, "请在 .env 中设置 OPENAI_MODEL")
        self.assertTrue(os.getenv("OPENAI_API_KEY"), "请在 .env 中设置 OPENAI_API_KEY")
        self.assertTrue(os.getenv("PGPASSWORD"), "请在 .env 中设置 PGPASSWORD")

        now = datetime.now(ZoneInfo(settings.timezone))
        snapshot = load_snapshot(settings, now)
        self.assertTrue(
            snapshot["groups"],
            "数据库没有当前分析窗口内的有效报价，请检查 MARKETING_HOTEL、"
            "MARKETING_HORIZON_DAYS、MARKETING_FRESHNESS_DAYS 或先采集单晚报价",
        )
        print(f"\n酒店：{settings.hotel}\n模型：{settings.model}"
              f"\n分析时间：{now.isoformat()}\n报价分组：{len(snapshot['groups'])}", flush=True)

        # 执行 marketing 模块的真实建议生成和证据校验逻辑。
        result = generate(settings, snapshot)
        advice = Advice.model_validate(result["advice"])
        self.assertTrue(result["response_id"], "API 未返回响应 ID")
        self.assertTrue(advice.summary.strip(), "营销摘要不能为空")
        self.assertGreaterEqual(len(advice.recommendations), 1, "模型未生成营销建议")
        self.assertLessEqual(len(advice.recommendations), 5)
        valid_ids = ({group["evidence_id"] for group in snapshot["groups"]}
                     | {change["evidence_id"] for change in snapshot.get("price_changes", [])}
                     | {source["evidence_id"] for source in result.get("web_sources", [])})
        for recommendation in advice.recommendations:
            with self.subTest(title=recommendation.title):
                self.assertTrue(recommendation.evidence_ids)
                self.assertTrue(set(recommendation.evidence_ids) <= valid_ids)
                for field in ("title", "action", "audience", "channel", "timing", "validation"):
                    self.assertTrue(getattr(recommendation, field).strip(), f"{field} 不能为空")

        print("\n营销建议（待人工审核）：", flush=True)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

        if settings.email_enabled:
            # 复用正式报告邮件流程，邮件带完整 JSON 附件并记录发送状态。
            store = ReportStore(settings.hotel)
            store.initialize()
            run_key = f"{settings.hotel}:{now.date()}:test:{uuid4()}"
            payload = {
                "model": settings.model,
                "prompt_version": "2",
                "review_status": "pending",
                "snapshot": snapshot,
                **result,
            }
            if not store.claim(run_key):
                self.fail("无法创建本次测试营销报告")
            store.save(run_key, "succeeded", payload)
            email_status = send_report(settings, run_key)
            self.assertEqual(email_status, "sent", f"邮件未发送：{email_status}")
            print(f"\n邮件已由 SMTP 接受：{settings.email_to}", flush=True)
        else:
            print("\n邮件未发送：MARKETING_EMAIL_ENABLED 未设为 true。", flush=True)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    MarketingAdviceTest.live_enabled = True
    unittest.main(verbosity=2)

