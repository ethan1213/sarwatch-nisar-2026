import {useEffect} from 'react'
const EMPTY={type:'FeatureCollection',features:[]}
export default function useSectorOverlay(ref,geometry){
 useEffect(()=>{const m=ref.current;if(!m)return;const apply=()=>{const d=geometry||EMPTY;if(m.getSource('review-sectors'))m.getSource('review-sectors').setData(d);else{m.addSource('review-sectors',{type:'geojson',data:d});m.addLayer({id:'review-sectors',type:'line',source:'review-sectors',paint:{'line-color':['match',['get','kind'],'left','#7bd6db','right','#eead65','#d6f84c'],'line-width':4,'line-dasharray':[2,1]}})}};if(m.getLayer('context'))apply();else m.once('load',apply);return()=>m.off('load',apply)},[ref,geometry])
}
