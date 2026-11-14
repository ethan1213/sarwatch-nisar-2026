import io
import json
import unittest
from unittest.mock import patch
import numpy as np
from sarwatch.ml.forecast import antecedent_sum, build_design, rolling_evaluation, publication_decision, conformal_interval, MODELS
from weather import fetch_river_discharge


class Design(unittest.TestCase):
    def test_antecedent_sum_excludes_target_day_and_requires_complete_window(self):
        days = np.arange(np.datetime64("2026-07-01"), np.datetime64("2026-07-31"))
        rain = np.ones(days.size)
        total = antecedent_sum(days, rain, ["2026-07-10", "2026-07-03"], 7)
        self.assertEqual(total[0], 7)
        self.assertTrue(np.isnan(total[1]))
        lagged = antecedent_sum(days, rain, ["2026-07-10"], 7, lag_days=2)
        self.assertEqual(lagged[0], 7)

    def test_design_uses_only_past_information(self):
        dates = ["2026-07-17", "2026-07-05", "2026-07-29"]
        target = [-9.0, -10.0, -8.0]
        d, y, X, names = build_design(dates, target, {"rain7": [3.0, 1.0, 5.0]})
        self.assertEqual(str(d[0]), "2026-07-05")
        self.assertTrue(np.isnan(X[0, 0]))
        self.assertEqual(X[1, 0], -10.0)  # previous value is the chronologically earlier observation
        self.assertEqual(X[2, 2], 12)  # horizon days
        self.assertEqual(names[-1], "rain7")
        self.assertEqual(X[2, -1], 5.0)


class Evaluation(unittest.TestCase):
    def series(self):
        dates = np.arange(np.datetime64("2026-07-05"), np.datetime64("2026-11-20"), np.timedelta64(12, "D"))
        rng = np.random.default_rng(0)
        trend = np.linspace(-12, -8, dates.size)
        target = trend + rng.normal(0, .1, dates.size)
        return dates, target

    def test_rolling_evaluation_is_causal_and_scores_models(self):
        dates, target = self.series()
        d, y, X, names = build_design(dates, target)
        results = rolling_evaluation(d, y, X, min_train=3)
        self.assertIn("persistence", results)
        for name, res in results.items():
            self.assertGreater(res["n_evaluations"], 0, name)
            for row in res["evaluations"]:
                self.assertLess(np.datetime64(row["issued_from"]), np.datetime64(row["target_date"]))
        # A steadily trending series: anomaly ridge should beat persistence.
        self.assertGreater(results["ridge_anomaly"]["skill_vs_persistence"], 0)
        self.assertEqual(results["persistence"]["skill_vs_persistence"], 0.0)

    def test_publication_requires_skill_and_coverage(self):
        results = {"persistence": {"n_evaluations": 6, "mae": 1.0, "skill_vs_persistence": 0.0}, "ridge": {"n_evaluations": 6, "mae": .5, "skill_vs_persistence": .5, "interval": {"coverage": .9}}, "climatology": {"n_evaluations": 6, "mae": .4, "skill_vs_persistence": .6, "interval": {"coverage": .5}}}
        decision = publication_decision(results)
        self.assertTrue(decision["publishable"])
        self.assertEqual(decision["model"], "ridge")
        self.assertFalse(publication_decision({"persistence": {"n_evaluations": 2, "mae": 1.0}})["publishable"])
        self.assertAlmostEqual(conformal_interval([1, -2, 3, 4], .8), 4)
        self.assertTrue(np.isnan(conformal_interval([])))


class DischargeContract(unittest.TestCase):
    def test_incomplete_response_is_rejected(self):
        with patch("weather.urlopen", return_value=io.BytesIO(b'{"daily":{"time":["2026-07-01"]}}')):
            with self.assertRaises(ValueError):
                fetch_river_discharge(-17.2, -57.2, "2026-07-01", "2026-07-01")

    def test_valid_response_keeps_provider_and_cell(self):
        payload = {"latitude": -17.25, "longitude": -57.25, "daily": {"time": ["2026-07-01"], "river_discharge": [12.5]}}
        with patch("weather.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            result = fetch_river_discharge(-17.2, -57.2, "2026-07-01", "2026-07-01")
            self.assertIn("flood-api.open-meteo.com", request.call_args.args[0])
            self.assertEqual(result["kind"], "modelled river discharge")
            self.assertEqual(result["cell_latitude"], -17.25)


if __name__ == "__main__":
    unittest.main()
