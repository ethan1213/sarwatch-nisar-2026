"""Read-only experimental and thermal outputs for the React client."""
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException

from api.raster import categorical_rgba, png_data_url, sar_overlay
from sarwatch.detections import change_mask_path, change_sentence, detection_reference, display_grid
from sarwatch.postfire import scenario_sentence

router = APIRouter(prefix="/api/study", tags=["studies"])
DATA = Path(os.environ.get("DATA_DIR", "data"))
SITES = {"pantanal", "metropolitana", "valparaiso"}


def site_root(slug):
    if slug not in SITES:
        raise HTTPException(404, "Sitio desconocido")
    return DATA if slug == "pantanal" else DATA / slug


def catalog(name):
    path = Path("catalog") / name
    if not path.is_file():
        raise HTTPException(503, "Resultados no generados todavía")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{slug}/impacts")
def impacts(slug: str):
    site_root(slug)
    if slug != "metropolitana":
        raise HTTPException(404, "Sin estimación de impactos para este sitio")
    return catalog("fire_impacts_reference.json")


@router.get("/{slug}/postfire")
def postfire(slug: str):
    site_root(slug)
    if slug != "metropolitana":
        raise HTTPException(404, "Sin referencia PostFuego para este sitio")
    return catalog("postfire_reference.json")


@router.get("/{slug}/overlay")
def overlay(slug: str, kind: str = "change", scenario: str = "octubre"):
    root = site_root(slug)
    if kind == "change":
        path = change_mask_path(root)
        caption = change_sentence(detection_reference(), slug)
    elif kind == "postfire" and slug == "metropolitana":
        if scenario not in {"enero", "octubre", "actual"}:
            raise HTTPException(400, "Escenario inválido")
        path = root / "postfire" / f"semaforo_{scenario}.tif"
        caption = scenario_sentence(catalog("postfire_reference.json"), scenario)
    elif kind == "concentration" and slug == "metropolitana":
        path = root / "postfire/relative_concentration.tif"
        caption = "Índice relativo experimental 0–1. No profundidad ni ruta segura; sin validación de terreno."
    else:
        raise HTTPException(400, "Capa no disponible para este sitio")
    if path is None or not path.is_file():
        raise HTTPException(404, "Ráster no generado")
    with rasterio.open(path) as src:
        values = src.read(1)
        transform, crs = src.transform, src.crs
    if kind == "change":
        rgba, bounds = categorical_rgba(values, transform, crs, "change")
    elif kind == "postfire":
        grid, corners = display_grid(values, transform, crs)
        (south, west), (north, east) = corners
        bounds = dict(south=south, west=west, north=north, east=east)
        rgba = np.zeros(grid.shape + (4,), dtype="uint8")
        for code, color in {0: (198, 40, 40, 215), 1: (212, 160, 23, 210), 2: (46, 125, 50, 190)}.items():
            rgba[grid == code] = color
    else:
        rgba, bounds = sar_overlay(values * 12 - 6, transform, crs, True)
    return {"png_data_url": png_data_url(rgba), "bounds": bounds, "sentence": caption}


@router.get("/{slug}/thermal")
def thermal(slug: str):
    root = site_root(slug)
    reference = catalog("thermal_reference.json").get("aois", {}).get(slug)
    folder = root / "thermal"
    available = (folder / "cube.npz").is_file()
    zones_path = folder / "zones.json"
    zones = json.loads(zones_path.read_text(encoding="utf-8")) if zones_path.is_file() else None
    return {"reference": reference, "cells_available": available,
            "radar_dates": zones.get("sar_dates", []) if zones else [],
            "current_manifest": json.loads((folder / "manifest.json").read_text(encoding="utf-8")) if available else None,
            "limitation": "SAR no mide temperatura. Un foco térmico no confirma un incendio ni su área. No se publica predicción de focos."}


@lru_cache(maxsize=3)
def thermal_cube(slug):
    folder = site_root(slug) / "thermal"
    if not (folder / "cube.npz").is_file():
        raise HTTPException(503, "Faltan los rásteres térmicos locales; el resumen histórico sigue disponible")
    with np.load(folder / "cube.npz") as data:
        return {key: data[key] for key in data.files}


@router.get("/{slug}/thermal-cells")
def thermal_cells(slug: str, layer: str = "focos"):
    cube = thermal_cube(slug)
    codes = cube["mask"].astype(int)
    codes = np.where((codes >= 30) & (codes <= 35), codes - 20, codes)
    if layer in {"focos", "confiables"}:
        hot = np.isin(codes, (10, 11, 12, 13, 14, 15) if layer == "focos" else (10, 11, 13))
        values = hot.sum(axis=0).astype(float)
        units = "detecciones"
    elif layer in {"hv_last", "hv_change", "elevacion_m", "pendiente_grados"}:
        path = site_root(slug) / "thermal/zones.json"
        if not path.is_file():
            raise HTTPException(503, "Cruce SAR/DEM por celda aún no generado")
        zones = json.loads(path.read_text(encoding="utf-8"))
        if layer.startswith("hv"):
            usable = [r for r in zones["radar"] if any(v is not None for v in r["hv_db"])]
            if not usable:
                raise HTTPException(404, "Sin radar válido en estas celdas")
            last = np.array(usable[-1]["hv_db"], dtype=float)
            values = last if layer == "hv_last" else last - np.array(usable[0]["hv_db"], dtype=float)
            if layer == "hv_change" and len(usable) < 2:
                raise HTTPException(404, "Se requieren dos fechas válidas para diferencia")
            units = "dB · fechas SAR indicadas, no simultáneas al térmico"
        else:
            values = np.array(zones["static"][layer], dtype=float)
            units = "m" if layer == "elevacion_m" else "grados"
        values = values.reshape(cube["lat"].shape)
    elif layer in {"bt_mir", "bt_tir", "lst"}:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            values = np.nanmax(cube[layer], axis=0) - 273.15
        units = "°C · máximo del período"
    else:
        raise HTTPException(400, "Capa térmica inválida")
    features = []
    for r in range(values.shape[0]):
        for c in range(values.shape[1]):
            ring = [[float(cube["corner_lon"][rr, cc]), float(cube["corner_lat"][rr, cc])] for rr, cc in ((r,c),(r,c+1),(r+1,c+1),(r+1,c),(r,c))]
            value = float(values[r, c]) if np.isfinite(values[r,c]) else None
            features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                             "properties": {"value": value, "row": r, "col": c, "units": units}})
    return {"type": "FeatureCollection", "features": features}
