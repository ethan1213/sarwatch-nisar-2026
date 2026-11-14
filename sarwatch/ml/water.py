"""Threshold-based open-water detection in dB. Interpretable baselines, evaluated against optical labels."""
import numpy as np
from scipy import stats
from skimage.filters import threshold_otsu

NODATA = 255
MAX_SAMPLES = 2_000_000


def _finite_sample(values, valid=None, seed=0):
    values = np.asarray(values, dtype=np.float32)
    mask = np.isfinite(values) if valid is None else (np.isfinite(values) & np.asarray(valid, dtype=bool))
    sample = values[mask]
    if sample.size > MAX_SAMPLES:
        sample = np.random.default_rng(seed).choice(sample, MAX_SAMPLES, replace=False)
    return sample


def otsu_threshold(values_db, valid=None):
    sample = _finite_sample(values_db, valid)
    if sample.size < 100:
        raise ValueError("Muestra insuficiente para Otsu")
    return float(threshold_otsu(sample, nbins=512))


def kittler_illingworth_threshold(values_db, valid=None, bins=512):
    """Minimum-error thresholding (Kittler & Illingworth, 1986) on a histogram of dB values."""
    sample = _finite_sample(values_db, valid)
    if sample.size < 100:
        raise ValueError("Muestra insuficiente para Kittler-Illingworth")
    hist, edges = np.histogram(sample, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    p = hist.astype(np.float64) / hist.sum()
    c1 = np.cumsum(p)
    c2 = 1 - c1
    m1 = np.cumsum(p * centers) / np.where(c1 > 0, c1, np.nan)
    m2 = (np.sum(p * centers) - np.cumsum(p * centers)) / np.where(c2 > 0, c2, np.nan)
    v1 = np.cumsum(p * centers**2) / np.where(c1 > 0, c1, np.nan) - m1**2
    v2 = (np.sum(p * centers**2) - np.cumsum(p * centers**2)) / np.where(c2 > 0, c2, np.nan) - m2**2
    with np.errstate(invalid="ignore", divide="ignore"):
        cost = 1 + 2 * (c1 * np.log(np.sqrt(np.clip(v1, 1e-12, None))) + c2 * np.log(np.sqrt(np.clip(v2, 1e-12, None)))) - 2 * (c1 * np.log(c1) + c2 * np.log(c2))
    cost[~np.isfinite(cost)] = np.inf
    cost[(c1 < .01) | (c2 < .01)] = np.inf
    return float(centers[int(np.argmin(cost))])


def bimodality_coefficient(values_db, valid=None):
    """Sarle's bimodality coefficient; values above ~0.555 suggest a bimodal distribution."""
    sample = _finite_sample(values_db, valid).astype(np.float64)
    n = sample.size
    if n < 4:
        raise ValueError("Muestra insuficiente")
    skew = stats.skew(sample)
    kurt = stats.kurtosis(sample)  # excess kurtosis
    return float((skew**2 + 1) / (kurt + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))))


def water_mask(values_db, threshold, hand=None, max_hand_m=None, slope=None, max_slope_deg=None):
    """uint8 mask: 1 water (below threshold and allowed by terrain), 0 not water, 255 no data.

    Terrain rules remove radar shadow and steep slopes that mimic water; both are optional and
    recorded by the caller. Pixels with missing terrain keep the SAR decision.
    """
    values = np.asarray(values_db, dtype=np.float32)
    mask = np.full(values.shape, NODATA, dtype=np.uint8)
    finite = np.isfinite(values)
    water = finite & (values < threshold)
    if hand is not None and max_hand_m is not None:
        hand = np.asarray(hand, dtype=np.float32)
        water &= ~(np.isfinite(hand) & (hand > max_hand_m))
    if slope is not None and max_slope_deg is not None:
        slope = np.asarray(slope, dtype=np.float32)
        water &= ~(np.isfinite(slope) & (slope > max_slope_deg))
    mask[finite] = water[finite].astype(np.uint8)
    return mask


def area_km2(mask, resolution_m):
    return float((np.asarray(mask) == 1).sum() * resolution_m**2 / 1e6)
