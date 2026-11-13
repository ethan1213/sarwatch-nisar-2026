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
