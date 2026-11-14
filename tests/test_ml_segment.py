import unittest
import numpy as np
from sarwatch.ml.segment import windows, predict_tiles, normalize_channels, NODATA


class WindowedInference(unittest.TestCase):
    def test_windows_cover_grid_with_overlap(self):
        covered = np.zeros((700, 530), dtype=int)
        for r0, r1, c0, c1 in windows(700, 530, size=256, overlap=32):
            covered[r0:r1, c0:c1] += 1
        self.assertTrue((covered >= 1).all())
        self.assertGreater(covered.max(), 1)
        with self.assertRaises(ValueError):
            list(windows(10, 10, size=8, overlap=8))

    def test_predictions_average_overlaps_and_respect_nodata(self):
        stack = np.random.default_rng(0).normal(0, 1, (2, 300, 300)).astype("float32")
        stack[0, :20, :20] = np.nan
        run = lambda tile: (tile[0] < 0).astype("float32")  # pseudo model: water where channel 0 negative
        proba, mask = predict_tiles(run, stack, size=128, overlap=32)
        self.assertEqual(mask[0, 0], NODATA)
        self.assertTrue(np.isnan(proba[0, 0]))
        valid = np.isfinite(stack).all(axis=0)
        expected = (stack[0] < 0)[valid]
        self.assertTrue(((mask[valid] == 1) == expected).all())
        normalized = normalize_channels(stack, [0, 0], [1, 1])
        self.assertTrue(np.isnan(normalized[0, 0, 0]))


if __name__ == "__main__":
    unittest.main()
