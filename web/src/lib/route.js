// GPX stays in the browser. Segment boundaries are preserved: no invented connecting paths.
export function validateSegments(segments) {
  const usable = segments.filter(s => s.length > 1)
  const count = usable.reduce((n, s) => n + s.length, 0)
  if (!count || count > 20000) throw new Error('El GPX debe contener entre 2 y 20.000 puntos de recorrido.')
  if (usable.some(s => s.some(p => p.length !== 2 || !p.every(Number.isFinite) || p[0] < -76 || p[0] > -66 || p[1] < -56 || p[1] > -17))) throw new Error('Hay coordenadas inválidas o fuera del área de consulta de Chile.')
  return usable
}
export function parseGpx(text) {
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error('GPX con declaraciones externas no admitido.')
  const xml = new DOMParser().parseFromString(text, 'application/xml')
  if (xml.querySelector('parsererror') || xml.documentElement.localName !== 'gpx') throw new Error('El archivo no es un GPX válido.')
  const groups = Array.from(xml.getElementsByTagNameNS('*', 'trkseg'))
  if (!groups.length) groups.push(...xml.getElementsByTagNameNS('*', 'rte'))
  return validateSegments(groups.map(g => Array.from(g.children).filter(n => ['trkpt', 'rtept'].includes(n.localName)).map(n => [n.hasAttribute('lon') && n.getAttribute('lon').trim() ? Number(n.getAttribute('lon')) : NaN, n.hasAttribute('lat') && n.getAttribute('lat').trim() ? Number(n.getAttribute('lat')) : NaN])))
}
export function routeKm(segments) {
  const rad = Math.PI / 180
  let total = 0
  for (const segment of segments) for (let i = 1; i < segment.length; i++) {
    const [a,b] = [segment[i-1],segment[i]]
    const h = Math.sin((b[1]-a[1])*rad/2)**2 + Math.cos(a[1]*rad)*Math.cos(b[1]*rad)*Math.sin((b[0]-a[0])*rad/2)**2
    total += 6371 * 2 * Math.asin(Math.sqrt(Math.min(1,h)))
  }
  return total
}
export function sampleRoute(segments, limit=20) {
  const points = segments.flat()
  const count = Math.min(points.length,limit)
  return Array.from({length:count}, (_,i) => ({id:i, coordinate:points[Math.round(i*(points.length-1)/(count-1))]}))
}
export function insideRing([x,y], ring) {
  let inside=false
  for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
    const [a,b]=ring[i], [c,d]=ring[j]
    if (((b>y)!==(d>y)) && x<(c-a)*(y-b)/(d-b)+a) inside=!inside
  }
  return inside
}
export function terrainAt(point, features) {
  return features.find(f => f.geometry.type==='Polygon' && insideRing(point,f.geometry.coordinates[0]) && !f.geometry.coordinates.slice(1).some(r=>insideRing(point,r)))?.properties ?? null
}
