"""Optional meteorological context. Never modifies NISAR layers or metadata."""
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch_weather(latitude, longitude, start=None, end=None):
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordenadas fuera de rango")
    historical = start is not None and end is not None
    if (start is None) != (end is None):
        raise ValueError("Se requieren ambas fechas históricas")
    params = {"latitude":latitude, "longitude":longitude, "timezone":"UTC", "daily":"precipitation_sum,temperature_2m_max,temperature_2m_min"}
    if historical:
        params.update(start_date=start, end_date=end, models="era5")
        base = "https://archive-api.open-meteo.com/v1/archive"
    else:
        params.update(forecast_days=7)
        base = "https://api.open-meteo.com/v1/forecast"
    with urlopen(base+"?"+urlencode(params), timeout=12) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Error del proveedor"))
    daily = payload.get("daily", {})
    expected = ("time", "precipitation_sum", "temperature_2m_max", "temperature_2m_min")
    if any(k not in daily for k in expected) or not daily["time"]:
        raise ValueError("Respuesta meteorológica incompleta")
    if any(len(daily[k]) != len(daily["time"]) for k in expected):
        raise ValueError("Series meteorológicas incompatibles")
    return {"provider":"Open-Meteo", "kind":"ERA5 reanalysis" if historical else "weather forecast", "retrieved_utc":datetime.now(timezone.utc).isoformat(), "requested_latitude":latitude, "requested_longitude":longitude, "payload":payload}


def fetch_river_discharge(latitude, longitude, start, end):
    """GloFAS modelled river discharge (m3/s) from the Open-Meteo Flood API for a 0.05 degree cell.

    Coarse hydrological model output: it is not a gauge measurement and a cell may miss the channel.
    """
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordenadas fuera de rango")
    if not start or not end:
        raise ValueError("Se requieren fecha inicial y final")
    params = {"latitude":latitude, "longitude":longitude, "daily":"river_discharge", "start_date":start, "end_date":end}
    with urlopen("https://flood-api.open-meteo.com/v1/flood?"+urlencode(params), timeout=12) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Error del proveedor"))
    daily = payload.get("daily", {})
    if "time" not in daily or "river_discharge" not in daily or not daily["time"] or len(daily["time"]) != len(daily["river_discharge"]):
        raise ValueError("Respuesta de caudal incompleta")
    return {"provider":"Open-Meteo Flood API (GloFAS)", "kind":"modelled river discharge", "retrieved_utc":datetime.now(timezone.utc).isoformat(), "requested_latitude":latitude, "requested_longitude":longitude, "cell_latitude":payload.get("latitude"), "cell_longitude":payload.get("longitude"), "payload":payload}
