import {useEffect,useMemo,useState} from 'react'
import {parseGpx,routeKm,sampleRoute,terrainAt} from '../lib/route'
import RouteMap from './RouteMap'
import RainfallContext from './RainfallContext'

function LandslideContext({point}) {
 const [state,setState]=useState({status:'loading'})
 const [lon,lat]=point
 useEffect(()=>{
  const controller=new AbortController()
  fetch(`/api/fire/landslide-context?lat=${lat}&lon=${lon}`,{signal:controller.signal})
   .then(r=>{if(!r.ok)throw Error();return r.json()})
   .then(data=>setState({status:'ready',data}))
   .catch(e=>{if(e.name!=='AbortError')setState({status:'error'})})
  return ()=>controller.abort()
 },[lat,lon])
 return <section className="fire-card"><h3>Deslizamientos · referencia regional NASA</h3>
  {state.status==='loading'&&<p role="status">Consultando el archivo LHASA…</p>}
  {state.status==='error'&&<p role="status">No hay datos LHASA para este punto. No se puede inferir seguridad del recorrido.</p>}
  {state.status==='ready'&&<><p>LHASA {state.data.publisher_version}. Celdas de aproximadamente 1 km; resultados archivados por fecha, no alerta vigente. El porcentaje corresponde al modelo regional y no a la probabilidad de derrumbe en el sendero.</p>
   <div style={{overflowX:'auto'}}><table><caption>Estimación del modelo en la celda del punto</caption><thead><tr><th>Fecha UTC</th><th>Probabilidad modelada</th></tr></thead><tbody>{state.data.observations.map(o=><tr key={o.date_utc}><td>{o.date_utc.slice(0,10)}</td><td>{o.probability===null?'Sin dato':`${(o.probability*100).toFixed(1)} %`}</td></tr>)}</tbody></table></div>
   <p>LHASA no cubre todos los tipos de derrumbe. Estos valores no certifican transitabilidad; revisa avisos oficiales y condiciones del lugar. <a href="https://github.com/nasa/LHASA/blob/master/README.md" target="_blank" rel="noreferrer">Cómo funciona LHASA · NASA ↗</a></p></>}
 </section>
}

function PointWeather({point}) {
 const [data,setData]=useState(null),[error,setError]=useState(false),[attempt,setAttempt]=useState(0)
 const [lon,lat]=point
 useEffect(()=>{
  const controller=new AbortController()
  fetch(`/api/fire/forecast?lat=${lat}&lon=${lon}`,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(setData).catch(e=>{if(e.name!=='AbortError')setError(true)})
  return ()=>controller.abort()
 },[lat,lon,attempt])
 return <section className="fire-card"><h3>Próximas 48 horas · pronóstico</h3>{error?<p role="alert">No se pudo consultar el pronóstico. <button onClick={()=>{setError(false);setAttempt(n=>n+1)}}>Reintentar</button></p>:!data?<p role="status">Consultando condiciones…</p>:<><p>Open-Meteo · obtenido {data.retrieved_utc}. Celda del modelo: {data.cell_latitude}, {data.cell_longitude}. No es una estación del sendero.</p><div style={{overflowX:'auto',maxHeight:320}}><table><caption>Lluvia por hora y viento a 10 m · horas UTC</caption><thead><tr><th>Hora UTC</th><th>Lluvia (mm)</th><th>Viento (km/h)</th><th>Desde (°)</th><th>Ráfaga (km/h)</th></tr></thead><tbody>{data.hourly.time.map((t,i)=><tr key={t}><td>{t.replace('T',' ')}</td>{['precipitation','wind_speed_10m','wind_direction_10m','wind_gusts_10m'].map(k=><td key={k}>{data.hourly[k][i]??'Sin dato'}</td>)}</tr>)}</tbody></table></div></>}
 <RainfallContext point={{lat,lon}}/><LandslideContext point={point}/></section>
}
export default function TrekkingRoute({data}) {
 const [gpxText,setGpxText]=useState('')
 const [segments,setSegments]=useState(null),[error,setError]=useState(''),[selected,setSelected]=useState(null),[weatherId,setWeatherId]=useState(null)
 const samples=useMemo(()=>segments?sampleRoute(segments):[],[segments])
 const points=useMemo(()=>samples.map(p=>({...p,terrain:terrainAt(p.coordinate,data.cells.features)})),[samples,data])
 const point=selected===null?null:points[selected]
 function pasteRoute() {
  setError('');setWeatherId(null);setSelected(null);setSegments(null)
  try {if(gpxText.length>2*1024*1024)throw Error('Usa un GPX de hasta 2 MB.');setSegments(parseGpx(gpxText))}catch(e){setError(e.message)}
 }
 async function load(event) {
  const file=event.target.files[0]
  setError('');setWeatherId(null);setSelected(null);setSegments(null)
  if(!file)return
  try {
   if(file.size>2*1024*1024)throw Error('Usa un GPX de hasta 2 MB.')
   setSegments(parseGpx(await file.text()))
  }catch(e){setError(e.message)}
  event.target.value=''
 }
 return <section><h3>Revisa tu recorrido</h3><p>Abre un GPX de Chile para ver su trazado. El archivo se procesa en este navegador. Al consultar clima se envían solo las coordenadas del punto elegido a SARWatch y Open-Meteo.</p><label className="fg-primary">Abrir recorrido GPX <input type="file" accept=".gpx,application/gpx+xml" onChange={load}/></label><details><summary>Pegar contenido GPX como alternativa</summary><label>Contenido GPX<textarea style={{width:'100%',minHeight:120}} value={gpxText} maxLength={2*1024*1024} onChange={e=>setGpxText(e.target.value)}/></label><button onClick={pasteRoute}>Mostrar recorrido pegado</button></details>{error&&<p role="alert">{error}</p>}
 {!segments?<p>El archivo debe contener un track o una ruta. No usamos nombres ni datos personales del GPX.</p>:<><p><b>{routeKm(segments).toFixed(2)} km</b> de longitud horizontal aproximada · {segments.length} segmentos · {samples.length} puntos de consulta distribuidos por orden del archivo. No se evalúa cada metro del recorrido.</p><div className="fg-color-key"><span><i style={{background:'#78bafa'}}/>Azul: trazado del archivo</span><span><i style={{background:'#e9edaa'}}/>Puntos claros: lugares consultables, sin clasificación de riesgo</span></div><RouteMap segments={segments} samples={samples} onSelect={id=>{setSelected(id);setWeatherId(null)}}/><p>Selecciona un punto del mapa o de la tabla. El relieve disponible corresponde a medias de celdas de Biobío; fuera de ellas se muestra «Sin cobertura».</p><div style={{overflowX:'auto',maxHeight:320}}><table><caption>Contexto del terreno en los puntos de consulta</caption><thead><tr><th>Punto</th><th>Coordenadas</th><th>Altura media</th><th>Pendiente media</th></tr></thead><tbody>{points.map(p=><tr key={p.id}><td><button aria-pressed={selected===p.id} onClick={()=>{setSelected(p.id);setWeatherId(null)}}>Punto {p.id+1}</button></td><td>{p.coordinate[1].toFixed(5)}, {p.coordinate[0].toFixed(5)}</td><td>{p.terrain?.elev_m!=null?`${p.terrain.elev_m} m`:'Sin cobertura'}</td><td>{p.terrain?.slope_deg!=null?`${p.terrain.slope_deg}°`:'Sin cobertura'}</td></tr>)}</tbody></table></div>
 {point&&<section className="fire-card"><h3>Punto {point.id+1}</h3><p>{point.coordinate[1].toFixed(5)}, {point.coordinate[0].toFixed(5)}. No se infiere estabilidad del terreno a partir de su pendiente.</p><button className="fg-primary" onClick={()=>setWeatherId(point.id)}>Consultar lluvia y viento de este punto</button>{weatherId===point.id&&<PointWeather key={point.id} point={point.coordinate}/>}</section>}</>}
 <section className="fire-card"><h3>Antes de decidir una salida</h3><p>Esta consulta no certifica transitabilidad ni predice derrumbes. Sin datos tampoco significa sin peligro. Contrasta cierres y avisos oficiales y las condiciones del lugar.</p><a href="https://www.senapred.cl/" target="_blank" rel="noreferrer">SENAPRED · información oficial</a> · <a href="https://www.sernageomin.cl/visores-mineros/" target="_blank" rel="noreferrer">SERNAGEOMIN · cartografía</a></section></section>
}
