import { useEffect, useRef } from 'react'
import { Map, NavigationControl, Marker } from 'maplibre-gl'
import { FIRE_CONTEXT_STYLE as CONTEXT_STYLE } from '../mapStyle'
import useSectorOverlay from './useSectorOverlay'

const PRIORITY_COLOR = ['interpolate', ['linear'], ['get', 'priority'], 0, '#28506b', 0.5, '#8c6a3a', 1, '#d1361f']

// Antes: 2,547 cells coloured by the exploratory surveillance-priority index for the chosen
// pass, with an outline on cells where GOES later saw confident heat (held-out passes only).
export default function FireBeforeMap({ cellsGeoJSON, showHot, colorExpression = PRIORITY_COLOR, onCellClick, terrain3D = false, satellite = false, focus = null }) {
  const el = useRef(null)
  const map = useRef(null)
  const fitted = useRef(false)
  const onClickRef = useRef(onCellClick)
  useEffect(() => { onClickRef.current = onCellClick }, [onCellClick])

  useEffect(() => {
    const m = new Map({ container: el.current, style: CONTEXT_STYLE, center: [-72.9, -36.7], zoom: 8.5, scrollZoom: true })
    map.current = m
    m.addControl(new NavigationControl())
    m.on('click','before-cells',e=>onClickRef.current?.(e.features[0].properties))
    return () => m.remove()
  }, [])

  useEffect(() => {
    const m=map.current
    if(!m)return
    const apply=()=>{
      if(terrain3D){
        if(!m.getSource('relief-dem')) m.addSource('relief-dem',{type:'raster-dem',tiles:['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],encoding:'terrarium',tileSize:256,maxzoom:15,attribution:'Relieve 3D: Mapzen Terrain Tiles · USGS SRTM/GMTED2010 · NOAA ETOPO1'})
        m.setTerrain({source:'relief-dem',exaggeration:1})
        m.jumpTo({pitch:58,bearing:-20,...(focus?{center:[focus.lon,focus.lat]}:{})})
      }else{m.setTerrain(null);m.jumpTo({pitch:0,bearing:0})}
      if(satellite){
        if(!m.getSource('satellite-context')){
          m.addSource('satellite-context',{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Imagen de contexto © Esri, Maxar, Earthstar Geographics; fecha variable'})
          m.addLayer({id:'satellite-context',type:'raster',source:'satellite-context'},'place-names')
        }
        m.setLayoutProperty('satellite-context','visibility','visible')
        if(m.getLayer('before-cells'))m.setPaintProperty('before-cells','fill-opacity',0.12)
      }else{
        if(m.getLayer('satellite-context'))m.setLayoutProperty('satellite-context','visibility','none')
        if(m.getLayer('before-cells'))m.setPaintProperty('before-cells','fill-opacity',0.85)
      }
      if(m.getLayer('place-names'))m.moveLayer('place-names')
    }
    if(m.getLayer('context'))apply();else m.once('load',apply)
    return ()=>m.off('load',apply)
  },[terrain3D,satellite,focus])

  useEffect(() => {
    const m = map.current
    if (!m || !cellsGeoJSON) return
    const apply = () => {
      const source = m.getSource('before-cells')
      if (source) {
        source.setData(cellsGeoJSON)
      } else {
        m.addSource('before-cells', { type: 'geojson', data: cellsGeoJSON })
        m.addLayer({ id: 'before-cells', type: 'fill', source: 'before-cells', paint: { 'fill-color': colorExpression, 'fill-opacity': satellite ? 0.12 : 0.85 } })
        m.addLayer({ id: 'before-hot', type: 'line', source: 'before-cells', filter: ['==', ['get', 'hot'], 1], paint: { 'line-color': '#fff', 'line-width': 2 } })
      }
      m.setPaintProperty('before-cells','fill-color',colorExpression)
      m.setLayoutProperty('before-hot','visibility',showHot?'visible':'none')
      if (!fitted.current && !focus) {
        const pts = cellsGeoJSON.bbox ? [[cellsGeoJSON.bbox[0],cellsGeoJSON.bbox[1]],[cellsGeoJSON.bbox[2],cellsGeoJSON.bbox[3]]] : cellsGeoJSON.features.flatMap((f) => f.geometry.coordinates[0])
        if (pts.length) {
          m.fitBounds(
            [
              [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1]))],
              [Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))],
            ],
            { padding: 30, duration: 0 },
          )
          fitted.current = true
        }
      }
      m.moveLayer('place-names')
    }
    if (m.getLayer('context')) apply()
    else m.once('load', apply)
  }, [cellsGeoJSON, colorExpression, showHot, satellite, focus])

  useEffect(() => {
    const m = map.current
    if (!m || !m.getLayer('before-hot')) return
    m.setLayoutProperty('before-hot', 'visibility', showHot ? 'visible' : 'none')
  }, [showHot])

  useEffect(()=>{if(!focus||!map.current)return;const marker=new Marker({color:'#d6f84c'}).setLngLat([focus.lon,focus.lat]).addTo(map.current);return()=>marker.remove()},[focus])
  useSectorOverlay(map,focus?.windContext?.geometry)
  return <div><div className="fire-controls"><button onClick={()=>map.current?.easeTo({bearing:0,pitch:0})}>Vista desde arriba</button>{terrain3D&&<><button onClick={()=>map.current?.easeTo({pitch:55})}>Inclinar relieve</button><button onClick={()=>map.current?.easeTo({bearing:map.current.getBearing()+45})}>Girar 45°</button></>}<button onClick={()=>{const b=cellsGeoJSON?.bbox;if(b)map.current?.fitBounds([[b[0],b[1]],[b[2],b[3]]],{padding:30,pitch:terrain3D?55:0});else map.current?.easeTo({center:[-72.9,-36.7],zoom:8.5,bearing:0,pitch:terrain3D?55:0})}}>Volver al área</button></div><div ref={el} className="fire-map" /></div>
}
