"""Pantanal (flood/water-change) view: FastAPI port of the Streamlit flow in app.py's
Pantanal branch. Reuses the same manifest, detection masks, catalogs and the local
rule-based assistant - no new computation, no synthetic data. Not yet ported from app.py:
the native-CRS plotly detail charts and the raw provenance JSON dump (st.json(scene)).
"""
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import rasterio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.raster import categorical_rgba, png_data_url, sar_overlay
from sarwatch.assistant.chat import answer as chat_answer
from sarwatch.detections import WATER_METHODS, detection_reference, read_mask, water_fraction, water_mask_paths, water_sentence
from sarwatch.interpretation import GUIDES, PROFILES, describe, summarize
from sarwatch.repository import RasterRepository
from science import difference

def create_site_router(slug):
    BASE_ROOT = Path(os.environ.get("DATA_DIR", "data")).resolve()
    ROOT = BASE_ROOT if slug == "pantanal" else BASE_ROOT / slug
    REGION = {"pantanal": "Pantanal", "metropolitana": "Región Metropolitana", "valparaiso": "Región de Valparaíso", "concepcion_penco": "Concepción y Penco"}[slug]
    AOI_SLUG = slug
    MODEL_NAMES = {"climatology": "promedio de las fechas anteriores", "persistence": "repetir el valor anterior", "ridge": "regresión lineal"}

    router = APIRouter(prefix=f"/api/{slug}", tags=[slug])
    repository = RasterRepository(ROOT)


    @lru_cache(maxsize=1)
    def manifest():
        try:
            return repository.manifest()
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(503, f"{REGION} sin capas procesadas: {exc}")


    def scenes():
        return manifest()["scenes"]


    def scene_or_404(index):
        rows = scenes()
        if not (0 <= index < len(rows)):
            raise HTTPException(404, "Índice de escena fuera de rango")
        return rows[index]


    @lru_cache(maxsize=4)
    def read_layer(path_str):
        with rasterio.open(path_str) as src:
            return src.read(1), src.transform, str(src.crs)


    def _load_catalog(name):
        path = Path("catalog") / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


    def build_context(before_idx, after_idx, pol):
        if pol not in ("HH", "HV"):
            raise HTTPException(400, "Polarización inválida")
        before, after = scene_or_404(before_idx), scene_or_404(after_idx)
        a, transform, crs = read_layer(str(repository.product_path(before["products"][pol])))
        b, transform_b, crs_b = read_layer(str(repository.product_path(after["products"][pol])))
        if a.shape != b.shape or transform != transform_b or crs != crs_b:
            raise HTTPException(409, "Las grillas no son comparables")
        context = {
            "region": REGION,
            "before": before["fecha_observacion"][:10],
            "after": after["fecha_observacion"][:10],
            "polarization": pol,
            "statistics": summarize(a, b),
            "source": after["url_metadatos"],
        }
        return a, b, transform, crs, context


    def evidence_items(after_date, polarization, statistics):
        """Mirrors sarwatch/views/components.py::story's item list, without the st.markdown rendering."""
        detection = _load_catalog("detection_reference.json") or {}
        forecast = _load_catalog("prediction_reference.json") or {}
        items = []
        if statistics.get("median_db") is None:
            items.append({"level": "ausente", "text": "No hay píxeles comparables entre estas fechas; no describimos el cambio."})
        else:
            move = "aumentó" if statistics["median_db"] > 0 else "disminuyó" if statistics["median_db"] < 0 else "se mantuvo"
            items.append({"level": "observado", "text": f"La respuesta típica del radar ({polarization}) {move}: diferencia mediana {statistics['median_db']:+.2f} dB sobre el {100 * statistics['coverage']:.0f} % del recorte con dato válido en ambas fechas."})
        water = (detection.get("water") or {}).get(AOI_SLUG)
        if water:
            area = next((item for item in water["areas"] if item["date"] == after_date), None)
            lg = water["lightgbm"]
            if area and area.get("lightgbm_km2") is not None:
                items.append({"level": "estimado", "text": f"Agua abierta estimada el {after_date}: {area['lightgbm_km2']:.1f} km² (clasificador evaluado contra Sentinel-2: F1 {lg['spatial_f1']:.2f} en bloques retenidos, {lg['temporal_f1']:.2f} en la fecha retenida). No incluye agua bajo vegetación."})
        change = (detection.get("change") or {}).get(AOI_SLUG)
        if change:
            land = change["land"]
            pct = 100 * ((land.get("increase") or 0) + (land.get("decrease") or 0))
            items.append({"level": "estimado", "text": f"El {pct:.2f} % de los píxeles de tierra cambió de forma estadísticamente significativa entre ambas fechas (prueba de Conradsen, α = {change['alpha']}). Sobre el mar y embalses el cambio refleja viento y oleaje."})
        items.append({"level": "hipotesis", "text": "Un cambio de señal puede deberse a humedad, vegetación, construcción, viento sobre el agua o geometría. La causa no se confirma con radar solo."})
        decision = (forecast.get("best_model") or {}) if slug == "pantanal" else {}
        if decision.get("publishable"):
            items.append({"level": "estimado", "text": f"Pronóstico de referencia disponible para la mediana del recorte ({MODEL_NAMES.get(decision['model'], decision['model'])}); no es un pronóstico de inundación."})
        else:
            items.append({"level": "ausente", "text": "No hay pronóstico publicable: ningún modelo superó a repetir el valor anterior con intervalos calibrados. No anticipamos inundaciones ni daños."})
        items.append({"level": "ausente", "text": "Falta validación con observaciones de terreno y pruebas con personas de cada perfil."})
        return items


    @router.get("/manifest")
    def get_manifest():
        data = manifest()
        return {
            "region": REGION,
            "bbox_wgs84": data["bbox_wgs84"],
            "quality_status": data["quality_status"],
            "scenes": [{"index": i, "fecha": s["fecha_observacion"][:10], "finite_positive_fraction": s["finite_positive_fraction"]} for i, s in enumerate(scenes())],
        }


    @router.get("/layer")
    def get_layer(before: int, after: int, pol: str = "HH", mode: str = "diff"):
        if mode not in ("diff", "single"):
            raise HTTPException(400, "mode debe ser 'diff' o 'single'")
        a, b, transform, crs, context = build_context(before, after, pol)
        values = difference(a, b) if mode == "diff" else b
        rgba, bounds = sar_overlay(values, transform, crs, mode == "diff")
        return {"bounds": bounds, "png_data_url": png_data_url(rgba), "context": context, "describe": describe(context), "resolution_m": abs(transform.a), "n_scenes": len(scenes())}


    @router.get("/water-methods")
    def get_water_methods(after: int):
        scene = scene_or_404(after)
        date = scene["fecha_observacion"][:10]
        available = water_mask_paths(ROOT, date) if slug == "pantanal" else {}
        return {"date": date, "methods": [{"key": m, "label": WATER_METHODS[m]} for m in available]}


    @router.get("/water-layer")
    def get_water_layer(after: int, pol: str = "HH", method: str = "lgbm"):
        if pol not in ("HH", "HV"):
            raise HTTPException(400, "Polarización inválida")
        scene = scene_or_404(after)
        date = scene["fecha_observacion"][:10]
        available = water_mask_paths(ROOT, date) if slug == "pantanal" else {}
        if method not in available:
            raise HTTPException(404, "Método no disponible para esta fecha")
        mask, mt, mc, tags = read_mask(available[method])
        b, transform, crs = read_layer(str(repository.product_path(scene["products"][pol])))
        if (mt, mc, mask.shape) != (transform, crs, b.shape):
            raise HTTPException(409, "La máscara no comparte la grilla SAR; no se muestra")
        rgba, bounds = categorical_rgba(mask, mt, mc, "water")
        return {
            "bounds": bounds,
            "png_data_url": png_data_url(rgba),
            "fraction": water_fraction(mask),
            "sentence": water_sentence(detection_reference(), AOI_SLUG, method),
            "method_tag": tags.get("method", ""),
            "status_tag": tags.get("status", ""),
        }


    @router.get("/point-series")
    def get_point_series(lon: float, lat: float, pol: str = "HH"):
        if pol not in ("HH", "HV"):
            raise HTTPException(400, "Polarización inválida")
        data = manifest()
        west, south, east, north = data["bbox_wgs84"]
        if not (west <= lon <= east and south <= lat <= north):
            raise HTTPException(400, "Punto fuera del área de estudio")
        rows = repository.point_series(scenes(), pol, lon, lat)
        for row in rows:
            if row["dB"] is None or math.isnan(row["dB"]):
                row["dB"] = None
        return {"rows": rows}


    @router.get("/reading")
    def get_reading(before: int, after: int, pol: str = "HH", profile: str = "Público general"):
        if profile not in PROFILES:
            raise HTTPException(400, "Perfil inválido")
        _, _, _, _, context = build_context(before, after, pol)
        return {"context": context, "describe": describe(context), "guide": GUIDES[profile], "evidence": evidence_items(context["after"], pol, context["statistics"])}


    @router.get("/prediction-reference")
    def get_prediction_reference():
        if slug != "pantanal":
            raise HTTPException(404, "No hay pronóstico SAR evaluado para Chile")
        data = _load_catalog("prediction_reference.json")
        if not data:
            raise HTTPException(404, "Sin referencia de pronóstico publicada todavía")
        return data


    @lru_cache(maxsize=64)
    def _cached_weather(lat, lon, start, end):
        from weather import fetch_weather

        return fetch_weather(lat, lon, start, end)


    @router.get("/weather")
    def get_weather(lat: float, lon: float, mode: str = "historical", start: Optional[str] = None, end: Optional[str] = None):
        if mode == "historical" and not (start and end):
            raise HTTPException(400, "Se requieren start y end para el modo histórico")
        try:
            result = _cached_weather(round(lat, 3), round(lon, 3), start if mode == "historical" else None, end if mode == "historical" else None)
        except Exception as exc:
            raise HTTPException(502, f"Meteorología no disponible ({type(exc).__name__})")
        return result


    class ChatRequest(BaseModel):
        question: str = Field(min_length=1, max_length=1000)
        before: int
        after: int
        polarization: str = "HH"
        profile: str = "Público general"


    @router.post("/assistant")
    def post_assistant(body: ChatRequest):
        if body.profile not in PROFILES:
            raise HTTPException(400, "Perfil inválido")
        _, _, _, _, context = build_context(body.before, body.after, body.polarization)
        result = chat_answer(body.question, context, body.profile)
        if not result.verified:
            raise HTTPException(503, "La respuesta no superó el verificador de evidencia; consulta las fuentes del panel")
        return {"text": result.text, "sources": result.sources, "intent": result.intent, "generator": result.generator, "verified": result.verified}

    return router


router = create_site_router("pantanal")
