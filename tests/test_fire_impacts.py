import math
import unittest
import numpy as np

from sarwatch.ml.emissions import co2_emitted
from sarwatch.ml.debris_volume import relative_depth_index, gartner_emergency_volume


class FireImpactsTests(unittest.TestCase):
    def test_one_hectare_shrubland_mass_units(self):
        result = co2_emitted([[4]], [[20]], 10000)
        self.assertAlmostEqual(result['total_co2_t'], 14.3 * 1.613)
        self.assertLessEqual(result['sensitivity_low_t'], result['total_co2_t'])
        self.assertGreaterEqual(result['sensitivity_high_t'], result['total_co2_t'])

    def test_no_data_and_unsupported_cover_are_not_zero_emissions(self):
        result = co2_emitted([[255, 4, 4]], [[20, 40, 20]], 10000)
        self.assertEqual(result['burned_signal_area_ha'], 2)
        self.assertEqual(result['unmodeled_burned_area_ha'], 1)
        self.assertEqual(result['modeled_burned_fraction'], .5)

    def test_invalid_inputs(self):
        for area in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                co2_emitted([[4]], [[20]], area)
        with self.assertRaises(ValueError):
            co2_emitted([4], [[20]], 1)
        with self.assertRaises(ValueError):
            co2_emitted([4], [20], 1, {1: .1, 2: .2, 3: .3, 4: 2})

    def test_relative_index_missing_and_monotonic(self):
        index = relative_depth_index([1, 10, 100, 100], [30, 30, 30, float('nan')], [1, 1, 1, 1])
        self.assertTrue(0 <= index[0] < index[1] < index[2] <= 1)
        self.assertTrue(np.isnan(index[3]))
        self.assertEqual(relative_depth_index([100], [30], [0])[0], 0)

    def test_gartner_reference_equation_and_rainfall_gate(self):
        self.assertIsNone(gartner_emergency_volume(None, 1, 500)['volume_m3'])
        result = gartner_emergency_volume(20, 1, 500, years_since_fire=1)
        expected = math.exp(4.22 + .39 * math.sqrt(20) + .13 * math.sqrt(500))
        self.assertAlmostEqual(result['volume_m3'], expected)
        self.assertFalse(result['outside_calibration'])
        with self.assertRaises(ValueError):
            gartner_emergency_volume(20, 1, 500, rainfall_interval_minutes=60)
        self.assertTrue(gartner_emergency_volume(100, 1, 500, years_since_fire=3)['outside_calibration'])

    def test_zero_burned_area_not_valid_for_log_model(self):
        with self.assertRaises(ValueError):
            gartner_emergency_volume(20, 0, 500)

    def test_large_emission_figures_are_verified_whole(self):
        from sarwatch.assistant.verify import verify
        self.assertTrue(verify('Escenario 174165.5 t.', {'co2': 174165.5}, [])[0])
        self.assertFalse(verify('Escenario 174165.5 t.', {'co2': 5}, [])[0])


if __name__ == '__main__':
    unittest.main()
