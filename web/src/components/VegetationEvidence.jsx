import { useEffect, useState } from 'react'

const series = [['ndvi', 'Vegetación (NDVI)', '#7bd49b'], ['ndmi', 'Agua en la vegetación (NDMI)', '#78bafa']]
const dateLabel = value => new Date(value).toLocaleDateString('es-CL', { timeZone: 'UTC' })

export default function VegetationEvidence() {
  const [data, setData] = useState(null), [error, setError] = useState(false), [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/fire/vegetation-sample', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error('Unavailable')
      return r.json()
    }).then(setData).catch(e => { if (e.name !== 'AbortError') setError(true) })
    return () => controller.abort()
  }, [attempt])
  if (error) return <div role="alert">No pudimos cargar la serie.<button onClick={() => { setError(false); setAttempt(n => n + 1) }}>Reintentar</button></div>
  if (!data) return <p role="status">Cargando observaciones de vegetación…</p>
  if (!data.observations?.length) return <p>No hay observaciones válidas para esta muestra.</p>
  const rows = [...data.observations].sort((a, b) => a.date.localeCompare(b.date))
  const start = Date.parse(rows[0].date), span = Math.max(1, Date.parse(rows.at(-1).date) - start)
  const x = date => 58 + 660 * (Date.parse(date) - start) / span
  const y = value => 32 + (1 - value) * 110
  return <section className="fg-vegetation">
    <h3>Un punto de Penco, observado en {rows.length} fechas</h3>
    <p>Coordenadas: {data.point.lat}, {data.point.lon}. Esta muestra corresponde a un punto fijo; no representa toda la comuna ni el lugar seleccionado en otros mapas.</p>
    <div className="fg-color-key">{series.map(([key, label, color]) => <span key={key}><i style={{ background: color }}/>{label}</span>)}</div>
    <svg viewBox="0 0 760 300" role="img" aria-labelledby="vegetation-chart-title vegetation-chart-desc" style={{ width: '100%', maxHeight: 360 }}>
      <title id="vegetation-chart-title">Observaciones Sentinel-2 de vegetación en 2026</title>
      <desc id="vegetation-chart-desc">Puntos separados por fecha real. Eje vertical de menos uno a uno, sin unidades. Los valores exactos están en la tabla inferior. No se interpolan los días sin observación.</desc>
      {[-1, -0.5, 0, 0.5, 1].map(v => <g key={v}><line x1="52" x2="730" y1={y(v)} y2={y(v)} stroke="currentColor" opacity="0.18"/><text x="42" y={y(v) + 4} fill="currentColor" textAnchor="end" fontSize="12">{v}</text></g>)}
      {series.map(([key, label, color]) => rows.map(row => <circle key={key + row.date} cx={x(row.date)} cy={y(row[key])} r="5" fill={color}><title>{dateLabel(row.date)} · {label}: {row[key]}</title></circle>))}
      {[rows[0], rows[Math.floor(rows.length / 2)], rows.at(-1)].map((r, i) => <text key={i} x={x(r.date)} y="280" fill="currentColor" textAnchor="middle" fontSize="12">{dateLabel(r.date)}</text>)}
    </svg>
    <p><b>Verde:</b> NDVI describe el contraste de la vegetación con su entorno. <b>Azul:</b> NDMI es sensible al contenido de agua y a la estructura de la vegetación. Ambos son índices sin unidades, no porcentajes.</p>
    <p>Un descenso del azul merece revisión, pero por sí solo no demuestra combustible seco ni anticipa la dirección del fuego. Tampoco confirma un derrumbe.</p>
    <details><summary>Ver fechas, valores y archivos originales</summary><div style={{ overflowX: 'auto' }}><table><caption>Muestra puntual · fechas UTC · sin datos interpolados</caption><thead><tr><th>Fecha</th><th>NDVI</th><th>NDMI</th><th>Producto</th></tr></thead><tbody>{rows.map(r => <tr key={r.item}><td>{dateLabel(r.date)}</td><td>{r.ndvi.toFixed(4)}</td><td>{r.ndmi.toFixed(4)}</td><td><a target="_blank" rel="noreferrer" href={`https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/${encodeURIComponent(r.item)}`}>{r.item}</a></td></tr>)}</tbody></table></div></details>
    <details><summary>Cómo se obtuvo y qué límites tiene</summary><p>Se eligió una adquisición válida por mes entre hasta cinco candidatas con menos de 20 % de nubes en la escena. Se aceptaron píxeles clasificados como vegetación (SCL 4); esta máscara puede equivocarse. No son promedios mensuales ni una serie diaria.</p><p>NDVI usa rojo e infrarrojo cercano a 10 m. NDMI combina infrarrojo cercano a 10 m e infrarrojo de onda corta a 20 m, muestreados en la misma coordenada, con distinta superficie de píxel. No hay calibración local de humedad de combustible.</p><p>Fuente: {data.source}. Extracción: {dateLabel(data.generated_utc)}.</p><a href="/api/fire/vegetation-sample" target="_blank" rel="noreferrer">Descargar evidencia JSON</a></details>
  </section>
}
