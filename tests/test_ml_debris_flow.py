import unittest
import numpy as np
from sarwatch.ml.debris_flow import (
    BASE_THRESHOLD_MM_30MIN, MIN_THRESHOLD_MM_30MIN, concentration_factor, dynamic_threshold,
    explain, moisture_factor, saturation_factor, semaphore, severity_factor,
)


class Factors(unittest.TestCase):
    def test_each_factor_is_bounded_and_monotonic(self):
        self.assertEqual(severity_factor(0.0), 1.0)
        self.assertAlmostEqual(severity_factor(1.0), 0.5)
        self.assertTrue(severity_factor(0.2) > severity_factor(0.8))
        self.assertEqual(saturation_factor(0), 1.0)
        self.assertTrue(saturation_factor(30) > saturation_factor(90))
        self.assertAlmostEqual(saturation_factor(600), 1 - 0.65, places=5)
        self.assertEqual(concentration_factor(10, 10), 1.0)
        self.assertTrue(concentration_factor(10000, 10) < concentration_factor(10, 10))
        self.assertEqual(moisture_factor(0), 1.0)
        self.assertTrue(moisture_factor(3) < moisture_factor(1))
        self.assertAlmostEqual(moisture_factor(-5), 1.0)  # drying never increases the threshold here


class DynamicThreshold(unittest.TestCase):
    def test_saturated_wetter_case_needs_less_rain_than_dry_case(self):
        dry, factors_dry = dynamic_threshold(0.3, 2, 500, 200)
        wet, factors_wet = dynamic_threshold(0.3, 110, 500, 200, delta_hh_db=2.0)
        self.assertLess(float(wet), float(dry))
        self.assertLessEqual(float(wet), BASE_THRESHOLD_MM_30MIN)
        self.assertIn("moisture", factors_wet)
        self.assertNotIn("moisture", factors_dry)

    def test_threshold_never_drops_below_the_floor(self):
        threshold, _ = dynamic_threshold(1.0, 1000, 1e9, 1, delta_hh_db=10)
        self.assertEqual(float(threshold), MIN_THRESHOLD_MM_30MIN)

    def test_semaphore_breaks_and_nodata(self):
        colors = semaphore(np.array([3.0, 10.0, 18.0, np.nan]))
        self.assertEqual(colors.tolist(), [0, 1, 2, 255])

    def test_explain_cites_the_dominant_factor(self):
        threshold, factors = dynamic_threshold(0.3, 110, 500, 200, delta_hh_db=2.0)
        text = explain(factors, threshold)
        self.assertIn("lluvia previa", text)
        self.assertIn("umbral efectivo", text)


if __name__ == "__main__":
    unittest.main()
