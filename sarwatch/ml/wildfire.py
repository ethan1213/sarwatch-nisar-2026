"""Burn severity from Sentinel-2 NBR/dNBR. Severity classes follow the USGS convention (Key & Benson,
2006); they describe optical burn signal, not a calibrated hazard probability."""
import numpy as np

# dNBR class breaks (USGS/UNSPIDER convention), applied to (NBR_pre - NBR_post).
CLASSES = {0: "sin_quema_o_rebrote", 1: "baja", 2: "moderada_baja", 3: "moderada_alta", 4: "alta"}
BREAKS = (0.1, 0.27, 0.44, 0.66)  # class 0 below first break, class 4 above last
NODATA = 255


def boa_reflectance(dn, processing_baseline):
    """Sentinel-2 L2A digital numbers -> surface reflectance; NaN where the DN is 0 (no data).

    Since processing baseline 04.00 (January 2022) the DN carries BOA_ADD_OFFSET = -1000, so
    reflectance = (DN - 1000) / 10000. Skipping the offset leaves the numerator of a normalised index
    untouched and inflates its denominator by 2000: NBR and dNBR come out compressed and burn severity
    is underestimated.
    """
    dn = np.asarray(dn, dtype=np.float32)
    offset = 1000.0 if float(processing_baseline) >= 4.0 else 0.0
    return np.where(dn > 0, (dn - offset) / 10000.0, np.nan).astype(np.float32)


def nbr(nir, swir2):
    """Normalized Burn Ratio = (NIR - SWIR2) / (NIR + SWIR2); NaN where undefined."""
    nir = np.asarray(nir, dtype=np.float32)
    swir2 = np.asarray(swir2, dtype=np.float32)
    if nir.shape != swir2.shape:
        raise ValueError("NIR y SWIR2 deben compartir grilla")
    with np.errstate(invalid="ignore", divide="ignore"):
        result = (nir - swir2) / (nir + swir2)
    result[(nir + swir2) <= 0] = np.nan
    return result


def dnbr(nbr_pre, nbr_post):
    pre = np.asarray(nbr_pre, dtype=np.float32)
    post = np.asarray(nbr_post, dtype=np.float32)
    if pre.shape != post.shape:
        raise ValueError("Grillas incompatibles")
    valid = np.isfinite(pre) & np.isfinite(post)
    return np.where(valid, pre - post, np.nan).astype(np.float32)


def severity_class(delta_nbr, breaks=BREAKS):
    """uint8 class per CLASSES; 255 where delta_nbr is NaN."""
    delta = np.asarray(delta_nbr, dtype=np.float32)
    valid = np.isfinite(delta)
    classes = np.digitize(np.clip(delta, -1, 1), breaks).astype(np.uint8)
    out = np.full(delta.shape, NODATA, dtype=np.uint8)
    out[valid] = classes[valid]
    return out


def burned_fraction(severity, min_class=1):
    valid = severity != NODATA
    return float((severity[valid] >= min_class).mean()) if valid.any() else None


def severity_summary(severity):
    valid = severity != NODATA
    n = int(valid.sum())
    if not n:
        return {"n": 0}
    values, counts = np.unique(severity[valid], return_counts=True)
    return {"n": n, **{CLASSES[int(v)]: float(c / n) for v, c in zip(values, counts)}}
