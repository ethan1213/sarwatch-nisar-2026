import hashlib
import json
import unittest
from pathlib import Path
from sarwatch.ml.sector_context import GEOD, wind_reference_sectors, spatial_context, context_for_cell

class WindReferenceSemantics(unittest.TestCase):
    def test_meteorological_north_wind_blows_south_and_laterals_are_relative_to_motion(self):
        sectors={s["key"]:s for s in wind_reference_sectors(-73,-37,0)}
        self.assertLess(sectors["downwind"]["lat"],-37)
        self.assertGreater(sectors["left"]["lon"],-73)
        self.assertLess(sectors["right"]["lon"],-73)
        for s in sectors.values():self.assertAlmostEqual(GEOD.inv(-73,-37,s["lon"],s["lat"])[2],2000,places=3)

    def test_calm_wind_has_no_qualitative_direction_or_safe_route(self):
        r=spatial_context({"before":{"cells":{"features":[]}}},-73,-37,0,0)
        self.assertEqual(r["sectors"],[])
        self.assertIsNone(r["safe_approach"])
        self.assertFalse(r["fire_flank_prediction"])

    def test_unknown_time_or_cell_cannot_use_nearest_future_observation(self):
        story=json.loads(Path("catalog/fire_story/story.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):context_for_cell(story,999999,"2026-01-18T06:00Z")
        with self.assertRaises(ValueError):context_for_cell(story,0,"2030-01-01T00:00Z")

class VinaHistoricalEvidence(unittest.TestCase):
    def test_real_optical_dates_bracket_the_fire_and_assets_match(self):
        root=Path("catalog/vina_2024")
        d=json.loads((root/"story.json").read_text(encoding="utf-8"))
        self.assertLess(d["observations"][0]["date"][:10],d["fire_dates"][0])
        self.assertGreater(d["observations"][1]["date"][:10],d["fire_dates"][-1])
        self.assertIn("Sentinel-2",d["source"])
        self.assertGreater(d["valid_comparison_fraction"],0.8)
        for name,digest in d["assets_sha256"].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)


class OfficialPerimeterEvidence(unittest.TestCase):
    def test_acquisitions_are_dated_and_display_geometries_keep_traceability(self):
        root=Path("catalog/official_fire_perimeters")
        report=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
        dates=[p["date_utc"] for p in report["products"]]
        self.assertEqual(len(dates),5)
        self.assertEqual(dates,sorted(dates))
        self.assertGreaterEqual(dates[0],"2026-01-21")
        for p in report["products"]:
            self.assertEqual(len(p["sha256"]),64)
            self.assertEqual(hashlib.sha256((root/p["asset"]).read_bytes()).hexdigest(),p["display_sha256"])
