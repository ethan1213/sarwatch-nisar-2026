"""Reader for NISAR L2 GUNW (geocoded unwrapped interferogram) products: coherence and phase/deformation.

GUNW is a different HDF5 layout from GCOV (no fixed public schema was embedded in this codebase before
a real file was opened), so this reader WALKS the file looking for datasets whose name matches a known
pattern (coherence, unwrapped phase, connected components) instead of hardcoding one exact path. It
reports exactly which path it used, so the first real run documents the schema for everyone after it.
Coherence in [0,1]: high = the ground did not reorganise between passes (rock, pavement, intact slope);
low = something changed (vegetation growth, tillage, snow, water, or a channel reworked by a flow). A
drop in coherence along a quebrada is consistent with a debris flow but is not proof of one on its own.
"""
import re
from pathlib import Path

import numpy as np

PATTERNS = {
    "coherence": re.compile(r"coherence", re.IGNORECASE),
    "unwrapped_phase": re.compile(r"unwrapped.*phase", re.IGNORECASE),
    "connected_components": re.compile(r"connected.*component", re.IGNORECASE),
}


def find_datasets(path, frequency="frequencyA", polarization=None):
    """Return {kind: (hdf5_internal_path, shape, dtype)} for every pattern matched under science/LSAR/GUNW."""
    import h5py
    found = {}

    def visit(name, obj):
        if not isinstance(obj, h5py.Dataset) or obj.ndim != 2:
            return
        if frequency and frequency not in name:
            return
        if polarization and polarization not in name:
            return
        for kind, pattern in PATTERNS.items():
            if kind not in found and pattern.search(name):
                found[kind] = (f"{group.name}/{name}", obj.shape, str(obj.dtype))

    with h5py.File(path, "r") as handle:
        group = handle.get("science/LSAR/GUNW") or handle.get("science/LSAR")
        if group is None:
            raise ValueError(f"{path}: no se encontró el grupo science/LSAR(/GUNW) esperado en un producto NISAR")
        group.visititems(visit)
    return found


def read_layer(path, internal_path):
    import h5py
    with h5py.File(path, "r") as handle:
        dataset = handle[internal_path]
        values = dataset[()]
        fill = dataset.attrs.get("_FillValue")
    values = np.asarray(values, dtype=np.float32)
    if fill is not None:
        values = np.where(values == fill, np.nan, values)
    return values


def coherence_drop_mask(coherence, threshold=0.3):
    """uint8: 1 where coherence fell below threshold (candidate ground reorganisation), 0 otherwise,
    255 where no data. threshold=0.3 is a conventional InSAR "decorrelated" cut (literature range 0.2-0.4);
    it flags candidate change, not a validated debris-flow detector."""
    values = np.asarray(coherence, dtype=np.float32)
    out = np.full(values.shape, 255, dtype=np.uint8)
    valid = np.isfinite(values) & (values >= 0) & (values <= 1)
    out[valid] = (values[valid] < threshold).astype(np.uint8)
    return out


def summarize_coherence(coherence, mask=None):
    values = np.asarray(coherence, dtype=np.float32)
    valid = np.isfinite(values) & (values >= 0) & (values <= 1)
    if mask is not None:
        valid &= np.asarray(mask, dtype=bool)
    if not valid.any():
        return {"n": 0}
    sample = values[valid]
    return {"n": int(valid.sum()), "mean": float(sample.mean()), "median": float(np.median(sample)), "p10": float(np.percentile(sample, 10)), "low_fraction": float((sample < 0.3).mean())}
