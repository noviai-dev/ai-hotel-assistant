"""Regression checks for evidence validation and SDK web-source compatibility."""
import unittest
import warnings
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import OpenAI

from marketing.advisor import Advice, Recommendation, generate
from marketing.config import Settings


class AdvisorEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(hotel="Test hotel", model="test")
        self.snapshot = {
            "as_of": "2026-11-05T09:00:00+09:00",
            "groups": [{"evidence_id": "price-001"}],
            "price_history": [{"evidence_id": "history-301"}],
            "self_price_comparisons": [{"evidence_id": "comparison-001"}],
        }

    def advice(self, evidence_ids, count=1):
        return Advice(
            email_body="请根据报价历史核对本店价位。", summary="核对本店价位",
            recommendations=[Recommendation(
                title="核对价格", evidence_ids=evidence_ids,
                action="核对报价", audience="家庭", channel="官网", timing="入住前",
                constraints=["待审核"], validation="核对可比报价", confidence="low",
            ) for _ in range(count)], missing_data=[],
        )

    def generate_mocked(self, evidence_ids, count=1, raw=None, status="completed"):
        response = SimpleNamespace(
            status=status, output_parsed=self.advice(evidence_ids, count),
            id="test-response", usage=None, model_dump=lambda **kwargs: raw or {},
        )
        client = MagicMock()
        client.responses.parse.return_value = response
        with patch("openai.OpenAI") as constructor:
            constructor.return_value.__enter__.return_value = client
            return generate(self.settings, self.snapshot)

    def test_accepts_history_and_comparison_with_market_evidence(self):
        ids = ["history-301", "comparison-001", "price-001"]
        result = self.generate_mocked(ids)
        self.assertEqual(result["advice"]["recommendations"][0]["evidence_ids"], ids)

    def test_unknown_ids_are_still_rejected(self):
        for evidence_id in ("history-999", "comparison-999", "price-999", "web-999"):
            with self.subTest(evidence_id=evidence_id), self.assertRaisesRegex(
                ValueError, evidence_id
            ):
                self.generate_mocked([evidence_id])

    def test_empty_evidence_and_too_many_recommendations_are_rejected(self):
        for ids, count in (([], 1), (["history-301"], 6)):
            with self.subTest(ids=ids, count=count), self.assertRaises(ValueError):
                self.generate_mocked(ids, count)

    def test_optional_collections_can_be_missing(self):
        del self.snapshot["price_history"]
        del self.snapshot["self_price_comparisons"]
        self.generate_mocked(["price-001"])

    def test_web_url_alias_is_normalized(self):
        raw = {"output": [{"action": {"sources": [
            {"type": "url", "url": "https://example.com/prices", "title": "Prices"}
        ]}}]}
        result = self.generate_mocked(["https://example.com/prices?utm_source=test"], raw=raw)
        self.assertEqual(result["advice"]["recommendations"][0]["evidence_ids"], ["web-001"])

    def test_incomplete_response_remains_rejected(self):
        with self.assertRaisesRegex(ValueError, "输出不完整"):
            self.generate_mocked(["price-001"], status="incomplete")

    def test_real_sdk_parses_api_sources_without_serialization_warnings(self):
        # Exercise the installed SDK parser over a fake HTTP response, without network.
        raw = {
            "id": "resp_test", "created_at": 0, "model": "test",
            "object": "response", "status": "completed", "usage": None,
            "output": [
                {"id": "ws_test", "type": "web_search_call", "status": "completed",
                 "action": {"type": "search", "queries": ["prices"], "sources": [
                     {"type": "api", "name": "oai-calculator"},
                     {"type": "url", "url": "https://example.com/prices"},
                 ]}},
                {"id": "msg_test", "type": "message", "role": "assistant",
                 "status": "completed", "content": [
                     {"type": "output_text", "annotations": [],
                      "text": self.advice(["history-301", "comparison-001"]).model_dump_json()},
                 ]},
            ],
        }

        def respond(request):
            warnings.warn("Unrelated warning must stay visible", UserWarning)
            return httpx.Response(200, json=raw)

        client = OpenAI(api_key="offline-test", max_retries=0,
                        http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with patch("openai.OpenAI", return_value=client):
                result = generate(self.settings, self.snapshot)
        self.assertEqual([str(item.message) for item in captured],
                         ["Unrelated warning must stay visible"])
        self.assertEqual(result["web_sources"], [{
            "evidence_id": "web-001", "title": "https://example.com/prices",
            "url": "https://example.com/prices",
        }])
        self.assertEqual(result["advice"]["recommendations"][0]["evidence_ids"],
                         ["history-301", "comparison-001"])


if __name__ == "__main__":
    unittest.main()
