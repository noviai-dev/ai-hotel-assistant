"""Offline checks for the historical quote lookback configuration."""
import unittest
from unittest.mock import patch

from marketing.config import Settings


class HistorySettingsTest(unittest.TestCase):
    def load_settings(self, **environment):
        with patch("marketing.config.load_dotenv"), patch.dict(
            "os.environ", {"MARKETING_HOTEL": "Test hotel", **environment}, clear=True
        ):
            return Settings.load()

    def test_default_lookback(self):
        self.assertEqual(Settings(hotel="Test hotel", model="test").history_days, 30)
        self.assertEqual(self.load_settings().history_days, 30)

    def test_environment_override(self):
        self.assertEqual(self.load_settings(MARKETING_HISTORY_DAYS="60").history_days, 60)

    def test_valid_boundaries(self):
        for days in (1, 366):
            with self.subTest(days=days):
                self.assertEqual(
                    self.load_settings(MARKETING_HISTORY_DAYS=str(days)).history_days, days
                )

    def test_invalid_boundaries(self):
        for days in (0, 367):
            with self.subTest(days=days), self.assertRaisesRegex(
                ValueError, "MARKETING_HISTORY_DAYS"
            ):
                self.load_settings(MARKETING_HISTORY_DAYS=str(days))


if __name__ == "__main__":
    unittest.main()
