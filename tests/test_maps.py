import json
import unittest
from pathlib import Path
import numpy as np
from rasterio.transform import from_origin
from sarwatch.maps import raster_map


class GeographicViews(unittest.TestCase):
    def test_regional_catalogs_are_polygons(self):
        for name,count in [('metropolitana',52),('valparaiso',36)]:
            data=json.loads(Path('catalog',name+'.geojson').read_text(encoding='utf-8'))
            self.assertEqual(len(data['features']),count)
            self.assertTrue(all(f['geometry']['type'] in ('Polygon','MultiPolygon') for f in data['features']))

    def test_raster_is_georeferenced_on_map(self):
        m=raster_map(np.ones((10,10),dtype='float32'),from_origin(350000,6300000,20,20),'EPSG:32719')
        html=m.get_root().render()
        self.assertIn('NISAR',html)
        self.assertIn('imageOverlay',html)
        self.assertIn('OpenStreetMap',html)
