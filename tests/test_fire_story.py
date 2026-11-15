import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from weather import FIRE_HOURLY, fetch_fire_forecast

PACK = Path("catalog/fire_story")


class FireStoryPack(unittest.TestCase):
    def setUp(self):
        self.story = json.loads((PACK / "story.json").read_text(encoding="utf-8"))

    def test_overlays_listed_by_the_pack_exist(self):
        after = self.story["after"]
        for layer in after["radar"] + [after["severity"]]:
            self.assertTrue((PACK / layer["png"]).is_file(), layer["png"])
            bounds = layer["bounds"]
            self.assertLess(bounds["west"], bounds["east"])
            self.assertLess(bounds["south"], bounds["north"])

    def test_replay_frames_point_to_existing_cells_and_weather_hours(self):
        during = self.story["during"]
        n = len(during["cells"]["features"])
        hours = set(during["weather"]["times"])
        for frame in during["frames"]:
            self.assertTrue(all(0 <= c < n for c in frame["cells"]))
            self.assertEqual(len(frame["cells"]), len(frame["frp_mw"]))
            self.assertIn(frame["t"], hours)
        self.assertEqual(sum(len(f["cells"]) for f in during["frames"]), during["confident_detections"])
        for point in during["weather"]["points"]:
            self.assertEqual(len(point["wind_kmh"]), len(during["weather"]["times"]))

    def test_ranking_is_labelled_exploratory_and_quotes_the_benchmark(self):
        before = self.story["before"]
        benchmark = json.loads(Path("docs/fire_benchmark_biobio.json").read_text(encoding="utf-8"))["aois"][before["aoi"]]["anticipation"]
        self.assertEqual(before["held_out_dates"], benchmark["split"]["temporal"]["test_dates"])
        self.assertAlmostEqual(before["benchmark"][before["model"]]["held_out_dates"]["roc_auc"], benchmark["models"][before["model"]]["held_out_dates"]["roc_auc"], places=3)
        self.assertTrue(any("exploratorio" in limit for limit in before["limits"]))
        for date in before["held_out_dates"]:
            key = date.replace("-", "")
            hits = sum(f["properties"].get(f"h{key}", 0) for f in before["cells"]["features"])
            self.assertEqual(hits, before["passes"][date]["hot_next"])


class FireForecastContract(unittest.TestCase):
    def test_incomplete_forecast_fails_without_fake_values(self):
        with patch("weather.urlopen", return_value=io.BytesIO(b'{"hourly":{"time":[]}}')):
            with self.assertRaises(ValueError):
                fetch_fire_forecast(-36.7, -72.9)

    def test_forecast_is_labelled_and_keeps_nulls(self):
        hourly = {"time": ["2026-11-15T04:00"], **{name: [None] for name in FIRE_HOURLY}, "precipitation_probability": [0]}
        with patch("weather.urlopen", return_value=io.BytesIO(json.dumps({"latitude": -36.73, "longitude": -72.99, "hourly": hourly}).encode())) as request:
            result = fetch_fire_forecast(-36.7, -72.9)
        self.assertIn("api.open-meteo.com/v1/forecast", request.call_args.args[0])
        self.assertEqual(result["kind"], "weather forecast")
        self.assertIsNone(result["hourly"]["wind_speed_10m"][0])
