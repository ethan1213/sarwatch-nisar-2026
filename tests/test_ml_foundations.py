import json
import tempfile
import unittest
import numpy as np
from sarwatch.ml.features import stack_features, unstack, local_std, slope_degrees, ratio_db, grid_signature, assert_same_grid
from sarwatch.ml.splits import block_ids, spatial_block_split, assert_blocks_not_shared, temporal_holdout, rolling_origin
from sarwatch.ml.metrics import binary_scores, regression_scores, brier_score, calibration_table, interval_coverage, skill_score, scores_by_group
from sarwatch.ml.experiments import record


class Features(unittest.TestCase):
    def test_stack_uses_common_finite_mask_and_roundtrips(self):
        a = np.array([[1., np.nan], [3., 4.]], dtype='float32')
        b = np.array([[1., 2.], [np.nan, 4.]], dtype='float32')
        X, valid, names = stack_features({'a': a, 'b': b})
        self.assertEqual(names, ['a', 'b'])
        self.assertEqual(X.shape, (2, 2))
        self.assertEqual(int(valid.sum()), 2)
        grid = unstack(X[:, 0], valid)
        self.assertTrue(np.isnan(grid[0, 1]) and np.isnan(grid[1, 0]))
        self.assertEqual(grid[1, 1], 4)

    def test_misaligned_layers_are_rejected(self):
        with self.assertRaises(ValueError):
            stack_features({'a': np.zeros((2, 2)), 'b': np.zeros((3, 2))})
        with self.assertRaises(ValueError):
            assert_same_grid(grid_signature('EPSG:32721', (20, 0, 0, 0, -20, 0), (2, 2)), grid_signature('EPSG:32721', (20, 0, 0, 0, -20, 0), (2, 3)))

    def test_texture_and_slope_respect_nodata(self):
        values = np.full((7, 7), 5., dtype='float32')
        values[3, 3] = np.nan
        texture = local_std(values, 3)
        self.assertTrue(np.isnan(texture[3, 3]))
        self.assertAlmostEqual(float(texture[0, 0]), 0, places=5)
        dem = np.tile(np.arange(5, dtype=float) * 20, (5, 1))
        slope = slope_degrees(dem, 20)
        self.assertAlmostEqual(float(slope[2, 2]), 45, places=4)
        np.testing.assert_allclose(ratio_db([-10.], [-16.]), [6.])


class Splits(unittest.TestCase):
    def test_blocks_never_shared_and_buffer_removes_neighbours(self):
        shape = (256, 256)
        ids = block_ids(shape, 64)
        valid = np.ones(shape, dtype=bool)
        train, test = spatial_block_split(ids, valid, test_fraction=.25, seed=1, buffer_blocks=1)
        assert_blocks_not_shared(ids, train, test)
        self.assertTrue(test.any() and train.any())
        self.assertFalse((train & test).any())
        test_blocks = np.unique(ids[test])
        n_cols = 4
        for block in np.unique(ids[train]):
            r, c = block // n_cols, block % n_cols
            for t in test_blocks:
                self.assertTrue(max(abs(r - t // n_cols), abs(c - t % n_cols)) > 1)

    def test_random_pixel_split_is_detected(self):
        ids = block_ids((8, 8), 4)
        rng = np.random.default_rng(0)
        mask = rng.random((8, 8)) < .5
        with self.assertRaises(ValueError):
            assert_blocks_not_shared(ids, mask, ~mask)

    def test_temporal_splits_are_chronological(self):
        dates = ['2026-08-10', '2026-07-05', '2026-09-03', '2026-07-17']
        train, test = temporal_holdout(dates, 1)
        self.assertEqual(test, [2])
        self.assertEqual(sorted(train), [0, 1, 3])
        folds = rolling_origin(dates, min_train=2)
        self.assertEqual(len(folds), 2)
        for train_idx, test_idx in folds:
            self.assertTrue(all(np.datetime64(dates[i]) < np.datetime64(dates[test_idx[0]]) for i in train_idx))


class Metrics(unittest.TestCase):
    def test_binary_scores_known_values(self):
        s = binary_scores([1, 1, 0, 0, 1], [1, 0, 0, 1, 1])
        self.assertEqual((s['tp'], s['fp'], s['fn'], s['tn']), (2, 1, 1, 1))
        self.assertAlmostEqual(s['f1'], 2 / 3)
        self.assertAlmostEqual(s['iou'], .5)
        self.assertIsNone(binary_scores([0, 0], [0, 0])['precision'])

    def test_group_scores_and_regression(self):
        by = scores_by_group([1, 0, 1, 0], [1, 0, 0, 0], [10, 10, 20, 20], {10: 'agua', 20: 'urbano'})
        self.assertEqual(by['agua']['f1'], 1)
        self.assertEqual(by['urbano']['recall'], 0)
        r = regression_scores([1, 2, 3], [1, 2, 5])
        self.assertAlmostEqual(r['mae'], 2 / 3)
        self.assertAlmostEqual(r['bias'], 2 / 3)
        self.assertAlmostEqual(skill_score(.5, 1.), .5)
        self.assertIsNone(skill_score(.5, 0))

    def test_probabilistic_metrics(self):
        self.assertAlmostEqual(brier_score([1, 0], [1, 0])['brier'], 0)
        self.assertAlmostEqual(brier_score([1, 0], [.5, .5])['brier'], .25)
        with self.assertRaises(ValueError):
            brier_score([1], [1.5])
        table = calibration_table([1, 0, 1, 1], [.95, .1, .9, .85], bins=2)
        self.assertEqual(table[1]['n'], 3)
        self.assertAlmostEqual(table[1]['observed_frequency'], 1)
        cov = interval_coverage([1, 2, 3], [0, 2.5, 2], [2, 3, 4])
        self.assertAlmostEqual(cov['coverage'], 2 / 3)


class Experiments(unittest.TestCase):
    def test_record_requires_dataset_split_metrics_and_is_json(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                record('x', {'metrics': {}}, root)
            path = record('prueba', {'dataset': {'aoi': 'Pantanal'}, 'split': 'bloques', 'metrics': {'f1': np.float32(.5)}}, root)
            body = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(body['metrics']['f1'], .5)
            self.assertIn('python', body['environment'])


if __name__ == '__main__':
    unittest.main()
