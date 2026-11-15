import { useEffect, useRef, useState } from 'react'
import '../fire.css'
import '../fireground.css'
import { fetchFireStory } from '../api'
import FireBefore from '../components/FireBefore'
import FireDuring from '../components/FireDuring'
import FireAfter from '../components/FireAfter'
import FireRadarSite from '../components/FireRadarSite'
import FireTerrain from '../components/FireTerrain'
import FireVina2024 from '../components/FireVina2024'
import FireOfficialPerimeters from '../components/FireOfficialPerimeters'

const LAYERS = [
  {key:'during', icon:'◉', label:'Focos y clima', source:'FIRMS / GOES-19 / Open-Meteo'},
  {key:'scar', icon:'◈', label:'Señal de quema', source:'Sentinel-2 · comparación óptica'},
  {key:'radar', icon:'▱', label:'Evolución NISAR', source:'GCOV · HV · feb–oct 2026'},
  {key:'official',icon:'⬡',label:'Extensión observada',source:'Copernicus EMS · 21–25 ene 2026'},
  {key:'terrain',icon:'△',label:'Altura y pendiente',source:'Copernicus DEM · medias por celda'},
  {key:'before', icon:'◎', label:'Prioridad de vigilancia', source:'Modelo exploratorio · 12 días'},
]
const HEADINGS = {official:['Cómo cambió la extensión cartografiada','Delimitaciones oficiales de Copernicus EMS, con fechas de adquisición y versiones.'],terrain:['Cómo es el terreno','Altura y pendiente del DEM externo, agregadas por celda. No provienen de NISAR.'],during:['Focos y condiciones','Selecciona un punto FIRMS para consultar clima y sectores laterales al viento. El histórico de enero usa GOES-19.'],scar:['Qué señales quedaron','Señal óptica de quema. Las clases no equivalen a un perímetro oficial del incendio.'],radar:['Cómo evolucionó el terreno','Dos observaciones NISAR posteriores al incendio; desliza para compararlas.'],before:['Qué podemos anticipar','Evaluación de un índice de vigilancia. No pronostica el recorrido del frente del fuego.']}
function Dialog({kind,summary,capability,onClose}) {
  const ref=useRef(null)
  useEffect(()=>{ref.current.showModal()},[])
  return <dialog className="fg-dialog" ref={ref} onCancel={onClose} aria-labelledby="dialog-title"><button className="fg-close" aria-label="Cerrar panel" onClick={onClose}>×</button>
    <p className="fg-kicker">TRANSPARENCIA</p><h2 id="dialog-title">{kind==='sources'?'Fuentes y procedencia':kind==='ai'?'Uso de IA':'Anticipación y propagación'}</h2>
    {kind==='sources' && <><p>Cada observación mantiene su fuente y fecha. El mapa base aporta contexto geográfico.</p><ul>{Object.values(summary.sources).map(s=><li key={s}>{s}</li>)}</ul><p>Diseño adaptado de la propuesta de Figma compartida por el equipo. Traza Urbana se cita como referencia de interfaz indicada en esa propuesta; no se copian sus datos.</p><a href="https://www.figma.com/make/zwU59kMtbg8bR9XPZJBfmI/NISAR-Surface-Change-App" target="_blank" rel="noreferrer">Diseño de referencia</a> · <a href="https://trazaurbana.cl/" target="_blank" rel="noreferrer">Traza Urbana</a></>}
    {kind==='ai' && <><p>Claude Code y Codex ayudaron a programar, revisar y documentar. La aplicación no envía preguntas a un modelo de lenguaje externo. Las cifras provienen de scripts reproducibles y archivos de resultados.</p><p>Los mapas muestran observaciones o estimaciones identificadas; no son imágenes generadas por IA. El índice de vigilancia es exploratorio y su evaluación está disponible en el panel.</p><a href="https://github.com/ethan1213/sarwatch-nisar-2026/blob/main/docs/entrega/uso_de_ia.md" target="_blank" rel="noreferrer">Declaración y fuentes</a></>}
    {kind==='limits' && <>{capability?.existing_model&&<section className="fg-model-metrics"><h3>Índice de vigilancia evaluado</h3><p>AUC en fechas retenidas: {capability.existing_model.evaluation[capability.existing_model.name].held_out_dates.roc_auc.toFixed(3)}. Casos con calor en esa evaluación: {capability.existing_model.evaluation[capability.existing_model.name].held_out_dates.positives}. Una AUC de 0,5 equivale al azar; no es precisión de trayectoria.</p></section>}<p>En Biobío, el modelo disponible ordena celdas por prioridad de vigilancia a 12 días. Eso es distinto de calcular por dónde y a qué velocidad se propagará un incendio.</p><h3>Insumos que faltan para evaluar propagación</h3><ul>{(capability?.missing_inputs || ['La consulta del inventario no está disponible. Revisa las fuentes y los registros descargables.']).map(s=><li key={s}>{s}</li>)}</ul><p>La humedad relativa del aire no sustituye la humedad del combustible. La señal NISAR no se convierte directamente en biomasa ni en un modelo de combustible. No se calculan flancos seguros, rutas de entrada ni probabilidades de propagación sin validación.</p><a href="https://research.fs.usda.gov/treesearch/55928" target="_blank" rel="noreferrer">Fundamento de modelos de propagación · USDA Forest Service</a></>}
    <button className="fg-primary" onClick={onClose}>Volver al mapa</button>
  </dialog>
}
export default function FireView({onNavigate}) {
  const [summary,setSummary]=useState(null), [error,setError]=useState(''), [parts,setParts]=useState({}), [partError,setPartError]=useState('')
  const [exportError,setExportError]=useState('')
  const [controlsOpen,setControlsOpen]=useState(false)
  const [vinaMode,setVinaMode]=useState('historical'),[terrainFocus,setTerrainFocus]=useState(null)
  const [area,setArea]=useState('biobio'), [layer,setLayer]=useState('during'), [dialog,setDialog]=useState(null), [capability,setCapability]=useState(null)
  const part=layer==='scar'||layer==='radar'?'after':layer==='terrain'?'before':layer
  useEffect(()=>{let alive=true; fetchFireStory().then(d=>{if(alive)setSummary(d)}).catch(()=>{if(alive)setError('No pudimos cargar las observaciones. Reintenta la consulta.')}); fetch('/api/fire/propagation-readiness').then(r=>r.ok?r.json():null).then(d=>{if(alive)setCapability(d)}).catch(()=>{});return()=>{alive=false}},[])
  useEffect(()=>{if(parts[part]||area!=='biobio'||layer==='official')return;let alive=true;fetchFireStory(part).then(d=>{if(alive)setParts(p=>({...p,[part]:d}))}).catch(()=>{if(alive)setPartError('Esta capa no pudo cargar. Puedes elegir otra o reintentar.')});return()=>{alive=false}},[part,parts,area,layer])
  function focusMain(){requestAnimationFrame(()=>document.querySelector('.fg-main')?.scrollIntoView({block:'start',behavior:'instant'}))}
  function selectLayer(key){setPartError('');setLayer(key);setControlsOpen(false);focusMain()}
  function selectArea(key){setArea(key);setControlsOpen(false);focusMain()}
  async function exportEvidence(){
    try {
      const evidence=area==='biobio'?summary:await fetch(vinaMode==='historical'?'/api/fire/vina-2024':'/api/valparaiso/manifest').then(r=>{if(!r.ok)throw new Error();return r.json()})
      const blob=new Blob([JSON.stringify({exported_utc:new Date().toISOString(),area,layer:area==='biobio'?layer:vinaMode,evidence,terrain_focus:terrainFocus,propagation:area==='biobio'?capability:{spread_prediction_enabled:false,reason:'No existe un modelo de propagación evaluado para Viña del Mar.'}},null,2)],{type:'application/json'})
      const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`sarwatch-${area}-evidencia.json`;a.click();URL.revokeObjectURL(url);setExportError('')
    } catch {setExportError('No pudimos exportar los datos. Reintenta cuando vuelva la conexión.')}
  }
  return <div className="fg fire">
    <header className="fg-header"><a href="#" className="fg-brand"><img className="fg-logo" src="/favicon.svg" width="44" height="44" alt="" /><span>SARWATCH<small>ANÁLISIS TERRITORIAL PARA BRIGADAS</small></span></a><nav aria-label="Navegación principal"><button aria-current={!dialog?'page':undefined} onClick={()=>setDialog(null)}>Explorar</button><button onClick={()=>setDialog('sources')}>Fuentes y datos</button><button onClick={()=>setDialog('ai')}>Uso de IA</button></nav><span className="fg-revisit"><b>NISAR</b> · NO ES EN VIVO</span></header>
    <div className="fg-warning"><span>◉ <strong>FUENTES Y FECHAS VISIBLES</strong> · Observaciones satelitales y pronóstico meteorológico.</span><button onClick={()=>setDialog('limits')}>Ver alcance y límites →</button></div>
    <div className="fg-workspace"><aside className="fg-sidebar"><p className="fg-kicker">ÁREA DE ESTUDIO</p><h1>{area==='biobio'?'Concepción–Penco–Tomé':'Viña del Mar'}</h1><div className="fg-area-switch"><button aria-pressed={area==='biobio'} onClick={()=>selectArea('biobio')}>Biobío<small>Incendios · enero 2026</small></button><button aria-pressed={area==='valparaiso'} onClick={()=>selectArea('valparaiso')}>Viña del Mar<small>Incendio 2024 · radar 2026</small></button></div>
      <button className="fg-mobile-controls" aria-expanded={controlsOpen} onClick={()=>setControlsOpen(v=>!v)}>Capas y fuentes · {area==='biobio'?LAYERS.find(l=>l.key===layer).label:'Radar'} ▾</button><div className={`fg-sidebar-rest ${controlsOpen?'is-open':''}`}><p className="fg-context">{area==='biobio'?'NISAR: febrero, junio y octubre de 2026. No hay observación previa al incendio de enero en esta serie.':'Sentinel-2 muestra el antes y después de febrero de 2024. NISAR de octubre de 2026 se consulta por separado.'}</p>
      <div className="fg-sidebar-title"><p className="fg-kicker">QUÉ QUIERES OBSERVAR</p><button onClick={()=>setDialog('sources')}>Fuentes</button></div>
      <nav className="fg-layers" aria-label="Capas de análisis">{area==='biobio'?LAYERS.map(l=><button key={l.key} aria-pressed={layer===l.key} onClick={()=>selectLayer(l.key)}><span className="fg-layer-icon" aria-hidden="true">{l.icon}</span><span>{l.label}<small>{l.source}</small></span><span className="fg-radio" aria-hidden="true" /></button>):<><button aria-pressed={vinaMode==='historical'} onClick={()=>setVinaMode('historical')}>Incendio de 2024<small>Sentinel-2 · antes y después</small></button><button aria-pressed={vinaMode==='radar'} onClick={()=>setVinaMode('radar')}>Radar de 2026<small>NISAR · HH / HV</small></button></>}</nav>
      <section className="fg-model-status"><p className="fg-kicker">ANTICIPACIÓN</p><strong>Prioridad de vigilancia a 12 días</strong><p>Modelo evaluado para ordenar celdas que requieren revisión. La trayectoria del fuego se estudia por separado.</p><button onClick={()=>setDialog('limits')}>Métricas y alcance ↗</button></section>
      <details className="fg-more"><summary>Otros estudios y código</summary><button onClick={()=>onNavigate?.('metropolitana')}>Santiago · laboratorio</button><button onClick={()=>onNavigate?.('concepcion_penco')}>Catálogo NISAR de Biobío</button><a href="https://github.com/ethan1213/sarwatch-nisar-2026" target="_blank" rel="noreferrer">Código abierto · Apache-2.0 ↗</a></details>
      <p className="fg-attribution">Proyecto independiente de Software Detective. Sin patrocinio ni respaldo institucional de NASA, ISRO o NOAA.</p></div>
    </aside>
    <main className="fg-main"><div className="fg-toolbar"><div><p className="fg-kicker">{area==='biobio'?'ANÁLISIS PARA BRIGADAS · BIOBÍO':vinaMode==='historical'?'SENTINEL-2 · VIÑA 2024':'NISAR · CHILE CENTRAL'}</p><h2>{area==='biobio'?HEADINGS[layer][0]:vinaMode==='historical'?'Incendio de Viña · febrero de 2024':'Radar del terreno · octubre de 2026'}</h2></div><button disabled={!summary} onClick={exportEvidence}>↓ Exportar evidencia</button></div>
      <p className="fg-explanation">{area==='biobio'?HEADINGS[layer][1]:vinaMode==='historical'?'Comparación óptica anterior y posterior al incendio; distinta del radar NISAR de 2026.':'Observaciones del terreno en dos fechas; la causa del cambio requiere evidencia independiente.'}</p>
      {exportError && <p role="alert">{exportError}</p>}
      {error && <div role="alert" className="fire-empty">{error}<button onClick={()=>window.location.reload()}>Reintentar</button></div>}
      {!summary&&!error && <p role="status" className="fire-empty">Cargando observaciones verificadas…</p>}
      {summary&&area==='biobio'&&layer==='official'&&<FireOfficialPerimeters/>}
      {summary&&area==='biobio'&&layer!=='official'&&<>{partError?<div role="status" className="fire-empty">{partError}<button onClick={()=>{setPartError('');setParts(p=>({...p}))}}>Reintentar</button></div>:!parts[part]?<p role="status" className="fire-empty">Cargando capa…</p>:<>{layer==='during'&&<FireDuring data={parts.during} initialPoint={terrainFocus?.mode==='forecast'?terrainFocus:null} onInspectTerrain={point=>{setTerrainFocus(point);selectLayer('terrain')}}/>}{(layer==='scar'||layer==='radar')&&<FireAfter key={layer} data={parts.after} initialMode={layer}/>}{layer==='before'&&<FireBefore data={parts.before}/>} {layer==='terrain'&&<FireTerrain data={parts.before} focus={terrainFocus}/>}</>}</>}
      {area==='valparaiso'&&(vinaMode==='historical'?<FireVina2024/>:<FireRadarSite/>)}
    </main></div>
    {dialog&&summary&&<Dialog kind={dialog} summary={summary} capability={capability} onClose={()=>setDialog(null)}/>}
  </div>
}
