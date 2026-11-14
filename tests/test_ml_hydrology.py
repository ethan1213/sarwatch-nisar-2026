import unittest
import numpy as np
from sarwatch.ml.hydrology import coarsen_mean, flow_accumulation, flow_direction, subbasin_labels


class FlowRouting(unittest.TestCase):
    def test_single_valley_drains_fully_to_its_outlet(self):
        rows, cols = 6, 5
        dem = np.zeros((rows, cols))
        for r in range(rows):
            for c in range(cols):
                dem[r, c] = (rows - r) * 10 + abs(c - 2) * 5
        direction = flow_direction(dem)
        accumulation = flow_accumulation(dem, direction)
        self.assertEqual(accumulation[rows - 1, 2], rows * cols)
        seeds = np.zeros_like(dem, dtype=bool)
        seeds[rows - 1, 2] = True
        labels = subbasin_labels(direction, seeds)
        self.assertTrue((labels == 1).all())

    def test_two_basins_split_without_unlabelled_cells(self):
        rows, cols = 12, 17
        r_idx, c_idx = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        dem = np.minimum((r_idx - 3.0) ** 2 + (c_idx - 4.0) ** 2, (r_idx - 8.0) ** 2 * 1.3 + (c_idx - 12.0) ** 2 * 1.1).astype(float)
        dem += 0.001 * (r_idx + 0.37 * c_idx)  # breaks residual ties without changing the basin ranking
        direction = flow_direction(dem)
        sinks = np.argwhere(direction == -1)
        self.assertEqual(len(sinks), 2)
        seeds = np.zeros_like(dem, dtype=bool)
        for r, c in sinks:
            seeds[r, c] = True
        labels = subbasin_labels(direction, seeds)
        self.assertEqual(int((labels == 0).sum()), 0)
        accumulation = flow_accumulation(dem, direction)
        for (r, c), expected_label in zip(sinks, (1, 2)):
            self.assertEqual(accumulation[r, c], float((labels == expected_label).sum()))

    def test_nan_cells_never_route_or_accumulate(self):
        dem = np.array([[3.0, 2.0, np.nan], [2.0, 1.0, 0.0], [1.0, 0.0, -1.0]])
        direction = flow_direction(dem)
        self.assertEqual(direction[0, 2], -1)
        accumulation = flow_accumulation(dem, direction)
        self.assertEqual(accumulation[0, 2], 0)
        self.assertGreaterEqual(accumulation[2, 2], 1)

    def test_coarsen_mean_matches_manual_block_average(self):
        values = np.arange(16, dtype=float).reshape(4, 4)
        coarse = coarsen_mean(values, 2)
        self.assertEqual(coarse.shape, (2, 2))
        self.assertEqual(coarse[0, 0], np.mean([0, 1, 4, 5]))
        self.assertEqual(coarse[1, 1], np.mean([10, 11, 14, 15]))
        with self.assertRaises(ValueError):
            coarsen_mean(values, 0)


if __name__ == "__main__":
    unittest.main()
