import unittest
from sarwatch.firms import parse_csv


class FirmsTests(unittest.TestCase):
    def test_bounds_time_units_and_duplicate_overpasses(self):
        text = 'latitude,longitude,acq_date,acq_time,confidence,frp,version\n-36.7,-73.0,2026-11-13,5,nominal,10.5,2.0NRT\n-36.7,-73.0,2026-11-13,5,n,10.5,2.0NRT\n0,0,2026-11-13,1200,h,20,2.0NRT\n'
        rows = parse_csv(text, 'NOAA-20', [-74,-38,-72,-36])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['properties']['utc'], '2026-11-13T00:05:00Z')
        self.assertEqual(rows[0]['properties']['frp_mw'], 10.5)

    def test_empty_result_is_valid_not_proof_of_absence(self):
        self.assertEqual(parse_csv('latitude,longitude,acq_date,acq_time,confidence,frp\n', 'NOAA-20', [-74,-38,-72,-36]), [])

    def test_bad_html_or_bad_confidence_fails_before_publication(self):
        with self.assertRaises(ValueError):
            parse_csv('<html>Access denied</html>', 'NOAA-20', [-74,-38,-72,-36])
        with self.assertRaises(ValueError):
            parse_csv('latitude,longitude,acq_date,acq_time,confidence,frp\n-36.7,-73,2026-11-13,0100,unknown,12\n','NOAA-20',[-74,-38,-72,-36])
