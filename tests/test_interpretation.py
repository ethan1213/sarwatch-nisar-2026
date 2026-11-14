import unittest
import numpy as np
from sarwatch.interpretation import summarize,answer,storage_bytes


class EvidenceBoundInterpretation(unittest.TestCase):
    def context(self):
        return {'region':'Caso de prueba','before':'2026-10-05','after':'2026-10-17','polarization':'HH','statistics':summarize(np.array([1.,np.nan,2.]),np.array([3.,4.,4.])),'source':'https://cmr.earthdata.nasa.gov/'}

    def test_summary_uses_intersection_and_robust_location(self):
        s=self.context()['statistics']
        self.assertEqual(s['pixels'],2)
        self.assertEqual(s['median_db'],2)
        self.assertAlmostEqual(s['coverage'],2/3)

    def test_missing_is_not_zero_change(self):
        self.assertIsNone(summarize(np.array([np.nan]),np.array([1.]))['median_db'])

    def test_prediction_request_does_not_invent_risk(self):
        text,_=answer('¿Puedes predecir una inundación mañana?',self.context())
        self.assertIn('Todavía no podemos predecir',text)

    def test_unknown_question_abstains(self):
        text,_=answer('¿Quién ganó el partido?',self.context())
        self.assertIn('No tengo evidencia',text)

    def test_storage_units_and_quadratic_resolution(self):
        self.assertAlmostEqual(storage_bytes(10000,20,2,30),8e9)
        self.assertEqual(storage_bytes(10000,20,2,30)/storage_bytes(10000,80,2,30),16)
