import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchChileOverview, fetchFireForecast } from '../api'
import FireDuringMap from './FireDuringMap'
import FireTodayMap from './FireTodayMap'
import FireWeatherCard from './FireWeatherCard'

const COVER_LABELS = [
  ['trees', 'bosque'],
  ['crops', 'cultivo'],
  ['grass', 'pastizal'],
  ['urban', 'urbano'],
]

function dominantCover(props) {
  let best = null
  for (const [key, label] of COVER_LABELS) {
    if (props[key] != null && (!best || props[key] > best[1])) best = [label, props[key]]
  }
  return best ? `${best[0]} (${Math.round(best[1] * 100)}%)` : null
}

function localTime(iso) {
  // Chile in January is UTC-3 (no DST ambiguity needed for this fixed historical window).
  const d = new Date(iso.replace('Z', '+00:00'))
  d.setUTCHours(d.getUTCHours() - 3)
  return d.toLocaleString('es-CL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
}

function nearestPointIndex(points, lon, lat) {
  let best = 0
  let bestD = Infinity
  points.forEach((p, i) => {
    const d = (p.lon - lon) ** 2 + (p.lat - lat) ** 2
    if (d < bestD) {
      bestD = d
      best = i
    }
  })
  return best
}

function cellCentroid(feature) {
  const ring = feature.geometry.coordinates[0]
  const lon = ring.reduce((s, p) => s + p[0], 0) / ring.length
  const lat = ring.reduce((s, p) => s + p[1], 0) / ring.length
  return [lon, lat]
}

export default function FireDuring({ data }) {
  const [frameIndex, setFrameIndex] = useState(() => data.frames.reduce((best,f,i,all) => f.cells.length > all[best].cells.length ? i : best, 0))
  const [playing, setPlaying] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [todayMode, setTodayMode] = useState(false)
  const [todayOverview, setTodayOverview] = useState(null)
  const [todayPoint, setTodayPoint] = useState(null)
  const [todayForecast, setTodayForecast] = useState(null)
  const [forecastError, setForecastError] = useState('')
  const timer = useRef(null)

  const frames = data.frames
  const timeIndex = useMemo(() => data.weather.times.indexOf(frames[frameIndex].t), [data, frames, frameIndex])

  useEffect(() => {
    if (!playing) {
      clearInterval(timer.current)
      return
    }
    timer.current = setInterval(() => setFrameIndex((i) => (i + 1 >= frames.length ? 0 : i + 1)), 350)
    return () => clearInterval(timer.current)
  }, [playing, frames.length])

  useEffect(() => {
    if (!todayMode || todayOverview) return
    fetchChileOverview('biobio').then(setTodayOverview).catch(() => setTodayOverview({ firms: null, audit: { bbox: [-73.6, -37.6, -72.3, -36.3] } }))
  }, [todayMode, todayOverview])

  useEffect(() => {
    if (!todayPoint) return
    let alive = true
    fetchFireForecast(todayPoint.lat, todayPoint.lon)
      .then((d) => { if (alive) setTodayForecast({ lat: todayPoint.lat, lon: todayPoint.lon, data: d }) })
      .catch(() => { if (alive) setForecastError('El pronóstico no está disponible. Selecciona otro punto para reintentar.') })
    return () => { alive = false }
  }, [todayPoint])

  const cellsById = useMemo(() => new Map(data.cells.features.map((f) => [f.properties.i, f])), [data])

  const cellsGeoJSON = useMemo(() => {
    const hotSoFar = new Set()
    for (let k = 0; k <= frameIndex; k++) frames[k].cells.forEach((i) => hotSoFar.add(i))
    const hotNow = new Set(frames[frameIndex].cells)
    return {
      type: 'FeatureCollection',
      features: data.cells.features.map((f) => ({ ...f, properties: { ...f.properties, heat_state: hotNow.has(f.properties.i) ? 2 : hotSoFar.has(f.properties.i) ? 1 : 0 } })),
    }
  }, [data, frames, frameIndex])

  const windGeoJSON = useMemo(() => {
    if (timeIndex < 0) return { type: 'FeatureCollection', features: [] }
    return {
      type: 'FeatureCollection',
      features: data.weather.points.map((p) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
        properties: { bearing: (p.wind_from_deg[timeIndex] + 180) % 360, speed: p.wind_kmh[timeIndex] },
      })),
    }
  }, [data, timeIndex])

  function handleCellClick(props) {
    setSelectedId(props.i)
  }

  const selectedFeature = selectedId != null ? cellsById.get(selectedId) : null
  const selectedWeather = useMemo(() => {
    if (!selectedFeature || timeIndex < 0) return null
    const [lon, lat] = cellCentroid(selectedFeature)
    const idx = nearestPointIndex(data.weather.points, lon, lat)
    const p = data.weather.points[idx]
    return { t_c: p.t_c[timeIndex], rh_pct: p.rh_pct[timeIndex], wind_kmh: p.wind_kmh[timeIndex], gust_kmh: p.gust_kmh[timeIndex], vpd_kpa: p.vpd_kpa[timeIndex] }
  }, [selectedFeature, data, timeIndex])

  const frame = frames[frameIndex]
  const dayDetections = data.by_day.find((d) => frame.t.startsWith(d.date))

  return (
    <div className="fire-layout">
      <div className="fire-map-col">
        <div className="fire-controls">
          <button className="toggle" aria-pressed={!todayMode} onClick={() => setTodayMode(false)}>
            Enero 2026 (evento)
          </button>
          <button className="toggle fire-today-toggle" aria-pressed={todayMode} onClick={() => { setPlaying(false); setTodayMode(true) }}>
            Detecciones recientes
          </button>
        </div>

        {!todayMode && (
          <>
            <div className="fire-timeline">
              <button className="play" onClick={() => setPlaying((p) => !p)} aria-label={playing ? 'Pausar' : 'Reproducir'}>
                {playing ? '⏸' : '▶'}
              </button>
              <input aria-label="Hora de observación" type="range" min={0} max={frames.length - 1} value={frameIndex} onChange={(e) => setFrameIndex(Number(e.target.value))} />
              <time>{localTime(frame.t)} (hora Chile)</time>
            </div>
            <FireDuringMap cellsGeoJSON={cellsGeoJSON} windGeoJSON={windGeoJSON} onCellClick={handleCellClick} selectedCellId={selectedId} />
            <p className="fire-legend">Rojo intenso: celda con calor confiable en esta hora. Ámbar tenue: ya tuvo calor antes. Flechas: hacia donde sopla el viento (ERA5), largo según velocidad.</p>
          </>
        )}

        {todayMode && todayOverview && (
          <FireTodayMap data={todayOverview.firms} bbox={todayOverview.audit?.bbox || [-73.6, -37.6, -72.3, -36.3]} onSelect={p => { setForecastError(''); setTodayPoint(p) }} />
        )}
        {todayMode && !todayOverview && <div className="fire-empty">Consultando focos recientes…</div>}
        {todayMode && <p className="fire-legend">Consulta guardada de FIRMS, sin actualización continua. Selecciona un punto para consultar el pronóstico meteorológico actual de ese lugar.</p>}
      </div>

      <div className="fire-side">
        <div className="fire-card">
          <h3>{todayMode ? 'Detecciones en la consulta' : 'Áreas con calor en esta hora'}</h3>
          <div className="fire-stat">{todayMode ? (todayOverview?.firms?.features?.length ?? '—') : frame.cells.length}</div>
          <div className="fire-stat-label">{todayMode ? 'observaciones VIIRS; pueden repetir el mismo lugar' : 'celdas GOES; no equivalen a incendios distintos'}</div>
          <p>
            {!todayMode && `${data.cells_hot} celdas tuvieron calor a lo largo del evento. ${dayDetections ? dayDetections.detections + ' detecciones el ' + dayDetections.date + ' (UTC).' : ''}`}
            {todayMode && todayOverview?.firms?.period_observed_utc && `Observaciones: ${todayOverview.firms.period_observed_utc.join(' a ')} (UTC).`}
          </p>
        </div>

        {!todayMode && selectedWeather && (
          <FireWeatherCard
            title={`Punto más cercano a la celda elegida`}
            sourceLabel="Viento de reanálisis ERA5: orienta, no indica por dónde entrar."
            {...selectedWeather}
            slope_deg={selectedFeature?.properties.slope_deg}
            cover={dominantCover(selectedFeature.properties)}
          />
        )}
        {!todayMode && !selectedWeather && <div className="fire-card"><p>Haz clic en una celda del mapa para ver viento, humedad y temperatura de ese lugar y esa hora.</p></div>}

        {todayMode && forecastError && <p role="status" className="fire-card">{forecastError}</p>}
        {todayMode && !forecastError && todayPoint && (!todayForecast || todayForecast.lat !== todayPoint.lat || todayForecast.lon !== todayPoint.lon) && (
          <div className="fire-card">
            <p>Consultando pronóstico…</p>
          </div>
        )}
        {todayMode && todayPoint && todayForecast && todayForecast.lat === todayPoint.lat && todayForecast.lon === todayPoint.lon && (
          <FireWeatherCard
            title="Pronóstico del punto elegido"
            sourceLabel={`Open-Meteo: pronóstico válido para ${todayForecast.data.hourly.time[0]} UTC; no es medición en terreno.`}
            t_c={todayForecast.data.hourly.temperature_2m[0]}
            rh_pct={todayForecast.data.hourly.relative_humidity_2m[0]}
            wind_kmh={todayForecast.data.hourly.wind_speed_10m[0]}
            gust_kmh={todayForecast.data.hourly.wind_gusts_10m[0]}
            vpd_kpa={todayForecast.data.hourly.vapour_pressure_deficit[0]}
          />
        )}
        {todayMode && !todayPoint && <div className="fire-card"><p>Elige un punto de calor reciente para ver su pronóstico.</p></div>}

        <details>
          <summary>Límites de esta vista</summary>
          <ul>
            {data.limits.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </details>
      </div>
    </div>
  )
}
