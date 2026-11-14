import io
import unittest
from unittest.mock import patch
from sarwatch.fire_hotspots import fetch_active_fire, summarize

CSV_OK = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n-33.40,-70.52,345.2,0.4,0.4,2026-01-28,1805,N,h,2.0NRT,290.1,12.4,D\n-33.41,-70.53,330.0,0.4,0.4,2026-01-28,1805,N,n,2.0NRT,280.0,3.1,D\n"


class FireHotspots(unittest.TestCase):
    def test_missing_key_is_a_clear_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                fetch_active_fire(-70.9, -33.7, -70.4, -33.25, map_key=None)

    def test_invalid_bbox_and_days_rejected(self):
        with self.assertRaises(ValueError):
            fetch_active_fire(-70.4, -33.7, -70.9, -33.25, map_key="x")
        with self.assertRaises(ValueError):
            fetch_active_fire(-70.9, -33.7, -70.4, -33.25, days=11, map_key="x")

    def test_parses_valid_csv_and_summarizes(self):
        with patch("sarwatch.fire_hotspots.urlopen") as mocked:
            mocked.return_value.__enter__.return_value.read.return_value = CSV_OK.encode()
            result = fetch_active_fire(-70.9, -33.7, -70.4, -33.25, map_key="demo")
        self.assertEqual(result["n_detections"], 2)
        summary = summarize(result)
        self.assertEqual(summary["n"], 2)
        self.assertAlmostEqual(summary["max_frp_mw"], 12.4)
        self.assertEqual(summary["high_confidence"], 1)

    def test_invalid_key_response_raises(self):
        with patch("sarwatch.fire_hotspots.urlopen") as mocked:
            mocked.return_value.__enter__.return_value.read.return_value = b"Invalid MAP_KEY"
            with self.assertRaises(ValueError):
                fetch_active_fire(-70.9, -33.7, -70.4, -33.25, map_key="bad")

    def test_empty_result_summarizes_to_zero(self):
        self.assertEqual(summarize({"detections": []}), {"n": 0, "max_frp_mw": None, "max_brightness_k": None})


if __name__ == "__main__":
    unittest.main()
