"""Evidence tools. Each returns {"facts": numbers and short values, "sources": urls/paths, "text": sentences}.

Every number the assistant may utter must appear in `facts` of some tool result.
"""
import json
from pathlib import Path

from sarwatch.interpretation import describe, storage_bytes

ASF_USING = "https://nisar-docs.asf.alaska.edu/using-overview/"
GLOSSARY_PATH = Path("catalog/glosario.json")
DETECTION_REFERENCE = Path("catalog/detection_reference.json")
PREDICTION_REFERENCE = Path("catalog/prediction_reference.json")
POSTFIRE_REFERENCE = Path("catalog/postfire_reference.json")
AOI_SLUGS = {"Pantanal": "pantanal", "Región Metropolitana": "metropolitana", "Región de Valparaíso": "valparaiso"}


def _load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def tool_statistics(context):
    s = context["statistics"]
    facts = {"median_db": s["median_db"], "q25_db": s["q25_db"], "q75_db": s["q75_db"], "coverage_pct": None if s["coverage"] is None else round(100 * s["coverage"], 1), "pixels": s["pixels"], "before": context["before"], "after": context["after"], "polarization": context["polarization"], "region": context["region"]}
    return {"facts": facts, "sources": [context["source"]], "text": describe(context)}


def tool_quality(context):
    s = context["statistics"]
    pct = None if s["coverage"] is None else round(100 * s["coverage"], 1)
    text = f"La cobertura comparable del recorte es {pct} %: proporción de píxeles con dato técnico válido en ambas fechas. No es precisión, probabilidad ni certeza. Las máscaras del producto excluyen muestras inválidas; la interpretación ambiental sigue sin validar." if pct is not None else "No hay cobertura comparable para este par."
    return {"facts": {"coverage_pct": pct, "pixels": s["pixels"]}, "sources": [ASF_USING, context["source"]], "text": text}


def tool_detection(context):
    reference = _load(DETECTION_REFERENCE)
    slug = AOI_SLUGS.get(context["region"], context["region"])
    if not reference:
        return {"facts": {}, "sources": [], "text": "No hay una detección evaluada registrada para este lugar; no puedo cuantificar agua ni cambio."}
    water = (reference.get("water") or {}).get(slug)
    change = (reference.get("change") or {}).get(slug)
    facts, sources, parts = {}, ["docs/detection_benchmark.json"], []
    if water:
        lg = water["lightgbm"]
        facts.update({"water_f1_blocks": round(lg["spatial_f1"], 2) if lg["spatial_f1"] is not None else None, "water_f1_date": round(lg["temporal_f1"], 2) if lg["temporal_f1"] is not None else None, "water_test_date": lg["temporal_test_date"], "ki_mean_f1": round(water["thresholds"]["kittler_illingworth"]["mean_f1"], 2) if water["thresholds"]["kittler_illingworth"]["mean_f1"] is not None else None, "n_label_dates": water["thresholds"]["kittler_illingworth"]["n_dates"]})
        latest = next((a for a in reversed(water["areas"]) if a["date"] == context["after"]), water["areas"][-1])
        facts.update({"water_area_date": latest["date"], "water_area_lgbm_km2": None if latest["lightgbm_km2"] is None else round(latest["lightgbm_km2"], 1), "water_area_ki_km2": round(latest.get("ki_km2", latest["otsu_km2"]), 1), "water_area_label_km2": round(latest["label_km2"], 1)})
        parts.append(f"Agua abierta estimada el {latest['date']}: {facts['water_area_lgbm_km2']} km² con LightGBM y {facts['water_area_ki_km2']} km² con umbral Kittler-Illingworth; la etiqueta óptica Sentinel-2 marcó {facts['water_area_label_km2']} km². El clasificador alcanzó F1 {facts['water_f1_blocks']} en bloques retenidos y F1 {facts['water_f1_date']} en la fecha retenida ({facts['water_test_date']}). Mide agua abierta; no confirma una inundación ni detecta agua bajo vegetación.")
        sources.append(water["label_source"])
    if change:
        land = change["land"]
        facts.update({"change_land_pct": round(100 * ((land.get("increase") or 0) + (land.get("decrease") or 0)), 2), "change_water_increase_pct": round(100 * (change["permanent_water"].get("increase") or 0), 1) if change.get("permanent_water") else None, "change_alpha": change["alpha"], "change_before": change["pair"]["before"][:10], "change_after": change["pair"]["after"][:10]})
        parts.append(f"Entre {facts['change_before']} y {facts['change_after']}, el {facts['change_land_pct']} % de los píxeles de tierra cambió de forma estadísticamente significativa (prueba de Conradsen, α = {facts['change_alpha']}). La prueba detecta cambio de la señal radar; no identifica su causa ni confirma daño.")
        if facts.get("change_water_increase_pct") is not None:
            parts[-1] += f" Sobre agua permanente el aumento fue {facts['change_water_increase_pct']} %, atribuible a viento y oleaje, no a daño."
    if not parts:
        parts.append("No hay detección evaluada para este lugar.")
    return {"facts": facts, "sources": sources, "text": " ".join(parts)}


def tool_postfire(context):
    reference = _load(POSTFIRE_REFERENCE)
    if not reference or context.get("region") != "Región Metropolitana":
        return {"facts": {}, "sources": [], "text": "PostFuego solo está evaluado hoy para la Región Metropolitana (caso Quebrada Honda, Las Condes); no hay referencia para este lugar."}
    scenarios = reference.get("scenarios") or {}
    facts, parts = {}, []
    for key, scenario in scenarios.items():
        prefix = key
        facts[f"{prefix}_umbral_mediano_mm"] = scenario["median_threshold_mm_30min"]
        facts[f"{prefix}_umbral_minimo_mm"] = scenario["min_threshold_mm_30min"]
        if scenario.get("observed_30min_mm") is not None:
            facts[f"{prefix}_lluvia_observada_mm"] = scenario["observed_30min_mm"]
        parts.append(f"{scenario['label']}: umbral mediano {scenario['median_threshold_mm_30min']} mm en 30 minutos.")
    severity = reference.get("fire_severity_summary") or {}
    alta = severity.get("alta")
    facts["severidad_alta_pct"] = round(100 * alta, 1) if alta is not None else None
    severity_text = f" Severidad de quema observada: {facts['severidad_alta_pct']}% del área en clase alta (dNBR Sentinel-2)." if alta is not None else ""
    text = "PostFuego es una heurística no calibrada, no un modelo validado: dos eventos no entrenan un predictor. " + " ".join(parts) + severity_text
    return {"facts": facts, "sources": ["docs/postfire_benchmark.json", "docs/postfuego/01_problematica.md"], "text": text}


def tool_forecast(context):
    reference = _load(PREDICTION_REFERENCE)
    base = "Todavía no podemos predecir inundaciones, daños o cambios futuros con este conjunto."
    if not reference:
        return {"facts": {}, "sources": ["https://open-meteo.com/en/docs/flood-api"], "text": base + " No hay un modelo de riesgo validado."}
    facts = {"n_evaluations": reference.get("n_evaluations"), "persistence_mae_db": None if reference.get("mae_db") is None else round(reference["mae_db"], 2)}
    decision = reference.get("best_model") or {}
    models = reference.get("models_mae") or {}
    for name, mae in models.items():
        if mae is not None:
            facts[f"mae_{name}_db"] = round(mae, 2)
    text = base + f" Como referencia retrospectiva en Pantanal, repetir la mediana HH anterior produjo {facts['n_evaluations']} evaluaciones a unos 12 días con error absoluto medio {facts['persistence_mae_db']} dB."
    if decision.get("publishable"):
        facts["published_model"] = decision["model"]
        text += f" El modelo {decision['model']} superó a la persistencia en los pliegues disponibles, pero sigue siendo una referencia de la mediana del recorte, no un predictor de inundación."
    else:
        text += " Ningún modelo probado superó a la persistencia con intervalos calibrados, así que no se publica un pronóstico. Hace falta una serie más larga, etiquetas independientes y evaluación fuera del entrenamiento."
    return {"facts": facts, "sources": ["catalog/prediction_reference.json", "https://open-meteo.com/en/docs/flood-api"], "text": text}


def tool_colors(context):
    return {"facts": {"diff_range_db": 6, "intensity_min_db": -30, "intensity_max_db": 10}, "sources": [ASF_USING], "text": "En la vista de diferencia, azul indica menor respuesta del radar y naranja mayor respuesta en la fecha final; el tono claro queda cerca de cero (escala ±6 dB). En una fecha individual el color representa intensidad entre −30 y 10 dB. Transparente significa sin dato válido, no ausencia de cambio. Los colores no representan peligro ni agua confirmada."}


def tool_units(context):
    return {"facts": {"polarization": context["polarization"]}, "sources": [ASF_USING], "text": "dB es una escala logarítmica para expresar la respuesta del radar: convertimos potencia positiva con 10·log10. HH y HV son dos formas de emitir y recibir la señal (horizontal-horizontal y horizontal-vertical); no son tipos de desastre. Comparamos siempre el mismo canal entre fechas y no mezclamos HH con HV."}


def tool_cause(context):
    return {"facts": {}, "sources": [ASF_USING], "text": "El cambio de radar puede relacionarse con humedad del suelo, vegetación, geometría del terreno, construcciones, viento sobre el agua u otros procesos. Estos datos no permiten confirmar por sí solos inundación, incendio o daño. Hace falta comparar con observaciones independientes de esas fechas y revisar la coherencia espacial."}


def tool_usage(context):
    return {"facts": {}, "sources": ["docs/chile_y_mapas.md"], "text": "Elige el lugar y las fechas, compara la señal en el mapa y haz clic dentro de la capa coloreada para consultar un punto: verás su serie de valores en dB y podrás descargarla en CSV. Los perfiles cambian el nivel de detalle, no los datos."}


def tool_storage(context, area_km2=10000, resolution_m=20, dates=30):
    size = storage_bytes(area_km2, resolution_m, 2, dates)
    gb = round(size / 1e9, 1)
    return {"facts": {"area_km2": area_km2, "resolution_m": resolution_m, "dates": dates, "size_gb": gb}, "sources": ["docs/experiencia_asistente_y_prediccion.md"], "text": f"Para {area_km2:g} km² a {resolution_m} m, dos canales y {dates} fechas, las capas float32 sin comprimir ocuparían unos {gb} GB incluyendo pirámides. Es una estimación geométrica, no es un presupuesto de nube ni el tamaño de la misión; la compresión real debe medirse. Para cobertura mundial: catálogo global, procesamiento por zona solicitada y teselas, no descargar todo el archivo."}


def tool_glossary(term):
    glossary = _load(GLOSSARY_PATH) or {}
    key = next((k for k in glossary if k.lower() in term.lower()), None)
    if key is None:
        return {"facts": {}, "sources": [], "text": ""}
    entry = glossary[key]
    return {"facts": {"term": key}, "sources": [entry.get("source", ASF_USING)], "text": f"{key}: {entry['definition']}"}


def tool_sources(context):
    facts = tool_statistics(context)["facts"]
    return {"facts": facts, "sources": [context["source"], "catalog/"], "text": describe(context) + " Procedencia: los identificadores oficiales de las escenas y sus checksums están en el panel de calidad y en el catálogo del proyecto."}
