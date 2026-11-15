import { Map as MapLibreMap, NavigationControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
import { CONTEXT_STYLE } from '../mapStyle'

const STYLE = CONTEXT_STYLE

function boundsToCoordinates(bounds) {
  const { west, east, south, north } = bounds
  return [
    [west, north],
    [east, north],
    [east, south],
    [west, south],
  ]
}

function boundsToLngLatBounds(bounds) {
  return [
    [bounds.west, bounds.south],
    [bounds.east, bounds.north],
  ]
}

// Generic SAR image-overlay map: one continuous base layer (before/after/diff, from
// /api/pantanal/layer) plus an optional categorical overlay (water/change masks). Both
// images already arrive reprojected to plain lon/lat (EPSG:4326) from the API, which is
// exactly what MapLibre's image source expects when given the four corner coordinates.
export default function SarMap({ layer, overlay, onPointClick }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const fittedRef = useRef(false)
  const onPointRef = useRef(onPointClick)
  onPointRef.current = onPointClick

  useEffect(() => {
    const map = new MapLibreMap({ container: containerRef.current, style: STYLE, center: [0, 0], zoom: 1 })
    mapRef.current = map
    map.addControl(new NavigationControl(), 'top-right')
    map.on('click', (e) => onPointRef.current?.(e.lngLat.lng, e.lngLat.lat))
    return () => map.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !layer) return
    const apply = () => {
      const coordinates = boundsToCoordinates(layer.bounds)
      const source = map.getSource('sar-layer')
      if (source) {
        source.updateImage({ url: layer.png_data_url, coordinates })
      } else {
        map.addSource('sar-layer', { type: 'image', url: layer.png_data_url, coordinates })
        map.addLayer({ id: 'sar-layer', type: 'raster', source: 'sar-layer', paint: { 'raster-opacity': 1 } })
      }
      if (!fittedRef.current) {
        map.fitBounds(boundsToLngLatBounds(layer.bounds), { padding: 20, duration: 0 })
        fittedRef.current = true
      }
    }
    if (map.isStyleLoaded()) apply()
    else map.once('load', apply)
  }, [layer])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const apply = () => {
      if (!overlay) {
        if (map.getLayer('water-layer')) map.removeLayer('water-layer')
        if (map.getSource('water-layer')) map.removeSource('water-layer')
        return
      }
      const coordinates = boundsToCoordinates(overlay.bounds)
      const source = map.getSource('water-layer')
      if (source) {
        source.updateImage({ url: overlay.png_data_url, coordinates })
      } else {
        map.addSource('water-layer', { type: 'image', url: overlay.png_data_url, coordinates })
        map.addLayer({ id: 'water-layer', type: 'raster', source: 'water-layer', paint: { 'raster-opacity': 1 } })
      }
    }
    if (map.isStyleLoaded()) apply()
    else map.once('load', apply)
  }, [overlay])

  return <div ref={containerRef} className="mundo-map" />
}
