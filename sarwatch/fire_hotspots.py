"""Active-fire thermal anomalies (NASA FIRMS). Optional adapter, like weather.py: never blocks SAR.

Needs a free FIRMS MAP_KEY (https://firms.modaps.eosdis.nasa.gov/api/map_key/, instant, no cost) read
from the FIRMS_MAP_KEY environment variable. brightness_k is the sensor's brightness temperature for
the fire-detecting channel (VIIRS I-4, ~4 micron) in Kelvin, not a calibrated land-surface temperature;
frp_mw is Fire Radiative Power in megawatts, a standard fire-intensity proxy. These are satellite
thermal detections at the moment of overpass, not a continuous temperature monitor.
"""
import csv
import io
import os
from datetime import datetime, timezone
from urllib.request import urlopen

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DEFAULT_SOURCE = "VIIRS_NOAA20_NRT"
FIELDS = {"latitude": float, "longitude": float, "bright_ti4": float, "acq_date": str, "acq_time": str, "confidence": str, "frp": float, "daynight": str}


def fetch_active_fire(west, south, east, north, days=7, source=DEFAULT_SOURCE, map_key=None, timeout=20):
    """List of fire-detection dicts in the bbox over the last `days` days (1-10 per the FIRMS API)."""
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Caja delimitadora inválida")
    if not 1 <= days <= 10:
        raise ValueError("days debe estar entre 1 y 10 (límite de la API FIRMS de área)")
    key = map_key or os.environ.get("FIRMS_MAP_KEY")
    if not key:
        raise ValueError("Falta FIRMS_MAP_KEY: crea una clave gratis en https://firms.modaps.eosdis.nasa.gov/api/map_key/")
    url = f"{BASE}/{key}/{source}/{west},{south},{east},{north}/{days}"
    with urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    if body.startswith("Invalid") or "Invalid MAP_KEY" in body:
        raise ValueError(f"FIRMS rechazó la clave o la solicitud: {body.strip()[:200]}")
    rows = list(csv.DictReader(io.StringIO(body)))
    detections = []
    for row in rows:
        try:
            detections.append({name: caster(row[name]) for name, caster in FIELDS.items() if name in row})
        except (KeyError, ValueError):
            continue
    return {"provider": "NASA FIRMS (VIIRS)", "source": source, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "bbox": [west, south, east, north], "days": days, "n_detections": len(detections), "detections": detections}


def summarize(result):
    detections = result.get("detections", [])
    if not detections:
        return {"n": 0, "max_frp_mw": None, "max_brightness_k": None}
    return {"n": len(detections), "max_frp_mw": round(max(d["frp"] for d in detections), 1), "max_brightness_k": round(max(d["bright_ti4"] for d in detections), 1), "high_confidence": sum(1 for d in detections if str(d.get("confidence")).lower() in ("h", "high", "9"))}
