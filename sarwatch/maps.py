"""Geographic views; scientific rasters remain separate from display sampling."""
import json
import os
from pathlib import Path
import folium
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
from streamlit_folium import st_folium
import streamlit as st
import rasterio
from sarwatch.repository import RasterRepository
from science import difference
from sarwatch.interpretation import summarize
from sarwatch.guidance import reading,assistant
from sarwatch.detections import CHANGE_LABEL, categorical_overlay, change_mask_path, change_sentence, detection_reference, read_mask


@st.cache_data(max_entries=8)
def regional_raster(path):
    with rasterio.open(path) as source:
        return source.read(1),source.transform,str(source.crs)


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
    normalized = np.clip((output+6)/12 if changes else (output+30)/40,0,1)
    rgba = np.zeros((h,w,4),dtype='uint8')
    # Blue-neutral-orange diverging scale; opacity distinguishes missing data.
    low=np.array([32,91,135.]);mid=np.array([242,242,232.]);high=np.array([198,96,28.])
    z=np.nan_to_num(normalized)
    rgb=np.where((z<=.5)[:,:,None],low+(mid-low)*(z*2)[:,:,None],mid+(high-mid)*((z-.5)*2)[:,:,None])
    rgba[:,:,:3]=rgb.astype('uint8')
    rgba[:,:,3] = np.isfinite(output).astype('uint8')*190
    m = base_map([(south+north)/2,(west+east)/2],10)
    folium.raster_layers.ImageOverlay(rgba, bounds=[[south,west],[north,east]], name='NISAR · diferencia dB' if changes else 'NISAR · retrodispersión dB', mercator_project=True).add_to(m)
    m.fit_bounds([[south,west],[north,east]])
    folium.LayerControl().add_to(m)
    return m


def chile_view(region,profile="Público general"):
    slug = 'metropolitana' if region == 'Región Metropolitana' else 'valparaiso'
    center = [-33.45,-70.66] if slug=='metropolitana' else [-33.047,-71.613]
    st.subheader(region)
    summary_area=st.container()
    framing = st.radio('Encuadre', ['Región completa', 'Santiago' if slug=='metropolitana' else 'Valparaíso / Viña del Mar'], horizontal=True,index=1)
    st.caption('Las líneas delimitan comunas. La capa coloreada muestra las observaciones del recorte urbano; fuera de ella no publicamos resultados SAR.')
    m=base_map(center,9)
    path=Path('catalog')/(slug+'.geojson')
    if path.is_file():
        data=json.loads(path.read_text(encoding='utf-8'))
        boundaries = folium.GeoJson(data,name='Límites comunales · CIREN',style_function=lambda f:{'fillColor':'#397a85','color':'#245360','weight':1,'fillOpacity':.08},tooltip=folium.GeoJsonTooltip(fields=['nomcom'], aliases=['Comuna'])).add_to(m)
        if framing == 'Región completa':
            m.fit_bounds(boundaries.get_bounds())
    folium.Marker([-33.45,-70.66],tooltip='Santiago').add_to(m)
    folium.Marker([-33.047,-71.613],tooltip='Valparaíso').add_to(m)
    products_root=Path(os.environ.get('DATA_DIR','data'))/slug
    manifest=None
    if (products_root/'manifest.json').is_file():
        repository=RasterRepository(products_root)
        manifest=repository.manifest()
        st.caption('NISAR: recorte del entorno urbano seleccionado, no cobertura completa de la región.')
        pol=st.selectbox('Polarización SAR',['HH','HV'],key=slug+'-pol')
        scenes=manifest['scenes']
        dates=[s['fecha_observacion'][:10] for s in scenes]
        view=st.radio('Capa SAR',[dates[0],dates[-1],'Diferencia en dB'],horizontal=True,index=2,key=slug+'-sar')
        before,t,c=regional_raster(str(repository.product_path(scenes[0]['products'][pol])))
        after,t2,c2=regional_raster(str(repository.product_path(scenes[-1]['products'][pol])))
        if t!=t2 or c!=c2 or before.shape!=after.shape:
            st.error('Las grillas SAR no coinciden. Capa temporal desactivada.')
            manifest=None
        else:
            values=difference(before,after) if view=='Diferencia en dB' else before if view==dates[0] else after
            overlay_map=raster_map(values,t,c,view=='Diferencia en dB')
            for child in list(overlay_map._children.values()):
                if isinstance(child,folium.raster_layers.ImageOverlay):
                    child.add_to(m)
            context={'region':region,'before':dates[0],'after':dates[-1],'polarization':pol,'statistics':summarize(before,after),'source':scenes[-1]['url_metadatos']}
            with summary_area:
                reading(context,profile)
            change_path=change_mask_path(products_root)
            if change_path is not None and st.checkbox('Mostrar cambio estadísticamente significativo',value=view=='Diferencia en dB',key=slug+'-change'):
                mask,mt,mc,tags=read_mask(change_path)
                if (mt,mc,mask.shape)!=(t,c,before.shape):
                    st.error('La máscara de cambio no comparte la grilla SAR; no se muestra.')
                else:
                    categorical_overlay(mask,mt,mc,'change',CHANGE_LABEL).add_to(m)
                    reference=detection_reference()
                    st.caption('Azul: disminución significativa de la señal; naranja: aumento. '+change_sentence(reference,slug))
                    if profile in ('Ciencia','Desarrollo y datos'):
                        block=((reference or {}).get('change') or {}).get(slug)
                        if block:
                            st.dataframe([{'cobertura (WorldCover 2021)':k,'píxeles':v['n'],'disminución %':round(100*(v['decrease'] or 0),3),'aumento %':round(100*(v['increase'] or 0),3)} for k,v in block['by_worldcover'].items()],hide_index=True)
                            st.caption(f"Método: {tags.get('method','')}. Looks: {block['looks_source']}. Acuerdo con umbral MAD (IoU): {block['agreement_iou_with_mad']:.2f}.")
            st.metric('Cobertura comparable del recorte',f'{np.isfinite(difference(before,after)).mean():.1%}')
            st.caption('Naranja: mayor respuesta; azul: menor. El tono claro indica diferencia cerca de cero. Diferencia: −6 a +6 dB; intensidad: −30 a 10 dB. Transparente: sin dato. Cambios de radar no equivalen a inundaciones.')
    folium.LayerControl().add_to(m)
    event=st_folium(m,height=560,use_container_width=True,key='chile-'+slug+framing,returned_objects=['last_clicked'])
    point=event.get('last_clicked') or {'lat':center[0],'lng':center[1]}
    st.caption(f"Punto seleccionado: {point['lat']:.5f}, {point['lng']:.5f}. Haz clic en el mapa para cambiarlo.")
    if manifest is not None:
        import pandas as pd
        frame=pd.DataFrame(repository.point_series(manifest['scenes'],pol,point['lng'],point['lat']))
        st.dataframe(frame if profile in ('Ciencia','Desarrollo y datos') else frame[['fecha','dB']],hide_index=True,column_config={'dB':st.column_config.NumberColumn('Respuesta del radar (dB)',format='%.2f'),'fecha':st.column_config.TextColumn('Fecha de observación (UTC)')})
        if frame['dB'].isna().all():
            st.warning('El punto no tiene valores SAR válidos; selecciona uno dentro de la capa coloreada.')
        assistant(context,profile)
        st.download_button('Descargar serie SAR del punto',frame.to_csv(index=False),slug+'-serie.csv','text/csv')
        with st.expander('Calidad y procedencia SAR'):
            st.write(manifest['quality_status'])
            st.json(manifest['scenes'])
    else:
        st.info('No hay una serie SAR procesada disponible para este recorte.')
    with st.expander('Catálogo de adquisiciones · detalle de datos'):
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
