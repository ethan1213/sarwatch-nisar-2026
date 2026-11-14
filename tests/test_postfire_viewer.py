import unittest
import numpy as np
from rasterio.transform import from_origin
from sarwatch.postfire import scenario_sentence, semaphore_overlay


class PostfireViewer(unittest.TestCase):
    def test_overlay_renders_three_colors(self):
        mask = np.array([[0, 1], [2, 255]], dtype="uint8")
        overlay = semaphore_overlay(mask, from_origin(323000, 6320120, 20, 20), "EPSG:32719", "PostFuego")
        import folium
        m = folium.Map(location=[-33.4, -70.6], zoom_start=10)
        overlay.add_to(m)
        self.assertIn("imageOverlay", m.get_root().render())

    def test_sentence_is_honest_without_reference(self):
        self.assertIn("Sin referencia", scenario_sentence(None, "octubre"))
        reference = {"scenarios": {"octubre": {"label": "8-octubre (saturado)", "median_threshold_mm_30min": 4.8, "min_threshold_mm_30min": 3.0, "observed_30min_mm": 8.8, "would_have_triggered": True, "fraction_rojo": 0.6, "fraction_amarillo": 0.3, "fraction_verde": 0.1}}}
        text = scenario_sentence(reference, "octubre")
        self.assertIn("4.8 mm", text)
        self.assertIn("superó el umbral", text)
        self.assertIn("no calibrada", text)


if __name__ == "__main__":
    unittest.main()
