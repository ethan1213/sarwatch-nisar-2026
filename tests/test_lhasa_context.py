"""Check that the archived LHASA crop resolves to the original Biobío cells."""
import unittest

from api.fire import get_landslide_context


class LandslideContextTests(unittest.TestCase):
    def test_penco_returns_dated_regional_model_values(self):
        context = get_landslide_context(-36.73, -72.96)
        self.assertFalse(context["operational_alert"])
        self.assertEqual(context["source_resolution_arcsec"], 30)
        self.assertEqual([item["date_utc"] for item in context["observations"]],
                         ["2026-01-31T00:00:00Z", "2026-11-16T00:00:00Z"])
        self.assertAlmostEqual(context["observations"][0]["probability"], 0.0022224097047001123)
        self.assertAlmostEqual(context["observations"][1]["probability"], 0.0008421851671300828)

    def test_missing_cell_is_not_classified_as_zero(self):
        context = get_landslide_context(-37.5, -72.5)
        self.assertTrue(all(item["probability"] is None for item in context["observations"]))


if __name__ == "__main__":
    unittest.main()
