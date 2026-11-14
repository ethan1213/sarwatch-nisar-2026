"""Post-fire debris-flow dynamic threshold: how much 30-minute rain a burned sub-basin can still
take before it is likely to mobilise.

This is an explicit, documented HEURISTIC, not a trained classifier: Chile does not have a public
labelled dataset of post-fire debris flows, and two observed events (the brief this module answers
cites 2026-01-31 and 2026-10-08 in the same quebrada) cannot calibrate a model. Every factor below is
a named, bounded multiplier on a literature-reported base threshold, so a reviewer can see exactly
which input moved the number and by how much. It must be shown with its components, never alone.

Base threshold: Cannon et al. (2008, USGS) report debris-flow-triggering peak 15-minute rainfall
intensities commonly in the 10-20 mm range on recently burned slopes in similar semi-arid terrain;
we use 20 mm per 30 minutes on UNBURNED ground as a conservative starting point for Mediterranean
Chile and reduce it from there. This is the single number in this module most in need of local
calibration once Chile-specific post-fire rainfall thresholds exist (e.g. from Sernageomin/CR2).
"""
import numpy as np

BASE_THRESHOLD_MM_30MIN = 20.0
SEVERITY_MAX_REDUCTION = 0.5       # a fully high-severity sub-basin needs only half the bare-ground rain
SATURATION_REFERENCE_MM = 60.0      # antecedent rain (3-7 days) at which soil saturation effect saturates
SATURATION_MAX_REDUCTION = 0.65     # matches the brief: Oct-8 (saturated) needed far less rain than Jan-31
CONCENTRATION_MAX_REDUCTION = 0.3   # extra reduction for the most flow-concentrated sub-basins
MOISTURE_MAX_REDUCTION = 0.2        # extra reduction when NISAR HH shows the soil already wetter
MIN_THRESHOLD_MM_30MIN = 3.0        # floor: below this we stop trusting the heuristic at all
SEMAPHORE_BREAKS = (8.0, 15.0)      # mm/30min effective threshold: <8 rojo, <15 amarillo, else verde


def severity_factor(burned_high_fraction):
    """1.0 (no reduction) down to 1-SEVERITY_MAX_REDUCTION as the moderate-high+high burn fraction -> 1."""
    fraction = np.clip(np.asarray(burned_high_fraction, dtype=np.float64), 0, 1)
    return 1.0 - SEVERITY_MAX_REDUCTION * fraction


def saturation_factor(antecedent_rain_mm):
    """1.0 (dry) down to 1-SATURATION_MAX_REDUCTION as antecedent rain approaches/exceeds the reference."""
    rain = np.clip(np.asarray(antecedent_rain_mm, dtype=np.float64), 0, None)
    ratio = np.clip(rain / SATURATION_REFERENCE_MM, 0, 1)
    return 1.0 - SATURATION_MAX_REDUCTION * ratio


def concentration_factor(flow_accumulation, reference_accumulation):
    """1.0 for cells at or below the reference (e.g. median) accumulation, dropping toward
    1-CONCENTRATION_MAX_REDUCTION as accumulation grows well past it (log scale: accumulation spans
    orders of magnitude from ridge to channel)."""
    acc = np.clip(np.asarray(flow_accumulation, dtype=np.float64), 1, None)
    reference = max(float(reference_accumulation), 1.0)
    excess = np.log10(acc / reference)
    ratio = np.clip(excess / 2.0, 0, 1)  # two orders of magnitude above reference -> full reduction
    return 1.0 - CONCENTRATION_MAX_REDUCTION * ratio


def moisture_factor(delta_hh_db, wet_reference_db=3.0):
    """1.0 when HH did not rise, down to 1-MOISTURE_MAX_REDUCTION as the HH rise (wetter soil, L-band
    backscatter increases with moisture on bare/sparse ground) approaches wet_reference_db."""
    delta = np.asarray(delta_hh_db, dtype=np.float64)
    ratio = np.clip(np.where(np.isfinite(delta), delta, 0) / wet_reference_db, 0, 1)
    return 1.0 - MOISTURE_MAX_REDUCTION * ratio


def dynamic_threshold(burned_high_fraction, antecedent_rain_mm, flow_accumulation, reference_accumulation, delta_hh_db=None):
    """Effective 30-minute rainfall threshold (mm) per sub-basin, with its components for transparency."""
    factors = {
        "severity": severity_factor(burned_high_fraction),
        "saturation": saturation_factor(antecedent_rain_mm),
        "concentration": concentration_factor(flow_accumulation, reference_accumulation),
    }
    if delta_hh_db is not None:
        factors["moisture"] = moisture_factor(delta_hh_db)
    combined = np.ones_like(np.asarray(burned_high_fraction, dtype=np.float64))
    for value in factors.values():
        combined = combined * value
    threshold = np.maximum(BASE_THRESHOLD_MM_30MIN * combined, MIN_THRESHOLD_MM_30MIN)
    return threshold, factors


def semaphore(threshold_mm_30min, breaks=SEMAPHORE_BREAKS):
    """0 rojo (umbral bajo: poca lluvia ya dispara), 1 amarillo, 2 verde. NaN threshold -> 255 (sin dato)."""
    threshold = np.asarray(threshold_mm_30min, dtype=np.float64)
    out = np.full(threshold.shape, 255, dtype=np.uint8)
    valid = np.isfinite(threshold)
    out[valid & (threshold < breaks[0])] = 0
    out[valid & (threshold >= breaks[0]) & (threshold < breaks[1])] = 1
    out[valid & (threshold >= breaks[1])] = 2
    return out


def explain(factors, threshold):
    """One factor-attributed sentence per sub-basin-level scalar inputs; for the assistant and the UI."""
    parts = [f"Umbral base {BASE_THRESHOLD_MM_30MIN:.0f} mm/30min en ladera sana"]
    labels = {"severity": "quema", "saturation": "lluvia previa", "concentration": "concentración del cauce", "moisture": "humedad NISAR"}
    for key, value in factors.items():
        reduction = (1 - float(value)) * 100
        if reduction > 1:
            parts.append(f"{labels.get(key, key)} lo reduce {reduction:.0f}%")
    parts.append(f"umbral efectivo {float(threshold):.1f} mm/30min")
    return "; ".join(parts) + "."
