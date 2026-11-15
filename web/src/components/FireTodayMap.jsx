import { useEffect, useRef } from 'react'
import { Map, NavigationControl } from 'maplibre-gl'
import { CONTEXT_STYLE } from '../mapStyle'

// "Hoy" mode: live VIIRS points (FIRMS), click reports lat/lon up so the parent can fetch a
// forecast for that point. Adapted from HotspotMap.jsx rather than editing it, since that
// component is shared with ChileView (out of scope for this package).
export default function FireTodayMap({ data, bbox, onSelect }) {
  const el = useRef(null)
  const map = useRef(null)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

  useEffect(() => {
    const m = new Map({ container: el.current, style: CONTEXT_STYLE, center: [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2], zoom: 8, scrollZoom: false })
    map.current = m
    m.addControl(new NavigationControl())
    m.on('click', 'today-hotspots', (e) => {
      const f = e.features[0]
      onSelectRef.current?.({ lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0], properties: f.properties })
    })
    m.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 35, duration: 0 })
    return () => m.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bbox])

  useEffect(() => {
    if (!data || !map.current) return
    const m = map.current
    const apply = () => {
      if (m.getSource('today-hotspots')) m.getSource('today-hotspots').setData(data)
      else {
        m.addSource('today-hotspots', { type: 'geojson', data })
        m.addLayer({ id: 'today-hotspots', type: 'circle', source: 'today-hotspots', paint: { 'circle-radius': 7, 'circle-color': '#e07a2c', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5, 'circle-opacity': 0.9 } })
      }
      m.moveLayer('place-names')
    }
    if (m.isStyleLoaded()) apply()
    else m.once('load', apply)
  }, [data])

  return <div ref={el} className="fire-map" />
}
