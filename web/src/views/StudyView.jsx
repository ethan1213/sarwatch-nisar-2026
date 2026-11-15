import { useEffect, useState } from 'react'
import { fetchStudy } from '../api'
import SarMap from '../components/SarMap'
import ThermalMap from '../components/ThermalMap'

const fmt = (value) => value == null ? 'sin dato' : Number(value).toLocaleString('es-CL', { maximumFractionDigits: 1 })
const day = value => new Date(value).toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

function DataTable({ rows }) {
  if (!rows?.length) return <p>Sin filas disponibles.</p>
  const keys = Object.keys(rows[0])
  const labels = { worldcover: 'Clase de cobertura', fuel: 'Combustible supuesto', severity: 'Severidad', area_ha: 'Área (ha)', co2_t: 'CO₂ (t)', sensitivity_low_t: 'Sensibilidad inferior (t)', sensitivity_high_t: 'Sensibilidad superior (t)', basin_id: 'Cuenca aproximada', area_km2: 'Área (km²)', burned_moderate_high_km2: 'Señal moderada-alta (km²)', relief_m: 'Relieve (m)', relative_index_max: 'Índice máximo (0–1)', relative_index_mean: 'Índice medio (0–1)' }
  return <div style={{ overflowX: 'auto' }}><table><thead><tr>{keys.map(k => <th key={k} scope="col">{labels[k] || k.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{keys.map(k => <td key={k}>{typeof row[k] === 'number' ? Number(row[k]).toLocaleString('es-CL', { maximumFractionDigits: k.includes('index') || k.includes('km2') ? 4 : 1 }) : String(row[k] ?? 'sin dato')}</td>)}</tr>)}</tbody></table></div>
}

export default function StudyView({ slug, kind, label }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [layer, setLayer] = useState(null)
  const [scenario, setScenario] = useState('octubre')
  const [heatLayer, setHeatLayer] = useState('focos')
  const [cells, setCells] = useState(null)
  useEffect(() => {
    let active = true
    fetchStudy(slug, kind).then(d => { if (active) setData(d) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [slug, kind])
  useEffect(() => {
    let active = true
    if (kind === 'postfire' || kind === 'impacts') {
      fetchStudy(slug, 'overlay', { kind: kind === 'postfire' ? 'postfire' : 'concentration', scenario })
        .then(d => { if (active) setLayer(d) }).catch(e => { if (active) setError(e.message) })
    }
    return () => { active = false }
  }, [slug, kind, scenario])
  useEffect(() => {
    let active = true
    if (kind === 'thermal' && data?.cells_available) fetchStudy(slug, 'thermal-cells', { layer: heatLayer })
      .then(d => { if (active) setCells(d) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [slug, kind, heatLayer, data])
  return <section className="study-view">
    <h1>{label}</h1>
    {error && <p role="alert" className="error">{error}</p>}
    {!data && !error && <p role="status">Cargando evidencia…</p>}
    {kind === 'impacts' && data && <>
      <p className="notice">Laboratorio experimental sin validación de terreno. No usar para alertas, inventarios certificados ni despliegue de brigadas.</p>
      <h2>CO₂ bruto · escenario de combustión</h2>
      <p className="metric-value">{fmt(data.emissions.total_co2_t)} t</p>
      <p>Sensibilidad: {fmt(data.emissions.sensitivity_low_t)}–{fmt(data.emissions.sensitivity_high_t)} t. No es un intervalo de confianza ni una medición atmosférica.</p>
      <p>Señal de quema: {fmt(data.emissions.burned_signal_area_ha)} ha. Sin factor asignado: {fmt(data.emissions.unmodeled_burned_area_ha)} ha; no se interpreta como emisión cero.</p>
      <details><summary>Cómo se calculó esta estimación</summary><DataTable rows={data.emissions.rows} />
      {data.emissions.limitations.map(t => <p className="caption" key={t}>{t}</p>)}
      <a href={data.emissions.source} target="_blank" rel="noreferrer">Método y tablas originales IPCC</a></details>
      <h2>Relieve y concentración relativa · DEM</h2>
      <p>Azul: índice bajo · naranja: índice alto · escala relativa 0–1. No son metros de profundidad ni rutas seguras.</p>
      {layer && <SarMap layer={layer} />}
      <p>{data.terrain.volume.reason}</p>
      <details><summary>Ver los sectores y el detalle del relieve</summary><DataTable rows={data.terrain.top_basins.slice(0, 10)} />
      <p className="caption">Diez cuencas con mayor índice. El archivo descargable conserva las cincuenta primeras con valores completos.</p>
      {data.terrain.limitations.map(t => <p className="caption" key={t}>{t}</p>)}</details>
    </>}
    {kind === 'postfire' && data && <>
      <p className="notice">Heurística experimental no calibrada · caso Quebrada Honda, Las Condes. No es una alerta operativa.</p>
      <label>Escenario histórico o de referencia <select value={scenario} onChange={e => setScenario(e.target.value)}>{Object.entries(data.scenarios).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}</select></label>
      <p>Rojo: menor umbral heurístico · amarillo: intermedio · verde: mayor umbral. Verde no significa seguridad.</p>
      {layer && <><SarMap layer={layer} /><p>{layer.sentence}</p></>}
      <details><summary>Ver fechas, cálculo y límites</summary><p>{data.nisar_window?.note}</p>
      <DataTable rows={Object.entries(data.scenarios).map(([key,s]) => ({ escenario: key, lluvia_antecedente_mm: s.antecedent_rain_mm, umbral_mediano_mm_30min: s.median_threshold_mm_30min, lluvia_observada_mm_30min: s.observed_30min_mm }))} />
      </details>
    </>}
    {kind === 'thermal' && data && <>
      <p className="notice">{data.limitation}</p>
      {data.cells_available ? <>
        <div className="view-heading"><div><p className="eyebrow">OBSERVACIÓN TÉRMICA</p><h2>{day(data.current_manifest.period_utc[0])}</h2></div><span className="status-pill warm">{data.current_manifest.hotspot_detections} detecciones ese día</span></div>
        <label>Qué quieres ver <select value={heatLayer} onChange={e => setHeatLayer(e.target.value)}><option value="focos">Dónde se detectó calor</option><option value="confiables">Detecciones de mayor confianza</option><option value="lst">Temperatura de la superficie</option><option value="elevacion_m">Altura del terreno</option><option value="pendiente_grados">Inclinación del terreno</option><option value="bt_mir">Infrarrojo 3,9 µm · detalle técnico</option><option value="bt_tir">Infrarrojo 11,2 µm · detalle técnico</option><option value="hv_last">Radar NISAR HV · detalle técnico</option><option value="hv_change">Cambio de radar HV · detalle técnico</option></select></label>
        <ThermalMap data={cells} />
        <details><summary>Cómo interpretar el mapa y sus fechas</summary><p>GOES-19 observa celdas de aproximadamente {data.current_manifest.pixel_km_east_west} × {data.current_manifest.pixel_km_north_south} km, no casas ni frentes de fuego.</p><p>Fechas del radar: {data.radar_dates?.map(day).join(', ')}. No son simultáneas a la observación térmica; no prueban una causa.</p></details>
      </> : <p>Los archivos térmicos por celda no están disponibles en esta instalación. El resumen conserva su procedencia; no se reconstruyen observaciones desde conteos.</p>}
      <details><summary>Ver el historial evaluado de este lugar</summary><p>Período: {data.reference?.period_utc?.map(day).join(' → ')}</p><DataTable rows={data.reference ? [{ detecciones: data.reference.hotspots.detections, confiables: data.reference.hotspots.confident_detections, días_con_focos: data.reference.hotspots.days_with_hotspots, celdas_con_focos: data.reference.hotspots.cells_ever_hot }] : []} /><p>Este historial es distinto del día del mapa. No hay una predicción validada de incendios.</p></details>
    </>}
    {data && <details><summary>Procedencia y resultados descargables</summary><a download={`sarwatch-${slug}-${kind}.json`} href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(data, null, 2))}`}>Descargar JSON</a><pre>{JSON.stringify(data, null, 2)}</pre></details>}
  </section>
}
