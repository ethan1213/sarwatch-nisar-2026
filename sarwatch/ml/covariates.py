"""Static covariates: terrain, surface-water history and land cover on the NISAR grid."""
import numpy as np
from scipy.ndimage import distance_transform_edt

WORLDCOVER = {10: "árboles", 20: "matorral", 30: "pastizal", 40: "cultivo", 50: "urbano", 60: "suelo desnudo", 70: "nieve y hielo", 80: "agua permanente", 90: "humedal herbáceo", 95: "manglar", 100: "musgo y liquen"}
PERMANENT_WATER_OCCURRENCE = 90  # JRC occurrence (%) treated as permanent water for the HAND proxy


def hand_proxy(dem, permanent_water, resolution_m):
    """Height above the nearest permanent-water pixel and distance to it, in metres.

    This is a proxy for HAND (Height Above Nearest Drainage) that uses observed permanent water
    instead of a hydrologically routed drainage network. Returns (height, distance); both NaN where
    the DEM is missing, and height/distance are NaN everywhere if no permanent water exists.
    """
    dem = np.asarray(dem, dtype=np.float32)
    water = np.asarray(permanent_water, dtype=bool)
    if dem.shape != water.shape:
        raise ValueError("DEM y agua permanente con distinta grilla")
    height = np.full(dem.shape, np.nan, dtype=np.float32)
    distance = np.full(dem.shape, np.nan, dtype=np.float32)
    if not water.any():
        return height, distance
    dist, (rows, cols) = distance_transform_edt(~water, return_indices=True)
    reference = dem[rows, cols]
    finite = np.isfinite(dem) & np.isfinite(reference)
    height[finite] = (dem - reference)[finite]
    distance[finite] = (dist * float(resolution_m))[finite]
    return height, distance


def permanent_water_mask(occurrence, threshold=PERMANENT_WATER_OCCURRENCE):
    occurrence = np.asarray(occurrence, dtype=np.float32)
    return np.isfinite(occurrence) & (occurrence >= threshold)
