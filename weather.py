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


FIRE_HOURLY = ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "vapour_pressure_deficit", "precipitation")


def fetch_fire_weather(points, start, end):
    """Hourly ERA5 wind, air humidity, temperature, vapour pressure deficit and rain for a list of (lat, lon).

    Reanalysis on a coarse grid (the provider returns the cell it used): context for a fire detection,
    not a station reading and not a forecast. Missing values stay null.
    """
    points = list(points)
    if not points or any(not (-90 <= lat <= 90 and -180 <= lon <= 180) for lat, lon in points):
        raise ValueError("Coordenadas ausentes o fuera de rango")
    if not start or not end:
        raise ValueError("Se requieren fecha inicial y final")
    params = {"latitude": ",".join(str(lat) for lat, _ in points), "longitude": ",".join(str(lon) for _, lon in points), "start_date": start, "end_date": end, "hourly": ",".join(FIRE_HOURLY), "models": "era5", "timezone": "UTC"}
    with urlopen("https://archive-api.open-meteo.com/v1/archive?" + urlencode(params), timeout=60) as response:
        payload = json.load(response)
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(payload.get("reason", "Error del proveedor"))
    cells = payload if isinstance(payload, list) else [payload]
    if len(cells) != len(points):
        raise ValueError("El proveedor no devolvió una serie por punto")
    for cell in cells:
        hourly = cell.get("hourly", {})
        if any(k not in hourly for k in ("time", *FIRE_HOURLY)) or not hourly["time"]:
            raise ValueError("Respuesta meteorológica incompleta")
        if any(len(hourly[k]) != len(hourly["time"]) for k in FIRE_HOURLY):
            raise ValueError("Series meteorológicas incompatibles")
    return {"provider": "Open-Meteo", "kind": "ERA5 reanalysis", "retrieved_utc": datetime.now(timezone.utc).isoformat(), "requested_points": points, "cells": cells}


def fetch_fire_forecast(latitude, longitude, hours=48):
    """Hourly forecast (not observation) of wind, gusts, air humidity, temperature and vapour pressure deficit."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordenadas fuera de rango")
    variables = FIRE_HOURLY + ("precipitation_probability",)
    params = {"latitude": latitude, "longitude": longitude, "hourly": ",".join(variables), "forecast_hours": hours, "timezone": "UTC"}
    with urlopen("https://api.open-meteo.com/v1/forecast?" + urlencode(params), timeout=12) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise ValueError(payload.get("reason", "Error del proveedor"))
    hourly = payload.get("hourly", {})
    if any(k not in hourly for k in ("time", *variables)) or not hourly["time"]:
        raise ValueError("Pronóstico incompleto")
    if any(len(hourly[k]) != len(hourly["time"]) for k in variables):
        raise ValueError("Series de pronóstico incompatibles")
    return {"provider": "Open-Meteo", "kind": "weather forecast", "retrieved_utc": datetime.now(timezone.utc).isoformat(), "requested_latitude": latitude, "requested_longitude": longitude,
            "cell_latitude": payload.get("latitude"), "cell_longitude": payload.get("longitude"), "cell_elevation_m": payload.get("elevation"), "units": payload.get("hourly_units", {}), "hourly": hourly}
