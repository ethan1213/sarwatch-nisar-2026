import { useMemo, useState } from 'react'
import FireBeforeMap from './FireBeforeMap'

const PASS_LABEL = { '2026-04-27': '27 abr 2026 (fecha retenida)', '2026-05-09': '9 may 2026 (fecha retenida)', '2026-10-12': '12 oct 2026 (última pasada)' }

export default function FireBefore({ data }) {
  const passDates = Object.keys(data.passes)
  const [pass, setPass] = useState(passDates[0])
  const held = data.held_out_dates.includes(pass)
  const rKey = 'r' + pass.replaceAll('-', '')
  const hKey = 'h' + pass.replaceAll('-', '')

  const cellsGeoJSON = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: data.cells.features.map((f) => ({ ...f, properties: { ...f.properties, priority: f.properties[rKey] ?? 0, hot: f.properties[hKey] ?? 0 } })),
    }),
    [data, rKey, hKey],
  )

  const passStats = data.passes[pass]
  const benchmark = data.benchmark[data.model]
  const persistence = data.benchmark.persistencia

  return (
    <div className="fire-layout">
      <div className="fire-map-col">
        <div className="fire-controls">
          <label>
            Fecha de la prueba{' '}
            <select value={pass} onChange={(e) => setPass(e.target.value)}>
              {passDates.map((d) => (
                <option key={d} value={d}>
                  {PASS_LABEL[d] || d}
                </option>
              ))}
            </select>
          </label>
        </div>
        <FireBeforeMap cellsGeoJSON={cellsGeoJSON} showHot={held} />
        <p className="fire-legend">Azul a rojo: prioridad de vigilancia exploratoria, de menor a mayor. {held ? 'Contorno blanco: celda donde GOES confirmó calor en los 12 días siguientes.' : 'Sin pasada térmica posterior descargada para esta fecha: no se puede comprobar.'}</p>
      </div>
      <div className="fire-side">
        <div className="fire-card">
          <h3>Prioridad de vigilancia · exploratoria</h3>
          {held ? (
            <>
              <div className="fire-stat">
                {passStats.hot_in_top_decile} / {passStats.hot_next}
              </div>
              <div className="fire-stat-label">celdas con calor detectado capturadas en el 10% de celdas con mayor prioridad ({passStats.top_decile_cells} celdas)</div>
            </>
          ) : (
            <p>{passStats.kind}</p>
          )}
        </div>
        <details className="fire-card">
          <summary>Resultados de la evaluación</summary><h3>Comprobación en fechas que el modelo no vio</h3>
          <div className="fire-stat">{benchmark.held_out_dates.roc_auc.toFixed(2)}</div>
          <div className="fire-stat-label">AUC del modelo radar+terreno, frente a {persistence.held_out_dates.roc_auc.toFixed(2)} de repetir dónde hubo calor antes</div>
          <p>
            En bloques espaciales retenidos: {benchmark.spatial_blocks.roc_auc.toFixed(2)} frente a {persistence.spatial_blocks.roc_auc.toFixed(2)}. En fechas nuevas la ventaja es pequeña y
            descansa en pocas celdas con calor: no es mejor que el azar en el 10% de mayor prioridad para estas dos fechas.
          </p>
        </details>
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
