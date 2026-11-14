"""Bounded forecasting of AOI-level SAR summaries with mandatory baselines and honest intervals.

Targets are scalar per date (median HH dB of the clip, open-water area km2). Models are compared
in rolling-origin folds: every forecast uses only information available before the target date.
Nothing here predicts floods or damage; it predicts the next value of a summary series.
"""
import numpy as np

from sarwatch.ml.metrics import interval_coverage, regression_scores, skill_score
from sarwatch.ml.splits import rolling_origin

MIN_TRAIN = 3
COVERAGE_REQUIRED = 0.8


def day_of_year_features(dates):
    days = np.asarray(dates, dtype="datetime64[D]")
    doy = (days - days.astype("datetime64[Y]")).astype(int) + 1
    angle = 2 * np.pi * doy / 365.25
    return np.column_stack([np.sin(angle), np.cos(angle)])


def antecedent_sum(daily_dates, daily_values, target_dates, days, lag_days=0):
    """Sum of a daily series over [target - lag - days, target - lag). Missing days count as NaN."""
    d = np.asarray(daily_dates, dtype="datetime64[D]")
    v = np.asarray(daily_values, dtype=np.float64)
    out = np.full(len(target_dates), np.nan)
    for i, target in enumerate(np.asarray(target_dates, dtype="datetime64[D]")):
        end = target - np.timedelta64(lag_days, "D")
        start = end - np.timedelta64(days, "D")
        sel = (d >= start) & (d < end)
        if sel.sum() == days and np.isfinite(v[sel]).all():
            out[i] = v[sel].sum()
    return out


def build_design(dates, target, exogenous=None):
    """Features for predicting target[k] from information at or before date[k-1].

    Columns: previous target, change between the two previous targets, horizon days, seasonal sin/cos,
    then any exogenous columns (already lagged by the caller so they end before the target date).
    Rows start at index 1 (first date has no previous observation).
    """
    dates = np.asarray(dates, dtype="datetime64[D]")
    target = np.asarray(target, dtype=np.float64)
    if dates.shape != target.shape or dates.size < 2:
        raise ValueError("Series incompatibles o demasiado cortas")
    order = np.argsort(dates)
    dates, target = dates[order], target[order]
    previous = np.r_[np.nan, target[:-1]]
    momentum = np.r_[np.nan, np.nan, target[1:-1] - target[:-2]]
    horizon = np.r_[np.nan, (dates[1:] - dates[:-1]).astype(int)]
    X = np.column_stack([previous, np.nan_to_num(momentum, nan=0.0), horizon, day_of_year_features(dates)])
    names = ["previous", "momentum", "horizon_days", "season_sin", "season_cos"]
    if exogenous:
        for name, values in exogenous.items():
            values = np.asarray(values, dtype=np.float64)[order]
            X = np.column_stack([X, values])
            names.append(name)
    return dates, target, X, names


def persistence(X_train, y_train, X_test):
    return X_test[:, 0]


def climatology(X_train, y_train, X_test):
    return np.full(X_test.shape[0], float(np.mean(y_train)))


def ridge(X_train, y_train, X_test, alpha=1.0):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    model.fit(X_train, y_train)
    return model.predict(X_test)


def anomaly_ridge(X_train, y_train, X_test, alpha=1.0):
    """Ridge on the change from the previous value; falls back to persistence when there is no signal."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    model.fit(X_train, y_train - X_train[:, 0])
    return X_test[:, 0] + model.predict(X_test)


MODELS = {"persistence": persistence, "climatology": climatology, "ridge": ridge, "ridge_anomaly": anomaly_ridge}


def conformal_interval(residuals, level=0.8):
    """Symmetric split-conformal half-width from past absolute residuals (finite-sample corrected)."""
    r = np.abs(np.asarray(residuals, dtype=np.float64))
    r = r[np.isfinite(r)]
    if r.size == 0:
        return np.nan
    n = r.size
    q = min(1.0, np.ceil((n + 1) * level) / n)
    return float(np.quantile(r, q))


def rolling_evaluation(dates, target, X, models=None, min_train=MIN_TRAIN, level=0.8):
    """Rolling-origin folds; returns per-model predictions, errors, intervals and summary scores."""
    models = models or MODELS
    folds = rolling_origin(dates, min_train=min_train)
    usable = ~np.isnan(X).any(axis=1) & np.isfinite(target)
    results = {}
    for name, fn in models.items():
        rows = []
        for train_idx, test_idx in folds:
            train_idx = [i for i in train_idx if usable[i]]
            k = test_idx[0]
            if not usable[k] or len(train_idx) < min_train:
                continue
            pred = float(fn(X[train_idx], target[train_idx], X[[k]])[0])
            # Interval from residuals of the same model on strictly earlier folds (no peeking).
            past = [r for r in rows]
            half = conformal_interval([r["error"] for r in past], level) if len(past) >= 2 else np.nan
            rows.append({"issued_from": str(dates[train_idx[-1]]), "target_date": str(dates[k]), "horizon_days": int((dates[k] - dates[train_idx[-1]]).astype(int)), "prediction": pred, "observed": float(target[k]), "error": pred - float(target[k]), "interval_half_width": half, "lower": pred - half if np.isfinite(half) else None, "upper": pred + half if np.isfinite(half) else None})
        if not rows:
            results[name] = {"n_evaluations": 0}
            continue
        scores = regression_scores([r["observed"] for r in rows], [r["prediction"] for r in rows])
        with_interval = [r for r in rows if r["lower"] is not None]
        coverage = interval_coverage([r["observed"] for r in with_interval], [r["lower"] for r in with_interval], [r["upper"] for r in with_interval]) if with_interval else {"n": 0, "coverage": None, "mean_width": None}
        results[name] = {"n_evaluations": len(rows), **scores, "interval_level": level, "interval": coverage, "evaluations": rows}
    baseline = results.get("persistence", {}).get("mae")
    for name, res in results.items():
        res["skill_vs_persistence"] = skill_score(res.get("mae"), baseline) if name != "persistence" else 0.0
    return results


def publication_decision(results, coverage_required=COVERAGE_REQUIRED, min_evaluations=4):
    """Which model (if any) may be shown: must beat persistence and have calibrated intervals."""
    candidates = []
    for name, res in results.items():
        if name == "persistence" or res.get("n_evaluations", 0) < min_evaluations:
            continue
        skill = res.get("skill_vs_persistence")
        coverage = (res.get("interval") or {}).get("coverage")
        if skill is not None and skill > 0 and coverage is not None and coverage >= coverage_required:
            candidates.append((skill, name))
    if not candidates:
        return {"publishable": False, "model": None, "reason": "ningún modelo supera a la persistencia con intervalos calibrados en los pliegues disponibles"}
    skill, name = max(candidates)
    return {"publishable": True, "model": name, "skill_vs_persistence": skill, "reason": "supera a la persistencia y cubre al menos el nivel requerido"}
