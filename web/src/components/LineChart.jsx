// Minimal dependency-free line chart for a single dB series over time. Gaps (null values,
// e.g. masked/no-data samples) break the line instead of interpolating across them.
const WIDTH = 320
const HEIGHT = 140
const PAD = { left: 36, right: 8, top: 8, bottom: 22 }

export default function LineChart({ points, yLabel }) {
  const values = points.map((p) => p.y).filter((y) => y !== null && y !== undefined)
  if (values.length === 0) return <p className="hint">Sin valores válidos en este punto.</p>
  const yMin = Math.min(...values)
  const yMax = Math.max(...values)
  const ySpan = yMax - yMin || 1
  const innerW = WIDTH - PAD.left - PAD.right
  const innerH = HEIGHT - PAD.top - PAD.bottom
  const x = (i) => PAD.left + (points.length <= 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const y = (v) => PAD.top + innerH - ((v - yMin) / ySpan) * innerH

  const segments = []
  let current = []
  points.forEach((p, i) => {
    if (p.y === null || p.y === undefined) {
      if (current.length) segments.push(current)
      current = []
    } else {
      current.push(`${x(i)},${y(p.y)}`)
    }
  })
  if (current.length) segments.push(current)

  return (
    <svg width={WIDTH} height={HEIGHT} className="line-chart" role="img">
      <text x={2} y={PAD.top + 4} className="axis-label">
        {yMax.toFixed(1)}
      </text>
      <text x={2} y={HEIGHT - PAD.bottom} className="axis-label">
        {yMin.toFixed(1)}
      </text>
      {segments.map((seg, i) => (
        <polyline key={i} points={seg.join(' ')} fill="none" stroke="#8fb3c7" strokeWidth="2" />
      ))}
      {points.map((p, i) =>
        p.y === null || p.y === undefined ? null : <circle key={i} cx={x(i)} cy={y(p.y)} r="2.5" fill="#d98a4a" />,
      )}
      <text x={PAD.left} y={HEIGHT - 4} className="axis-label">
        {points[0]?.label}
      </text>
      <text x={WIDTH - PAD.right} y={HEIGHT - 4} className="axis-label" textAnchor="end">
        {points[points.length - 1]?.label}
      </text>
      <text x={0} y={12} className="axis-title" transform={`rotate(-90 10 ${HEIGHT / 2})`}>
        {yLabel}
      </text>
    </svg>
  )
}
