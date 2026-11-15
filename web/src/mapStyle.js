// Geographic context only. The coloured overlays remain the actual scientific observations.
export const CONTEXT_STYLE = {
  version: 8,
  sources: {
    context: { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'], tileSize: 256,
      attribution: 'Mapa de contexto © Esri, HERE, Garmin, © OpenStreetMap' },
    names: { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}'], tileSize: 256 },
  },
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#dfe7e5' } }, { id: 'context', type: 'raster', source: 'context', paint: { 'raster-opacity': .85 } }, { id: 'place-names', type: 'raster', source: 'names' }],
}
