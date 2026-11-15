"""Qualify inputs for a future fire-spread experiment; never infer a fire front from heat points.

This is an input audit, not an implementation of Rothermel or an operational predictor.
Air humidity, radar backscatter and sparse thermal anomalies cannot silently replace fuel moisture,
fuel models and time-stamped fire perimeters. Numerical spread output stays disabled.
"""
REQUIRED = {
    "fuel_model": "Modelo local de combustible, con equivalencias verificadas",
    "fuel_moisture": "Humedad de combustible vivo y muerto, con fecha y método",
    "initial_perimeter": "Perímetro o ignición inicial con hora y procedencia",
    "terrain_grid": "Elevación, pendiente y orientación en una grilla común",
    "wind_field": "Viento temporal y espacial adecuado al motor de propagación",
    "validation_perimeters": "Perímetros independientes con hora para evaluar la trayectoria",
}
UNITS = {"fuel_model": "categorical", "fuel_moisture": "%", "initial_perimeter": "geometry_utc",
         "terrain_grid": "m_deg", "wind_field": "m/s_deg_utc", "validation_perimeters": "geometry_utc"}

def audit_spread_inputs(inputs):
    """Only explicitly qualified, traceable inputs count; coarse context does not pass the gate.

    Completeness permits planning a research experiment only. It is not scientific approval,
    statistical validation or a claim of operational capability.
    """
    qualified, missing = [], []
    for key, label in REQUIRED.items():
        record = inputs.get(key, {})
        checks = (record.get("qualified_for_spread") is True,
                  bool(record.get("source")), record.get("units") == UNITS[key],
                  bool(record.get("time_reference")), bool(record.get("grid_reference")),
                  isinstance(record.get("sha256"), str) and len(record.get("sha256", "")) == 64
                  and all(c in "0123456789abcdef" for c in record.get("sha256", "")))
        if all(checks):
            qualified.append(key)
        else:
            missing.append(label)
    return {"status": "research_inputs_complete" if not missing else "blocked_missing_inputs",
            "research_inputs_complete": not missing, "operational": False,
            "spread_prediction_enabled": False, "qualified_inputs": qualified,
            "missing_inputs": missing,
            "reason": "Completar insumos no valida un modelo; se requiere evaluación temporal y por evento independiente."}
