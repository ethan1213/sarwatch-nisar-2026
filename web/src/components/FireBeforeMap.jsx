import { useEffect, useRef } from 'react'
import { Map, NavigationControl } from 'maplibre-gl'
import { CONTEXT_STYLE } from '../mapStyle'

const PRIORITY_COLOR = ['interpolate', ['linear'], ['get', 'priority'], 0, '#28506b', 0.5, '#8c6a3a', 1, '#d1361f']

// Antes: 2,547 cells coloured by the exploratory surveillance-priority index for the chosen
// pass, with an outline on cells where GOES later saw confident heat (held-out passes only).
export default function FireBeforeMap({ cellsGeoJSON, showHot }) {
  const el = useRef(null)
  const map = useRef(null)
  const fitted = useRef(false)

  useEffect(() => {
    const m = new Map({ container: el.current, style: CONTEXT_STYLE, center: [-72.9, -36.7], zoom: 8.5, scrollZoom: false })
    map.current = m
    m.addControl(new NavigationControl())
    return () => m.remove()
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m || !cellsGeoJSON) return
    const apply = () => {
      const source = m.getSource('before-cells')
      if (source) {
        source.setData(cellsGeoJSON)
      } else {
        m.addSource('before-cells', { type: 'geojson', data: cellsGeoJSON })
        m.addLayer({ id: 'before-cells', type: 'fill', source: 'before-cells', paint: { 'fill-color': PRIORITY_COLOR, 'fill-opacity': 0.85 } })
        m.addLayer({ id: 'before-hot', type: 'line', source: 'before-cells', filter: ['==', ['get', 'hot'], 1], paint: { 'line-color': '#fff', 'line-width': 2 } })
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
    if (m.isStyleLoaded()) apply()
    else m.once('load', apply)
  }, [cellsGeoJSON])

  useEffect(() => {
    const m = map.current
    if (!m || !m.getLayer('before-hot')) return
    m.setLayoutProperty('before-hot', 'visibility', showHot ? 'visible' : 'none')
  }, [showHot])

  return <div ref={el} className="fire-map" />
}
