"""Optical water labels from Sentinel-2 L2A. Labels are evidence with a date, not ground truth."""
import numpy as np

# Scene classification (SCL) values treated as unusable for a water label.
SCL_INVALID = (0, 1, 2, 3, 8, 9, 10, 11)  # nodata, saturated, dark, cloud shadow, clouds, cirrus, snow
WATER_THRESHOLD = 0.0  # MNDWI > 0 is the conventional open-water rule (Xu, 2006); stored in provenance
NODATA = 255


def mndwi(green, swir1):
    """Modified NDWI = (green - swir1) / (green + swir1); NaN where undefined."""
    g = np.asarray(green, dtype=np.float32)
    s = np.asarray(swir1, dtype=np.float32)
    if g.shape != s.shape:
        raise ValueError("Bandas con distinta grilla")
    with np.errstate(invalid="ignore", divide="ignore"):
        result = (g - s) / (g + s)
    result[(g + s) <= 0] = np.nan
    return result


def valid_from_scl(scl):
    scl = np.asarray(scl)
    return ~np.isin(scl, SCL_INVALID)


def water_label(green, swir1, scl, threshold=WATER_THRESHOLD):
    """uint8 label: 1 water, 0 not water, 255 no usable observation."""
    index = mndwi(green, swir1)
    valid = valid_from_scl(scl) & np.isfinite(index) & (np.asarray(green) > 0) & (np.asarray(swir1) > 0)
    label = np.full(index.shape, NODATA, dtype=np.uint8)
    label[valid] = (index[valid] > threshold).astype(np.uint8)
    return label


def composite_nearest(labels_by_offset):
    """Fill a label grid preferring observations closest in time to the SAR date.

    `labels_by_offset` is an iterable of (abs_day_offset, label_uint8). Pixels are taken from the
    smallest offset first; later observations only fill pixels still at NODATA.
    Returns (label, source_offset) where source_offset is the offset used per pixel (255 = none).
    """
    ordered = sorted(labels_by_offset, key=lambda item: item[0])
    if not ordered:
        raise ValueError("Sin observaciones")
    label = np.full(ordered[0][1].shape, NODATA, dtype=np.uint8)
    source = np.full(label.shape, 255, dtype=np.uint8)
    for offset, candidate in ordered:
        if candidate.shape != label.shape:
            raise ValueError("Observaciones con distinta grilla")
        fill = (label == NODATA) & (candidate != NODATA)
        label[fill] = candidate[fill]
        source[fill] = min(int(round(offset)), 254)
    return label, source


def label_summary(label):
    valid = label != NODATA
    return {"valid_fraction": float(valid.mean()), "water_fraction_of_valid": float((label[valid] == 1).mean()) if valid.any() else None, "pixels_valid": int(valid.sum())}
