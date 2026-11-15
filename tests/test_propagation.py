import unittest
from sarwatch.ml.propagation import REQUIRED, UNITS, audit_spread_inputs

class SpreadQualification(unittest.TestCase):
    def qualified(self):
        return {k:{"qualified_for_spread":True,"source":"independent survey", "units":UNITS[k],
                   "time_reference":"2026-01-17T12:00Z","grid_reference":"EPSG:32718/30m",
                   "sha256":"a"*64} for k in REQUIRED}

    def test_context_cannot_replace_required_inputs(self):
        report=audit_spread_inputs({"air_humidity":{"value":30},"radar":{"value":-12},"hotspots":{"value":5}})
        self.assertEqual(len(report["missing_inputs"]),len(REQUIRED))
        self.assertFalse(report["spread_prediction_enabled"])

    def test_air_relative_humidity_is_not_fuel_moisture(self):
        inputs=self.qualified(); inputs["fuel_moisture"]["units"]="relative_air_humidity_%"
        self.assertFalse(audit_spread_inputs(inputs)["research_inputs_complete"])

    def test_missing_traceability_blocks_research_input(self):
        inputs=self.qualified(); del inputs["initial_perimeter"]["time_reference"]
        self.assertFalse(audit_spread_inputs(inputs)["research_inputs_complete"])

    def test_complete_inputs_do_not_claim_operational_validation(self):
        report=audit_spread_inputs(self.qualified())
        self.assertTrue(report["research_inputs_complete"])
        self.assertFalse(report["operational"])
        self.assertFalse(report["spread_prediction_enabled"])
