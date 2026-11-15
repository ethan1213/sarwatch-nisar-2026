import {useEffect,useState} from 'react'
export default function FireSectorPanel({url,onReport}){
 const [result,setResult]=useState(null)
 useEffect(()=>{if(!url)return;const controller=new AbortController();fetch(url,{signal:controller.signal}).then(r=>{if(!r.ok)throw new Error();return r.json()}).then(data=>{setResult({url,data});onReport({url,data})}).catch(e=>{if(e.name!=='AbortError')setResult({url,error:true})});return()=>controller.abort()},[url,onReport])
 if(!url)return null
 const current=result?.url===url?result:null
 if(!current)return <p role="status" className="fire-card">Consultando sectores y relieve…</p>
 if(current.error)return <p role="status" className="fire-card">No pudimos consultar los sectores para esta hora. Cambia de hora o vuelve a seleccionar el punto.</p>
 const data=current.data
 function download(){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='sarwatch-sectores-y-viento.json';a.click();URL.revokeObjectURL(u)}
 return <section className="fire-card"><h3>Sectores laterales al viento</h3><p>Referencias a 2 km del punto para comparar el terreno. No delimitan los flancos reales ni deciden por dónde atacar.</p>{data.sectors.length?data.sectors.filter(s=>s.key!=='downwind').map(s=><div key={s.key} className="fg-sector"><strong>{s.key==='left'?'◁ Izquierdo':'▷ Derecho'}</strong><p>{s.elevation_m??'Sin dato'} m de altura media · {s.slope_deg??'Sin dato'}° de pendiente media</p></div>):<p>Viento débil: no se interpreta una dirección dominante.</p>}<p className="fire-legend">Cian: izquierdo · ámbar: derecho · lima: a sotavento. {data.time_utc} UTC.</p><details><summary>Fuente y límites</summary><p>{data.weather_source}</p><ul>{data.limits.map(l=><li key={l}>{l}</li>)}</ul></details><button onClick={download}>↓ Exportar revisión del punto</button></section>
}
