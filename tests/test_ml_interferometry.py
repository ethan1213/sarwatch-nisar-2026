import tempfile
import unittest
from pathlib import Path
import numpy as np
import h5py
from sarwatch.ml.interferometry import coherence_drop_mask, find_datasets, read_layer, summarize_coherence


def write_fake_gunw(path):
    with h5py.File(path, "w") as f:
        grid = f.create_group("science/LSAR/GUNW/grids/frequencyA")
        coherence = np.array([[0.9, 0.1], [0.95, np.nan]], dtype="float32")
        coherence_clean = np.nan_to_num(coherence, nan=-9999.0)
        ds = grid.create_dataset("unwrappedInterferogram/HH/coherenceMagnitude", data=coherence_clean)
        ds.attrs["_FillValue"] = -9999.0
        grid.create_dataset("unwrappedInterferogram/HH/unwrappedPhase", data=np.zeros((2, 2), dtype="float32"))
        grid.create_dataset("connectedComponents", data=np.zeros((2, 2), dtype="uint8"))


class InterferometryReader(unittest.TestCase):
    def test_find_datasets_locates_known_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.h5"
            write_fake_gunw(path)
            found = find_datasets(path)
            self.assertIn("coherence", found)
            self.assertIn("unwrapped_phase", found)
            self.assertIn("connected_components", found)
            values = read_layer(path, found["coherence"][0])
            self.assertTrue(np.isnan(values[1, 1]))
            self.assertAlmostEqual(float(values[0, 0]), 0.9, places=5)

    def test_missing_lsar_group_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.h5"
            with h5py.File(path, "w") as f:
                f.create_group("not/the/right/group")
            with self.assertRaises(ValueError):
                find_datasets(path)


class CoherenceSummary(unittest.TestCase):
    def test_drop_mask_and_summary(self):
        coherence = np.array([[0.9, 0.1], [0.95, np.nan]], dtype="float32")
        mask = coherence_drop_mask(coherence)
        self.assertEqual(mask.tolist(), [[0, 1], [0, 255]])
        summary = summarize_coherence(coherence)
        self.assertEqual(summary["n"], 3)
        self.assertAlmostEqual(summary["low_fraction"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
