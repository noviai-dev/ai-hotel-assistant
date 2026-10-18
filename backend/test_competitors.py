import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import date

import httpx
import competitors as c


class CompetitorTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path(c.__file__).with_name("competitors.example.json").read_text(encoding="utf-8"))
        with patch.object(c, "tokyo_today", return_value=date(2026, 10, 11)):
            self.plan = c.build_plan(self.config)

    def item(self):
        return {"name": "Family Hotel", "type": "Hotel", "url": "https://www.booking.com/hotel/jp/family.html",
                "price": {"amount": 20000, "currency": "JPY"},
                "address": {"full": "Chuo-ku, Osaka"}, "rooms": []}

    def test_matrix_and_calendar(self):
        self.assertEqual(len(self.plan), self.config['calendar_days'] * 8)
        self.assertEqual(self.plan[0]['checkIn'], '2026-11-20')
        self.assertEqual((date.fromisoformat(self.plan[-1]['checkIn']) - date(2026, 11, 20)).days,
                         self.config['calendar_days'] - 1)
        for q in self.plan:
            self.assertEqual((date.fromisoformat(q['checkOut'])-date.fromisoformat(q['checkIn'])).days, 1)
            self.assertNotIn('priceMax', q)
        for q in self.plan:
            self.assertIn(q["adults"] + q["children"], range(3, 7))
            self.assertEqual(len(q["childrenAges"]), q["children"])

    def test_default_check_in_and_explicit_override(self):
        for today, expected in [(date(2026, 10, 18), '2026-11-27'),
                                (date(2026, 12, 31), '2027-02-09'),
                                (date(2028, 1, 31), '2028-03-11')]:
            for missing in (False, True):
                config = dict(self.config, check_in=None)
                if missing:
                    del config['check_in']
                with self.subTest(today=today, missing=missing), patch.object(c, 'tokyo_today', return_value=today):
                    self.assertEqual(c.build_plan(config)[0]['checkIn'], expected)
        with patch.object(c, 'tokyo_today', return_value=date(2026, 10, 18)):
            self.config['check_in'] = '2026-11-11'
            self.assertEqual(c.build_plan(self.config)[0]['checkIn'], '2026-11-11')
            self.config['check_in'] = '2026-10-17'
            with self.assertRaises(ValueError):
                c.build_plan(self.config)

    def test_price_location_and_missing_evidence(self):
        row = c.normalize(self.item(), self.plan[0], self.config)
        self.assertEqual(row["nightly_jpy"], 20000)
        self.assertEqual(row["status"], "match")
        self.assertEqual(row["guest_origin_evidence"], "unknown")
        self.assertEqual(row["capacity_evidence"], "search_party_only_unverified")
        item = self.item()
        item["price"]["currency"] = "USD"
        self.assertIsNone(c.normalize(item, self.plan[0], self.config)["nightly_jpy"])
        item["address"] = {}
        item["name"] = "Near Dotonbori Hotel"
        self.assertEqual(c.normalize(item, self.plan[0], self.config)["location_status"], "unknown")

    def test_radius_or_hotspot_and_own_property(self):
        self.config["center"] = [34.67, 135.5]
        item = self.item()
        item["address"] = {}
        item["location"] = {"lat": 34.67, "lng": 135.5}
        self.assertEqual(c.normalize(item, self.plan[0], self.config)["status"], "match")
        item["location"] = {"lat": 35, "lng": 136}
        self.assertEqual(c.normalize(item, self.plan[0], self.config)["location_status"], "outside")
        item["address"] = {"full": "Tennoji, Osaka"}
        self.assertEqual(c.normalize(item, self.plan[0], self.config)["location_status"], "match")
        item["name"] = "NOVI Dotonbori"
        self.assertIn("own_hotel", c.normalize(item, self.plan[0], self.config)["reasons"])

    def test_paid_run_poll_dataset_and_failure(self):
        calls = []
        def handler(req):
            calls.append(req)
            self.assertEqual(req.headers["Authorization"], "Bearer fake")
            if req.method == "POST":
                self.assertEqual(req.url.params["maxTotalChargeUsd"], "0.5")
                return httpx.Response(201, json={"data": {"id": "r1", "status": "RUNNING"}})
            if "actor-runs" in req.url.path:
                return httpx.Response(200, json={"data": {"id": "r1", "status": "SUCCEEDED", "defaultDatasetId": "d1"}})
            return httpx.Response(200, json=[self.item()])
        with tempfile.TemporaryDirectory() as folder, patch.object(c.time, "sleep"):
            with httpx.Client(base_url="https://api.apify.com", headers={"Authorization": "Bearer fake"}, transport=httpx.MockTransport(handler)) as client:
                items = c.collect(client, self.plan[0], self.config, Path(folder))
            self.assertEqual(len(items), 1)
            self.assertTrue((Path(folder) / "raw.json").exists())
        self.assertEqual(sum(r.method == "POST" for r in calls), 1)
        with httpx.Client(base_url="https://api.apify.com", transport=httpx.MockTransport(lambda req: httpx.Response(401))) as client:
            with self.assertRaises(RuntimeError):
                c.request(client, "POST", "/v2/acts/test/runs")


if __name__ == "__main__":
    unittest.main()
