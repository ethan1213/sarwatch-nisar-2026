import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from sarwatch.data_paths import site_data_root, verified_manifest
from sarwatch.publication import validate_prepared


class PublicationTests(unittest.TestCase):
    def fixture(self, root):
        transform = from_origin(300000, 6000000, 20, 20)
        scenes, checked = [], []
        for index in range(2):
            products = {}
            for pol in ('HH','HV'):
                name=f'{index}_{pol}.tif'; products[pol]=name
                with rasterio.open(root/name,'w',driver='GTiff',height=4,width=4,count=1,dtype='float32',crs='EPSG:32718',transform=transform,nodata=np.nan) as dst:
                    dst.write(np.ones((4,4),dtype='float32'),1); dst.update_tags(unit='dB')
            scenes.append({'id':str(index),'products':products,'finite_positive_fraction':{'HH':1.,'HV':1.}})
            checked.append({'id':str(index),'md5_calculado':'0'*32,'sha256':'0'*64})
        return {'scenes':scenes,'grid':{'height':4,'width':4,'epsg':32718,'transform':tuple(transform)}}, {'status':'integridad verificada; prueba de contrato','scenes':checked}

    def test_publish_gate_requires_report_grid_units_and_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest, report=self.fixture(Path(folder))
            ready=validate_prepared(manifest,report,folder)
            self.assertTrue(verified_manifest(ready))
            self.assertFalse(verified_manifest(manifest))
            wrong=copy.deepcopy(report); wrong['scenes'][0]['sha256']=''
            with self.assertRaises(ValueError):validate_prepared(manifest,wrong,folder)
            wrong=copy.deepcopy(manifest); wrong['grid']['epsg']=32719
            with self.assertRaises(ValueError):validate_prepared(wrong,report,folder)
            wrong=copy.deepcopy(manifest); wrong['scenes'][0]['finite_positive_fraction']['HH']=.5
            with self.assertRaises(ValueError):validate_prepared(wrong,report,folder)

    def test_remote_storage_changes_only_the_new_site(self):
        with patch.dict(os.environ,{'DATA_DIR':'local-data','REMOTE_DATA_DIR':'remote-data'}):
            self.assertEqual(site_data_root('concepcion_penco'),Path('remote-data/concepcion_penco'))
            self.assertEqual(site_data_root('metropolitana'),Path('local-data/metropolitana'))
            self.assertEqual(site_data_root('pantanal'),Path('local-data'))
            with self.assertRaises(ValueError):site_data_root('../secret')
