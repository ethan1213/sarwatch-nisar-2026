import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException
from api.fire import get_vegetation_sample


class VegetationApiTests(unittest.TestCase):
    def test_sample_keeps_location_dates_and_provenance(self):
        data = get_vegetation_sample()
        self.assertEqual(data['point'], {'lon': -72.99, 'lat': -36.74})
        self.assertTrue(data['limits'])
        dates = [r['date'] for r in data['observations']]
        self.assertEqual(dates, sorted(set(dates)))
        for row in data['observations']:
            self.assertIn('_MSIL2A_', row['item'])
            self.assertEqual(row['scl'], 4)
            for key in ('ndvi', 'ndmi'):
                self.assertTrue(-1 <= row[key] <= 1)

    def test_missing_pack_returns_service_error_not_fake_data(self):
        with TemporaryDirectory() as folder, patch('api.fire.Path', return_value=Path(folder) / 'missing.json'):
            with self.assertRaises(HTTPException) as caught:
                get_vegetation_sample()
        self.assertEqual(caught.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
