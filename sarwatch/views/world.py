"""World coverage view: where NISAR GCOV data exist (CMR index), how many dates, and what is processed here."""
import gzip
import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

COVERAGE = Path("catalog/global/coverage_1deg.json")
INDEX = Path("catalog/global/gcov_index.csv.gz")
SITES = {"Pantanal": [-57.25, -17.25], "Región Metropolitana": [-70.65, -33.475], "Región de Valparaíso": [-71.55, -33.05]}


@st.cache_data(show_spinner=False)
def coverage():
    return json.loads(COVERAGE.read_text(encoding="utf-8")) if COVERAGE.is_file() else None


@st.cache_data(show_spinner=False)
def index_frame():
    if not INDEX.is_file():
        return None
    with gzip.open(INDEX, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    frame["date"] = frame["time_start"].str[:10]
    return frame


def granules_at(frame, lon, lat):
    hit = frame[(frame.west <= lon) & (frame.east >= lon) & (frame.south <= lat) & (frame.north >= lat)].copy()
    hit["geometry"] = hit.track.astype(str) + "_" + hit.direction.astype(str) + "_" + hit.frame.astype(str)
    return hit.sort_values("date")


def _color(dates):
    return "#c6601c" if dates >= 8 else "#d98a4a" if dates >= 4 else "#8fb3c7" if dates >= 2 else "#cfdbe2"


COLORS = {"#cfdbe2": (207, 219, 226), "#8fb3c7": (143, 179, 199), "#d98a4a": (217, 138, 74), "#c6601c": (198, 96, 28)}


@st.cache_data(show_spinner=False)
def coverage_image(cells_json):
    """360x180 RGBA image of 1-degree cells coloured by number of distinct dates (one pixel per cell)."""
    import numpy as np
    cells = json.loads(cells_json)
    rgba = np.zeros((180, 360, 4), dtype="uint8")
    for c in cells:
        row = 89 - int(c["lat"])  # row 0 is latitude +89..+90
        col = int(c["lon"]) + 180
        if 0 <= row < 180 and 0 <= col < 360:
            rgba[row, col, :3] = COLORS[_color(c["dates"])]
            rgba[row, col, 3] = 170
    return rgba


def world_view(profile="Público general"):
    st.subheader("Mundo · dónde hay observaciones NISAR")
    data = coverage()
    if data is None:
        st.info("El índice mundial aún no se ha construido. Ejecuta scripts/build_global_catalog.py (solo metadatos, sin descargar imágenes).")
        return
    st.caption(f"Índice de {data['granules_indexed']:,} granulos GCOV del catálogo oficial CMR ({data['generated_utc'][:10]}). Color por número de fechas distintas en cada celda de 1°: claro 1, azul 2–3, naranja claro 4–7, naranja ≥ 8. Es disponibilidad en el catálogo, no cobertura procesada ni validada.")
    m = folium.Map(location=[0, 0], zoom_start=2, tiles="CartoDB positron", control_scale=True)
    folium.raster_layers.ImageOverlay(coverage_image(json.dumps(data["cells"])), bounds=[[-90, -180], [90, 180]], name="Fechas NISAR GCOV por celda de 1°", opacity=1.0, mercator_project=True).add_to(m)
    folium.LayerControl().add_to(m)
    for name, (lon, lat) in SITES.items():
        folium.Marker([lat, lon], tooltip=f"{name}: procesado y evaluado en SARWatch", icon=folium.Icon(color="darkblue", icon="ok-sign")).add_to(m)
    event = st_folium(m, height=520, use_container_width=True, key="world-map", returned_objects=["last_clicked"])
    clicked = event.get("last_clicked")
    c1, c2 = st.columns(2)
    lon = c1.number_input("Longitud", -180.0, 180.0, float(clicked["lng"]) if clicked else -57.25, format="%.3f", key="world-lon")
    lat = c2.number_input("Latitud", -90.0, 90.0, float(clicked["lat"]) if clicked else -17.25, format="%.3f", key="world-lat")
    frame = index_frame()
    if frame is None:
        return
    cell = next((c for c in data["cells"] if c["lon"] == int(lon // 1) and c["lat"] == int(lat // 1)), None)
    if cell:
        st.write(f"Celda 1° ({cell['lon']}, {cell['lat']}): {cell['dates']} fechas distintas, {cell['granules']} granulos, de {cell['first_date']} a {cell['last_date']}.")
    hit = granules_at(frame, lon, lat)
    if hit.empty:
        st.warning("No hay granulos GCOV cuya huella nominal cubra ese punto. Prueba otro lugar o espera nuevos ciclos de 12 días.")
        return
    repeats = hit.groupby("geometry").agg(fechas=("date", "nunique"), primera=("date", "min"), ultima=("date", "max"), GB=("size_mib", lambda s: round(s.sum() / 1024, 1))).sort_values("fechas", ascending=False)
    st.write(f"{len(hit)} granulos cubren el punto; {len(repeats)} geometrías de órbita distintas. Para comparar fechas se usa una sola geometría.")
    st.dataframe(repeats.reset_index(), hide_index=True)
    best = repeats.index[0]
    st.caption(f"Mejor serie: geometría {best} con {int(repeats.loc[best, 'fechas'])} fechas; descargar sus granulos pesa {repeats.loc[best, 'GB']} GB. Procesar este lugar requiere ejecutar el flujo bajo demanda (scripts/request_aoi.py) con Earthdata Login; no ocurre al hacer clic.")
    if profile in ("Desarrollo y datos", "Ciencia"):
        st.dataframe(hit[hit.geometry == best][["id", "date", "polarization", "size_mib"]].reset_index(drop=True), hide_index=True)
        st.code(f"python scripts/request_aoi.py select --name mi_sitio --bbox {lon-0.25:.2f} {lat-0.25:.2f} {lon+0.25:.2f} {lat+0.25:.2f} --start {repeats.loc[best, 'primera']}", language="bash")
