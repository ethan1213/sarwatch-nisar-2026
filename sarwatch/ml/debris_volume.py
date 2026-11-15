"""Experimental terrain ranking and Gartner et al. 2014 Eq.3 sediment volume.

doi:10.1016/j.enggeo.2014.04.008. Calibrated in southern California within two years
of fire, not Chile. Sediment volume at a basin outlet is NOT deposit depth or runout.
"""
import math
import numpy as np

SOURCE = "https://doi.org/10.1016/j.enggeo.2014.04.008"


def relative_depth_index(accumulation, slope, severity_fraction):
    arrays = [np.asarray(a, dtype=float) for a in (accumulation, slope, severity_fraction)]
    if len({a.shape for a in arrays}) != 1:
        raise ValueError("Grillas incompatibles")
    acc, slope, severity = arrays
    valid = np.isfinite(acc) & np.isfinite(slope) & np.isfinite(severity) & (acc >= 1) & (slope >= 0) & (slope <= 90) & (severity >= 0) & (severity <= 1)
    out = np.full(acc.shape, np.nan, dtype=np.float32)
    if valid.any():
        # AOI-relative log accumulation and slope / 45° are explicit heuristic choices.
        denom = max(float(np.log1p(acc[valid]).max()), 1.)
        out[valid] = np.log1p(acc[valid]) / denom * np.clip(slope[valid] / 45., 0, 1) * severity[valid]
    return out


def gartner_emergency_volume(i15_mm_h, burned_moderate_high_km2, relief_m, *, rainfall_interval_minutes=15, years_since_fire=None):
    if i15_mm_h is None:
        return {"status": "missing_i15", "volume_m3": None, "operational": False,
                "reason": "Falta intensidad pico observada en intervalos de 15 minutos; no sustituir por lluvia horaria o diaria."}
    if rainfall_interval_minutes != 15:
        raise ValueError("Se requiere intensidad de 15 minutos, no precipitación horaria/diaria")
    values = (i15_mm_h, burned_moderate_high_km2, relief_m)
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("Intensidad, área quemada y relieve deben ser finitos y positivos")
    if years_since_fire is not None and (not math.isfinite(years_since_fire) or years_since_fire < 0):
        raise ValueError("Edad del incendio inválida")
    ranges = ((3, 72), (.01, 15.01), (100, 2028))
    outside = [name for name, value, bounds in zip(("i15", "Bmh", "R"), values, ranges) if not bounds[0] <= value <= bounds[1]]
    if years_since_fire is None:
        outside.append("edad del incendio no verificada")
    elif years_since_fire > 2:
        outside.append("más de dos años desde el incendio")
    log_v = 4.22 + .39 * math.sqrt(i15_mm_h) + .36 * math.log(burned_moderate_high_km2) + .13 * math.sqrt(relief_m)
    return {"status": "experimental_extrapolation" if outside else "experimental_in_source_range",
            "volume_m3": math.exp(log_v), "residual_envelope_m3": [math.exp(log_v - 1.96 * 1.04), math.exp(log_v + 1.96 * 1.04)],
            "outside_calibration": outside, "source": SOURCE, "operational": False,
            "limitations": "Envolvente residual aproximada; no intervalo predictivo completo. Sin validación chilena. No estima profundidad, huella ni rutas seguras."}
