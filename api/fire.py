"""Biobío fire story: serves the pack written by scripts/build_fire_story.py and a live wind/humidity forecast.

The pack (catalog/fire_story/) holds every figure and overlay; nothing is computed here. The forecast is the
only live call: it is model output for the next hours, labelled as such, never an observation of a fire.
"""
import json
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from weather import fetch_fire_forecast

router = APIRouter(prefix="/api/fire", tags=["fire"])
PACK = Path("catalog/fire_story")


@router.get("/vegetation-sample")
def get_vegetation_sample():
    path = Path("catalog/biobio_vegetation_sample.json")
    if not path.is_file():
        raise HTTPException(503, "Muestra de vegetación no disponible")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _story(modified):
    return json.loads((PACK / "story.json").read_text(encoding="utf-8"))


def story():
    path = PACK / "story.json"
    if not path.is_file():
        raise HTTPException(503, "Historia de incendios no generada; ejecutar scripts/build_fire_story.py")
    return _story(path.stat().st_mtime_ns)


@router.get("/story")
def get_story(part: str = Query("summary", pattern="^(summary|before|during|after)$")):
    """`summary` is small (sources, counts, metrics); each part carries its own cells or overlays."""
    data = story()
    if part != "summary":
        return data[part]
    before, during, after = data["before"], data["during"], data["after"]
    return {"generated_utc": data["generated_utc"], "place": data["place"], "sources": data["sources"],
            "before": {k: before[k] for k in ("model", "horizon_days", "passes", "held_out_dates", "latest_date", "benchmark", "limits")},
            "during": {k: during[k] for k in ("window_utc", "cell_km", "confident_detections", "cells_hot", "by_day", "limits")},
            "after": {k: after[k] for k in ("area_km2", "dates", "limits")} | {"radar_dates": [layer["date"] for layer in after["radar"]], "label": after["severity"]["label"]}}


@router.get("/asset/{name}")
def get_asset(name: str):
    """Overlay PNGs of the pack; only names the pack itself lists are served."""
    after = story()["after"]
    allowed = {layer["png"] for layer in after["radar"]} | {after["severity"]["png"]}
    if name not in allowed:
        raise HTTPException(404, "Capa desconocida")
    return FileResponse(PACK / name, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@lru_cache(maxsize=256)
def _forecast(lat, lon, hour_bucket):
    return fetch_fire_forecast(lat, lon)


@router.get("/forecast")
def get_forecast(lat: float = Query(..., ge=-56, le=-17), lon: float = Query(..., ge=-76, le=-66)):
    """Wind, gusts, air humidity, temperature and vapour pressure deficit for the next 48 h at a point in Chile."""
    try:
        return _forecast(round(lat, 2), round(lon, 2), int(time.time() // 3600))
    except Exception as exc:
        raise HTTPException(502, f"Pronóstico no disponible ({type(exc).__name__})")


@router.get("/propagation-readiness")
def get_propagation_readiness():
    path = Path("catalog/fire_propagation_readiness.json")
    if not path.is_file():
        raise HTTPException(503, "Auditoría de propagación pendiente")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/sector-context")
def get_sector_context(cell_id: int = Query(..., ge=0), time_utc: str = Query(..., max_length=32)):
    from sarwatch.ml.sector_context import context_for_cell
    try:
        return context_for_cell(story(), cell_id, time_utc)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

@router.get("/vina-2024")
def get_vina_2024():
    path=Path("catalog/vina_2024/story.json")
    if not path.is_file():
        raise HTTPException(503, "Comparación Sentinel-2 de 2024 en preparación")
    return json.loads(path.read_text(encoding="utf-8"))

@router.get("/vina-2024/asset/{name}")
def get_vina_asset(name: str):
    report=get_vina_2024()
    if name not in report["assets_sha256"]:
        raise HTTPException(404, "Capa óptica desconocida")
    return FileResponse(Path("catalog/vina_2024")/name,media_type="image/png")


@router.get("/forecast-sectors")
def get_forecast_sectors(lat: float=Query(...,ge=-38.65,le=-36), lon: float=Query(...,ge=-74,le=-70.85), hour: int=Query(0,ge=0,le=47)):
    import math
    from sarwatch.ml.sector_context import spatial_context
    forecast=get_forecast(lat,lon)
    h=forecast["hourly"]
    if hour>=len(h["time"]):
        raise HTTPException(404,"Hora no disponible")
    direction=h["wind_direction_10m"][hour];speed=h["wind_speed_10m"][hour]
    if direction is None or speed is None or not math.isfinite(direction) or not math.isfinite(speed):
        raise HTTPException(404,"Sin viento válido para esa hora")
    report=spatial_context(story(),lon,lat,direction,speed)
    report.update({"time_utc":h["time"][hour],"weather_source":"Open-Meteo pronóstico de viento a 10 m, no observación en terreno", "wind_from_deg":direction,"wind_speed_kmh":speed,"retrieved_utc":forecast["retrieved_utc"]})
    return report


@router.get("/official-perimeters")
def get_official_perimeters():
    path=Path("catalog/official_fire_perimeters/manifest.json")
    if not path.is_file():
        raise HTTPException(503,"Inventario de perímetros en preparación")
    return json.loads(path.read_text(encoding="utf-8"))

@router.get("/official-perimeters/{index}")
def get_official_perimeter(index: int):
    report=get_official_perimeters()
    if not 0<=index<len(report["products"]):
        raise HTTPException(404,"Observación no disponible")
    return FileResponse(Path("catalog/official_fire_perimeters")/report["products"][index]["asset"],media_type="application/geo+json")


@lru_cache(maxsize=256)
def _rainfall(lat, lon, day_bucket):
    from weather import rainfall_context
    return rainfall_context(lat, lon)


@router.get("/rainfall-context")
def get_rainfall_context(lat: float = Query(..., ge=-56, le=-17), lon: float = Query(..., ge=-76, le=-66)):
    try:
        return _rainfall(round(lat, 2), round(lon, 2), int(time.time() // 86400))
    except Exception:
        raise HTTPException(502, "Historial de lluvia no disponible")
