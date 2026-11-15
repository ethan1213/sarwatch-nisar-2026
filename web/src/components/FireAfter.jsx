import { useState } from 'react'
import FireAfterMap from './FireAfterMap'
const date = value => new Date(value + 'T12:00:00Z').toLocaleDateString('es-CL', { day:'numeric', month:'short', year:'numeric', timeZone:'UTC' })
export default function FireAfter({ data, initialMode = 'scar' }) {
  const [leftIdx, setLeftIdx] = useState(0)
  const [rightIdx, setRightIdx] = useState(data.radar.length - 1)
  const mode = initialMode
  const dateInfo = data.dates.find(d => d.date === data.radar[rightIdx].date)
  const land = data.area_km2.land_by_class
  return <div className="fire-layout">
    <div className="fire-map-col">
      {mode === 'radar' && <div className="fire-controls">
        <label>Primera fecha <select value={leftIdx} onChange={e => { const i=Number(e.target.value); setLeftIdx(i); if(i >= rightIdx) setRightIdx(i+1) }}>{data.radar.slice(0,-1).map((r,i)=><option key={r.date} value={i}>{date(r.date)}</option>)}</select></label>
        <label>Segunda fecha <select value={rightIdx} onChange={e=>setRightIdx(Number(e.target.value))}>{data.radar.map((r,i)=>i>leftIdx && <option key={r.date} value={i}>{date(r.date)}</option>)}</select></label>
      </div>}
      <FireAfterMap key={mode} left={data.radar[leftIdx]} right={data.radar[rightIdx]} severityOn={mode === 'scar'} severity={data.severity} single={mode === 'scar'} />
      <p className="fire-legend">{mode === 'scar' ? 'Amarillo: señal baja. Naranja: moderada. Rojo: alta. Comparación óptica entre diciembre–enero y enero–febrero; también puede responder a sequía y cosecha.' : `Desliza la línea blanca para comparar dos fechas posteriores al incendio. Gris oscuro a claro: intensidad del radar HV (${data.radar_scale_db.join(' a ')} dB). No muestra temperatura ni demuestra recuperación del bosque. Las zonas sin imagen no tienen píxeles válidos para esa fecha.`}</p>
    </div>
    <aside className="fire-side">
      <section className="fire-card"><h3>Señal óptica moderada o alta</h3><div className="fire-stat">{(land.moderada_baja + land.moderada_alta + land.alta).toLocaleString('es-CL', {maximumFractionDigits:1})} km²</div><p>Sobre tierra en el recorte estudiado. Es una estimación satelital, pendiente de contrastar con el perímetro oficial.</p></section>
      <section className="fire-card"><h3>El radar comienza en febrero</h3><p>No tenemos una imagen NISAR anterior al incendio de enero en esta geometría. Comparamos observaciones posteriores.</p></section>
      <details><summary>Método, calidad y resultados</summary>
        <p>Señal óptica dNBR; categoría alta: {land.alta} km². La señal baja incluye secado estival.</p>
        <p>Separación HV de bosque con señal alta frente a bosque sin señal: AUC {dateInfo.separation_high_vs_unburned.hv_db.auc.toFixed(2)}, {dateInfo.date}. 0,5 equivale al azar; 1 a separación perfecta. No es precisión de área quemada.</p>
        <ul>{data.limits.map(l=><li key={l}>{l}</li>)}</ul>
      </details>
    </aside>
  </div>
}
