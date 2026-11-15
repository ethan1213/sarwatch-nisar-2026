"""Experimental gross fire CO2 estimate, IPCC 2006 AFOLU Eq 2.27, Tables 2.4/2.5.

Source: https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_02_Ch2_Generic.pdf
Consumption uncertainties are SE; emission-factor uncertainties are SD. The envelope below
is sensitivity to +/- one tabulated uncertainty, NOT a confidence interval. dNBR scaling and
WorldCover-to-fuel mapping are engineering assumptions, not IPCC recommendations.
"""
import numpy as np

SOURCE = "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_02_Ch2_Generic.pdf"
SEVERITY_FACTORS = {1: 0.15, 2: 0.4, 3: 0.7, 4: 1.0}
# WorldCover: (label, consumption t DM/ha, SE, emission g/kg, SD)
FUELS = {10: ("bosque templado (supuesto local)", 50.4, 53.7, 1569., 131.),
         20: ("matorral (factor gaseoso de sabana, supuesto)", 14.3, 9., 1613., 95.),
         30: ("pastizal/sabana media-tardía (supuesto)", 10., 10.1, 1613., 95.)}
LIMITATIONS = [
    "Estimación experimental de CO₂ bruto liberado durante la combustión; no medición atmosférica ni balance neto posterior.",
    "Sin calibración ni validación de terreno en Chile; no utilizable como inventario certificado o alerta operativa.",
    "dNBR no demuestra un incendio por sí solo; se requiere perímetro y fecha independientes.",
    "Factores por severidad y equivalencias WorldCover/combustible son supuestos propios.",
    "Rango de sensibilidad con SE de consumo y SD del factor gaseoso; no intervalo de confianza.",
    "No incluye recuperación, carbono del suelo, turba, emisiones diferidas ni clases sin factor asignado."]


def co2_emitted(severity, worldcover, pixel_area_m2, factors=None):
    severity, cover = np.asarray(severity), np.asarray(worldcover)
    if severity.shape != cover.shape:
        raise ValueError("Severidad y cobertura deben compartir grilla")
    if not np.isfinite(pixel_area_m2) or pixel_area_m2 <= 0:
        raise ValueError("Área de píxel positiva en m² requerida")
    factors = dict(SEVERITY_FACTORS if factors is None else factors)
    if set(factors) != {1, 2, 3, 4} or any(not np.isfinite(v) or not 0 <= v <= 1 for v in factors.values()):
        raise ValueError("Se requieren factores finitos 0–1 para clases 1–4")
    valid_severity = np.isin(severity, [0, 1, 2, 3, 4])
    burned = valid_severity & (severity > 0)
    covered = burned & np.isin(cover, list(FUELS))
    rows = []
    for code, (name, consumption, se, emission, sd) in FUELS.items():
        for level, scale in factors.items():
            n = int(((severity == level) & (cover == code)).sum())
            if not n:
                continue
            area = n * pixel_area_m2 / 10000
            amount = area * scale * consumption * emission / 1000
            low = area * scale * max(0., consumption - se) * max(0., emission - sd) / 1000
            high = area * scale * (consumption + se) * (emission + sd) / 1000
            rows.append({"worldcover": code, "fuel": name, "severity": level, "area_ha": area,
                         "co2_t": amount, "sensitivity_low_t": low, "sensitivity_high_t": high})
    n_burned = int(burned.sum())
    return {"method": "IPCC 2006 ecuación 2.27 + supuestos experimentales", "source": SOURCE,
            "severity_factors_assumption": factors, "rows": rows,
            "total_co2_t": sum(r["co2_t"] for r in rows),
            "sensitivity_low_t": sum(r["sensitivity_low_t"] for r in rows),
            "sensitivity_high_t": sum(r["sensitivity_high_t"] for r in rows),
            "burned_signal_area_ha": n_burned * pixel_area_m2 / 10000,
            "unmodeled_burned_area_ha": int((burned & ~covered).sum()) * pixel_area_m2 / 10000,
            "modeled_burned_fraction": float(covered.sum() / n_burned) if n_burned else None,
            "severity_valid_fraction": float(valid_severity.mean()), "limitations": LIMITATIONS,
            "validation_status": "experimental_unvalidated", "operational": False}
