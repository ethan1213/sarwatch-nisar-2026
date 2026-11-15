"""SARWatch API: FastAPI backend serving the same verified JSON/CSV outputs the Streamlit app reads,
as JSON over HTTP for the React frontend in web/. No new computation happens here - every number
still comes from the scripts in scripts/ and the files they write to catalog/ and docs/. This process
never touches NISAR HDF5, Earthdata credentials, or GCP billing; it only reads already-generated files.
"""
import gzip
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from api.pantanal import router as pantanal_router, create_site_router
from api.studies import router as studies_router
from api.chile import router as chile_router
from api.fire import router as fire_router

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "catalog/global/coverage_1deg.json"
INDEX = ROOT / "catalog/global/gcov_index.csv.gz"
WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title="SARWatch API", version="0.1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"], allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(pantanal_router)
app.include_router(create_site_router("metropolitana"))
app.include_router(create_site_router("valparaiso"))
app.include_router(studies_router)
app.include_router(chile_router)
app.include_router(create_site_router("concepcion_penco"))
app.include_router(fire_router)


@lru_cache(maxsize=1)
def load_coverage():
    if not COVERAGE.is_file():
        return None
    return json.loads(COVERAGE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_index():
    if not INDEX.is_file():
        return None
    with gzip.open(INDEX, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    frame["date"] = frame["time_start"].str[:10]
    return frame


def cell_to_polygon(cell):
    lon, lat = cell["lon"], cell["lat"]
    ring = [[lon, lat], [lon + 1, lat], [lon + 1, lat + 1], [lon, lat + 1], [lon, lat]]
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}, "properties": {"dates": cell["dates"], "granules": cell["granules"], "geometries": cell["geometries"], "first_date": cell["first_date"], "last_date": cell["last_date"]}}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/world/meta")
def world_meta():
    data = load_coverage()
    if data is None:
        raise HTTPException(503, "Índice mundial no generado todavía; ejecutar scripts/build_global_catalog.py")
    return {"generated_utc": data["generated_utc"], "granules_indexed": data["granules_indexed"], "short_name": data.get("short_name"), "metric": data.get("metric"), "n_cells": len(data["cells"])}


@app.get("/api/world/cells")
def world_cells():
    """GeoJSON FeatureCollection of every indexed 1-degree cell. ~35k features, ~4-7 MB; the frontend
    colours them client-side (see web/src/colorScale.js, mirroring sarwatch/views/world.py::_color)."""
    data = load_coverage()
    if data is None:
        raise HTTPException(503, "Índice mundial no generado todavía")
    return {"type": "FeatureCollection", "features": [cell_to_polygon(c) for c in data["cells"]]}


@app.get("/api/world/point")
def world_point(lon: float = Query(..., ge=-180, le=180), lat: float = Query(..., ge=-90, le=90)):
    """Same lookup as the Streamlit world view's point click: every repeat-orbit geometry touching
    (lon, lat), with its comparable date count, date range and estimated download size."""
    frame = load_index()
    if frame is None:
        raise HTTPException(503, "Índice de granulos no generado todavía")
    hit = frame[(frame.west <= lon) & (frame.east >= lon) & (frame.south <= lat) & (frame.north >= lat)].copy()
    if hit.empty:
        return {"lon": lon, "lat": lat, "n_granules": 0, "geometries": []}
    hit["geometry"] = hit.track.astype(str) + "_" + hit.direction.astype(str) + "_" + hit.frame.astype(str)
    repeats = hit.groupby("geometry").agg(n_dates=("date", "nunique"), first_date=("date", "min"), last_date=("date", "max"), estimated_gb=("size_mib", lambda s: round(float(s.sum()) / 1024, 1))).sort_values("n_dates", ascending=False)
    return {"lon": lon, "lat": lat, "n_granules": int(len(hit)), "n_geometries": int(len(repeats)), "geometries": [{"geometry": idx, **row} for idx, row in repeats.reset_index().set_index("geometry").to_dict("index").items()]}


# Serve the built React app (web/dist, produced by `npm run build`) at the root, after the build
# exists. In local dev, run `npm run dev` in web/ separately and leave this unmounted.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
