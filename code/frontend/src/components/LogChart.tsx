import { useMemo } from "react"

interface DataPoint {
  time: string   // ISO timestamp
  delta: number
  score: number  // cumulative
  reason: string
}

function parseLog(content: string): DataPoint[] {
  const points: DataPoint[] = []
  // Split by ## headings (each entry starts with ## <timestamp>)
  const blocks = content.split(/^## /m).filter((b) => b.trim())
  let cumulative = 0

  for (const block of blocks) {
    const lines = block.split("\n")
    const time = lines[0].trim()
    if (!time) continue

    const deltaMatch = block.match(/分值变动[：:]\s*([+-]?\d+)/)
    if (!deltaMatch) continue
    const delta = parseInt(deltaMatch[1], 10)
    cumulative += delta

    // Extract reason (分值变动理由 line)
    const reasonMatch = block.match(/分值变动理由[：:]\s*(.+)/)
    const reason = reasonMatch ? reasonMatch[1].trim() : ""

    points.push({ time, delta, score: cumulative, reason })
  }
  return points
}

const W = 560
const H = 260
const PAD = { top: 24, right: 24, bottom: 48, left: 48 }
const CHART_W = W - PAD.left - PAD.right
const CHART_H = H - PAD.top - PAD.bottom

function formatDate(iso: string): string {
  // Accept "2025-01-03T08:30:45" or similar
  const m = iso.match(/(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : iso.slice(0, 10)
}

interface Props {
  content: string
  patternName: string
}

export default function LogChart({ content, patternName }: Props) {
  const points = useMemo(() => parseLog(content), [content])

  if (points.length === 0) {
    return <div className="log-chart-empty">暂无数据（log.md 中未找到分值变动记录）</div>
  }

  const scores = points.map((p) => p.score)
  const minScore = Math.min(0, ...scores)
  const maxScore = Math.max(1, ...scores)
  const range = maxScore - minScore || 1

  const toX = (i: number) =>
    points.length === 1
      ? PAD.left + CHART_W / 2
      : PAD.left + (i / (points.length - 1)) * CHART_W

  const toY = (score: number) =>
    PAD.top + CHART_H - ((score - minScore) / range) * CHART_H

  const polyline = points.map((p, i) => `${toX(i)},${toY(p.score)}`).join(" ")

  // Y axis ticks
  const yTicks = [minScore, Math.round((minScore + maxScore) / 2), maxScore]

  return (
    <div className="log-chart-wrap">
      <div className="log-chart-title">{patternName} · 存在强度变化</div>
      <svg viewBox={`0 0 ${W} ${H}`} className="log-chart-svg">
        {/* Grid lines */}
        {yTicks.map((v) => (
          <line
            key={v}
            x1={PAD.left} y1={toY(v)}
            x2={PAD.left + CHART_W} y2={toY(v)}
            stroke="#3a3a4a" strokeWidth="1" strokeDasharray="4 3"
          />
        ))}
        {/* Y axis labels */}
        {yTicks.map((v) => (
          <text key={v} x={PAD.left - 6} y={toY(v) + 4}
            textAnchor="end" fontSize="11" fill="#888">{v}</text>
        ))}
        {/* X axis labels */}
        {points.map((p, i) => (
          <text key={i} x={toX(i)} y={H - 8}
            textAnchor="middle" fontSize="10" fill="#888">{formatDate(p.time)}</text>
        ))}
        {/* Area fill */}
        <polygon
          points={[
            `${toX(0)},${toY(minScore)}`,
            ...points.map((p, i) => `${toX(i)},${toY(p.score)}`),
            `${toX(points.length - 1)},${toY(minScore)}`,
          ].join(" ")}
          fill="rgba(124,158,245,0.12)"
        />
        {/* Line */}
        <polyline points={polyline} fill="none" stroke="#7c9ef5" strokeWidth="2.5" strokeLinejoin="round" />
        {/* Data points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={toX(i)} cy={toY(p.score)} r="5"
              fill="#7c9ef5" stroke="#1e1e2e" strokeWidth="2" />
            <text x={toX(i)} y={toY(p.score) - 10}
              textAnchor="middle" fontSize="11" fill="#c0c0d0">{p.score}</text>
          </g>
        ))}
      </svg>
      {/* Detail list */}
      <div className="log-chart-entries">
        {points.map((p, i) => (
          <div key={i} className="log-chart-entry">
            <span className="log-chart-entry-time">{formatDate(p.time)}</span>
            <span className={`log-chart-entry-delta ${p.delta >= 0 ? "pos" : "neg"}`}>
              {p.delta >= 0 ? `+${p.delta}` : p.delta}
            </span>
            <span className="log-chart-entry-score">→ {p.score}</span>
            {p.reason && <span className="log-chart-entry-reason">{p.reason}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
