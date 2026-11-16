import {useEffect,useRef} from 'react'
import {Map,NavigationControl} from 'maplibre-gl'
import {FIRE_CONTEXT_STYLE} from '../mapStyle'
export default function RouteMap({segments,samples,onSelect}) {
 const element=useRef(null), callback=useRef(onSelect)
 useEffect(()=>{callback.current=onSelect},[onSelect])
 useEffect(()=>{
  const all=segments.flat()
  const m=new Map({container:element.current,style:FIRE_CONTEXT_STYLE,center:all[0],zoom:11,scrollZoom:true})
  m.addControl(new NavigationControl())
  m.on('load',()=>{
   m.addSource('route',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'MultiLineString',coordinates:segments}}})
   m.addLayer({id:'route',source:'route',type:'line',paint:{'line-color':'#78bafa','line-width':4}})
   m.addSource('samples',{type:'geojson',data:{type:'FeatureCollection',features:samples.map(p=>({type:'Feature',properties:{id:p.id},geometry:{type:'Point',coordinates:p.coordinate}}))}})
   m.addLayer({id:'samples',source:'samples',type:'circle',paint:{'circle-radius':6,'circle-color':'#e9edaa','circle-stroke-width':2,'circle-stroke-color':'#152323'}})
   m.fitBounds([[Math.min(...all.map(p=>p[0])),Math.min(...all.map(p=>p[1]))],[Math.max(...all.map(p=>p[0])),Math.max(...all.map(p=>p[1]))]],{padding:40,maxZoom:15,duration:0})
  })
  m.on('click','samples',e=>callback.current(Number(e.features[0].properties.id)))
  return ()=>m.remove()
 },[segments,samples])
 return <div ref={element} className="fire-map" aria-label="Recorrido GPX y puntos de consulta"/>
}
