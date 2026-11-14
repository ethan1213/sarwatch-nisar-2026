"""Geographic views; scientific rasters remain separate from display sampling."""
import json
from pathlib import Path
import folium
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
from streamlit_folium import st_folium
import streamlit as st


@st.cache_data(ttl=3600, max_entries=32)
def point_forecast(latitude, longitude):
    from weather import fetch_weather
    return fetch_weather(latitude, longitude)


def base_map(center, zoom=9):
    m = folium.Map(location=center, zoom_start=zoom, tiles='OpenStreetMap', control_scale=True)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Tiles © Esri — imagery providers', name='Imagen satelital de contexto (no NISAR)').add_to(m)
    return m


def raster_map(values, transform, crs, changes=False):
    height, width = values.shape
    bounds = array_bounds(height, width, transform)
    dst_transform, w, h = calculate_default_transform(crs, 'EPSG:4326', width, height, *bounds, dst_width=600, dst_height=600)
    output = np.full((h,w), np.nan, dtype='float32')
    reproject(values, output, src_transform=transform, src_crs=crs, src_nodata=np.nan, dst_transform=dst_transform, dst_crs='EPSG:4326', dst_nodata=np.nan, resampling=Resampling.nearest)
    west,south,east,north = array_bounds(h,w,dst_transform)
    normalized = np.clip((output+6)/12 if changes else (output+30)/30,0,1)
    rgba = np.zeros((h,w,4),dtype='uint8')
    rgba[:,:,0] = np.nan_to_num(normalized*255).astype('uint8')
    rgba[:,:,1] = np.nan_to_num((1-abs(normalized-.5)*2)*200).astype('uint8')
    rgba[:,:,2] = np.nan_to_num((1-normalized)*255).astype('uint8')
    rgba[:,:,3] = np.isfinite(output).astype('uint8')*190
    m = base_map([(south+north)/2,(west+east)/2],10)
    folium.raster_layers.ImageOverlay(rgba, bounds=[[south,west],[north,east]], name='NISAR · diferencia dB' if changes else 'NISAR · retrodispersión dB', mercator_project=True).add_to(m)
    m.fit_bounds([[south,west],[north,east]])
    folium.LayerControl().add_to(m)
    return m


def chile_view(region):
    slug = 'metropolitana' if region == 'Región Metropolitana' else 'valparaiso'
    center = [-33.45,-70.66] if slug=='metropolitana' else [-33.047,-71.613]
    st.subheader(region)
    framing = st.radio('Encuadre', ['Región completa', 'Santiago' if slug=='metropolitana' else 'Valparaíso / Viña del Mar'], horizontal=True)
    st.caption('Límites comunales continentales de CIREN / IDE Minagri. Cartografía de referencia; no representa una medición SAR.')
    m=base_map(center,9)
    path=Path('catalog')/(slug+'.geojson')
    if path.is_file():
        data=json.loads(path.read_text(encoding='utf-8'))
        boundaries = folium.GeoJson(data,name='Límites comunales · CIREN',style_function=lambda f:{'fillColor':'#397a85','color':'#245360','weight':1,'fillOpacity':.08},tooltip=folium.GeoJsonTooltip(fields=['nomcom'], aliases=['Comuna'])).add_to(m)
        if framing == 'Región completa':
            m.fit_bounds(boundaries.get_bounds())
    folium.Marker([-33.45,-70.66],tooltip='Santiago').add_to(m)
    folium.Marker([-33.047,-71.613],tooltip='Valparaíso').add_to(m)
    folium.LayerControl().add_to(m)
    event=st_folium(m,height=560,use_container_width=True,key='chile-'+slug+framing,returned_objects=['last_clicked'])
    point=event.get('last_clicked') or {'lat':center[0],'lng':center[1]}
    st.caption(f"Punto seleccionado: {point['lat']:.5f}, {point['lng']:.5f}. Haz clic en el mapa para cambiarlo.")
    st.info('Las capas NISAR procesadas disponibles pertenecen a Pantanal. Para Chile se ofrece cartografía y búsqueda de adquisiciones; aún no hay una serie SAR local validada.')
    if Path('catalog/chile_cmr.json').is_file():
        catalog=json.loads(Path('catalog/chile_cmr.json').read_text(encoding='utf-8'))
        entries=catalog['response'].get('feed',{}).get('entry',[])
        st.write(f'{len(entries)} adquisiciones en la página de resultados consultada para Chile central. Son candidatos: intersección de huellas no garantiza cobertura útil de cada comuna.')
        st.dataframe([{'granulo':e.get('producer_granule_id'), 'inicio':e.get('time_start')} for e in entries],hide_index=True)
        st.download_button('Descargar búsqueda CMR y procedencia',json.dumps(catalog,ensure_ascii=False),'chile-cmr.json','application/json')
    if st.button('Consultar pronóstico del punto'):
        try:
            result=point_forecast(round(point['lat'],3),round(point['lng'],3))
            st.dataframe(result['payload']['daily'])
            st.caption('Open-Meteo · CC BY 4.0 · pronóstico, no observación NISAR. Precipitación en mm; temperatura en °C.')
            st.markdown('[Datos meteorológicos: Open-Meteo](https://open-meteo.com/) · [Condiciones y licencia](https://open-meteo.com/en/terms)')
        except Exception:
            st.warning('Pronóstico no disponible. El mapa sigue disponible.')
