"""Evaluation metrics with explicit sample counts. No metric is reported without n."""
import numpy as np


def _pair(y_true, y_pred):
    a = np.asarray(y_true).ravel()
    b = np.asarray(y_pred).ravel()
    if a.shape != b.shape:
        raise ValueError("Las series deben tener la misma longitud")
    keep = np.isfinite(a.astype(float)) & np.isfinite(b.astype(float))
    return a[keep], b[keep]


def binary_scores(y_true, y_pred):
    """Precision, recall, F1 and IoU for a positive class encoded as truthy values."""
    a, b = _pair(y_true, y_pred)
    a = a.astype(bool)
    b = b.astype(bool)
    tp = int((a & b).sum())
    fp = int((~a & b).sum())
    fn = int((a & ~b).sum())
    tn = int((~a & ~b).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    iou = tp / (tp + fp + fn) if tp + fp + fn else None
    return {"n": int(a.size), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1, "iou": iou, "positive_fraction": float(a.mean()) if a.size else None}


def scores_by_group(y_true, y_pred, groups, names=None):
    """Binary scores computed separately per group label (e.g. WorldCover class)."""
    a = np.asarray(y_true).ravel()
    b = np.asarray(y_pred).ravel()
    g = np.asarray(groups).ravel()
    if not a.shape == b.shape == g.shape:
        raise ValueError("Etiquetas, predicciones y grupos deben alinearse")
    result = {}
    for value in np.unique(g[np.isfinite(g.astype(float))]):
        mask = g == value
        key = names.get(int(value), str(value)) if names else str(value)
        result[key] = binary_scores(a[mask], b[mask])
    return result


def regression_scores(y_true, y_pred):
    a, b = _pair(np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float))
    if a.size == 0:
        return {"n": 0, "mae": None, "bias": None, "rmse": None}
    error = b - a
    return {"n": int(a.size), "mae": float(np.mean(np.abs(error))), "bias": float(np.mean(error)), "rmse": float(np.sqrt(np.mean(error**2)))}


def skill_score(model_error, baseline_error):
    """1 - model/baseline; positive means the model beats the baseline, None if undefined."""
    if model_error is None or baseline_error is None or baseline_error <= 0:
        return None
    return float(1 - model_error / baseline_error)


def brier_score(y_true, probability):
    a, p = _pair(np.asarray(y_true, dtype=float), np.asarray(probability, dtype=float))
    if ((p < 0) | (p > 1)).any():
        raise ValueError("Las probabilidades deben estar en [0,1]")
    return {"n": int(a.size), "brier": float(np.mean((p - a) ** 2)) if a.size else None}


def calibration_table(y_true, probability, bins=10):
    """Observed frequency per predicted-probability bin; empty bins are reported as such."""
    a, p = _pair(np.asarray(y_true, dtype=float), np.asarray(probability, dtype=float))
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (p >= low) & ((p < high) if high < 1 else (p <= high))
        rows.append({"bin_low": float(low), "bin_high": float(high), "n": int(mask.sum()), "mean_predicted": float(p[mask].mean()) if mask.any() else None, "observed_frequency": float(a[mask].mean()) if mask.any() else None})
    return rows


def interval_coverage(y_true, lower, upper):
    """Fraction of observations inside [lower, upper] and the mean interval width."""
    a = np.asarray(y_true, dtype=float).ravel()
    lo = np.asarray(lower, dtype=float).ravel()
    hi = np.asarray(upper, dtype=float).ravel()
    if not a.shape == lo.shape == hi.shape:
        raise ValueError("Series de distinta longitud")
    if (hi < lo).any():
        raise ValueError("Límite superior menor que el inferior")
    keep = np.isfinite(a) & np.isfinite(lo) & np.isfinite(hi)
    a, lo, hi = a[keep], lo[keep], hi[keep]
    if a.size == 0:
        return {"n": 0, "coverage": None, "mean_width": None}
    return {"n": int(a.size), "coverage": float(np.mean((a >= lo) & (a <= hi))), "mean_width": float(np.mean(hi - lo))}
