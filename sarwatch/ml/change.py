"""Change detection between two dates: robust log-ratio thresholds and the Conradsen Wishart test.

The GCOV products used here expose only the diagonal covariance terms (HHHH, HVHV), so the
Conradsen et al. test is applied in its diagonal form: channels are treated as independent
gamma-distributed intensities and the omnibus statistic has p degrees of freedom.
"""
import numpy as np
from scipy import stats
from skimage.morphology import remove_small_objects

NODATA = 255


def log_ratio_db(before_db, after_db):
    before = np.asarray(before_db, dtype=np.float32)
    after = np.asarray(after_db, dtype=np.float32)
    if before.shape != after.shape:
        raise ValueError("Grillas incompatibles")
    valid = np.isfinite(before) & np.isfinite(after)
    return np.where(valid, after - before, np.nan).astype(np.float32)


def mad_threshold(delta_db, k=3.0):
    """Symmetric threshold k * 1.4826 * MAD around the median of the difference."""
    sample = np.asarray(delta_db, dtype=np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size < 100:
        raise ValueError("Muestra insuficiente")
    median = float(np.median(sample))
    mad = float(np.median(np.abs(sample - median))) * 1.4826
    if mad <= 0:
        raise ValueError("Dispersión nula")
    return median - k * mad, median + k * mad


def change_mask_from_delta(delta_db, lower, upper, min_pixels=0):
    """uint8: 1 decrease, 2 increase, 0 no significant change, 255 no data."""
    delta = np.asarray(delta_db, dtype=np.float32)
    mask = np.full(delta.shape, NODATA, dtype=np.uint8)
    finite = np.isfinite(delta)
    decrease = finite & (delta < lower)
    increase = finite & (delta > upper)
    if min_pixels > 1:
        decrease = remove_small_objects(decrease, min_size=min_pixels)
        increase = remove_small_objects(increase, min_size=min_pixels)
    mask[finite] = 0
    mask[decrease] = 1
    mask[increase] = 2
    return mask


def enl_estimate(intensity, valid=None, window=None):
    """Equivalent number of looks from a homogeneous sample: mean^2 / variance of linear intensity."""
    values = np.asarray(intensity, dtype=np.float64)
    mask = np.isfinite(values) & (values > 0)
    if valid is not None:
        mask &= np.asarray(valid, dtype=bool)
    sample = values[mask]
    if sample.size < 100:
        raise ValueError("Muestra insuficiente para ENL")
    return float(sample.mean() ** 2 / sample.var())


def conradsen_diagonal_test(before, after, looks_before, looks_after):
    """Omnibus change test for diagonal covariance matrices (Conradsen et al. 2003/2016, diagonal case).

    `before` and `after` are sequences of linear-intensity arrays (one per channel, same grid).
    Returns (statistic, p_value) arrays; low p-values indicate change. Degrees of freedom = channels.
    """
    before = [np.asarray(b, dtype=np.float64) for b in before]
    after = [np.asarray(a, dtype=np.float64) for a in after]
    if len(before) != len(after) or not before:
        raise ValueError("Se requieren los mismos canales en ambas fechas")
    p = len(before)
    shape = before[0].shape
    n = np.broadcast_to(np.asarray(looks_before, dtype=np.float64), shape)
    m = np.broadcast_to(np.asarray(looks_after, dtype=np.float64), shape)
    valid = np.isfinite(n) & np.isfinite(m) & (n > 0) & (m > 0)
    ln_q = np.zeros(shape, dtype=np.float64)
    for b, a in zip(before, after):
        if b.shape != shape or a.shape != shape:
            raise ValueError("Grillas incompatibles")
        ok = np.isfinite(b) & np.isfinite(a) & (b > 0) & (a > 0)
        valid &= ok
        x = n * b
        y = m * a
        with np.errstate(invalid="ignore", divide="ignore"):
            ln_q += (n + m) * np.log(n + m) - n * np.log(n) - m * np.log(m) + n * np.log(x) + m * np.log(y) - (n + m) * np.log(x + y)
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = 1 - (2 * p**2 - 1) / (6 * p) * (1 / n + 1 / m - 1 / (n + m))
        statistic = -2 * rho * ln_q
    statistic = np.where(valid, statistic, np.nan)
    p_value = np.full(shape, np.nan, dtype=np.float64)
    p_value[valid] = stats.chi2.sf(statistic[valid], df=p)
    return statistic.astype(np.float32), p_value.astype(np.float32)


def change_mask_from_pvalue(p_value, delta_db, alpha=0.01, min_pixels=0):
    """uint8: 1 significant decrease, 2 significant increase, 0 no change, 255 no data."""
    p = np.asarray(p_value, dtype=np.float32)
    delta = np.asarray(delta_db, dtype=np.float32)
    if p.shape != delta.shape:
        raise ValueError("Grillas incompatibles")
    finite = np.isfinite(p) & np.isfinite(delta)
    significant = finite & (p < alpha)
    decrease = significant & (delta < 0)
    increase = significant & (delta > 0)
    if min_pixels > 1:
        decrease = remove_small_objects(decrease, min_size=min_pixels)
        increase = remove_small_objects(increase, min_size=min_pixels)
    mask = np.full(p.shape, NODATA, dtype=np.uint8)
    mask[finite] = 0
    mask[decrease] = 1
    mask[increase] = 2
    return mask


def change_fractions(mask, groups=None, names=None):
    """Fraction of decrease/increase pixels overall and per group (e.g. WorldCover class)."""
    mask = np.asarray(mask)
    valid = mask != NODATA

    def summary(sel):
        n = int(sel.sum())
        return {"n": n, "decrease": float((mask[sel] == 1).mean()) if n else None, "increase": float((mask[sel] == 2).mean()) if n else None}

    result = {"all": summary(valid)}
    if groups is not None:
        groups = np.broadcast_to(np.asarray(groups), mask.shape)
        for value in np.unique(groups[valid]):
            key = names.get(int(value), str(value)) if names else str(value)
            result[key] = summary(valid & (groups == value))
    return result
