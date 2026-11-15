// Mirrors sarwatch/views/world.py::_color exactly. See that docstring for why the typical
// range (7-12 dates) gets a neutral tone instead of an intense one: ~79% of cells land there
// (the normal NISAR repeat-orbit cadence), and giving it a strong color turns the whole map
// into one color.
export const BREAKS = [
  { max: 2, color: '#e7e2da', label: '< 2 fechas' },
  { max: 7, color: '#8fb3c7', label: '2 a 6 fechas (escaso)' },
  { max: 13, color: '#dfe6df', label: '7 a 12 fechas (típico)' },
  { max: 20, color: '#d98a4a', label: '13 a 19 fechas' },
  { max: Infinity, color: '#c6601c', label: '20 o más (excepcional)' },
]

export function colorFor(dates) {
  for (const b of BREAKS) if (dates < b.max) return b.color
  return BREAKS[BREAKS.length - 1].color
}

// MapLibre 'step' expression equivalent, built from the same breakpoints so the two never drift apart.
export function stepExpression(property = ['get', 'dates']) {
  return ['step', property, BREAKS[0].color, 2, BREAKS[1].color, 7, BREAKS[2].color, 13, BREAKS[3].color, 20, BREAKS[4].color]
}
