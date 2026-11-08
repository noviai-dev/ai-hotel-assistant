"""Offline checks for AI-written report emails; no SMTP or API calls."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from marketing.advisor import Advice, generate
from marketing.mailer import build_message


class MarketingMessageTest(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            hotel="Novi", model="test", email_from="reports@example.com",
            email_to="owner@example.com",
        )
        self.body = "早上好。12月5日至12月15日的价格需要重点关注。\n\n1. 先核对本店房型，再决定是否调价。"
        self.report = {
            "run_key": "Novi:2026-11-05:live",
            "payload": {
                "snapshot": {"as_of": "2026-11-05T09:00:00+09:00",
                             "limitations": ["内部数据限制"]},
                "advice": {"email_body": self.body, "summary": "内部摘要",
                           "recommendations": [{"title": "内部结构化建议"}],
                           "missing_data": ["内部缺失信息"]},
                "web_sources": [{"evidence_id": "web-001", "title": "内部来源",
                                 "url": "https://example.com"}],
            },
        }

    def test_body_is_ai_answer_and_attachment_preserves_report(self):
        message = build_message(self.settings, self.report)
        self.assertEqual(message.get_body().get_content(), self.body + "\n")
        self.assertEqual(message["To"], self.settings.email_to)
        self.assertIn("2026-11-05", message["Subject"])
        attachment, = message.iter_attachments()
        self.assertEqual(json.loads(attachment.get_content()), self.report)

    def test_legacy_report_uses_ai_summary(self):
        del self.report["payload"]["advice"]["email_body"]
        message = build_message(self.settings, self.report)
        self.assertEqual(message.get_body().get_content(), "内部摘要\n")

    def test_missing_answer_is_rejected(self):
        self.report["payload"]["advice"] = {"email_body": "  "}
        with self.assertRaisesRegex(ValueError, "缺少 AI 邮件正文"):
            build_message(self.settings, self.report)

    def test_generated_answer_reaches_email_body(self):
        advice = Advice(email_body=self.body, summary="摘要",
                        recommendations=[], missing_data=[])
        response = SimpleNamespace(
            status="completed", output_parsed=advice, id="response-test",
            usage=None, model_dump=lambda **kwargs: {},
        )
        client = MagicMock()
        client.responses.parse.return_value = response
        with patch("openai.OpenAI") as openai:
            openai.return_value.__enter__.return_value = client
            result = generate(self.settings, {"as_of": "2026-11-05", "groups": []})
        self.report["payload"].update(result)
        message = build_message(self.settings, self.report)
        self.assertEqual(message.get_body().get_content(), self.body + "\n")


if __name__ == "__main__":
    unittest.main()
