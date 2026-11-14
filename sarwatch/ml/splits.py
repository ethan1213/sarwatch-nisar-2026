"""Leakage-safe splitting. Neighbouring pixels never straddle train and test."""
import numpy as np


def block_ids(shape, block=64):
    """Integer block id per pixel for a (rows, cols) grid."""
    rows, cols = shape
    if block < 1:
        raise ValueError("block debe ser positivo")
    r = np.arange(rows) // block
    c = np.arange(cols) // block
    n_cols = int(np.ceil(cols / block))
    return (r[:, None] * n_cols + c[None, :]).astype(np.int64)


def spatial_block_split(ids, valid_mask, test_fraction=0.2, seed=0, buffer_blocks=0):
    """Assign whole blocks to train or test; optionally drop a buffer ring around test blocks.

    Returns (train_mask, test_mask) at pixel level. Blocks without valid pixels are ignored.
    """
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction debe estar en (0,1)")
    if ids.shape != valid_mask.shape:
        raise ValueError("ids y valid_mask deben compartir grilla")
    present = np.unique(ids[valid_mask])
    if present.size < 2:
        raise ValueError("Se necesitan al menos dos bloques con datos válidos")
    rng = np.random.default_rng(seed)
    n_test = max(1, int(round(present.size * test_fraction)))
    test_blocks = rng.choice(present, size=n_test, replace=False)
    test_mask = np.isin(ids, test_blocks) & valid_mask
    excluded = _buffer(ids, test_blocks, buffer_blocks) if buffer_blocks > 0 else np.zeros_like(test_mask)
    train_mask = valid_mask & ~test_mask & ~excluded
    if not train_mask.any():
        raise ValueError("Sin píxeles de entrenamiento tras aplicar el buffer")
    return train_mask, test_mask


def _buffer(ids, test_blocks, buffer_blocks):
    """Pixels whose block lies within `buffer_blocks` (Chebyshev) of any test block."""
    unique = np.unique(ids)
    n_cols = int(np.unique(ids[0, :]).size)
    rows_of = unique // n_cols
    cols_of = unique % n_cols
    tr, tc = test_blocks // n_cols, test_blocks % n_cols
    near = np.zeros(unique.size, dtype=bool)
    for r, c in zip(tr, tc):
        near |= (np.abs(rows_of - r) <= buffer_blocks) & (np.abs(cols_of - c) <= buffer_blocks)
    buffer_ids = unique[near & ~np.isin(unique, test_blocks)]
    return np.isin(ids, buffer_ids)


def assert_blocks_not_shared(ids, train_mask, test_mask):
    """Raise if any block contributes pixels to both splits (the random-pixel-split bug)."""
    shared = np.intersect1d(np.unique(ids[train_mask]), np.unique(ids[test_mask]))
    if shared.size:
        raise ValueError(f"{shared.size} bloques comparten entrenamiento y prueba")


def temporal_holdout(dates, n_test=1):
    """Chronological split: the latest n_test observations are the test set."""
    order = np.argsort(np.asarray(dates, dtype="datetime64[ns]"))
    if n_test < 1 or n_test >= len(order):
        raise ValueError("n_test debe dejar al menos una fecha de entrenamiento")
    return order[:-n_test].tolist(), order[-n_test:].tolist()


def rolling_origin(dates, min_train=3):
    """Forecast folds: train on all dates before each target, never after it."""
    order = np.argsort(np.asarray(dates, dtype="datetime64[ns]")).tolist()
    if min_train < 1 or min_train >= len(order):
        raise ValueError("min_train incompatible con el número de fechas")
    return [(order[:k], [order[k]]) for k in range(min_train, len(order))]
