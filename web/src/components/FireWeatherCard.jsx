// Shared weather fiche: historical (ERA5, during) or forecast (Open-Meteo, "Hoy"). The
// 30-30-30 lights are a plain-language fire-weather heuristic (hot/dry/windy), not a risk score.
export default function FireWeatherCard({ title, sourceLabel, t_c, rh_pct, wind_kmh, gust_kmh, vpd_kpa, slope_deg, elev_m, cover, wind_from_deg, precipitation_mm, precipitation_probability }) {
  const lights = [
    { label: `Temp. > 30°C`, on: t_c != null && t_c > 30 },
    { label: 'Humedad < 30%', on: rh_pct != null && rh_pct < 30 },
    { label: 'Viento > 30 km/h', on: wind_kmh != null && wind_kmh > 30 },
  ]
  const na = (v, unit, digits = 1) => (v == null ? 'sin dato' : `${v.toFixed(digits)}${unit}`)
  return (
    <div className="fire-card">
      <h3>{title}</h3>
      <div className="fire-lights">
        {lights.map((l) => (
          <div key={l.label} className={'fire-light' + (l.on ? ' on' : '')}>
            {l.label}
          </div>
        ))}
      </div>
      <div className="fire-weather-grid">
        {elev_m != null && <><span className="label">Altura media de la celda</span><span className="value">{na(elev_m, ' m', 0)}</span></>}
        <span className="label">Temperatura</span>
        <span className="value">{na(t_c, ' °C')}</span>
        <span className="label">Humedad relativa</span>
        <span className="value">{na(rh_pct, ' %', 0)}</span>
        <span className="label">Viento</span>
        <span className="value">{na(wind_kmh, ' km/h', 0)}</span>
        {wind_from_deg!=null&&<><span className="label">Viento desde</span><span className="value">{['Norte','Noreste','Este','Sureste','Sur','Suroeste','Oeste','Noroeste'][Math.round(wind_from_deg/45)%8]} ({na(wind_from_deg,'°',0)})</span></>}
        {precipitation_mm!=null&&<><span className="label">Precipitación prevista</span><span className="value">{na(precipitation_mm,' mm')}</span></>}
        {precipitation_probability!=null&&<><span className="label">Probabilidad de lluvia</span><span className="value">{na(precipitation_probability,' %',0)}</span></>}
        <span className="label">Ráfaga</span>
        <span className="value">{na(gust_kmh, ' km/h', 0)}</span>
        <span className="label">Déficit de presión de vapor</span>
        <span className="value">{na(vpd_kpa, ' kPa', 2)}</span>
        {slope_deg != null && (
          <>
            <span className="label">Pendiente de la celda</span>
            <span className="value">{na(slope_deg, '°', 0)}</span>
          </>
        )}
        {cover && (
          <>
            <span className="label">Cobertura dominante</span>
            <span className="value">{cover}</span>
          </>
        )}
      </div>
      <p>{sourceLabel}</p>
    </div>
  )
}
