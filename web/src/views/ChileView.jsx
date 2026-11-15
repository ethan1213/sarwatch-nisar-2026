import { useEffect, useMemo, useState } from 'react'
import HotspotMap from '../components/HotspotMap'
import PantanalView from './PantanalView'

const date = value => new Date(value).toLocaleDateString('es-CL', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'})
const consultedDate = value => new Date(value).toLocaleDateString('es-CL', {day:'numeric',month:'short',year:'numeric',timeZone:'America/Santiago'})
const maturity = { BETA: 'Experimental · sin calibración completa', PROVISIONAL: 'Calibrado · validación parcial', VALIDATED: 'Calibrado y validado por la misión' }

export default function ChileView({ slug }) {
  const [data, setData] = useState(null), [showRadar, setShowRadar] = useState(false), [notice, setNotice] = useState('')
  useEffect(() => {
    let alive = true
    fetch(`/api/chile/${slug}/overview`).then(r => { if (!r.ok) throw new Error(); return r.json() }).then(d => { if (alive) setData(d) }).catch(() => { if (alive) setNotice('No pudimos actualizar la consulta. Puedes explorar los otros lugares mientras vuelve la conexión.') })
    return () => { alive = false }
  }, [slug])
  const bbox = useMemo(() => data?.audit?.bbox || [-73.25,-36.95,-72.7,-36.5], [data])
  if (showRadar) return <><button className="back-button" onClick={() => setShowRadar(false)}>← Volver al resumen de Biobío</button><PantanalView slug="concepcion_penco" label="Concepción y Penco" /></>
  return <main className="chile-view">
    <div className="view-heading"><div><p className="eyebrow">DATOS REALES DE CHILE</p><h1>{slug === 'biobio' ? 'Biobío y su entorno' : 'Concepción, Penco y alrededores'}</h1></div><span className="status-pill">Consulta oficial NASA / ASF</span></div>
    {notice && <p role="status" className="soft-notice">{notice}</p>}
    {!data && !notice && <p role="status" className="loading-card">Buscando observaciones disponibles…</p>}
    {data && <>
      <div className="overview-cards">
        <section><span className="card-symbol">◷</span><h2>Observaciones del terreno</h2><p>{data.audit?.cohorts?.filter(c => c.n_dates > 1).length || 0} series con fechas repetidas identificadas.</p><span className="subtle">Todavía no confirman un incendio.</span></section>
        <section><span className="card-symbol warm">♨</span><h2>Detecciones de calor</h2><p>{data.firms ? `${data.firms.detections} observaciones recientes de FIRMS` : 'Consulta reciente en preparación'}</p><span className="subtle">Cada punto es una observación, no un incendio distinto.</span></section>
        <section><span className="card-symbol">✓</span><h2>Imágenes verificadas</h2><p>{data.rasters_ready ? 'Listas para comparar' : 'Verificación pendiente'}</p>{data.rasters_ready ? <button className="primary-button" onClick={() => setShowRadar(true)}>Comparar imágenes →</button> : <span className="subtle">Se habilitan después de comprobar integridad y calidad.</span>}</section>
      </div>
      <section className="map-card"><div className="section-heading"><div><p className="eyebrow">CALOR OBSERVADO · FIRMS</p><h2>Localiza una detección</h2></div><span className="status-pill warm">375 m por píxel · VIIRS</span></div>
        <p className="subtle">Selecciona un punto para conocer su hora y sensor. No muestra el frente del fuego ni una ruta segura.</p>
        {data.firms ? <HotspotMap data={data.firms} bbox={bbox} /> : <div className="empty-map">Los puntos estarán disponibles cuando termine la descarga de FIRMS.</div>}
        <div className="map-legend"><span><i className="dot" />Detección de calor</span><span>Un punto no es una vivienda ni el perímetro de un incendio.</span></div>
        {data.firms?.period_observed_utc && <p className="subtle">Fechas UTC de las detecciones: {date(data.firms.period_observed_utc[0])} a {date(data.firms.period_observed_utc[1])}. Consulta realizada en Chile: {consultedDate(data.firms_retrieved_utc)}.</p>}
      </section>
      <section className="plain-card"><h2>¿Podemos ver el incendio de enero con NISAR?</h2><p>La búsqueda no encontró escenas BETA sobre la ventana de Concepción/Penco. La serie provisional comienza el 26 de febrero de 2026: permite estudiar cambios posteriores, pero no demostrar un antes/después del incendio de enero.</p><span className="subtle">Esto describe el catálogo consultado, no prueba que la misión no haya adquirido datos.</span></section>
      <details className="technical-panel"><summary>Fechas, versiones y fuentes · detalle técnico</summary>
        <p>BETA, PROVISIONAL y VALIDATED se mantienen separados. Tampoco se comparan automáticamente órbitas distintas.</p>
        <div className="table-scroll"><table><thead><tr><th>Estado del producto</th><th>Versión de procesamiento</th><th>Geometría</th><th>Fechas</th><th>Primera</th><th>Última</th></tr></thead><tbody>{data.audit?.cohorts?.map(c => <tr key={`${c.maturity}-${c.geometry}-${c.crid}`}><td>{maturity[c.maturity]}</td><td>{c.crid} · colección v1</td><td>{c.geometry}</td><td>{c.n_dates}</td><td>{date(c.first_date)}</td><td>{date(c.last_date)}</td></tr>)}</tbody></table></div>
        <p>El rectángulo de búsqueda regional no es un límite administrativo. Una huella que toca la zona no garantiza píxeles útiles en toda ella.</p>
        <p>{data.historical_status}</p>
        <a href="https://nisar-docs.asf.alaska.edu/availability-overview/" target="_blank" rel="noreferrer">Madurez y versiones NISAR · ASF</a> · <a href="https://firms.modaps.eosdis.nasa.gov/content/active_fire/" target="_blank" rel="noreferrer">Focos y límites · NASA FIRMS</a>
      </details>
    </>}
  </main>
}
