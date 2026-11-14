import unittest
import numpy as np
from sarwatch.ml.labels import mndwi, water_label, composite_nearest, NODATA, label_summary
from sarwatch.ml.covariates import hand_proxy, permanent_water_mask


class OpticalLabels(unittest.TestCase):
    def test_mndwi_and_water_rule(self):
        green = np.array([[2000, 500, 0, 1000]], dtype="uint16")
        swir = np.array([[500, 2000, 0, 1000]], dtype="uint16")
        index = mndwi(green, swir)
        self.assertAlmostEqual(float(index[0, 0]), .6)
        self.assertTrue(np.isnan(index[0, 2]))
        scl = np.array([[4, 6, 4, 9]])
        label = water_label(green, swir, scl)
        self.assertEqual(label.tolist(), [[1, 0, NODATA, NODATA]])

    def test_composite_prefers_nearest_observation(self):
        near = np.array([[1, NODATA, 0]], dtype="uint8")
        far = np.array([[0, 1, 1]], dtype="uint8")
        label, source = composite_nearest([(5, far), (1, near)])
        self.assertEqual(label.tolist(), [[1, 1, 0]])
        self.assertEqual(source.tolist(), [[1, 5, 1]])
        summary = label_summary(np.array([[1, 0, NODATA, NODATA]], dtype="uint8"))
        self.assertAlmostEqual(summary["valid_fraction"], .5)
        self.assertAlmostEqual(summary["water_fraction_of_valid"], .5)


class Terrain(unittest.TestCase):
    def test_hand_proxy_height_and_distance(self):
        dem = np.array([[10., 12., 15.], [10., 11., 14.], [10., 10., np.nan]], dtype="float32")
        water = np.zeros((3, 3), dtype=bool)
        water[:, 0] = True
        height, distance = hand_proxy(dem, water, 20)
        self.assertAlmostEqual(float(height[0, 2]), 5)
        self.assertAlmostEqual(float(distance[0, 2]), 40)
        self.assertAlmostEqual(float(height[1, 0]), 0)
        self.assertTrue(np.isnan(height[2, 2]))
        self.assertTrue(np.isnan(hand_proxy(dem, np.zeros((3, 3), bool), 20)[0]).all())
        self.assertEqual(permanent_water_mask(np.array([95., 50., np.nan])).tolist(), [True, False, False])


if __name__ == "__main__":
    unittest.main()
