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
