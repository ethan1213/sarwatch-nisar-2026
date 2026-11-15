import { useEffect, useRef, useState } from 'react'
import { Map, NavigationControl } from 'maplibre-gl'
import { CONTEXT_STYLE } from '../mapStyle'

export default function HotspotMap({ data, bbox }) {
  const el = useRef(null), map = useRef(null)
  const [selected, setSelected] = useState(null)
  useEffect(() => {
    const m = new Map({ container: el.current, style: CONTEXT_STYLE, center: [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2], zoom: 9, scrollZoom: false })
    map.current = m
    m.addControl(new NavigationControl())
    m.on('click', 'hotspots', e => setSelected(e.features[0].properties))
    m.fitBounds([[bbox[0],bbox[1]],[bbox[2],bbox[3]]], { padding: 35, duration: 0 })
    return () => m.remove()
  }, [bbox])
  useEffect(() => {
    if (!data || !map.current) return
    const m = map.current
    const apply = () => {
      if (m.getSource('hotspots')) m.getSource('hotspots').setData(data)
      else {
        m.addSource('hotspots', { type: 'geojson', data })
        m.addLayer({ id: 'hotspots', type: 'circle', source: 'hotspots', paint: { 'circle-radius': 6, 'circle-color': ['match',['get','confidence'],'h','#b73522','n','#e87826','#c8a878'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5, 'circle-opacity': .85 } })
      }
      m.moveLayer('place-names')
    }
    if (m.isStyleLoaded()) apply(); else m.once('load', apply)
  }, [data])
  return <><div ref={el} className="hotspot-map" />{selected && <div className="map-selection"><strong>Detección de calor</strong><span>{selected.sensor} · {selected.utc}</span><span>Potencia radiativa: {selected.frp_mw ?? 'sin dato'} MW · no es CO₂ ni área quemada.</span></div>}</>
}
