import { Map, Marker, NavigationControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
import { stepExpression } from '../colorScale'
import { SITES } from '../sites'
import { CONTEXT_STYLE } from '../mapStyle'

const CELLS_SOURCE = 'nisar-cells'
const CELLS_LAYER = 'nisar-cells-fill'

// Dark, neutral basemap drawn from OSM-derived vector tiles would need a key; for a dependency-free
// start we render cells over a plain background and let the fill layer itself carry all the signal.
const STYLE = CONTEXT_STYLE

export default function MundoMap({ cellsGeoJSON, onPointClick }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)

  useEffect(() => {
    const map = new Map({
      container: containerRef.current,
      style: STYLE,
      center: [0, 10],
      zoom: 1.4,
      minZoom: 1,
      maxZoom: 9,
    })
    mapRef.current = map
    map.addControl(new NavigationControl(), 'top-right')

    map.on('load', () => {
      for (const site of SITES) {
        const el = document.createElement('div')
        el.className = 'site-marker'
        el.title = `${site.name}: procesado y evaluado en SARWatch`
        new Marker({ element: el }).setLngLat([site.lon, site.lat]).addTo(map)
      }
    })

    map.on('click', (e) => {
      onPointClick(e.lngLat.lng, e.lngLat.lat)
    })
    map.on('mouseenter', CELLS_LAYER, () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', CELLS_LAYER, () => { map.getCanvas().style.cursor = '' })

    return () => map.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !cellsGeoJSON) return
    const apply = () => {
      if (map.getSource(CELLS_SOURCE)) {
        map.getSource(CELLS_SOURCE).setData(cellsGeoJSON)
        return
      }
      map.addSource(CELLS_SOURCE, { type: 'geojson', data: cellsGeoJSON })
      map.addLayer({
        id: CELLS_LAYER,
        type: 'fill',
        source: CELLS_SOURCE,
        paint: {
          'fill-color': stepExpression(),
          'fill-opacity': 0.75,
          'fill-outline-color': 'rgba(0,0,0,0.15)',
        },
      })
    }
    if (map.isStyleLoaded()) apply()
    else map.once('load', apply)
  }, [cellsGeoJSON])

  return <div ref={containerRef} className="mundo-map" />
}
