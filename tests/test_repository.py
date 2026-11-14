import tempfile
import unittest
from sarwatch.repository import RasterRepository


class RepositoryBoundary(unittest.TestCase):
    def test_products_cannot_escape_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = RasterRepository(directory)
            with self.assertRaises(ValueError):
                repository.product_path('../private.txt')
            self.assertEqual(repository.product_path('scene.tif').parent, repository.root)
