import unittest
import numpy as np
from rasterio.transform import from_origin
from sarwatch.detections import categorical_overlay, change_sentence, change_summary, water_fraction, water_sentence


class DetectionLayers(unittest.TestCase):
    def test_overlay_renders_only_detected_classes(self):
        mask = np.full((20, 20), 255, dtype="uint8")
        mask[5:10, 5:10] = 1
        mask[12:14, 12:14] = 0
        overlay = categorical_overlay(mask, from_origin(446780, 8120440, 20, 20), "EPSG:32721", "water", "Agua")
        import folium
        m = folium.Map(location=[-17, -57], zoom_start=9)
        overlay.add_to(m)
        self.assertIn("imageOverlay", m.get_root().render())
        self.assertAlmostEqual(water_fraction(mask), 25 / 29)
        change = np.array([[1, 2, 0, 255]], dtype="uint8")
        summary = change_summary(change)
        self.assertEqual(summary["n"], 3)
        self.assertAlmostEqual(summary["increase"], 1 / 3)

    def test_sentences_are_honest_without_reference(self):
        self.assertIn("no se puede afirmar", water_sentence(None, "pantanal", "otsu"))
        self.assertIn("sin etiquetas independientes", change_sentence(None, "metropolitana"))
        reference = {"water": {"pantanal": {"thresholds": {"otsu": {"mean_f1": .71, "n_dates": 6}}, "lightgbm": {"spatial_f1": .8, "temporal_f1": .75, "temporal_test_date": "2026-09-27"}}}, "change": {"valparaiso": {"pair": {"before": "2026-10-05T10", "after": "2026-10-17T10"}, "alpha": .01, "land": {"increase": .001, "decrease": .0005}, "permanent_water": {"n": 10, "increase": .11}}}}
        self.assertIn("F1 0.80", water_sentence(reference, "pantanal", "lgbm"))
        self.assertIn("no confirma inundación", water_sentence(reference, "pantanal", "otsu"))
        text = change_sentence(reference, "valparaiso")
        self.assertIn("0.15 %", text)
        self.assertIn("mar", text)


if __name__ == "__main__":
    unittest.main()
