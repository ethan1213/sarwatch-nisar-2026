"""Viewer access to evaluated detection products (water and change masks). Runtime-safe: no ML libraries."""
import json
from pathlib import Path

import folium
import numpy as np
import rasterio
from rasterio.transform import array_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject

WATER_METHODS = {"lgbm": "Agua estimada · LightGBM", "ki": "Agua estimada · umbral Kittler-Illingworth", "otsu": "Agua estimada · umbral Otsu (referencia débil)"}
CHANGE_LABEL = "Cambio significativo · prueba de Conradsen"
REFERENCE_PATH = Path("catalog/detection_reference.json")


def detection_reference():
    if REFERENCE_PATH.is_file():
        return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return None


def water_mask_paths(root, date):
    folder = Path(root) / "detections"
    return {method: folder / f"{date}_water_{method}.tif" for method in WATER_METHODS if (folder / f"{date}_water_{method}.tif").is_file()}


def change_mask_path(root):
    folder = Path(root) / "detections"
    matches = sorted(folder.glob("*_change_conradsen.tif")) if folder.is_dir() else []
    return matches[-1] if matches else None


def read_mask(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, str(src.crs), dict(src.tags())


def display_grid(mask, transform, crs, nodata=255, size=600):
    """Nearest-neighbour reprojection of a categorical mask to WGS84 for display only."""
    height, width = mask.shape
    bounds = array_bounds(height, width, transform)
    dst_transform, w, h = calculate_default_transform(crs, "EPSG:4326", width, height, *bounds, dst_width=size, dst_height=size)
    output = np.full((h, w), nodata, dtype=mask.dtype)
    reproject(mask, output, src_transform=transform, src_crs=crs, src_nodata=nodata, dst_transform=dst_transform, dst_crs="EPSG:4326", dst_nodata=nodata, resampling=Resampling.nearest)
    west, south, east, north = array_bounds(h, w, dst_transform)
    return output, [[south, west], [north, east]]


def image_overlay(rgba, bounds, name, opacity=1.0):
    """RGBA uint8 image in WGS84 as a Leaflet overlay with the colours exactly as given.

    folium's own mercator_project returns floats and then rescales every channel to its maximum,
    which shifts hues (orange turns yellow) and makes semi-transparent layers opaque. The projection
    is done here and cast back to uint8 so the legend matches the map.
    """
    from folium.utilities import mercator_transform
    (south, _), (north, _) = bounds
    projected = mercator_transform(rgba, (south, north), origin="upper")
    exact = np.clip(np.rint(projected), 0, 255).astype("uint8")
    return folium.raster_layers.ImageOverlay(exact, bounds=bounds, name=name, opacity=opacity, mercator_project=False)


def categorical_overlay(mask, transform, crs, kind, name):
    """Water: class 1 in teal. Change: 1 decrease in blue, 2 increase in orange. Everything else transparent."""
    grid, bounds = display_grid(mask, transform, crs)
    rgba = np.zeros(grid.shape + (4,), dtype="uint8")
    if kind == "water":
        rgba[grid == 1] = (23, 112, 140, 200)
    else:
        rgba[grid == 1] = (32, 91, 135, 210)
        rgba[grid == 2] = (198, 96, 28, 210)
    return image_overlay(rgba, bounds, name)


def water_fraction(mask):
    valid = mask != 255
    return float((mask[valid] == 1).mean()) if valid.any() else None


def change_summary(mask):
    valid = mask != 255
    n = int(valid.sum())
    return {"n": n, "decrease": float((mask[valid] == 1).mean()) if n else None, "increase": float((mask[valid] == 2).mean()) if n else None}


def water_sentence(reference, aoi, method):
    """Plain-language evaluation sentence for a water mask, or an honest fallback."""
    block = ((reference or {}).get("water") or {}).get(aoi)
    if not block:
        return "Esta capa no tiene evaluación registrada; no se puede afirmar su exactitud."
    if method == "lgbm":
        spatial = block["lightgbm"]["spatial_f1"]
        temporal = block["lightgbm"]["temporal_f1"]
        return f"Evaluado contra agua óptica Sentinel-2: F1 {spatial:.2f} en bloques retenidos y F1 {temporal:.2f} en la fecha retenida ({block['lightgbm']['temporal_test_date']}). Detecta agua abierta; no detecta agua bajo vegetación ni confirma inundación."
    key = {"ki": "kittler_illingworth", "otsu": "otsu"}.get(method, method)
    scores = block["thresholds"].get(key)
    if not scores or scores.get("mean_f1") is None:
        return "Método sin evaluación registrada."
    label = "Kittler-Illingworth" if key == "kittler_illingworth" else "Otsu"
    return f"Umbral {label} evaluado contra agua óptica Sentinel-2: F1 medio {scores['mean_f1']:.2f} en {scores['n_dates']} fechas. Agua abierta estimada; no confirma inundación ni agua bajo vegetación."


def change_sentence(reference, aoi):
    block = ((reference or {}).get("change") or {}).get(aoi)
    if not block:
        return "Cambio estadístico de la señal entre las dos fechas; sin etiquetas independientes no se reporta exactitud."
    land = block.get("land", {})
    water = block.get("permanent_water", {})
    text = f"Entre {block['pair']['before'][:10]} y {block['pair']['after'][:10]}, el {100*(land.get('increase') or 0)+100*(land.get('decrease') or 0):.2f} % de los píxeles de tierra cambió de forma estadísticamente significativa (prueba de Conradsen, α = {block['alpha']})."
    if water and water.get("n"):
        text += f" Sobre agua permanente el aumento fue {100*(water.get('increase') or 0):.1f} %: el mar y los embalses cambian con el viento, no indican daño."
    return text + " La prueba detecta cambio de la señal radar; no identifica su causa."
