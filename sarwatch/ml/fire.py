"""Cross between thermal hot spots (GOES cells) and the NISAR grid: zones, zonal SAR means, interval labels.

The unit of analysis is the GOES pixel ("celda térmica", about 2 km): hot spots are only known at that
scale, so SAR, terrain and land cover are aggregated into each cell instead of pretending the hot spot
has a 20 m position.
"""
import numpy as np

from sarwatch.ml.thermal import scan_angles


def zone_raster(lat, lon, window, axis_x, axis_y, proj):
    """Index (row * n_cols + col) of the thermal cell containing each point; -1 outside the window or the disk."""
    row0, row1, col0, col1 = window
    x, y = scan_angles(lat, lon, proj)
    with np.errstate(invalid="ignore"):
        col = np.rint((x - axis_x[1]) / axis_x[0]) - col0
        row = np.rint((y - axis_y[1]) / axis_y[0]) - row0
    inside = np.isfinite(col) & np.isfinite(row) & (row >= 0) & (row < row1 - row0) & (col >= 0) & (col < col1 - col0)
    zones = np.full(np.shape(lat), -1, dtype=np.int32)
    zones[inside] = (row[inside] * (col1 - col0) + col[inside]).astype(np.int32)
    return zones


def zonal_mean(values, zones, n_zones):
    """(mean, valid_fraction) per zone over finite values; mean is NaN where a zone has no finite value."""
    values, zones = np.asarray(values, dtype=np.float64).ravel(), np.asarray(zones).ravel()
    inside = zones >= 0
    finite = inside & np.isfinite(values)
    total = np.bincount(zones[inside], minlength=n_zones).astype(np.float64)
    count = np.bincount(zones[finite], minlength=n_zones).astype(np.float64)
    summed = np.bincount(zones[finite], weights=values[finite], minlength=n_zones)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, summed / count, np.nan), np.where(total > 0, count / total, 0.0)


def zonal_mean_db(db, zones, n_zones):
    """Zonal mean of backscatter averaged in linear power and returned in dB (dB values are not averaged directly)."""
    mean, fraction = zonal_mean(np.power(10.0, np.asarray(db, dtype=np.float64) / 10.0), zones, n_zones)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 10.0 * np.log10(mean), fraction


def zonal_fraction(mask, valid, zones, n_zones):
    """Fraction of the valid pixels of each zone where mask is true; NaN without valid pixels."""
    mask, valid, zones = np.asarray(mask, dtype=bool).ravel(), np.asarray(valid, dtype=bool).ravel(), np.asarray(zones).ravel()
    keep = valid & (zones >= 0)
    total = np.bincount(zones[keep], minlength=n_zones).astype(np.float64)
    hits = np.bincount(zones[keep & mask], minlength=n_zones).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, hits / total, np.nan)


def window_any(flags, times, start, end):
    """Per-cell 'any flag' over start < time <= end; flags is (time, y, x) boolean, times datetime64."""
    times = np.asarray(times, dtype="datetime64[m]")
    keep = (times > np.datetime64(start, "m")) & (times <= np.datetime64(end, "m"))
    return np.asarray(flags)[keep].any(axis=0) if keep.any() else np.zeros(np.shape(flags)[1:], dtype=bool)


def neighbour_fraction(flags):
    """Fraction of the 8 neighbours of each cell that are flagged (edges use the neighbours that exist)."""
    flags = np.asarray(flags, dtype=np.float64)
    padded, ones = np.pad(flags, 1), np.pad(np.ones_like(flags), 1)
    total = sum(padded[1 + dr:padded.shape[0] - 1 + dr, 1 + dc:padded.shape[1] - 1 + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))
    count = sum(ones[1 + dr:ones.shape[0] - 1 + dr, 1 + dc:ones.shape[1] - 1 + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))
    return total / count


def rank_auc(score, label):
    """Probability that a positive outranks a negative (ties count half); None without both classes."""
    score, label = np.asarray(score, dtype=np.float64), np.asarray(label, dtype=bool)
    keep = np.isfinite(score)
    score, label = score[keep], label[keep]
    n_pos, n_neg = int(label.sum()), int((~label).sum())
    if not n_pos or not n_neg:
        return None
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(score.size, dtype=np.float64)
    ranks[order] = np.arange(1, score.size + 1)
    sorted_scores = score[order]
    boundaries = np.flatnonzero(np.diff(sorted_scores)) + 1
    for first, last in zip(np.r_[0, boundaries], np.r_[boundaries, score.size]):
        if last - first > 1:
            ranks[order[first:last]] = (first + 1 + last) / 2
    return float((ranks[label].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
