"""Feature construction on the native NISAR grid. Rejects misaligned inputs."""
import numpy as np
from scipy.ndimage import uniform_filter


def grid_signature(crs, transform, shape):
    """Hashable description of a raster grid used to refuse silent misalignment."""
    return (str(crs), tuple(np.round(np.asarray(transform, dtype=float), 6).tolist()), tuple(int(s) for s in shape))


def assert_same_grid(reference, candidate):
    if reference != candidate:
        raise ValueError(f"Grillas incompatibles: {reference} != {candidate}")


def ratio_db(hh_db, hv_db):
    """HH minus HV in dB equals the log of the intensity ratio; NaN propagates."""
    hh = np.asarray(hh_db, dtype=np.float32)
    hv = np.asarray(hv_db, dtype=np.float32)
    if hh.shape != hv.shape:
        raise ValueError("HH y HV deben compartir grilla")
    return hh - hv


def local_std(values, size=5):
    """Local standard deviation ignoring NaN; returns NaN where the window has no data."""
    values = np.asarray(values, dtype=np.float64)
    if size < 3 or size % 2 == 0:
        raise ValueError("size debe ser impar y >= 3")
    finite = np.isfinite(values)
    filled = np.where(finite, values, 0.0)
    count = uniform_filter(finite.astype(np.float64), size=size, mode="constant")
    mean = uniform_filter(filled, size=size, mode="constant")
    mean_sq = uniform_filter(filled**2, size=size, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = mean / count
        variance = mean_sq / count - mean**2
    result = np.sqrt(np.clip(variance, 0, None)).astype(np.float32)
    result[(count <= 0) | ~finite] = np.nan
    return result


def slope_degrees(dem, resolution_m):
    """Slope in degrees from a DEM on a square grid (Horn finite differences)."""
    dem = np.asarray(dem, dtype=np.float64)
    if dem.ndim != 2:
        raise ValueError("El DEM debe ser bidimensional")
    dz_dy, dz_dx = np.gradient(dem, float(resolution_m))
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy))).astype(np.float32)
    slope[~np.isfinite(dem)] = np.nan
    return slope


def stack_features(layers):
    """Flatten aligned 2-D layers into a (n_valid, k) matrix over the common finite mask.

    `layers` is an ordered mapping name -> 2-D array. Returns (X, valid_mask, names).
    A pixel is used only if every layer is finite there; nothing is imputed silently.
    """
    if not layers:
        raise ValueError("Sin capas")
    names = list(layers)
    arrays = [np.asarray(layers[n], dtype=np.float32) for n in names]
    shape = arrays[0].shape
    for name, array in zip(names, arrays):
        if array.shape != shape:
            raise ValueError(f"La capa {name} no comparte la grilla {shape}")
    valid = np.ones(shape, dtype=bool)
    for array in arrays:
        valid &= np.isfinite(array)
    X = np.column_stack([a[valid] for a in arrays]) if valid.any() else np.empty((0, len(names)), dtype=np.float32)
    return X, valid, names


def unstack(values, valid_mask, fill=np.nan):
    """Place a 1-D vector back on the grid described by valid_mask."""
    values = np.asarray(values)
    if values.shape[0] != int(valid_mask.sum()):
        raise ValueError("El vector no coincide con la máscara")
    grid = np.full(valid_mask.shape, fill, dtype=np.result_type(values.dtype, np.float32))
    grid[valid_mask] = values
    return grid
