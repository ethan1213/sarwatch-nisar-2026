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
from sarwatch.theme import scale_legend
from sarwatch.views.components import percent, short_date
from sarwatch.detections import CHANGE_LABEL, categorical_overlay, image_overlay, change_mask_path, change_sentence, detection_reference, read_mask
from sarwatch.postfire import SCENARIO_LABELS, postfire_reference, scenario_sentence, semaphore_overlay, semaphore_path
from sarwatch.postfire import read_mask as read_postfire_mask


@st.cache_data(max_entries=8)
def regional_raster(path):
    with rasterio.open(path) as source:
        return source.read(1),source.transform,str(source.crs)


@st.cache_data(ttl=3600, max_entries=32)
def point_forecast(latitude, longitude):
    from weather import fetch_weather
    return fetch_weather(latitude, longitude)


ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/'
ESRI_ATTRIBUTION = 'Mapa base © Esri, HERE, Garmin, © OpenStreetMap'
MAP_CSS = '<style>.leaflet-container{font-family:system-ui,sans-serif}.leaflet-control-attribution{font-size:10px;line-height:1.4}.leaflet-control-scale-line{font-size:10px}</style>'


def base_map(center, zoom=9):
    """Quiet grey base so the radar layer carries the colour; satellite imagery stays one click away."""
    m = folium.Map(location=center, zoom_start=zoom, tiles=None, control_scale=True)
    m.get_root().header.add_child(folium.Element(MAP_CSS))
    folium.TileLayer(ESRI + 'World_Imagery/MapServer/tile/{z}/{y}/{x}', attr=ESRI_ATTRIBUTION, name='Imagen satelital de contexto (no NISAR)', show=False).add_to(m)
    folium.TileLayer(ESRI + 'Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attr=ESRI_ATTRIBUTION, name='Mapa base').add_to(m)
    folium.TileLayer(ESRI + 'Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', attr=ESRI_ATTRIBUTION, name='Nombres de lugares', overlay=True, control=False).add_to(m)
    return m


def place_marker(location, label):
    """Circle marker: the default Leaflet pin loads its image from a CDN path that breaks."""
    return folium.CircleMarker(location, radius=5, color='#10293a', weight=2, fill=True, fill_color='#ffffff', fill_opacity=1, tooltip=label)


def raster_map(values, transform, crs, changes=False, layer_control=True):
    """layer_control=False lets the caller add more layers first; the control must be added last."""
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
    image_overlay(rgba, [[south,west],[north,east]], 'NISAR · diferencia dB' if changes else 'NISAR · retrodispersión dB').add_to(m)
    m.fit_bounds([[south,west],[north,east]])
    if layer_control:
        folium.LayerControl().add_to(m)
    return m


def chile_view(region,profile="Público general"):
    slug = 'metropolitana' if region == 'Región Metropolitana' else 'valparaiso'
    center = [-33.45,-70.66] if slug=='metropolitana' else [-33.047,-71.613]
    st.subheader(region)
    map_column, reading_column = st.columns([3, 2], gap='large')
    summary_area=reading_column.container()
    with map_column:
        controls, legend_slot, map_slot, notes = st.container(), st.container(), st.container(), st.container()
        row = controls.columns([5, 3, 6])
        framing = row[0].radio('Encuadre', ['Región completa', 'Santiago' if slug=='metropolitana' else 'Valparaíso / Viña del Mar'], horizontal=True,index=1)
        notes.caption('Las líneas delimitan comunas. La capa coloreada muestra las observaciones del recorte urbano; fuera de ella no publicamos resultados SAR.')
        m=base_map(center,9)
        path=Path('catalog')/(slug+'.geojson')
        if path.is_file():
            data=json.loads(path.read_text(encoding='utf-8'))
            boundaries = folium.GeoJson(data,name='Límites comunales · CIREN',style_function=lambda f:{'fillColor':'#397a85','color':'#245360','weight':1,'fillOpacity':.08},tooltip=folium.GeoJsonTooltip(fields=['nomcom'], aliases=['Comuna'])).add_to(m)
            if framing == 'Región completa':
                m.fit_bounds(boundaries.get_bounds())
        place_marker([-33.45,-70.66],'Santiago').add_to(m)
        place_marker([-33.047,-71.613],'Valparaíso').add_to(m)
        products_root=Path(os.environ.get('DATA_DIR','data'))/slug
        manifest=None
        if (products_root/'manifest.json').is_file():
            repository=RasterRepository(products_root)
            manifest=repository.manifest()
            notes.caption('NISAR: recorte del entorno urbano seleccionado, no cobertura completa de la región.')
            pol=row[1].selectbox('Polarización SAR',['HH','HV'],key=slug+'-pol')
            scenes=manifest['scenes']
            dates=[s['fecha_observacion'][:10] for s in scenes]
            view=row[2].radio('Capa SAR',[dates[0],dates[-1],'Diferencia en dB'],horizontal=True,index=2,key=slug+'-sar',format_func=lambda value: 'Diferencia' if value=='Diferencia en dB' else short_date(value))
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
                        if framing != 'Región completa':
                            m.fit_bounds(child.bounds)
                context={'region':region,'before':dates[0],'after':dates[-1],'polarization':pol,'statistics':summarize(before,after),'source':scenes[-1]['url_metadatos']}
                with summary_area:
                    reading(context,profile)
                # Solo una capa categórica a la vez: apilar "cambio significativo" y "PostFuego" sobre la
                # diferencia continua produce una mezcla óptica de colores que no se distingue (bug real
                # reportado por el usuario: "se ve todo el mapa de un color"). Un selector único evita
                # que dos capas semitransparentes se mezclen entre sí.
                change_path=change_mask_path(products_root)
                postfire_ref=postfire_reference() if slug=='metropolitana' else None
                layer_options=['Ninguna']
                if change_path is not None:
                    layer_options.append('Cambio estadísticamente significativo')
                if postfire_ref is not None:
                    layer_options.append('PostFuego · semáforo de aluvión')
                extra_layer=controls.radio('Capa adicional',layer_options,index=1 if len(layer_options)>1 else 0,horizontal=True,key=slug+'-extra-layer') if len(layer_options)>1 else 'Ninguna'
                if extra_layer=='Cambio estadísticamente significativo':
                    mask,mt,mc,tags=read_mask(change_path)
                    if (mt,mc,mask.shape)!=(t,c,before.shape):
                        st.error('La máscara de cambio no comparte la grilla SAR; no se muestra.')
                    else:
                        categorical_overlay(mask,mt,mc,'change',CHANGE_LABEL).add_to(m)
                        reference=detection_reference()
                        notes.caption('Azul: disminución significativa de la señal; naranja: aumento. '+change_sentence(reference,slug))
                        if profile in ('Ciencia','Desarrollo y datos'):
                            block=((reference or {}).get('change') or {}).get(slug)
                            if block:
                                notes.dataframe([{'cobertura (WorldCover 2021)':k,'píxeles':v['n'],'disminución %':round(100*(v['decrease'] or 0),3),'aumento %':round(100*(v['increase'] or 0),3)} for k,v in block['by_worldcover'].items()],hide_index=True)
                                notes.caption(f"Método: {tags.get('method','')}. Looks: {block['looks_source']}. Acuerdo con umbral MAD (IoU): {block['agreement_iou_with_mad']:.2f}.")
                elif extra_layer=='PostFuego · semáforo de aluvión':
                    notes.caption('Prueba de concepto heurística y no calibrada (caso Quebrada Honda, Las Condes). No es una alerta operativa. Detalle en docs/postfuego_las_condes.md.')
                    scenario_key=controls.radio('Escenario PostFuego',list(SCENARIO_LABELS),format_func=lambda k:SCENARIO_LABELS[k],horizontal=True,key=slug+'-postfire-scenario')
                    sema_path=semaphore_path(products_root,scenario_key)
                    if sema_path is not None:
                        sema_mask,st_,sc_,_=read_postfire_mask(sema_path)
                        if (st_,sc_,sema_mask.shape)==(t,c,before.shape):
                            semaphore_overlay(sema_mask,st_,sc_,'PostFuego · semáforo').add_to(m)
                        else:
                            notes.error('La capa PostFuego no comparte la grilla SAR; no se muestra.')
                    notes.caption(scenario_sentence(postfire_ref,scenario_key))
                with legend_slot:
                    scale_legend(view=='Diferencia en dB')
                notes.metric('Cobertura comparable del recorte',percent(np.isfinite(difference(before,after)).mean()))
                notes.caption('Escala de −6 a +6 dB en diferencias y de −30 a 10 dB en intensidad. Transparente: sin dato. Cambios de radar no equivalen a inundaciones.')
        folium.LayerControl().add_to(m)
        with map_slot:
            event=st_folium(m,height=600,use_container_width=True,key='chile-'+slug+framing,returned_objects=['last_clicked'])
        point=event.get('last_clicked') or {'lat':center[0],'lng':center[1]}
        map_slot.caption(f"Punto seleccionado: {point['lat']:.5f}, {point['lng']:.5f}. Haz clic en el mapa para cambiarlo.")
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
