import unittest
import numpy as np
from sarwatch.ml.water import otsu_threshold, kittler_illingworth_threshold, bimodality_coefficient, water_mask, area_km2
from sarwatch.ml.change import log_ratio_db, mad_threshold, change_mask_from_delta, conradsen_diagonal_test, change_mask_from_pvalue, enl_estimate, change_fractions
from sarwatch.ml.pixel_classifier import scene_features, features_matrix, train_lightgbm, predict_proba, subsample_balanced, feature_importance


class WaterThresholds(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.values = np.concatenate([rng.normal(-20, 1.5, 20000), rng.normal(-8, 2, 60000)]).astype("float32")

    def test_thresholds_fall_between_modes_and_distribution_is_bimodal(self):
        for threshold in (otsu_threshold(self.values), kittler_illingworth_threshold(self.values)):
            self.assertTrue(-18 < threshold < -10, threshold)
        self.assertGreater(bimodality_coefficient(self.values), .555)
        self.assertLess(bimodality_coefficient(np.random.default_rng(1).normal(0, 1, 5000)), .555)

    def test_water_mask_respects_terrain_and_nodata(self):
        values = np.array([[-25., -25., -5., np.nan]], dtype="float32")
        hand = np.array([[1., 40., 1., 1.]], dtype="float32")
        mask = water_mask(values, -15, hand=hand, max_hand_m=20)
        self.assertEqual(mask.tolist(), [[1, 0, 0, 255]])
        self.assertAlmostEqual(area_km2(mask, 20), 20 * 20 / 1e6)


class ChangeTests(unittest.TestCase):
    def test_mad_threshold_and_mask(self):
        rng = np.random.default_rng(0)
        delta = rng.normal(0, .5, (200, 200)).astype("float32")
        delta[:10, :10] = 6
        delta[50:60, 50:60] = -6
        delta[0, 199] = np.nan
        lower, upper = mad_threshold(delta)
        self.assertTrue(-2.5 < lower < -1 and 1 < upper < 2.5)
        mask = change_mask_from_delta(delta, lower, upper, min_pixels=20)
        self.assertEqual(int(mask[5, 5]), 2)
        self.assertEqual(int(mask[55, 55]), 1)
        self.assertEqual(int(mask[0, 199]), 255)
        self.assertEqual(int((mask == 2).sum()), 100)
        fractions = change_fractions(mask, np.where(np.arange(200)[:, None] < 100, 10, 50), {10: "arboles", 50: "urbano"})
        self.assertEqual(fractions["urbano"]["increase"], 0)
        self.assertGreater(fractions["arboles"]["increase"], 0)

    def test_conradsen_detects_scaled_intensity_and_enl_recovers_looks(self):
        rng = np.random.default_rng(0)
        looks = 9.7
        shape = (120, 120)
        hh_before = rng.gamma(looks, 0.05 / looks, shape)
        hv_before = rng.gamma(looks, 0.01 / looks, shape)
        hh_after = rng.gamma(looks, 0.05 / looks, shape)
        hv_after = rng.gamma(looks, 0.01 / looks, shape)
        hh_after[:40, :40] *= 6  # about +7.8 dB; with ~10 looks per date a 4x change is only weakly detectable
        statistic, p = conradsen_diagonal_test([hh_before, hv_before], [hh_after, hv_after], looks, looks)
        self.assertLess(float(np.median(p[:40, :40])), .01)
        self.assertGreater(float(np.median(p[60:, 60:])), .2)
        # Calibration under no change: about alpha of pixels should fall below alpha.
        self.assertLess(float((p[60:, 60:] < .01).mean()), .03)
        delta = log_ratio_db(10 * np.log10(hh_before), 10 * np.log10(hh_after))
        mask = change_mask_from_pvalue(p, delta, alpha=.01)
        self.assertGreater(float((mask[:40, :40] == 2).mean()), .7)
        self.assertLess(float((mask[60:, 60:] != 0).mean()), .05)
        self.assertAlmostEqual(enl_estimate(hh_before[60:, 60:]), looks, delta=1.5)


class Classifier(unittest.TestCase):
    def test_lightgbm_learns_a_separable_rule(self):
        rng = np.random.default_rng(0)
        hh = rng.normal(-10, 3, (80, 80)).astype("float32")
        hv = hh - 6 + rng.normal(0, .5, (80, 80)).astype("float32")
        slope = rng.uniform(0, 30, (80, 80)).astype("float32")
        layers = scene_features(hh, hv, {"slope": slope})
        X, valid, names = features_matrix(layers)
        self.assertEqual(names[:4], ["hh_db", "hv_db", "ratio_db", "texture_hh"])
        y = ((layers["hh_db"][valid] < -12) & (slope[valid] < 15)).astype(int)
        Xs, ys = subsample_balanced(X, y, 2000)
        booster = train_lightgbm(Xs[:3000], ys[:3000], Xs[3000:], ys[3000:], num_rounds=100)
        proba = predict_proba(booster, X)
        accuracy = float(((proba > .5).astype(int) == y).mean())
        self.assertGreater(accuracy, .95)
        importance = feature_importance(booster, names)
        self.assertGreater(importance["hh_db"] + importance["slope"], .6)
        with self.assertRaises(ValueError):
            train_lightgbm(X[:10], np.zeros(10))


if __name__ == "__main__":
    unittest.main()
