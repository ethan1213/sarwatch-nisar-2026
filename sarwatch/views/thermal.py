"""Heat view: GOES hot spots and temperatures per thermal cell, crossed with NISAR backscatter, terrain and land cover.

Runtime-safe (no ML libraries). Evaluated figures come from catalog/thermal_reference.json; the view itself only
filters and counts observations that scripts/fetch_thermal.py and scripts/evaluate_fire.py wrote to disk.
"""
import json
import warnings
from datetime import date, timedelta
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from sarwatch.maps import base_map
from sarwatch.views.components import evidence_board, percent, short_date

REFERENCE_PATH = Path("catalog/thermal_reference.json")
FIRE_NAMES = {10: "foco procesado", 11: "foco saturado", 12: "foco parcialmente cubierto por nube", 13: "probabilidad alta", 14: "probabilidad media", 15: "probabilidad baja"}
CONFIDENT = (10, 11, 13)
CLOUD_CODES = (150, 151, 152, 153, 200, 201, 205, 210, 215, 220, 225, 230, 240, 245)
DAY_HOURS_UTC = (15, 16, 17, 18, 19)
HEAT_RAMP = ("#f7ecd9", "#e9a55f", "#c6601c", "#5c1f06")      # one hue, light to dark: magnitude
RADAR_RAMP = ("#205b87", "#f2f2e8", "#c6601c")                # the viewer's blue-neutral-orange radar scale
SERIES = {"tir": ("Infrarrojo térmico 11,2 µm", "#1f6aa5"), "mir": ("Infrarrojo medio 3,9 µm", "#c6601c"), "lst": ("Temperatura de superficie", "#7a4a9e")}  # validated: CVD ΔE ≥ 18
INK, MUTED = "#10293a", "#3d5563"
COVER_NAMES = {"cob_arboles": "árboles", "cob_matorral": "matorral", "cob_pastizal": "pastizal", "cob_cultivo": "cultivo", "cob_urbano": "urbano", "cob_suelo_desnudo": "suelo desnudo", "cob_agua": "agua", "cob_humedal": "humedal"}
LAYERS = {
    "focos": ("Focos de calor · detecciones en el período", "detecciones", HEAT_RAMP),
    "lst": ("Temperatura de superficie · mediana de la tarde", "°C", HEAT_RAMP),
    "mir": ("Infrarrojo medio 3,9 µm · máximo", "°C", HEAT_RAMP),
    "tir": ("Infrarrojo térmico 11,2 µm · máximo", "°C", HEAT_RAMP),
    "dif": ("Diferencia 3,9 − 11,2 µm · máximo sin nube", "K", HEAT_RAMP),
    "hv": ("Radar NISAR · HV de la última pasada del período", "dB", RADAR_RAMP),
    "dhv": ("Radar NISAR · cambio de HV entre pasadas del período", "dB", RADAR_RAMP),
    "pendiente": ("Terreno · pendiente media", "°", HEAT_RAMP),
    "elevacion": ("Terreno · elevación media", "m", HEAT_RAMP),
}


def thermal_root(data_dir, slug):
    return Path(data_dir) if slug == "pantanal" else Path(data_dir) / slug


def thermal_available(data_dir, slug):
    folder = thermal_root(data_dir, slug) / "thermal"
    return (folder / "cube.npz").is_file() and (folder / "manifest.json").is_file()


def thermal_reference():
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8")) if REFERENCE_PATH.is_file() else None


@st.cache_data(max_entries=4, show_spinner=False)
def load_thermal(folder, stamp):
    """stamp (file modification time) invalidates the cache when the products are regenerated."""
    folder = Path(folder)
    cube = dict(np.load(folder / "cube.npz"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    zones = json.loads((folder / "zones.json").read_text(encoding="utf-8")) if (folder / "zones.json").is_file() else None
    cube["times"] = cube["times"].astype("U16").astype("datetime64[m]")
    codes = cube["mask"].astype(np.int32)
    codes = np.where((codes >= 30) & (codes <= 35), codes - 20, codes)
    cube["fire"] = np.where((codes >= 10) & (codes <= 15), codes, 0).astype(np.int16)
    return cube, manifest, zones


def ramp_colour(fraction, ramp):
    """Hex colour of a 0-1 position along evenly spaced stops; None for NaN."""
    if fraction is None or not np.isfinite(fraction):
        return None
    stops = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in ramp], dtype=float)
    position = float(np.clip(fraction, 0, 1)) * (len(ramp) - 1)
    low = min(int(position), len(ramp) - 2)
    rgb = stops[low] + (stops[low + 1] - stops[low]) * (position - low)
    return "#" + "".join(f"{int(round(v)):02x}" for v in rgb)


def period_summary(cube, start, end):
    """Counts and per-cell aggregates of the observations with start <= time < end (datetime64)."""
    keep = (cube["times"] >= start) & (cube["times"] < end)
    fire, mask = cube["fire"][keep], cube["mask"][keep]
    hours = cube["times"][keep].astype("datetime64[h]").astype(int) % 24
    afternoon = np.isin(hours, DAY_HOURS_UTC)
    cloud = np.isin(mask, CLOUD_CODES)
    processed = mask >= 0
    with np.errstate(all="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells (cloud) stay NaN
            difference = np.where(cloud, np.nan, cube["bt_mir"][keep] - cube["bt_tir"][keep])
            empty = np.full(cube["lat"].shape, np.nan, dtype=np.float32)
            cells = {
                "focos": (fire > 0).sum(axis=0).astype(float), "confiables": np.isin(fire, CONFIDENT).sum(axis=0).astype(float),
                "lst": np.nanmedian(cube["lst"][keep][afternoon], axis=0) - 273.15 if afternoon.any() else empty,
                "mir": np.nanmax(cube["bt_mir"][keep], axis=0) - 273.15 if keep.any() else empty, "tir": np.nanmax(cube["bt_tir"][keep], axis=0) - 273.15 if keep.any() else empty,
                "dif": np.nanmax(difference, axis=0) if keep.any() else empty, "frp": np.nanmax(cube["frp"][keep], axis=0) if keep.any() else empty,
            }
    days = np.unique(cube["times"][keep][(fire > 0).any(axis=(1, 2))].astype("datetime64[D]"))
    return {"steps": int(keep.sum()), "detections": int((fire > 0).sum()), "confident": int(np.isin(fire, CONFIDENT).sum()), "cells_hot": int((fire > 0).any(axis=0).sum()), "days_hot": int(days.size),
            "cloud_fraction": float(cloud.sum() / processed.sum()) if processed.any() else None, "cells": cells}


def radar_layers(zones, start, end):
    """HV of the last pass inside the period and HV change between the first and last usable passes inside it."""
    n = len(zones["n_pixels"])
    blank = np.full(n, np.nan)
    inside = [r for r in zones["radar"] if str(start)[:10] <= r["date"] <= str(end - np.timedelta64(1, "m"))[:10] and np.nanmean(np.array(r["fraccion_valida"], dtype=float)) > 0.5]
    as_array = lambda values: np.array([np.nan if v is None else v for v in values], dtype=float)
    if not inside:
        return blank, blank, None
    last = as_array(inside[-1]["hv_db"])
    change = last - as_array(inside[0]["hv_db"]) if len(inside) > 1 else blank
    return last, change, (inside[0]["date"], inside[-1]["date"])


def cell_at(cube, latitude, longitude):
    """Index of the cell whose centre is nearest to a point, or None if the point is outside every footprint."""
    if not (np.nanmin(cube["corner_lat"]) <= latitude <= np.nanmax(cube["corner_lat"]) and np.nanmin(cube["corner_lon"]) <= longitude <= np.nanmax(cube["corner_lon"])):
        return None
    distance = ((cube["lat"] - latitude) * 110.57) ** 2 + ((cube["lon"] - longitude) * 111.32 * np.cos(np.radians(latitude))) ** 2
    return int(np.argmin(distance))


def cell_polygon(cube, index):
    row, col = divmod(index, cube["lat"].shape[1])
    corners = [(row, col), (row, col + 1), (row + 1, col + 1), (row + 1, col), (row, col)]
    return [[round(float(cube["corner_lon"][r, c]), 5), round(float(cube["corner_lat"][r, c]), 5)] for r, c in corners]


def decimal(value, spec=".2f"):
    """Number with a decimal comma, as the rest of the Spanish interface writes them."""
    return format(value, spec).replace(".", ",")


def count(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def response_sentence(block):
    """What the offline evaluation found about radar change where GOES saw heat. Never claims burned area."""
    response = (block or {}).get("response") or {}
    hv = response.get("hv")
    if not hv:
        return "ausente", "No hay suficientes celdas con foco entre dos pasadas NISAR para medir si el radar responde al calor detectado."
    low, high = hv["auc_bootstrap_90"]
    text = (f"Entre dos pasadas NISAR, la señal HV cambió {decimal(hv['median_change_with_heat_db'], '+.2f')} dB (mediana) en las {hv['n_with_heat']} celdas donde GOES detectó calor con confianza, "
            f"frente a {decimal(hv['median_change_without_heat_db'], '+.2f')} dB en las {hv['n_without_heat']} sin ningún foco. ")
    auc, interval = decimal(hv["auc_decrease_separates_heat"]), f"{decimal(low)}–{decimal(high)}"
    if low > 0.5:
        return "estimado", text + f"La caída de HV separa unas de otras con AUC {auc} (intervalo 90 %: {interval}): el radar registra un cambio compatible con pérdida de vegetación donde hubo calor, sin confirmar área quemada."
    if high < 0.5:
        return "estimado", text + f"AUC {auc} (intervalo 90 %: {interval}): HV subió más donde hubo calor; no es la firma esperada de pérdida de vegetación."
    return "estimado", text + f"AUC {auc} (intervalo 90 %: {interval}): a escala de celda, el cambio de HV no distingue las celdas con calor de las demás."


def anticipation_sentence(block):
    """Whether radar + terrain add anything to anticipating hot cells, according to the held-out evaluation."""
    models = (block or {}).get("anticipation") or {}
    if "persistencia" not in models:
        return "ausente", "No hay focos suficientes en este recorte para evaluar si se pueden anticipar. No mostramos ninguna predicción."
    number = lambda value: "sin dato" if value is None else decimal(value)
    parts, wins = [], []
    for split, label in (("spatial_blocks", "zonas retenidas"), ("held_out_dates", "fechas retenidas")):
        base, full, radar = (models[name][split].get("average_precision") for name in ("persistencia", "todo", "radar_terreno"))
        prevalence = models["persistencia"][split].get("prevalence")
        if base is None or full is None:
            parts.append(f"en {label} no hay positivos suficientes para puntuar")
            wins.append(False)
            continue
        parts.append(f"en {label}, precisión media {number(full)} con todas las variables, {number(radar)} solo con radar y terreno, {number(base)} repitiendo dónde hubo calor (azar: {number(prevalence)})")
        wins.append(full > base)
    verdict = "El modelo completo supera a la persistencia en ambas pruebas; aún falta tarjeta de modelo y validación con área quemada antes de mostrarlo como capa." if all(wins) else "No supera de forma consistente a repetir dónde hubo calor: no se publica ninguna capa de predicción."
    return "estimado", "Anticipar qué celdas tendrán un foco en los 12 días siguientes a una pasada NISAR: " + "; ".join(parts) + ". " + verdict


def legend(label, unit, low, high, ramp):
    digits = 0 if unit == "detecciones" else 1
    text = lambda value: "sin dato" if not np.isfinite(value) else f"{value:,.{digits}f}".replace(",", " ").replace(".", ",") + ("" if unit == "detecciones" else f" {unit}")
    st.markdown(f"<div class='sw-scale'><div class='sw-scale-bar' role='img' aria-label='Escala de color de {label}' style='background:linear-gradient(90deg,{','.join(ramp)})'></div><div class='sw-scale-labels'><span>{text(low)}</span><span>{label}</span><span>{text(high)}</span></div></div>", unsafe_allow_html=True)


def heat_map(cube, values, limits, ramp, summary, selected, center):
    """Cells coloured by the chosen layer; cells with hot spots get a dark outline, the selected one a thick outline."""
    m = base_map(center, 10)
    low, high = limits
    hot, sure = summary["cells"]["focos"].ravel(), summary["cells"]["confiables"].ravel()
    features = []
    for index in range(values.size):
        value = values[index]
        colour = ramp_colour((value - low) / (high - low) if high > low else 0.5, ramp)
        features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [cell_polygon(cube, index)]},
                         "properties": {"valor": "sin dato" if not np.isfinite(value) else f"{value:.1f}".replace(".", ","), "focos": int(hot[index]), "confiables": int(sure[index]), "fill": colour, "sel": index == selected}})
    style = lambda f: {"fillColor": f["properties"]["fill"] or "#000000", "fillOpacity": 0.78 if f["properties"]["fill"] else 0, "color": INK if f["properties"]["sel"] or f["properties"]["focos"] else "#ffffff",
                       "weight": 4 if f["properties"]["sel"] else 2 if f["properties"]["confiables"] else 1.2 if f["properties"]["focos"] else 0.3, "dashArray": None if f["properties"]["confiables"] or f["properties"]["sel"] or not f["properties"]["focos"] else "4 3"}
    folium.GeoJson({"type": "FeatureCollection", "features": features}, name="Celdas térmicas GOES-19", style_function=style, highlight_function=lambda f: {"weight": 3, "color": INK},
                   tooltip=folium.GeoJsonTooltip(fields=["valor", "focos", "confiables"], aliases=["Valor de la capa", "Detecciones de foco", "De ellas, confiables"])).add_to(m)
    m.fit_bounds([[float(np.nanmin(cube["corner_lat"])), float(np.nanmin(cube["corner_lon"]))], [float(np.nanmax(cube["corner_lat"])), float(np.nanmax(cube["corner_lon"]))]])
    folium.LayerControl().add_to(m)
    return m


DAILY_ABOVE_DAYS = 21  # longer periods show one value per day so the series stays readable


def cell_frame(cube, index, start, end):
    """Cloud-free temperatures (°C) of one cell: hourly, or one row per day when the period is long.

    Daily rows hold the maximum of each infrared channel and the afternoon median of the surface temperature.
    Returns (frame, daily); `foco` counts hot-spot detections in the row and `clase` names the most confident one.
    """
    row, col = divmod(index, cube["lat"].shape[1])
    keep = (cube["times"] >= start) & (cube["times"] < end)
    cloud = np.isin(cube["mask"][keep, row, col], CLOUD_CODES)
    fire = cube["fire"][keep, row, col]
    frame = pd.DataFrame({"utc": cube["times"][keep].astype("datetime64[s]"), "tir": np.where(cloud, np.nan, cube["bt_tir"][keep, row, col] - 273.15), "mir": np.where(cloud, np.nan, cube["bt_mir"][keep, row, col] - 273.15),
                          "lst": cube["lst"][keep, row, col] - 273.15, "foco": (fire > 0).astype(int), "orden": np.where(fire > 0, fire, 99)})
    daily = (end - start) > np.timedelta64(DAILY_ABOVE_DAYS, "D")
    if daily and len(frame):
        frame["lst"] = frame["lst"].where(frame["utc"].dt.hour.isin(DAY_HOURS_UTC))
        frame = frame.groupby(frame["utc"].dt.floor("D")).agg(tir=("tir", "max"), mir=("mir", "max"), lst=("lst", "median"), foco=("foco", "sum"), orden=("orden", "min")).reset_index()
    frame["clase"] = [FIRE_NAMES.get(int(code), "") for code in frame["orden"]]
    return frame.drop(columns="orden"), bool(daily)


def cell_series(cube, zones, index, start, end):
    """Temperatures of one cell on a single axis (°C), hot-spot detections as markers, NISAR passes as vertical lines."""
    frame, daily = cell_frame(cube, index, start, end)
    names = {"tir": SERIES["tir"][0] + (" · máximo del día" if daily else ""), "mir": SERIES["mir"][0] + (" · máximo del día" if daily else ""), "lst": SERIES["lst"][0] + (" · mediana de la tarde" if daily else "")}
    figure = go.Figure()
    for key in ("tir", "mir", "lst"):
        figure.add_trace(go.Scatter(x=frame["utc"], y=frame[key], name=names[key], mode="lines", line={"color": SERIES[key][1], "width": 2}, connectgaps=False, hovertemplate="%{y:.1f} °C<extra>" + names[key] + "</extra>"))
    hot = frame[frame["foco"] > 0]
    if len(hot):
        text = [f"{n} detecciones · {c}" if n > 1 else c for n, c in zip(hot["foco"], hot["clase"])]
        figure.add_trace(go.Scatter(x=hot["utc"], y=hot["mir"], name="Foco detectado por GOES", mode="markers", text=text, marker={"symbol": "diamond", "size": 11, "color": INK, "line": {"color": "#ffffff", "width": 2}}, hovertemplate="%{text}<extra>Foco GOES</extra>"))
    for pass_date in (zones or {}).get("sar_dates", []):
        if start <= np.datetime64(pass_date) < end:
            figure.add_vline(x=str(pass_date), line={"color": MUTED, "width": 1, "dash": "dot"})
            figure.add_annotation(x=str(pass_date), y=1, yref="paper", text="NISAR", showarrow=False, yanchor="bottom", font={"size": 11, "color": MUTED})
    figure.update_layout(height=430, margin={"l": 50, "r": 10, "t": 30, "b": 110}, hovermode="x unified", yaxis_title="Temperatura (°C)", legend={"orientation": "h", "y": -0.16, "yanchor": "top"}, plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)", font={"color": INK})
    figure.update_xaxes(gridcolor="#e7ece9")
    figure.update_yaxes(gridcolor="#e7ece9", zeroline=False)
    return figure, daily


def cell_radar(zones, index):
    frame = pd.DataFrame([{"fecha": r["date"], "HV": r["hv_db"][index], "HH": r["hh_db"][index], "valido": r["fraccion_valida"][index]} for r in zones["radar"]])
    frame = frame[frame["valido"].fillna(0) >= 0.5]
    figure = go.Figure()
    for band, colour in (("HH", "#1f6aa5"), ("HV", "#c6601c")):
        figure.add_trace(go.Scatter(x=frame["fecha"], y=frame[band], name=band, mode="lines+markers", line={"color": colour, "width": 2}, marker={"size": 8, "color": colour, "line": {"color": "#ffffff", "width": 2}}, hovertemplate="%{y:.2f} dB<extra>" + band + "</extra>"))
    figure.update_layout(height=430, margin={"l": 50, "r": 10, "t": 30, "b": 110}, hovermode="x unified", yaxis_title="Retrodispersión media (dB)", legend={"orientation": "h", "y": -0.16, "yanchor": "top"}, plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)", font={"color": INK})
    figure.update_xaxes(gridcolor="#e7ece9")
    figure.update_yaxes(gridcolor="#e7ece9", zeroline=False)
    return figure, frame


def dominant_cover(zones, index):
    shares = {name: zones["static"][key][index] for key, name in COVER_NAMES.items() if zones["static"].get(key) and zones["static"][key][index] is not None}
    if not shares:
        return None
    name = max(shares, key=shares.get)
    return f"{name} ({percent(shares[name])})"


def thermal_view(region, slug, data_dir, profile="Público general"):
    folder = thermal_root(data_dir, slug) / "thermal"
    cube, manifest, zones = load_thermal(str(folder), (folder / "cube.npz").stat().st_mtime)
    reference = ((thermal_reference() or {}).get("aois") or {}).get(slug)
    first_day, last_day = cube["times"][0].astype("datetime64[D]").astype(date), cube["times"][-1].astype("datetime64[D]").astype(date)
    st.subheader(f"{region} · calor y focos")
    st.caption(f"Sensor térmico: GOES-19 ABI, una observación cada {manifest['step_minutes']} minutos, celdas de {manifest['pixel_km_east_west']:.1f} × {manifest['pixel_km_north_south']:.1f} km".replace(".", ",") + ". El radar NISAR no mide temperatura: aquí describe la vegetación y el terreno dentro de cada celda térmica.")
    map_column, reading_column = st.columns([3, 2], gap="large")
    with map_column:
        row = st.columns([4, 5])
        passes = [d for d in (zones or {}).get("sar_dates", []) if first_day.isoformat() <= d <= last_day.isoformat()]
        presets = {"Todo el período": (first_day, last_day), **{f"Entre pasadas NISAR · {short_date(a)} → {short_date(b)}": (date.fromisoformat(a), date.fromisoformat(b)) for a, b in zip(passes, passes[1:])}}
        if passes:
            presets[f"Después de la última pasada · {short_date(passes[-1])}"] = (date.fromisoformat(passes[-1]), last_day)

        def apply_preset():
            st.session_state[slug + "-heat-range"] = presets[st.session_state[slug + "-heat-preset"]]

        row[0].selectbox("Período", list(presets), key=slug + "-heat-preset", on_change=apply_preset)
        layer = row[1].selectbox("Capa del mapa", list(LAYERS), format_func=lambda k: LAYERS[k][0], key=slug + "-heat-layer")
        st.session_state.setdefault(slug + "-heat-range", (first_day, last_day))
        chosen = st.slider("Ajustar fechas (UTC)", min_value=first_day, max_value=last_day, format="DD/MM/YYYY", key=slug + "-heat-range")
        start, end = np.datetime64(chosen[0], "m"), np.datetime64(chosen[1] + timedelta(days=1), "m")
        summary = period_summary(cube, start, end)
        last_hv, change_hv, radar_dates = radar_layers(zones, start, end) if zones else (None, None, None)
        static = lambda key: np.array([np.nan if v is None else v for v in zones["static"][key]], dtype=float) if zones else np.full(cube["lat"].size, np.nan)
        values = {"hv": last_hv, "dhv": change_hv, "pendiente": static("pendiente_grados"), "elevacion": static("elevacion_m")}.get(layer)
        values = summary["cells"][layer].ravel() if values is None and layer in summary["cells"] else np.full(cube["lat"].size, np.nan) if values is None else values
        label, unit, ramp = LAYERS[layer]
        finite = values[np.isfinite(values)]
        if layer == "dhv":
            limits = (-3.0, 3.0)
        elif layer == "focos":
            limits = (1.0, max(float(finite.max()) if finite.size else 2.0, 2.0))
            values = np.where(values > 0, values, np.nan)
        else:
            limits = (float(np.quantile(finite, 0.02)), float(np.quantile(finite, 0.98))) if finite.size else (0.0, 1.0)
        legend(label.split(" · ")[-1], unit, *limits, ramp)
        selected = st.session_state.get(slug + "-heat-cell")
        if selected is None:
            with_radar = np.array(zones["n_pixels"]) > 0 if zones else np.zeros(cube["lat"].size, dtype=bool)
            activity = summary["cells"]["confiables"].ravel() * 1000 + summary["cells"]["focos"].ravel()
            ranking = np.where(activity > 0, activity + 1e6 * with_radar, 0)
            selected = int(np.argmax(ranking)) if ranking.max() > 0 else int(np.flatnonzero(with_radar)[with_radar.sum() // 2]) if with_radar.any() else int(cube["lat"].size // 2)
        center = [float(np.nanmean(cube["lat"])), float(np.nanmean(cube["lon"]))]
        event = st_folium(heat_map(cube, values, limits, ramp, summary, selected, center), height=600, use_container_width=True, key=f"heat-map-{slug}", returned_objects=["last_clicked"])
        clicked = (event or {}).get("last_clicked")
        if clicked:
            index = cell_at(cube, clicked["lat"], clicked["lng"])
            if index is not None and index != st.session_state.get(slug + "-heat-cell") and (clicked["lat"], clicked["lng"]) != st.session_state.get(slug + "-heat-click"):
                st.session_state[slug + "-heat-click"] = (clicked["lat"], clicked["lng"])
                st.session_state[slug + "-heat-cell"] = index
                st.rerun()
        notes = "Borde oscuro continuo: celda con al menos un foco confiable en el período. Borde punteado: solo detecciones de probabilidad media o baja. Borde grueso: celda seleccionada. Haz clic en una celda para ver su serie."
        if layer in ("hv", "dhv"):
            notes += f" Radar entre {short_date(radar_dates[0])} y {short_date(radar_dates[1])}." if radar_dates else " No hay pasadas NISAR utilizables dentro de este período."
        if layer in ("mir", "dif"):
            notes += " De día, el canal de 3,9 µm incluye sol reflejado: un valor alto no basta para afirmar que hay fuego."
        st.caption(notes)
    with reading_column:
        st.markdown(f"#### {short_date(chosen[0].isoformat())} → {short_date(chosen[1].isoformat())}")
        items = []
        if summary["detections"]:
            items.append(("observado", f"GOES-19 registró {count(summary['detections'], 'detección', 'detecciones')} de foco de calor ({count(summary['confident'], 'confiable', 'confiables')}) en {count(summary['cells_hot'], 'celda', 'celdas')}, en {count(summary['days_hot'], 'día distinto', 'días distintos')}. Con una observación por hora, los focos breves pueden no aparecer."))
        else:
            items.append(("observado", "GOES-19 no registró focos de calor en este recorte durante el período. Con una observación por hora y nubes, eso no descarta quemas pequeñas o breves."))
        if summary["cloud_fraction"] is not None:
            items.append(("observado", f"El {percent(summary['cloud_fraction'])} de las observaciones del período estaba cubierto por nube: en esas horas no se puede detectar calor."))
        items.append(response_sentence(reference))
        items.append(anticipation_sentence(reference))
        items.append(("hipotesis", "Un foco es una anomalía térmica dentro de una celda de varios km²: puede ser quema agrícola, incendio de vegetación, una fuente industrial o una falsa alarma. No indica su posición exacta ni su tamaño."))
        items.append(("ausente", "Faltan focos VIIRS de 375 m, viento y humedad del aire, y un mapa de área quemada independiente para validar. Sin eso no hablamos de riesgo ni de incendios confirmados."))
        evidence_board(items)
        if profile == "Gestión territorial":
            st.caption("Uso sugerido: orientar dónde mirar con otras fuentes y en terreno. No es una alerta operativa.")
        elif profile == "Comunicaciones":
            st.caption("Qué puedes afirmar: lo observado y lo estimado, citando la métrica. Qué no: incendios confirmados, superficie quemada ni riesgo futuro.")
    row_index, col_index = divmod(selected, cube["lat"].shape[1])
    st.subheader("La celda seleccionada")
    st.caption(f"Centro {cube['lat'][row_index, col_index]:.4f}, {cube['lon'][row_index, col_index]:.4f} · {count(int(summary['cells']['focos'][row_index, col_index]), 'detección', 'detecciones')} de foco en el período.")
    facts = st.columns(4)
    if zones and zones["n_pixels"][selected]:
        number = lambda key, unit, digits=0: "sin dato" if zones["static"][key][selected] is None else f"{zones['static'][key][selected]:.{digits}f}".replace(".", ",") + unit
        facts[0].metric("Elevación media", number("elevacion_m", " m"))
        facts[1].metric("Pendiente media", number("pendiente_grados", "°", 1))
        facts[2].metric("Cobertura dominante", dominant_cover(zones, selected) or "sin dato")
        facts[3].metric("Píxeles NISAR en la celda", f"{zones['n_pixels'][selected]:,}".replace(",", " "))
    else:
        st.info("Esta celda queda fuera del recorte NISAR: solo tiene observaciones térmicas." if zones else "Falta el cruce con NISAR de este recorte (scripts/evaluate_fire.py): solo se muestran observaciones térmicas.")
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Temperaturas de la celda")
        series_figure, daily = cell_series(cube, zones, selected, start, end)
        st.plotly_chart(series_figure, width="stretch", key=f"heat-series-{slug}")
        st.caption(("Un valor por día porque el período supera los 21 días; acórtalo para ver cada hora. " if daily else "Una observación por hora. ") + "Temperatura de brillo en dos canales infrarrojos y temperatura de superficie, solo con cielo despejado. Los huecos son nubes o datos ausentes; no se interpolan.")
    with right:
        st.markdown("#### Radar NISAR en la misma celda")
        if zones and zones["n_pixels"][selected]:
            figure, radar_frame = cell_radar(zones, selected)
            if len(radar_frame):
                st.plotly_chart(figure, width="stretch", key=f"heat-radar-{slug}")
                st.caption("Promedio de los píxeles de 20 m dentro de la celda, calculado en potencia. Una caída de HV puede indicar pérdida de vegetación; también cambia con la humedad.")
            else:
                st.info("Ninguna pasada cubre al menos la mitad de esta celda.")
        else:
            st.info("Sin radar en esta celda.")
    st.subheader("Celdas con más actividad térmica en el período")
    cells = summary["cells"]
    order = np.argsort(-(cells["confiables"].ravel() * 1000 + cells["focos"].ravel()))[:15]
    order = [int(i) for i in order if cells["focos"].ravel()[i] > 0]
    if order:
        table = pd.DataFrame([{"celda": i, "latitud": round(float(cube["lat"].ravel()[i]), 4), "longitud": round(float(cube["lon"].ravel()[i]), 4), "detecciones": int(cells["focos"].ravel()[i]), "confiables": int(cells["confiables"].ravel()[i]),
                               "potencia máx. (MW)": None if not np.isfinite(cells["frp"].ravel()[i]) else round(float(cells["frp"].ravel()[i]), 1), "temp. superficie tarde (°C)": None if not np.isfinite(cells["lst"].ravel()[i]) else round(float(cells["lst"].ravel()[i]), 1),
                               "cambio HV (dB)": None if change_hv is None or not np.isfinite(change_hv[i]) else round(float(change_hv[i]), 2), "pendiente (°)": None if not zones or zones["static"]["pendiente_grados"][i] is None else zones["static"]["pendiente_grados"][i], "cobertura": dominant_cover(zones, i) if zones else None} for i in order])
        picked = st.dataframe(table, hide_index=True, on_select="rerun", selection_mode="single-row", key=f"heat-table-{slug}")
        rows = (picked or {}).get("selection", {}).get("rows", [])
        if rows and int(table.iloc[rows[0]]["celda"]) != selected and st.session_state.get(slug + "-heat-row") != (rows[0], chosen):
            st.session_state[slug + "-heat-row"] = (rows[0], chosen)
            st.session_state[slug + "-heat-cell"] = int(table.iloc[rows[0]]["celda"])
            st.rerun()
        st.caption("Selecciona una fila para ver esa celda. La potencia radiativa es la estimación del producto GOES para el píxel completo.")
        st.download_button("Descargar tabla CSV", table.to_csv(index=False), f"sarwatch-calor-{slug}.csv", "text/csv", key=f"heat-download-{slug}")
    else:
        st.info("Ninguna celda registró focos en este período.")
    with st.expander("Procedencia y límites"):
        st.write(manifest["limits"])
        st.json({k: manifest[k] for k in ("satellite", "bucket", "products", "period_utc", "step_minutes", "time_steps", "steps_with", "hotspot_detections_by_class", "cloud_fraction_of_processed", "generated_utc") if k in manifest})
        if reference:
            st.download_button("Descargar evaluación y límites", json.dumps(reference, ensure_ascii=False, indent=2), f"thermal-reference-{slug}.json", "application/json", key=f"heat-reference-{slug}")
