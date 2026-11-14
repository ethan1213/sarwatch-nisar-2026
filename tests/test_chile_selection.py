import unittest
from scripts.select_chile_pairs import contains, select


class ChileSelection(unittest.TestCase):
    def test_footprint_must_contain_point(self):
        entry={'polygons':[['-34 -72 -32 -72 -32 -70 -34 -70 -34 -72']]}
        self.assertTrue(contains(entry,-71,-33))
        self.assertFalse(contains(entry,-69,-33))

    def test_distinct_polarizations_are_not_paired(self):
        base={'polygons':[['-34 -72 -32 -72 -32 -70 -34 -70 -34 -72']]}
        entries=[dict(base,producer_granule_id=f'NISAR_L2_PR_GCOV_033_075_A_161_2005_{pol}_A_20261017T104431',time_start=date) for pol,date in [('DHDH','2026-10-05'),('SHSH','2026-10-17')]]
        self.assertEqual(select(entries,-71,-33),[])
