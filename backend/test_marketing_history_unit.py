"""Offline checks for history snapshot serialization and group limits."""
import json
from copy import deepcopy
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from marketing.config import Settings
from marketing.advisor import Advice, Recommendation, _compact_table, _prepare_model_snapshot, generate
from marketing.repository import MAX_HISTORY_GROUPS, _load_self_price_comparisons, load_snapshot


class PriceHistoryTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(hotel="Test hotel", model="test", history_days=30)
        self.now = datetime(2026, 11, 5, 12, tzinfo=timezone(timedelta(hours=9)))
        self.observations = [{
            "collected_at": "2026-11-01T10:00:00+09:00",
            "nightly_jpy": 12000,
        }, {
            "collected_at": "2026-11-05T10:00:00+09:00",
            "nightly_jpy": 12600,
        }]
        self.history = ("hotel-1", date(2026, 12, 5), date(2026, 12, 7),
                        2, [5], 1, self.observations)

    def snapshot(self, history_rows):
        conn = MagicMock()
        # Transaction setup, current market, historical series, own comparisons.
        conn.execute.side_effect = [
            MagicMock(), MagicMock(),
            MagicMock(fetchall=lambda: []),
            MagicMock(fetchall=lambda: history_rows),
            MagicMock(fetchall=lambda: []),
        ]
        with patch("marketing.repository.connect") as connect:
            connect.return_value.__enter__.return_value = conn
            snapshot = load_snapshot(self.settings, self.now)
        return snapshot, conn

    def test_history_preserves_dates_observations_and_json(self):
        snapshot, conn = self.snapshot([self.history])
        history = snapshot["price_history"][0]
        self.assertEqual(history["check_in"], "2026-12-05")
        self.assertEqual(history["check_out"], "2026-12-07")
        self.assertEqual(len(history["observations"]), 2)
        self.assertNotIn("observation_count", history)
        self.assertNotIn("price_changes", snapshot)
        self.assertEqual(history["observations"], self.observations)
        self.assertEqual(history["evidence_id"], "history-001")
        json.dumps(snapshot)
        recent_params = conn.execute.call_args_list[2].args[1]
        history_params = conn.execute.call_args_list[3].args[1]
        self.assertEqual(recent_params[3], self.now - timedelta(days=7))
        self.assertEqual(history_params[3], self.now - timedelta(days=30))
        self.assertEqual(history_params[4], self.now)
        self.assertEqual(history_params[5], MAX_HISTORY_GROUPS + 1)

    def test_accepts_more_than_500_history_groups(self):
        snapshot, _ = self.snapshot([self.history] * 501)
        self.assertEqual(len(snapshot["price_history"]), 501)

    def test_accepts_history_limit_and_rejects_overflow(self):
        snapshot, _ = self.snapshot([self.history] * MAX_HISTORY_GROUPS)
        self.assertEqual(len(snapshot["price_history"]), MAX_HISTORY_GROUPS)
        with self.assertRaisesRegex(ValueError, "历史价格分组超过5000"):
            self.snapshot([self.history] * (MAX_HISTORY_GROUPS + 1))

    def test_history_window_environment_and_validation(self):
        with patch("marketing.config.load_dotenv"), patch.dict(
            "os.environ", {"MARKETING_HOTEL": "Test hotel",
                           "MARKETING_HISTORY_DAYS": "60"}, clear=True
        ):
            self.assertEqual(Settings.load().history_days, 60)
        for value in ("0", "367"):
            with self.subTest(value=value), patch("marketing.config.load_dotenv"), patch.dict(
                "os.environ", {"MARKETING_HOTEL": "Test hotel",
                               "MARKETING_HISTORY_DAYS": value}, clear=True
            ):
                with self.assertRaisesRegex(ValueError, "MARKETING_HISTORY_DAYS"):
                    Settings.load()


class SelfPriceComparisonTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
        self.start = self.now.date()
        self.end = self.start + timedelta(days=60)
        self.cutoff = self.now - timedelta(days=7)

    def load(self, rows):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows
        result = _load_self_price_comparisons(
            conn, "Test hotel", self.start, self.end, self.cutoff, self.now)
        return result, conn

    def test_empty_own_quotes(self):
        result, _ = self.load([])
        self.assertEqual(result, [])

    def test_retains_own_quote_without_competitors_and_scopes_both_sources(self):
        record = {
            "own_quote": {"nightly_jpy": 17000, "check_in": "2026-12-05",
                          "check_out": "2026-12-07", "room_type": "Family"},
            "competitor_count": 0, "competitors": [],
            "market_median_jpy": None, "difference_from_median_percent": None,
        }
        result, conn = self.load([(record,)])
        self.assertEqual(result[0]["own_quote"], record["own_quote"])
        self.assertEqual(result[0]["competitor_count"], 0)
        self.assertIsNone(result[0]["difference_from_median_percent"])
        self.assertEqual(result[0]["evidence_id"], "comparison-001")
        json.dumps(result)
        self.assertEqual(conn.execute.call_args.args[1], (
            "Test hotel", self.start, self.end, self.cutoff, self.now,
            "Test hotel", "Test hotel", self.start, self.end, self.cutoff,
            self.now, MAX_HISTORY_GROUPS + 1,
        ))

    def test_rejects_comparison_overflow(self):
        with self.assertRaisesRegex(ValueError, "本店价格比对分组超过5000"):
            self.load([({},)] * (MAX_HISTORY_GROUPS + 1))

    def test_advisor_accepts_comparison_evidence(self):
        recommendation = Recommendation(
            title="核对本店相对价位", evidence_ids=["comparison-001"],
            action="核对房型和税费", audience="家庭", channel="官网",
            timing="入住前", constraints=["待审核"],
            validation="检查可比报价", confidence="low",
        )
        response = SimpleNamespace(
            status="completed", output_parsed=Advice(
                email_body="本店相对价位待验证，建议先核对房型和税费。",
                summary="本店相对价位待验证", recommendations=[recommendation],
                missing_data=[]),
            model_dump=lambda **kwargs: {}, usage=None, id="test-response",
        )
        client = MagicMock()
        client.responses.parse.return_value = response
        openai = MagicMock()
        openai.OpenAI.return_value.__enter__.return_value = client
        snapshot = {"as_of": self.now.isoformat(), "groups": [],
                    "self_price_comparisons": [{"evidence_id": "comparison-001"}]}
        with patch.dict("sys.modules", {"openai": openai}):
            result = generate(Settings(hotel="Test hotel", model="test"), snapshot)
        self.assertEqual(result["advice"]["recommendations"][0]["evidence_ids"],
                         ["comparison-001"])
        self.assertEqual(client.responses.parse.call_args.kwargs["max_output_tokens"], 8000)
        openai.OpenAI.assert_called_once_with(timeout=180, max_retries=4)


class ModelSnapshotTest(unittest.TestCase):
    def test_compact_table_preserves_values_and_additional_fields(self):
        records = [{"collected_at": "2026-11-01T10:00:00+09:00",
                    "nightly_jpy": 12000, "change_jpy": None},
                   {"collected_at": "2026-11-05T10:00:00+09:00",
                    "nightly_jpy": 12600, "change_jpy": 600,
                    "elapsed_hours": 96}]
        table = _compact_table(records)
        restored = [dict(zip(table["columns"], row)) for row in table["rows"]]
        for before, after in zip(records, restored):
            self.assertTrue(before.items() <= after.items())
        self.assertEqual(len(restored), 2)
        self.assertEqual(_compact_table([]), {"columns": [], "rows": []})

    def test_filters_all_collections_inclusive_without_mutating_snapshot(self):
        dates = ["2026-12-04", "2026-12-05", "2026-12-15", "2026-12-16"]
        snapshot = {
            "groups": [{"evidence_id": f"price-{i}", "stay_date": day}
                       for i, day in enumerate(dates)],
            "price_history": [{"evidence_id": f"history-{i}", "check_in": day,
                               "observations": [{"nightly_jpy": 12000}]*11}
                              for i, day in enumerate(dates)],
            "self_price_comparisons": [{"evidence_id": f"comparison-{i}",
                                        "own_quote": {"check_in": day},
                                        "competitors": [{"hotel_key": "hotel-1"}]}
                                       for i, day in enumerate(dates)],
        }
        original = deepcopy(snapshot)
        prepared = _prepare_model_snapshot(snapshot, "2026-12-05", "2026-12-15")
        for name in snapshot:
            self.assertEqual(len(prepared[name]), 2)
            self.assertEqual(prepared["excluded_outside_window_groups"][name], 2)
        self.assertEqual(len(prepared["price_history"][0]["observations"]["rows"]), 11)
        self.assertEqual(snapshot, original)

    def test_compaction_reduces_repeated_history_keys(self):
        observation = {
            "collected_at": "2026-11-01T10:00:00+09:00",
            "nightly_jpy": 12000,
        }
        snapshot = {"price_history": [
            {"evidence_id": f"history-{i}", "check_in": "2026-12-05",
             "observations": [dict(observation) for _ in range(30)]}
            for i in range(30)
        ]}
        prepared = _prepare_model_snapshot(snapshot, "2026-12-05", "2026-12-15")
        original_size = len(json.dumps(snapshot))
        compact_size = len(json.dumps(prepared, separators=(",", ":")))
        self.assertLess(compact_size, original_size * 0.6)
        self.assertEqual(sum(len(row["observations"]["rows"])
                             for row in prepared["price_history"]), 900)


if __name__ == "__main__":
    unittest.main()
