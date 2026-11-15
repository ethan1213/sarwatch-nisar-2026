import { useEffect, useRef } from 'react'
import useSectorOverlay from './useSectorOverlay'
import { Map, NavigationControl } from 'maplibre-gl'
import { FIRE_CONTEXT_STYLE as CONTEXT_STYLE } from '../mapStyle'

const HEAT_COLOR = ['step', ['get', 'heat_state'], 'rgba(60,70,82,0.25)', 1, 'rgba(227,178,60,0.55)', 2, 'rgba(209,54,31,0.92)']

// Durante: 168 ~2x3 km cells coloured by whether GOES saw confident heat in them before/at the
// current hour, plus wind arrows (map-aligned, pointing where the wind blows toward) from the
// nearest ERA5 reanalysis points. Both update in place as the parent advances frameIndex.
export default function FireDuringMap({ cellsGeoJSON, windGeoJSON, onCellClick, selectedCellId, sectorGeometry }) {
  const el = useRef(null)
  const map = useRef(null)
  const onClickRef = useRef(onCellClick)
  onClickRef.current = onCellClick
  const fitted = useRef(false)

  useEffect(() => {
    const m = new Map({ container: el.current, style: CONTEXT_STYLE, center: [-72.9, -36.7], zoom: 9, scrollZoom: false })
    map.current = m
    m.addControl(new NavigationControl())
    m.on('click', 'during-cells', (e) => onClickRef.current?.(e.features[0].properties))
    return () => m.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m || !cellsGeoJSON) return
    const apply = () => {
      const source = m.getSource('during-cells')
      if (source) {
        source.setData(cellsGeoJSON)
      } else {
        m.addSource('during-cells', { type: 'geojson', data: cellsGeoJSON })
        m.addLayer({ id: 'during-cells', type: 'fill', source: 'during-cells', paint: { 'fill-color': HEAT_COLOR, 'fill-outline-color': 'rgba(255,255,255,0.08)' } })
        m.addLayer({ id: 'during-cells-selected', type: 'line', source: 'during-cells', filter: ['==', ['get', 'i'], -1], paint: { 'line-color': '#fff', 'line-width': 2 } })
      }
      if (!fitted.current) {
        const pts = cellsGeoJSON.features.flatMap((f) => f.geometry.coordinates[0])
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
  }, [cellsGeoJSON])

  useEffect(() => {
    const m = map.current
    if (!m || !m.getLayer('during-cells-selected')) return
    m.setFilter('during-cells-selected', ['==', ['get', 'i'], selectedCellId ?? -1])
  }, [selectedCellId])

  useEffect(() => {
    const m = map.current
    if (!m || !windGeoJSON) return
    const apply = () => {
      // Draw arrow geometry directly: works without remote glyph fonts and uses bearings from north.
      const arrows = {type:'FeatureCollection', features:windGeoJSON.features.map(f => {
        const [lon,lat]=f.geometry.coordinates
        const angle=f.properties.bearing*Math.PI/180
        const length=Math.min(0.035, Math.max(0.004, f.properties.speed*0.0006))
        const offset=(a,l)=>[lon+Math.sin(a)*l/Math.cos(lat*Math.PI/180), lat+Math.cos(a)*l]
        const tip=offset(angle,length)
        const wing=a=>[tip[0]-Math.sin(a)*length*0.3/Math.cos(lat*Math.PI/180),tip[1]-Math.cos(a)*length*0.3]
        return {type:'Feature',properties:{},geometry:{type:'MultiLineString',coordinates:[[[lon,lat],tip],[wing(angle-0.5),tip,wing(angle+0.5)]]}}
      })}
      const source = m.getSource('wind')
      if (source) {
        source.setData(arrows)
      } else {
        m.addSource('wind', { type: 'geojson', data: arrows })
        m.addLayer({ id:'wind-arrows', type:'line', source:'wind', paint:{'line-color':'#234b63','line-width':2,'line-opacity':0.8} })
      }
    }
    if (m.getLayer('context')) apply()
    else m.once('load', apply)
  }, [windGeoJSON])

  useSectorOverlay(map,sectorGeometry)
  return <div ref={el} className="fire-map" />
}
