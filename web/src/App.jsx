import { useState } from 'react'
import './App.css'
import MundoView from './views/MundoView'
import PantanalView from './views/PantanalView'
import StudyView from './views/StudyView'
import ChileView from './views/ChileView'

const REGIONS = [
  { key: 'concepcion_penco', label: 'Concepción y Penco', available: true },
  { key: 'biobio', label: 'Biobío', available: true },
  { key: 'pantanal', label: 'Pantanal', available: true },
  { key: 'metropolitana', label: 'Santiago', available: true },
  { key: 'valparaiso', label: 'Viña del Mar y Valparaíso', available: true },
  { key: 'mundo', label: 'Explorar el mundo', available: true },
]

export default function App() {
  const [region, setRegion] = useState('valparaiso')
  const [topic, setTopic] = useState('radar')
  const label = REGIONS.find(r => r.key === region).label
  const chile = ['concepcion_penco', 'biobio'].includes(region)

  return (
    <div className="app">
      <header className="brandbar"><a className="brand" href="#">SAR<span>Watch</span><small>Observa. Compara. Comprende.</small></a><div className="brand-tag">Datos de satélite, con evidencia visible</div></header>
      <div className="step-label"><span>1</span> Elige el lugar que quieres explorar</div>
      <nav className="region-switch" aria-label="Lugar de estudio">
        {REGIONS.map((r) => (
          <button key={r.key} className={region === r.key ? 'active' : ''} aria-pressed={region === r.key} onClick={() => { setRegion(r.key); setTopic('radar') }}>
            {r.label}
          </button>
        ))}
      </nav>
      {region !== 'mundo' && !chile && <nav className="region-switch topic-switch" aria-label="Qué quieres revisar">
        <span className="step-label"><span>2</span> Qué quieres revisar</span>
        <button aria-pressed={topic === 'radar'} onClick={() => setTopic('radar')}>◫ Comparar el terreno</button>
        <button aria-pressed={topic === 'thermal'} onClick={() => setTopic('thermal')}>♨ Ver calor detectado</button>
        {region === 'metropolitana' && <><button aria-pressed={topic === 'postfire'} onClick={() => setTopic('postfire')}>△ Escenarios de lluvia</button><button aria-pressed={topic === 'impacts'} onClick={() => setTopic('impacts')}>◇ Carbono y relieve · experimental</button></>}
      </nav>}
      {region === 'mundo' && <MundoView />}
      {chile && <ChileView key={region} slug={region} />}
      {region !== 'mundo' && !chile && topic === 'radar' && <PantanalView key={region} slug={region} label={label} />}
      {region !== 'mundo' && !chile && topic !== 'radar' && <StudyView key={`${region}-${topic}`} slug={region} kind={topic} label={`${label} · ${topic === 'impacts' ? 'Carbono y relieve' : topic === 'thermal' ? 'Calor detectado' : 'Escenarios de lluvia'}`} />}
      <footer className="caption" style={{padding: 20}}>Proyecto independiente de Software Detective. Fuentes NASA, ISRO, NOAA y Copernicus; no implica patrocinio ni respaldo institucional.</footer>
    </div>
  )
}
