"""Small, explicit scientific operations shared by processing and the viewer."""
import numpy as np


def power_db(power):
    values = np.asarray(power, dtype=np.float32)
    result = np.full(values.shape, np.nan, dtype=np.float32)
    valid = np.isfinite(values) & (values > 0)
    result[valid] = 10 * np.log10(values[valid])
    return result


def difference(before, after):
    if before.shape != after.shape:
        raise ValueError("Las grillas deben tener el mismo tamaño")
    valid = np.isfinite(before) & np.isfinite(after)
    return np.where(valid, after - before, np.nan)
