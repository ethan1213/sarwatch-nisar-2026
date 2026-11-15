import { useEffect, useMemo, useRef, useState } from 'react'
import { Map, NavigationControl } from 'maplibre-gl'
import { CONTEXT_STYLE } from '../mapStyle'

export default function ThermalMap({ data }) {
  const container = useRef(null), map = useRef(null)
  const [selected, setSelected] = useState(null)
  const range = useMemo(() => {
    const values = (data?.features || []).map(f => f.properties.value).filter(v => v != null)
    return values.length ? [Math.min(...values), Math.max(...values)] : null
  }, [data])
  useEffect(() => {
    const m = new Map({ container: container.current, style: CONTEXT_STYLE, scrollZoom: true })
    map.current = m
    m.addControl(new NavigationControl())
    m.on('click', 'heat', e => setSelected(e.features[0].properties))
    return () => m.remove()
  }, [])
  useEffect(() => {
    if (!data || !map.current) return
    const m = map.current
    const apply = () => {
      const numbers = data.features.map(f => f.properties.value).filter(v => v != null)
      const low = numbers.length ? Math.min(...numbers) : 0, high = Math.max(...numbers, low + 1)
      const source = m.getSource('cells')
      if (source) source.setData(data)
      else {
        m.addSource('cells', { type: 'geojson', data })
        m.addLayer({ id: 'heat', type: 'fill', source: 'cells', paint: { 'fill-opacity': .85, 'fill-outline-color': '#66788a', 'fill-color': '#e9a55f' } })
        const points = data.features.flatMap(f => f.geometry.coordinates[0])
        m.fitBounds([[Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1]))], [Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))]], { padding: 30, duration: 0 })
      }
      m.setPaintProperty('heat', 'fill-color', ['case', ['==', ['get', 'value'], null], '#172331', ['interpolate', ['linear'], ['get', 'value'], low, '#f7ecd9', high, '#a23e12']])
      m.moveLayer('place-names')
      setSelected(null)
    }
    if (m.isStyleLoaded()) apply(); else m.once('load', apply)
  }, [data])
  return <><div className="mundo-map" ref={container} /><div className="map-legend"><span>Claro: menor valor · oscuro: mayor valor</span>{range && <span>{range[0].toFixed(1)} a {range[1].toFixed(1)} · {data.features[0]?.properties.units}</span>}</div><p className="map-action">⌖ Selecciona una celda para consultar su valor.</p>{selected && <p>Celda seleccionada: {selected.value ?? 'sin dato'} {selected.units}</p>}</>
}
