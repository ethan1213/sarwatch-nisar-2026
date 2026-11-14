import unittest
import numpy as np
from sarwatch.views.thermal import anticipation_sentence, cell_at, cell_frame, cell_polygon, period_summary, radar_layers, ramp_colour, response_sentence


def cube():
    times = np.array(["2026-09-03T17:00", "2026-09-03T18:00", "2026-09-04T17:00", "2026-09-05T05:00"], dtype="datetime64[m]")
    lat, lon = np.meshgrid([-17.0, -17.02], [-57.5, -57.48], indexing="ij")
    corner_lat, corner_lon = np.meshgrid([-16.99, -17.01, -17.03], [-57.51, -57.49, -57.47], indexing="ij")
    fire = np.zeros((4, 2, 2), dtype=np.int16)
    fire[0, 0, 0], fire[1, 0, 0], fire[2, 1, 1] = 10, 15, 14
    mask = np.full((4, 2, 2), 100, dtype=np.int16)
    mask[3] = 150  # cloud everywhere in the last step
    bt_mir = np.full((4, 2, 2), 300.0, dtype=np.float32); bt_mir[0, 0, 0] = 340.0
    return {"times": times, "lat": lat, "lon": lon, "corner_lat": corner_lat, "corner_lon": corner_lon, "fire": fire, "mask": mask, "bt_mir": bt_mir,
            "bt_tir": np.full((4, 2, 2), 295.0, dtype=np.float32), "lst": np.full((4, 2, 2), 305.15, dtype=np.float32), "frp": np.full((4, 2, 2), np.nan, dtype=np.float32)}


class Summary(unittest.TestCase):
    def test_period_counts_follow_the_selected_dates(self):
        data = cube()
        everything = period_summary(data, np.datetime64("2026-09-03T00:00"), np.datetime64("2026-09-06T00:00"))
        self.assertEqual((everything["detections"], everything["confident"], everything["cells_hot"], everything["days_hot"]), (3, 1, 2, 2))
        self.assertAlmostEqual(everything["cloud_fraction"], 0.25)
        self.assertAlmostEqual(float(everything["cells"]["mir"][0, 0]), 340 - 273.15, places=3)
        self.assertAlmostEqual(float(everything["cells"]["lst"][1, 0]), 32.0, places=3)
        self.assertAlmostEqual(float(everything["cells"]["dif"][0, 0]), 45.0, places=3)
        first_day = period_summary(data, np.datetime64("2026-09-03T00:00"), np.datetime64("2026-09-04T00:00"))
        self.assertEqual((first_day["detections"], first_day["cells_hot"], first_day["cloud_fraction"]), (2, 1, 0.0))
        empty = period_summary(data, np.datetime64("2026-10-01T00:00"), np.datetime64("2026-10-02T00:00"))
        self.assertEqual((empty["steps"], empty["detections"], empty["cloud_fraction"]), (0, 0, None))

    def test_cell_series_drop_cloud_and_switch_to_daily_for_long_periods(self):
        data = cube()
        hourly, daily = cell_frame(data, 0, np.datetime64("2026-09-03T00:00"), np.datetime64("2026-09-06T00:00"))
        self.assertFalse(daily)
        self.assertEqual(len(hourly), 4)
        self.assertTrue(np.isnan(hourly["mir"].iloc[3]) and np.isnan(hourly["tir"].iloc[3]))  # cloud: no brightness temperature shown
        self.assertEqual(hourly["foco"].tolist(), [1, 1, 0, 0])
        self.assertEqual(hourly["clase"].tolist()[:2], ["foco procesado", "probabilidad baja"])
        by_day, daily = cell_frame(data, 0, np.datetime64("2026-08-10T00:00"), np.datetime64("2026-09-06T00:00"))
        self.assertTrue(daily)
        self.assertEqual(len(by_day), 3)
        self.assertAlmostEqual(by_day["mir"].iloc[0], 340 - 273.15, places=3)
        self.assertEqual((by_day["foco"].iloc[0], by_day["clase"].iloc[0]), (2, "foco procesado"))
        self.assertTrue(np.isnan(by_day["lst"].iloc[2]))  # 05 UTC is not an afternoon hour

    def test_cells_are_found_by_position_and_drawn_as_closed_rings(self):
        data = cube()
        self.assertEqual(cell_at(data, -17.021, -57.481), 3)
        self.assertIsNone(cell_at(data, -18.0, -57.5))
        ring = cell_polygon(data, 3)
        self.assertEqual(len(ring), 5)
        self.assertEqual(ring[0], ring[-1])
        self.assertEqual(ring[0], [-57.49, -17.01])

    def test_ramp_is_clamped_and_blank_for_missing_values(self):
        ramp = ("#000000", "#808080", "#ffffff")
        self.assertEqual(ramp_colour(0, ramp), "#000000"); self.assertEqual(ramp_colour(0.5, ramp), "#808080"); self.assertEqual(ramp_colour(7, ramp), "#ffffff")
        self.assertIsNone(ramp_colour(float("nan"), ramp))

    def test_radar_layers_use_only_usable_passes_inside_the_period(self):
        zones = {"n_pixels": [10, 10], "radar": [{"date": "2026-07-05", "hv_db": [None, None], "fraccion_valida": [0.0, 0.0]}, {"date": "2026-09-03", "hv_db": [-15.0, -14.0], "fraccion_valida": [1.0, 1.0]}, {"date": "2026-09-15", "hv_db": [-17.5, -14.0], "fraccion_valida": [1.0, 0.9]}]}
        last, change, dates = radar_layers(zones, np.datetime64("2026-07-01T00:00"), np.datetime64("2026-09-16T00:00"))
        np.testing.assert_allclose(last, [-17.5, -14.0]); np.testing.assert_allclose(change, [-2.5, 0.0])
        self.assertEqual(dates, ("2026-09-03", "2026-09-15"))
        last, change, dates = radar_layers(zones, np.datetime64("2026-09-10T00:00"), np.datetime64("2026-09-16T00:00"))
        self.assertTrue(np.isnan(change).all()); self.assertEqual(dates, ("2026-09-15", "2026-09-15"))
        self.assertIsNone(radar_layers(zones, np.datetime64("2026-07-01T00:00"), np.datetime64("2026-07-10T00:00"))[2])


class Sentences(unittest.TestCase):
    HV = {"n_with_heat": 40, "n_without_heat": 900, "median_change_with_heat_db": -0.8, "median_change_without_heat_db": 0.1, "auc_decrease_separates_heat": 0.71, "auc_bootstrap_90": [0.64, 0.78]}

    def test_response_states_the_finding_without_claiming_burned_area(self):
        level, text = response_sentence({"response": {"hv": self.HV}})
        self.assertEqual(level, "estimado")
        self.assertIn("−0,80".replace("−", "-"), text); self.assertIn("0,71", text); self.assertIn("sin confirmar área quemada", text)
        level, text = response_sentence({"response": {"hv": {**self.HV, "auc_bootstrap_90": [0.44, 0.58]}}})
        self.assertIn("no distingue", text)
        self.assertEqual(response_sentence({"response": None})[0], "ausente")
        self.assertEqual(response_sentence(None)[0], "ausente")

    def test_anticipation_never_publishes_a_model_that_does_not_beat_persistence(self):
        def models(full_spatial, full_dates):
            split = lambda ap: {"average_precision": ap, "prevalence": 0.03, "roc_auc": 0.7}
            return {"anticipation": {"persistencia": {"spatial_blocks": split(0.20), "held_out_dates": split(0.20)}, "todo": {"spatial_blocks": split(full_spatial), "held_out_dates": split(full_dates)}, "radar_terreno": {"spatial_blocks": split(0.08), "held_out_dates": split(0.05)}}}
        level, text = anticipation_sentence(models(0.30, 0.15))
        self.assertIn("no se publica ninguna capa de predicción", text); self.assertIn("0,15", text); self.assertIn("azar: 0,03", text)
        self.assertIn("supera a la persistencia en ambas pruebas", anticipation_sentence(models(0.30, 0.25))[1])
        self.assertEqual(anticipation_sentence({"anticipation": {"note": "sin focos"}})[0], "ausente")
        partial = models(0.3, 0.3); partial["anticipation"]["todo"]["held_out_dates"] = {"note": "sin positivos"}
        self.assertIn("no se publica", anticipation_sentence(partial)[1])


if __name__ == "__main__":
    unittest.main()
