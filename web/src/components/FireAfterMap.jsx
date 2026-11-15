import { useEffect, useRef } from 'react'
import { Map } from 'maplibre-gl'
import { FIRE_CONTEXT_STYLE as CONTEXT_STYLE } from '../mapStyle'
import { fireAssetUrl } from '../api'

function boundsToCoordinates(bounds) {
  const { west, east, south, north } = bounds
  return [[west, north], [east, north], [east, south], [west, south]]
}
function boundsToLngLatBounds(bounds) {
  return [[bounds.west, bounds.south], [bounds.east, bounds.north]]
}

function useRadarLayer(ref, layerId, radar, severityOn, severity) {
  useEffect(() => {
    const m = ref.current
    if (!m || !radar) return
    const apply = () => {
      const coords = boundsToCoordinates(radar.bounds)
      const url = radar.url || fireAssetUrl(radar.png)
      let source = m.getSource(layerId)
      if (source) source.updateImage({ url, coordinates: coords })
      else {
        m.addSource(layerId, { type: 'image', url, coordinates: coords })
        m.addLayer({ id: layerId, type: 'raster', source: layerId })
      }
      const sevId = layerId + '-severity'
      if (severityOn && severity) {
        const sevCoords = boundsToCoordinates(severity.bounds)
        const sevUrl = fireAssetUrl(severity.png)
        let sevSource = m.getSource(sevId)
        if (sevSource) sevSource.updateImage({ url: sevUrl, coordinates: sevCoords })
        else {
          m.addSource(sevId, { type: 'image', url: sevUrl, coordinates: sevCoords })
          m.addLayer({ id: sevId, type: 'raster', source: sevId, paint: { 'raster-opacity': 0.75 } })
        }
      } else if (m.getLayer(sevId)) {
        m.removeLayer(sevId)
        m.removeSource(sevId)
      }
      if (m.getLayer('place-names')) m.moveLayer('place-names')
    }
    if (m.getLayer('context')) apply()
    else m.once('load', apply)
  }, [ref, layerId, radar, severityOn, severity])
}

// Side-by-side comparator between two NISAR radar dates, with an optional dNBR severity
// overlay. Both panes share one fitBounds call so the clip-path slider lines up pixel for pixel.
function RadarComparator({ left, right, severityOn, severity, single = false }) {
  const elA = useRef(null)
  const elB = useRef(null)
  const mapA = useRef(null)
  const mapB = useRef(null)
  const fitted = useRef(false)

  useEffect(() => {
    mapA.current = new Map({ container: elA.current, style: CONTEXT_STYLE, center: [-72.9, -36.7], zoom: 9, scrollZoom: false, interactive: false })
    mapB.current = new Map({ container: elB.current, style: CONTEXT_STYLE, center: [-72.9, -36.7], zoom: 9, scrollZoom: false, interactive: false })
    return () => {
      mapA.current.remove()
      mapB.current.remove()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!left || !mapA.current || fitted.current) return
    const bounds = boundsToLngLatBounds(left.bounds)
    const apply = () => {
      mapA.current.fitBounds(bounds, { padding: 10, duration: 0 })
      mapB.current.fitBounds(bounds, { padding: 10, duration: 0 })
      fitted.current = true
    }
    if (mapA.current.getLayer('context') && mapB.current.getLayer('context')) apply()
    else { mapA.current.once('load', () => { if (mapB.current.getLayer('context')) apply() }); mapB.current.once('load', () => { if (mapA.current.getLayer('context')) apply() }) }
  }, [left])

  useRadarLayer(mapA, 'radar-a', left, severityOn, severity)
  useRadarLayer(mapB, 'radar-b', right, severityOn, severity)

  return (
    <div className="fire-compare">
      <div className="fire-map-a" ref={elA} />
      <div className="fire-map-b" ref={elB} style={{ '--clip': single ? '0%' : '50%' }} id="fire-compare-b" />
      {!single && <input
        type="range"
        className="fire-slider"
        min={0}
        max={100}
        defaultValue={50}
        onChange={(e) => {
          document.getElementById('fire-compare-b').style.setProperty('--clip', `${e.target.value}%`)
        }}
        aria-label="Comparar fechas"
      />}
      <span className="fire-compare-label left">{single ? 'Señal óptica de quema · Sentinel-2' : left?.date}</span>
      {!single && <span className="fire-compare-label right">{right?.date}</span>}
    </div>
  )
}

function ScarMap({ severity }) {
  const el = useRef(null), ref = useRef(null)
  useEffect(() => {
    const m = new Map({container:el.current, style:CONTEXT_STYLE, scrollZoom:false, center:[-72.9,-36.7], zoom:9})
    ref.current=m
    m.once('load',()=>m.fitBounds(boundsToLngLatBounds(severity.bounds),{padding:20,duration:0}))
    return ()=>m.remove()
  }, [severity])
  useRadarLayer(ref,'scar',severity,false,null)
  return <div ref={el} className="fire-map" aria-label="Señal óptica de quema Sentinel-2" />
}
export default function FireAfterMap(props) {
  return props.single ? <ScarMap severity={props.severity} /> : <RadarComparator {...props} />
}
