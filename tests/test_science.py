import unittest
import numpy as np
from science import power_db, difference


class ScientificOperations(unittest.TestCase):
    def test_power_units_and_invalid(self):
        actual = power_db([1, 10, .1, 0, -1, np.nan, np.inf])
        np.testing.assert_allclose(actual[:3], [0, 10, -10], atol=1e-5)
        self.assertTrue(np.isnan(actual[3:]).all())

    def test_difference_uses_common_validity(self):
        before = np.array([2., np.nan, 3.])
        after = np.array([5., 4., np.nan])
        np.testing.assert_allclose(difference(before, after), [3, np.nan, np.nan], equal_nan=True)
        self.assertEqual(float(difference(before, before)[0]), 0)


if __name__ == "__main__":
    unittest.main()
