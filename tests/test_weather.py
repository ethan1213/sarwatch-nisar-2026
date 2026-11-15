import io
import json
import unittest
from unittest.mock import patch
from weather import FIRE_HOURLY, fetch_fire_weather, fetch_weather


class WeatherContract(unittest.TestCase):
    def test_incomplete_response_fails_without_fake_values(self):
        with patch("weather.urlopen", return_value=io.BytesIO(b'{"daily":{}}')):
            with self.assertRaises(ValueError):
                fetch_weather(-17.2, -57.2)

    def test_forecast_is_separate_from_historical(self):
        payload = {"daily": {"time":["2026-07-05"], "precipitation_sum":[None], "temperature_2m_max":[28], "temperature_2m_min":[19]}}
        with patch("weather.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            result = fetch_weather(-17.2, -57.2, "2026-07-05", "2026-07-05")
            self.assertIn("archive-api.open-meteo.com", request.call_args.args[0])
            self.assertEqual(result["kind"], "ERA5 reanalysis")
            self.assertIsNone(result["payload"]["daily"]["precipitation_sum"][0])

    def test_fire_weather_keeps_nulls_and_one_series_per_point(self):
        cell = {"latitude": -36.75, "longitude": -73.0, "hourly_units": {"wind_speed_10m": "km/h"}, "hourly": {"time": ["2026-03-01T00:00"], **{name: [None] for name in FIRE_HOURLY}}}
        with patch("weather.urlopen", return_value=io.BytesIO(json.dumps([cell, cell]).encode())) as request:
            result = fetch_fire_weather([(-36.7, -72.9), (-36.9, -72.9)], "2026-03-01", "2026-03-01")
            self.assertIn("models=era5", request.call_args.args[0])
            self.assertIsNone(result["cells"][0]["hourly"]["wind_speed_10m"][0])
        with patch("weather.urlopen", return_value=io.BytesIO(json.dumps([cell]).encode())):
            with self.assertRaises(ValueError):
                fetch_fire_weather([(-36.7, -72.9), (-36.9, -72.9)], "2026-03-01", "2026-03-01")
