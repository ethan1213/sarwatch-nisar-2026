// Mirrors the lower half of sarwatch/views/world.py::world_view: once a point is clicked,
// show every repeat-orbit geometry touching it, sorted by date count, with the best series
// called out and its scripts/request_aoi.py command shown (no AOI processing happens on click).
export default function PointPanel({ point, result, loading, error }) {
  if (!point) {
    return <p className="hint">Haz clic en el mapa para consultar un punto.</p>
  }
  return (
    <div className="point-panel">
      <h3>
        {point.lat.toFixed(3)}, {point.lon.toFixed(3)}
      </h3>
      {loading && <p className="hint">Consultando índice CMR…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && result && (
        <>
          {result.n_granules === 0 ? (
            <p className="hint">
              No hay granulos GCOV cuya huella nominal cubra ese punto. Prueba otro lugar o espera
              nuevos ciclos de 12 días.
            </p>
          ) : (
            <>
              <p>
                {result.n_granules} granulos cubren el punto; {result.n_geometries} geometrías de
                órbita distintas. Para comparar fechas se usa una sola geometría.
              </p>
              <table>
                <thead>
                  <tr>
                    <th>geometría</th>
                    <th>fechas</th>
                    <th>primera</th>
                    <th>última</th>
                    <th>GB</th>
                  </tr>
                </thead>
                <tbody>
                  {result.geometries.map((g) => (
                    <tr key={g.geometry}>
                      <td>{g.geometry}</td>
                      <td>{g.n_dates}</td>
                      <td>{g.first_date}</td>
                      <td>{g.last_date}</td>
                      <td>{g.estimated_gb}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.geometries[0] && (
                <>
                  <p className="caption">
                    Mejor serie: geometría {result.geometries[0].geometry} con{' '}
                    {result.geometries[0].n_dates} fechas; descargar sus granulos pesa{' '}
                    {result.geometries[0].estimated_gb} GB. Procesar este lugar requiere ejecutar el
                    flujo bajo demanda (scripts/request_aoi.py) con Earthdata Login; no ocurre al
                    hacer clic.
                  </p>
                  <pre className="code">
                    {`python scripts/request_aoi.py select --name mi_sitio --bbox ${(point.lon - 0.25).toFixed(2)} ${(point.lat - 0.25).toFixed(2)} ${(point.lon + 0.25).toFixed(2)} ${(point.lat + 0.25).toFixed(2)} --start ${result.geometries[0].first_date}`}
                  </pre>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
