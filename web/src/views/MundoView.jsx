import { useEffect, useState } from 'react'
import { fetchWorldCells, fetchWorldMeta, fetchWorldPoint } from '../api'
import { BREAKS } from '../colorScale'
import MundoMap from '../components/MundoMap'
import PointPanel from '../components/PointPanel'

export default function MundoView() {
  const [meta, setMeta] = useState(null)
  const [cellsGeoJSON, setCellsGeoJSON] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [point, setPoint] = useState(null)
  const [pointResult, setPointResult] = useState(null)
  const [pointLoading, setPointLoading] = useState(false)
  const [pointError, setPointError] = useState(null)

  useEffect(() => {
    fetchWorldMeta().then(setMeta).catch((e) => setLoadError(e.message))
    fetchWorldCells().then(setCellsGeoJSON).catch((e) => setLoadError(e.message))
  }, [])

  function handlePointClick(lon, lat) {
    setPoint({ lon, lat })
    setPointResult(null)
    setPointError(null)
    setPointLoading(true)
    fetchWorldPoint(lon, lat)
      .then(setPointResult)
      .catch((e) => setPointError(e.message))
      .finally(() => setPointLoading(false))
  }

  return (
    <>
      <header className="topbar">
        <h1>SARWatch · Mundo · cobertura NISAR</h1>
        {meta && (
          <p className="caption">
            Índice de {meta.granules_indexed.toLocaleString('es-CL')} granulos GCOV del catálogo
            oficial CMR ({meta.generated_utc.slice(0, 10)}). Fechas de la mejor geometría de órbita
            repetida (comparable) por celda de 1°. Es disponibilidad en el catálogo, no cobertura
            procesada ni validada.
          </p>
        )}
        {loadError && <p className="error">No se pudo cargar el índice mundial: {loadError}</p>}
      </header>
      <main className="layout">
        <MundoMap cellsGeoJSON={cellsGeoJSON} onPointClick={handlePointClick} />
        <aside className="sidebar">
          <div className="legend">
            {BREAKS.map((b) => (
              <div key={b.color} className="legend-row">
                <span className="swatch" style={{ background: b.color }} />
                <span>{b.label}</span>
              </div>
            ))}
          </div>
          <PointPanel point={point} result={pointResult} loading={pointLoading} error={pointError} />
        </aside>
      </main>
    </>
  )
}
