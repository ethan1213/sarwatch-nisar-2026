import { useEffect, useState } from 'react'
import '../fire.css'
import { fetchFireStory } from '../api'
import FireBefore from '../components/FireBefore'
import FireDuring from '../components/FireDuring'
import FireAfter from '../components/FireAfter'

const TABS = [
  { key: 'during', label: '1. Qué ocurrió' },
  { key: 'after', label: '2. Qué quedó' },
  { key: 'before', label: '3. Qué podemos anticipar' },
]

export default function FireView() {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('during')
  const [parts, setParts] = useState({})
  const [partError, setPartError] = useState(null)

  useEffect(() => {
    fetchFireStory().then(setSummary).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (parts[tab]) return
    let alive = true
    fetchFireStory(tab)
      .then((d) => {
        if (!alive) return
        setPartError(null)
        setParts((p) => ({ ...p, [tab]: d }))
      })
      .catch((e) => { if (alive) setPartError(e.message) })
    return () => { alive = false }
  }, [tab, parts])

  if (error) {
    return (
      <div className="fire">
        <p className="fire-empty">No se pudo cargar la historia de incendios: {error}</p>
      </div>
    )
  }
  if (!summary) {
    return (
      <div className="fire">
        <p className="fire-empty">Cargando historia de incendios…</p>
      </div>
    )
  }

  const data = parts[tab]

  return (
    <div className="fire">
      <div className="fire-head">
        <h1>Incendios de Biobío · enero de 2026</h1>
        <p>Concepción, Penco, Tomé y alrededores. Del calor observado a las señales en el terreno.</p>
      </div>
      <div className="fire-banner">Evidencia satelital para comprender el territorio. Prototipo de investigación, sin alertas operativas.</div>

      <nav className="fire-tabs" aria-label="Historia del incendio">
        {TABS.map((t) => (
          <button key={t.key} aria-pressed={tab === t.key} onClick={() => { setPartError(null); setTab(t.key) }}>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="fire-chapter"><h2>{tab === 'during' ? '¿Dónde se observó calor?' : tab === 'after' ? '¿Qué señales dejó en el terreno?' : '¿Podemos anticipar nuevos focos?'}</h2><p>{tab === 'during' ? 'Avanza por las horas. Los cuadros son áreas observadas desde el espacio, no el borde del incendio.' : tab === 'after' ? 'Primero observa la señal óptica de quema. El radar permite explorar el terreno meses después.' : 'Todavía no de forma fiable. Esta prueba muestra tanto los resultados como sus límites.'}</p></div>

      {partError && <p className="fire-empty">No se pudo cargar este acto: {partError}</p>}
      {!data && !partError && <p className="fire-empty">Cargando…</p>}
      {data && tab === 'during' && <FireDuring data={data} />}
      {data && tab === 'after' && <FireAfter data={data} />}
      {data && tab === 'before' && <FireBefore data={data} />}

      <details className="fire-note">
        <summary>Fuentes</summary>
        <ul>
          {Object.entries(summary.sources).map(([k, v]) => (
            <li key={k}>{v}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}
