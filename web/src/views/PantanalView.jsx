import { useEffect, useMemo, useState } from 'react'
import { siteAPI, fetchStudy } from '../api'
import LineChart from '../components/LineChart'
import SarMap from '../components/SarMap'

const PROFILES = ['Público general', 'Ciencia', 'Desarrollo y datos', 'Comunicaciones', 'Gestión territorial']
const EVIDENCE_LEVELS = { observado: ['Observado', '#1f6f8b'], estimado: ['Estimado y evaluado', '#b8860b'], hipotesis: ['Hipótesis', '#8a5a2b'], ausente: ['Dato ausente', '#7a7a7a'] }
const shortDate = value => new Date(value + 'T12:00:00Z').toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

function defaultBeforeIndex(scenes, pol) {
  const hit = scenes.findIndex((s) => (s.finite_positive_fraction[pol] ?? 0) >= 0.5)
  return hit >= 0 ? hit : 0
}

function toCSV(rows) {
  const header = 'fecha,dB,granulo\n'
  const body = rows.map((r) => `${r.fecha},${r.dB ?? ''},${r.granulo}`).join('\n')
  return header + body
}

function downloadText(filename, text, mime) {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function PantanalView({ slug = 'pantanal', label = 'Pantanal' }) {
  const {
    fetchPantanalLayer, fetchPantanalManifest, fetchPantanalPointSeries,
    fetchPantanalPredictionReference, fetchPantanalReading, fetchPantanalWaterLayer,
    fetchPantanalWaterMethods, fetchPantanalWeather, postPantanalAssistant,
  } = useMemo(() => siteAPI(slug), [slug])
  const [manifest, setManifest] = useState(null)
  const [manifestError, setManifestError] = useState(null)
  const [pol, setPol] = useState('HH')
  const [beforeIdx, setBeforeIdx] = useState(null)
  const [afterIdx, setAfterIdx] = useState(null)
  const [mode, setMode] = useState('single')
  const [profile, setProfile] = useState(PROFILES[0])

  const [layer, setLayer] = useState(null)
  const [layerError, setLayerError] = useState(null)
  const [reading, setReading] = useState(null)

  const [waterMethods, setWaterMethods] = useState([])
  const [waterMethod, setWaterMethod] = useState('')
  const [waterLayer, setWaterLayer] = useState(null)
  const [waterError, setWaterError] = useState(null)

  const [point, setPoint] = useState(null)
  const [pointRows, setPointRows] = useState(null)
  const [pointError, setPointError] = useState(null)

  const [weatherMode, setWeatherMode] = useState('historical')
  const [weather, setWeather] = useState(null)
  const [weatherError, setWeatherError] = useState(null)
  const [weatherLoading, setWeatherLoading] = useState(false)

  const [prediction, setPrediction] = useState(null)
  const [chatLog, setChatLog] = useState([])
  const [question, setQuestion] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [changeEnabled, setChangeEnabled] = useState(false)
  const [changeLayer, setChangeLayer] = useState(null)
  const [beforeLayer, setBeforeLayer] = useState(null)
  const [showTechnical, setShowTechnical] = useState(false)
  useEffect(() => {
    let active = true
    if (!changeEnabled) { setChangeLayer(null); return }
    fetchStudy(slug, 'overlay', { kind: 'change' }).then(d => { if (active) setChangeLayer(d) }).catch(e => { if (active) setLayerError(e.message) })
    return () => { active = false }
  }, [slug, changeEnabled])

  useEffect(() => {
    fetchPantanalManifest()
      .then((data) => {
        setManifest(data)
        setBeforeIdx(defaultBeforeIndex(data.scenes, 'HH'))
        setAfterIdx(data.scenes.length - 1)
      })
      .catch((e) => setManifestError(e.message))
    fetchPantanalPredictionReference().then(setPrediction).catch(() => setPrediction(null))
  }, [fetchPantanalManifest, fetchPantanalPredictionReference])

  useEffect(() => {
    if (beforeIdx === null || afterIdx === null) return
    let active = true
    setLayerError(null)
    setBeforeLayer(null)
    fetchPantanalLayer(beforeIdx, beforeIdx, pol, 'single').then(d => { if (active) setBeforeLayer(d) }).catch(() => {})
    fetchPantanalLayer(beforeIdx, afterIdx, pol, mode)
      .then(d => { if (active) setLayer(d) })
      .catch((e) => {
        setLayer(null)
        setLayerError(e.message)
      })
    fetchPantanalReading(beforeIdx, afterIdx, pol, profile)
      .then(setReading)
      .catch(() => setReading(null))
    fetchPantanalWaterMethods(afterIdx)
      .then((d) => setWaterMethods(d.methods))
      .catch(() => setWaterMethods([]))
    setChatLog([])
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beforeIdx, afterIdx, pol, mode])

  useEffect(() => {
    if (!reading) return
    fetchPantanalReading(beforeIdx, afterIdx, pol, profile).then(setReading).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile])

  useEffect(() => {
    if (!waterMethod || afterIdx === null) {
      setWaterLayer(null)
      return
    }
    setWaterError(null)
    fetchPantanalWaterLayer(afterIdx, pol, waterMethod)
      .then(setWaterLayer)
      .catch((e) => {
        setWaterLayer(null)
        setWaterError(e.message)
      })
  }, [waterMethod, afterIdx, pol, fetchPantanalWaterLayer])

  function handlePointClick(lon, lat) {
    if (!manifest) return
    const [west, south, east, north] = manifest.bbox_wgs84
    if (lon < west || lon > east || lat < south || lat > north) return
    setPoint({ lon, lat })
    setPointError(null)
    setPointRows(null)
    setWeather(null)
    fetchPantanalPointSeries(lon, lat, pol)
      .then((d) => setPointRows(d.rows))
      .catch((e) => setPointError(e.message))
  }

  function requestWeather() {
    if (!point || !manifest) return
    setWeatherLoading(true)
    setWeatherError(null)
    const beforeDate = manifest.scenes[beforeIdx].fecha
    const afterDate = manifest.scenes[afterIdx].fecha
    let start, end
    if (weatherMode === 'historical') {
      const min = beforeDate < afterDate ? beforeDate : afterDate
      const max = beforeDate > afterDate ? beforeDate : afterDate
      const d = new Date(min + 'T00:00:00Z')
      d.setUTCDate(d.getUTCDate() - 7)
      start = d.toISOString().slice(0, 10)
      end = max
    }
    fetchPantanalWeather(point.lat, point.lon, weatherMode, start, end)
      .then(setWeather)
      .catch((e) => setWeatherError(e.message))
      .finally(() => setWeatherLoading(false))
  }

  function sendQuestion(e) {
    e.preventDefault()
    if (!question.trim() || beforeIdx === null || afterIdx === null) return
    setChatLoading(true)
    const q = question
    setQuestion('')
    postPantanalAssistant(q, beforeIdx, afterIdx, pol, profile)
      .then((res) => setChatLog((log) => [...log, { question: q, ...res }].slice(-6)))
      .catch((e) => setChatLog((log) => [...log, { question: q, text: `No se pudo responder (${e.message}).`, sources: [], intent: '-', generator: '-', verified: false }].slice(-6)))
      .finally(() => setChatLoading(false))
  }

  const chartPoints = useMemo(() => (pointRows || []).map((r) => ({ y: r.dB, label: r.fecha.slice(5, 10) })), [pointRows])

  if (manifestError) {
    return (
      <main className="layout">
        <p className="error" style={{ padding: 20 }}>
          Las imágenes de {label} todavía no están disponibles. Puedes elegir otro lugar mientras se completa la verificación.
        </p>
      </main>
    )
  }
  if (!manifest || beforeIdx === null) return <p className="hint" style={{ padding: 20 }}>Cargando {label}…</p>

  return (
    <>
      <header className="topbar">
        <div className="view-heading"><div><p className="eyebrow">COMPARAR EL TERRENO</p><h1>{label}</h1></div><span className="status-pill">Observaciones reales · radar</span></div>
        <div className="controls-row">
          {showTechnical && <label>
            Polarización
            <select value={pol} onChange={(e) => setPol(e.target.value)}>
              <option value="HH">HH</option>
              <option value="HV">HV</option>
            </select>
          </label>}
          <label>
            Antes
            <select value={beforeIdx} onChange={(e) => setBeforeIdx(Number(e.target.value))}>
              {manifest.scenes.map((s) => (
                <option key={s.index} value={s.index}>
                  {shortDate(s.fecha)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Después
            <select value={afterIdx} onChange={(e) => setAfterIdx(Number(e.target.value))}>
              {manifest.scenes.map((s) => (
                <option key={s.index} value={s.index}>
                  {shortDate(s.fecha)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Qué quieres ver
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="single">Comparar las dos fechas</option>
              <option value="diff">Resaltar las diferencias</option>
            </select>
          </label>
          {showTechnical && <label>
            Cómo quieres explorar
            <select value={profile} onChange={(e) => setProfile(e.target.value)}>
              {PROFILES.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>}
          <button className="quiet-button" onClick={() => setShowTechnical(v => !v)} aria-expanded={showTechnical}>{showTechnical ? 'Cerrar detalle técnico' : 'Opciones técnicas'}</button>
        </div>
        <p className="caption">Son mapas de radar, no fotografías. Un cambio de color indica una diferencia en la señal; por sí solo no confirma incendio, inundación ni daño.</p>
        {layerError && <p className="error">{layerError}</p>}
      </header>
      <main className="layout">
        <div className="map-column">
          {mode === 'single' ? <div className="comparison-grid">
            <section><h2>Antes <span>{shortDate(manifest.scenes[beforeIdx].fecha)}</span></h2>{!beforeLayer && <p role="status">Preparando mapa…</p>}<SarMap layer={beforeLayer} onPointClick={handlePointClick} /></section>
            <section><h2>Después <span>{shortDate(manifest.scenes[afterIdx].fecha)}</span></h2><SarMap layer={layer} overlay={changeLayer || waterLayer} onPointClick={handlePointClick} /></section>
          </div> : <SarMap layer={layer} overlay={changeLayer || waterLayer} onPointClick={handlePointClick} />}
          <p className="caption">Azul: menor señal · claro: valor intermedio · naranja: mayor señal. {mode === 'diff' ? 'Escala −6 a +6 dB.' : 'Escala −30 a +10 dB.'} Transparente: sin dato.</p>
          {['metropolitana','valparaiso'].includes(slug) && showTechnical && <><label><input type="checkbox" checked={changeEnabled} onChange={e => setChangeEnabled(e.target.checked)} /> Cambio estadísticamente significativo · Conradsen</label>{changeLayer && <p className="caption">{changeLayer.sentence}</p>}</>}
          {layer && showTechnical && (
            <div className="metrics-row">
              <div className="metric">
                <span className="metric-value">{(layer.context.statistics.coverage * 100).toFixed(1)}%</span>
                <span className="metric-label">Cobertura comparable</span>
              </div>
              <div className="metric">
                <span className="metric-value">{layer.n_scenes}</span>
                <span className="metric-label">Observaciones</span>
              </div>
              <div className="metric">
                <span className="metric-value">{layer.resolution_m.toFixed(0)} m</span>
                <span className="metric-label">Resolución de la grilla</span>
              </div>
            </div>
          )}
          <p className="map-action">⌖ Haz clic en la zona coloreada para consultar ese lugar.</p>
        </div>
        <aside className="sidebar">
          {reading && (
            <div className="reading">
              <h3>Qué podemos decir</h3>
              <div className="evidence-short"><span className="mini-icon">✓</span><p>Hay observaciones para comparar estas dos fechas.</p></div>
              <div className="evidence-short"><span className="mini-icon neutral">?</span><p>El radar no identifica por sí solo qué causó el cambio.</p></div>
              <details><summary>Ver la evidencia y sus límites</summary><p>{reading.describe}</p>
              {reading.evidence.map((item, i) => {
                const [label, color] = EVIDENCE_LEVELS[item.level]
                return (
                  <div key={i} className="evidence-item" style={{ borderColor: color }}>
                    <span className="evidence-label" style={{ background: color }}>
                      {label}
                    </span>
                    <p>{item.text}</p>
                  </div>
                )
              })}</details>
              <details>
                <summary>Cómo leer esta vista</summary>
                <p>{reading.guide}</p>
              </details>
            </div>
          )}

          {slug === 'pantanal' && <div className="water-panel">
            <label>
              Capa de detección evaluada
              <select value={waterMethod} onChange={(e) => setWaterMethod(e.target.value)}>
                <option value="">Ninguna</option>
                {waterMethods.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            {waterError && <p className="error">{waterError}</p>}
            {waterLayer && (
              <p className="caption">
                Verde azulado: agua abierta estimada ({(waterLayer.fraction * 100).toFixed(1)}% del recorte válido). {waterLayer.sentence}
              </p>
            )}
          </div>}

          <div className="point-series">
            <h3>Serie temporal de un punto</h3>
            {!point && <p className="hint">Haz clic en el mapa para ver la serie.</p>}
            {pointError && <p className="error">{pointError}</p>}
            {pointRows && (
              <>
                <LineChart points={chartPoints} yLabel={`${pol} (dB)`} />
                <button onClick={() => downloadText('sarwatch-serie.csv', toCSV(pointRows), 'text/csv')}>Descargar serie CSV</button>
              </>
            )}
          </div>

          {point && (
            <div className="weather-panel">
              <h3>Tiempo meteorológico · complemento opcional</h3>
              <p className="caption">Open-Meteo · CC BY 4.0. El histórico ERA5 es reanálisis en una grilla mucho más gruesa que SAR; el pronóstico es una estimación futura, no una medición NISAR.</p>
              <label className="radio-label">
                <input type="radio" checked={weatherMode === 'historical'} onChange={() => setWeatherMode('historical')} /> Histórico del período SAR
              </label>
              <label className="radio-label">
                <input type="radio" checked={weatherMode === 'forecast'} onChange={() => setWeatherMode('forecast')} /> Pronóstico de los próximos 7 días
              </label>
              <button onClick={requestWeather} disabled={weatherLoading}>
                {weatherLoading ? 'Consultando…' : 'Consultar meteorología del punto'}
              </button>
              {weatherError && <p className="error">Meteorología no disponible: {weatherError}</p>}
              {weather && (
                <>
                  <table>
                    <thead>
                      <tr>
                        <th>fecha</th>
                        <th>precip. mm</th>
                        <th>T max</th>
                        <th>T min</th>
                      </tr>
                    </thead>
                    <tbody>
                      {weather.payload.daily.time.map((t, i) => (
                        <tr key={t}>
                          <td>{t}</td>
                          <td>{weather.payload.daily.precipitation_sum[i]}</td>
                          <td>{weather.payload.daily.temperature_2m_max[i]}</td>
                          <td>{weather.payload.daily.temperature_2m_min[i]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="caption">
                    Tipo: {weather.kind} · Consulta UTC: {weather.retrieved_utc}
                  </p>
                </>
              )}
            </div>
          )}

          {prediction && (
            <details className="prediction-box">
              <summary>Qué podemos predecir hoy</summary>
              <p>Todavía no hay un modelo validado para anticipar inundaciones o daños. El cambio de señal describe el pasado; el tiempo meteorológico es un pronóstico de otro proveedor.</p>
              <p className="caption">
                Referencia retrospectiva en Pantanal: repetir la mediana HH anterior produjo {prediction.n_evaluations} evaluaciones a unos 12 días, con MAE {prediction.mae_db.toFixed(2)} dB. No es un porcentaje de exactitud ni un predictor de inundación; no se generaliza a Chile.
              </p>
            </details>
          )}

          <div className="chat-panel">
            <h3>Ayúdame a entender</h3>
            <div className="question-chips">{['¿Qué cambió?', '¿Qué significan los colores?', '¿Esto confirma un incendio?'].map(q => <button key={q} onClick={() => setQuestion(q)}>{q}</button>)}</div>
            {chatLog.map((entry, i) => (
              <div key={i} className="chat-entry">
                <p className="chat-question">{entry.question}</p>
                <p>{entry.text}</p>
                <p className="caption">
                  {entry.verified ? 'Respuesta basada en los datos disponibles' : 'No se pudo verificar la respuesta'}{showTechnical ? ` · Tema: ${entry.intent} · Motor: ${entry.generator}` : ''}
                </p>
              </div>
            ))}
            <form onSubmit={sendQuestion} className="chat-form">
              <input aria-label="Pregunta sobre el mapa" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Escribe tu pregunta…" maxLength={1000} />
              <button type="submit" disabled={chatLoading}>
                {chatLoading ? '…' : 'Enviar'}
              </button>
            </form>
          </div>

          <details>
            <summary>Cobertura por fecha</summary>
            <table>
              <thead>
                <tr>
                  <th>fecha</th>
                  <th>HH</th>
                  <th>HV</th>
                </tr>
              </thead>
              <tbody>
                {manifest.scenes.map((s) => (
                  <tr key={s.index}>
                    <td>{s.fecha}</td>
                    <td>{s.finite_positive_fraction.HH.toExponential(2)}</td>
                    <td>{s.finite_positive_fraction.HV.toExponential(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </aside>
      </main>
    </>
  )
}
