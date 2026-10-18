import os
from contextlib import contextmanager
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from marketing.config import Settings
from marketing.repository import ReportStore, load_snapshot
from marketing.service import run_once
from marketing.advisor import Advice, Recommendation, generate


class MarketingTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings("Test Hotel", "configured-model")
        self.store_patch = patch("marketing.service.ReportStore")
        self.store = self.store_patch.start().return_value
        self.store.claim.return_value = True
        self.addCleanup(self.store_patch.stop)
        self.now = datetime(2026, 10, 18, 9, tzinfo=ZoneInfo("Asia/Tokyo"))
        self.snapshot = {"groups": [{"evidence_id": "price-001"}]}

    def test_preview_does_not_call_model_or_block_live(self):
        with patch("marketing.service.load_snapshot", return_value=self.snapshot), \
             patch("marketing.service.generate", return_value={"advice": {}}) as model:
            self.assertEqual(run_once(self.settings, dry_run=True, now=self.now)["status"], "preview")
            model.assert_not_called()
            self.assertEqual(run_once(self.settings, now=self.now)["status"], "succeeded")
            self.store.claim.return_value = False
            self.assertEqual(run_once(self.settings, now=self.now)["status"], "already_exists")
            model.assert_called_once()

    def test_no_data_never_calls_api(self):
        with patch("marketing.service.load_snapshot", return_value={"groups": []}), \
             patch("marketing.service.generate") as model:
            self.assertEqual(run_once(self.settings, now=self.now)["status"], "no_data")
            model.assert_not_called()

    def test_failed_run_is_recorded_and_requires_explicit_retry(self):
        with patch("marketing.service.load_snapshot", return_value=self.snapshot), \
             patch("marketing.service.generate", side_effect=RuntimeError("secret-token")) as model:
            with self.assertRaises(RuntimeError):
                run_once(self.settings, now=self.now)
            saved = self.store.save.call_args.args
            self.assertEqual(saved[1], "failed")
            self.assertNotIn("secret-token", str(saved))
            self.store.claim.return_value = False
            self.assertEqual(run_once(self.settings, now=self.now)["status"], "already_exists")
            self.store.claim.return_value = True
            model.side_effect = None
            model.return_value = {"advice": {}}
            self.assertEqual(run_once(self.settings, now=self.now, force=True)["status"], "succeeded")

    def test_postgres_claim_and_jsonb_save(self):
        conn = MagicMock()
        with patch("marketing.repository.connect") as connect:
            connect.return_value.__enter__.return_value = conn
            conn.execute.return_value.fetchone.side_effect = [(1,), None]
            store = ReportStore("Test Hotel")
            self.assertTrue(store.claim("same"))
            self.assertFalse(store.claim("same"))
            self.assertIn("ON CONFLICT", conn.execute.call_args.args[0])
            conn.execute.return_value.rowcount = 1
            store.save("same", "succeeded", {"中文": "报告"})
            params = conn.execute.call_args.args[1]
            self.assertEqual(params[1].obj, {"中文": "报告"})
            self.assertEqual(params[2:], ("Test Hotel", "same"))

    def test_latest_is_scoped_to_hotel(self):
        with patch("marketing.repository.connect") as connect:
            conn = connect.return_value.__enter__.return_value
            conn.execute.return_value.fetchone.return_value = ("run", "succeeded", {"summary": "报告"})
            self.assertEqual(ReportStore("Hotel B").latest()["payload"], {"summary": "报告"})
            self.assertEqual(conn.execute.call_args.args[1], ("Hotel B",))

    def test_query_is_read_only_scoped_and_uses_bound_parameters(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            (self.now.date(), 2, [5], 1, 3, 10000, 15000, 20000, self.now, self.now)
        ]
        with patch("marketing.repository.connect") as connect:
            connect.return_value.__enter__.return_value = conn
            result = load_snapshot(self.settings, self.now)
        self.assertEqual(conn.execute.call_args_list[0].args[0], "SET TRANSACTION READ ONLY")
        sql, params = conn.execute.call_args.args
        self.assertNotIn("Test Hotel", sql)
        self.assertEqual(params[0], "Test Hotel")
        self.assertIn("b.status='succeeded'", sql)
        self.assertEqual(result["groups"][0]["median_jpy"], 15000)
        self.assertEqual(result["groups"][0]["children_ages"], [5])

    def test_oversized_snapshot_fails_instead_of_truncating(self):
        with patch("marketing.repository.connect") as connect:
            connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [()] * 501
            with self.assertRaises(ValueError):
                load_snapshot(self.settings, self.now)

    def test_invalid_evidence_and_incomplete_response_are_rejected(self):
        advice = Advice(summary="test", recommendations=[Recommendation(
            title="test", evidence_ids=["made-up"], action="test", audience="test",
            channel="test", timing="test", constraints=[], validation="test", confidence="low"
        )], missing_data=[])
        response = SimpleNamespace(output_parsed=advice, status="completed", id="test", usage=None)
        with patch("openai.OpenAI") as client:
            client.return_value.__enter__.return_value.responses.parse.return_value = response
            with self.assertRaises(ValueError):
                generate(self.settings, self.snapshot)
            advice.recommendations[0].evidence_ids = ["price-001"]
            self.assertEqual(generate(self.settings, self.snapshot)["response_id"], "test")
            response.status = "incomplete"
            with self.assertRaises(ValueError):
                generate(self.settings, self.snapshot)


@unittest.skipUnless(os.environ.get("TEST_POSTGRES") == "1", "Set TEST_POSTGRES=1 for PostgreSQL integration")
class PostgresReportTests(unittest.TestCase):
    def test_persistence_deduplication_and_hotel_isolation(self):
        from competitor_db import connect
        with connect() as conn:
            ddl = Path(__file__).with_name("sql").joinpath("004_a_marketing_reports.sql").read_text(encoding="utf-8")
            # Session-local table shadows the real table; no production records are touched.
            conn.execute(ddl.replace("CREATE TABLE IF NOT EXISTS", "CREATE TEMP TABLE"))
            conn.commit()

            @contextmanager
            def connection():
                with conn.transaction():
                    yield conn

            with patch("marketing.repository.connect", side_effect=connection):
                first = ReportStore("Hotel A")
                second = ReportStore("Hotel A")
                other = ReportStore("Hotel B")
                self.assertTrue(first.claim("same"))
                self.assertFalse(second.claim("same"))
                self.assertTrue(other.claim("same"))
                first.save("same", "succeeded", {"summary": "中文报告"})
                self.assertEqual(second.latest()["payload"], {"summary": "中文报告"})
                self.assertEqual(other.latest()["status"], "running")
                self.assertIsNone(ReportStore("Hotel C").latest())
                with self.assertRaises(LookupError):
                    first.save("missing", "failed", {})


if __name__ == "__main__":
    unittest.main()
