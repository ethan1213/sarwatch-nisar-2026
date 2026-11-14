"""Per-pixel gradient-boosted classifier (LightGBM) with spatial-block validation and a model card."""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from sarwatch.ml.features import local_std, ratio_db, stack_features
from sarwatch.ml.grids import read_layer

COVARIATE_FILES = {"slope": "slope.tif", "hand_proxy": "hand_proxy.tif", "dist_water": "dist_water.tif", "jrc_occurrence": "jrc_occurrence.tif"}
DEFAULT_PARAMS = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 200, "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 1.0, "verbose": -1, "num_threads": 4, "seed": 0}


def load_covariates(root):
    """Static covariate layers for an AOI as float32 arrays, or an empty dict if not prepared."""
    folder = Path(root) / "covariates"
    layers = {}
    for name, filename in COVARIATE_FILES.items():
        path = folder / filename
        if path.is_file():
            values, _, _ = read_layer(path)
            layers[name] = values.astype(np.float32)
    return layers


def scene_features(hh_db, hv_db, covariates, texture_size=5):
    """Ordered feature layers for one date. Missing covariates are simply absent."""
    layers = {"hh_db": np.asarray(hh_db, dtype=np.float32), "hv_db": np.asarray(hv_db, dtype=np.float32)}
    layers["ratio_db"] = ratio_db(layers["hh_db"], layers["hv_db"])
    layers["texture_hh"] = local_std(layers["hh_db"], texture_size)
    for name, values in covariates.items():
        layers[name] = values
    return layers


def change_features(before_layers, after_layers):
    """Pair features: after-date layers plus HH/HV differences (after minus before)."""
    layers = dict(after_layers)
    layers["delta_hh_db"] = after_layers["hh_db"] - before_layers["hh_db"]
    layers["delta_hv_db"] = after_layers["hv_db"] - before_layers["hv_db"]
    return layers


def train_lightgbm(X, y, X_valid=None, y_valid=None, params=None, num_rounds=400):
    import lightgbm as lgb
    if X.shape[0] != y.shape[0] or X.shape[0] == 0:
        raise ValueError("Datos de entrenamiento vacíos o desalineados")
    if len(np.unique(y)) < 2:
        raise ValueError("El entrenamiento requiere ambas clases")
    settings = {**DEFAULT_PARAMS, **(params or {})}
    train_set = lgb.Dataset(X, label=y.astype(np.float32))
    callbacks = []
    valid_sets = []
    if X_valid is not None and y_valid is not None and X_valid.shape[0] > 0:
        valid_sets = [lgb.Dataset(X_valid, label=y_valid.astype(np.float32), reference=train_set)]
        callbacks = [lgb.early_stopping(30, verbose=False)]
    booster = lgb.train(settings, train_set, num_boost_round=num_rounds, valid_sets=valid_sets, callbacks=callbacks)
    return booster


def predict_proba(booster, X):
    if X.shape[0] == 0:
        return np.empty(0, dtype=np.float32)
    return booster.predict(X, num_iteration=booster.best_iteration or None).astype(np.float32)


def feature_importance(booster, names):
    gains = booster.feature_importance(importance_type="gain")
    total = float(gains.sum()) or 1.0
    return {name: float(g / total) for name, g in sorted(zip(names, gains), key=lambda item: -item[1])}


def subsample_balanced(X, y, max_per_class, seed=0):
    rng = np.random.default_rng(seed)
    keep = []
    for value in np.unique(y):
        idx = np.flatnonzero(y == value)
        if idx.size > max_per_class:
            idx = rng.choice(idx, max_per_class, replace=False)
        keep.append(idx)
    keep = np.concatenate(keep)
    rng.shuffle(keep)
    return X[keep], y[keep]


def write_model_card(path, name, task, data, split, metrics, features, limits, extra=None):
    """A model card is mandatory for anything shown in the viewer."""
    card = {"name": name, "task": task, "created_utc": datetime.now(timezone.utc).isoformat(), "data": data, "split": split, "metrics": metrics, "features": features, "limits": limits, **(extra or {})}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2, default=_jsonable), encoding="utf-8")
    return path


def _jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def features_matrix(layers, names=None):
    """Stack selected layers into X with the common valid mask."""
    selected = {n: layers[n] for n in (names or list(layers))}
    return stack_features(selected)
