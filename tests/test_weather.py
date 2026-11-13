import io
import json
import unittest
from unittest.mock import patch
from weather import fetch_weather


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
