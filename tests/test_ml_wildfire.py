import unittest
import numpy as np
from sarwatch.ml.wildfire import boa_reflectance, nbr, dnbr, severity_class, burned_fraction, severity_summary, NODATA


class BurnSeverity(unittest.TestCase):
    def test_nbr_and_dnbr_known_values(self):
        pre = nbr(np.array([0.5, 0.5]), np.array([0.1, 0.1]))
        post = nbr(np.array([0.2, 0.5]), np.array([0.3, 0.1]))
        np.testing.assert_allclose(pre, [2 / 3, 2 / 3], rtol=1e-5)
        delta = dnbr(pre, post)
        self.assertAlmostEqual(float(delta[0]), 2 / 3 - (-0.2))
        self.assertAlmostEqual(float(delta[1]), 0, places=6)

    def test_reflectance_offset_since_baseline_04_changes_nbr(self):
        # Healthy vegetation: reflectance 0.30 NIR, 0.10 SWIR2 -> NBR 0.5. Raw DNs (4000, 2000) give only 1/3.
        nir, swir2 = np.array([4000, 0]), np.array([2000, 0])
        corrected = nbr(boa_reflectance(nir, "05.12"), boa_reflectance(swir2, "05.12"))
        self.assertAlmostEqual(float(corrected[0]), 0.5, places=5)
        self.assertTrue(np.isnan(corrected[1]))
        self.assertAlmostEqual(float(nbr(nir, swir2)[0]), 1 / 3, places=5)
        self.assertAlmostEqual(float(boa_reflectance(np.array([3000]), "03.01")[0]), 0.3, places=6)

    def test_nan_where_undefined_and_shape_mismatch_rejected(self):
        self.assertTrue(np.isnan(nbr(np.array([0.0]), np.array([0.0]))[0]))
        with self.assertRaises(ValueError):
            nbr(np.array([0.1, 0.2]), np.array([0.1]))

    def test_severity_classes_follow_usgs_breaks(self):
        delta = np.array([-0.3, 0.05, 0.2, 0.35, 0.5, 0.8, np.nan])
        classes = severity_class(delta)
        self.assertEqual(classes.tolist(), [0, 0, 1, 2, 3, 4, NODATA])
        self.assertAlmostEqual(burned_fraction(classes), 4 / 6)
        summary = severity_summary(classes)
        self.assertEqual(summary["n"], 6)
        self.assertAlmostEqual(summary["alta"], 1 / 6)


if __name__ == "__main__":
    unittest.main()
