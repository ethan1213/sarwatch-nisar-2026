const BASE = '/api'

export function siteAPI(slug) {
  const base = `/${slug}`
  return {
    fetchPantanalManifest: () => getJSON(base + '/manifest'),
    fetchPantanalLayer: (before, after, pol, mode) => getJSON(base + '/layer', { before, after, pol, mode }),
    fetchPantanalWaterMethods: (after) => getJSON(base + '/water-methods', { after }),
    fetchPantanalWaterLayer: (after, pol, method) => getJSON(base + '/water-layer', { after, pol, method }),
    fetchPantanalPointSeries: (lon, lat, pol) => getJSON(base + '/point-series', { lon, lat, pol }),
    fetchPantanalReading: (before, after, pol, profile) => getJSON(base + '/reading', { before, after, pol, profile }),
    fetchPantanalPredictionReference: () => getJSON(base + '/prediction-reference'),
    fetchPantanalWeather: (lat, lon, mode, start, end) => getJSON(base + '/weather', { lat, lon, mode, start, end }),
    postPantanalAssistant: (question, before, after, polarization, profile) => postJSON(base + '/assistant', { question, before, after, polarization, profile }),
  }
}

export const fetchStudy = (slug, kind, params) => getJSON(`/study/${slug}/${kind}`, params)

async function getJSON(path, params) {
  const url = new URL(BASE + path, window.location.origin)
  if (params) for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) url.searchParams.set(k, v)
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

async function postJSON(path, body) {
  const res = await fetch(BASE + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(payload.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const fetchWorldMeta = () => getJSON('/world/meta')
export const fetchWorldCells = () => getJSON('/world/cells')
export const fetchWorldPoint = (lon, lat) => getJSON('/world/point', { lon, lat })

export const fetchPantanalManifest = () => getJSON('/pantanal/manifest')
export const fetchPantanalLayer = (before, after, pol, mode) => getJSON('/pantanal/layer', { before, after, pol, mode })
export const fetchPantanalWaterMethods = (after) => getJSON('/pantanal/water-methods', { after })
export const fetchPantanalWaterLayer = (after, pol, method) => getJSON('/pantanal/water-layer', { after, pol, method })
export const fetchPantanalPointSeries = (lon, lat, pol) => getJSON('/pantanal/point-series', { lon, lat, pol })
export const fetchPantanalReading = (before, after, pol, profile) => getJSON('/pantanal/reading', { before, after, pol, profile })
export const fetchPantanalPredictionReference = () => getJSON('/pantanal/prediction-reference')
export const fetchPantanalWeather = (lat, lon, mode, start, end) => getJSON('/pantanal/weather', { lat, lon, mode, start, end })
export const postPantanalAssistant = (question, before, after, polarization, profile) => postJSON('/pantanal/assistant', { question, before, after, polarization, profile })
