import { useState } from "react"

interface Props {
  name: string
  arguments_: Record<string, unknown>
  result?: string
  status: "running" | "done"
}

export default function ToolCallCard({ name, arguments_, result, status }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`tool-call-card${status === "running" ? " running" : ""}`}>
      <div className="tool-call-header" onClick={() => setExpanded(!expanded)}>
        <span className="tool-call-chevron">{expanded ? "▾" : "▸"}</span>
        <span className="tool-call-indicator">{status === "running" ? "⚙" : "✓"}</span>
        <span className="tool-call-name">{name}</span>
      </div>
      {expanded && (
        <div className="tool-call-detail">
          {Object.keys(arguments_).length > 0 && (
            <div className="tool-call-args">
              {JSON.stringify(arguments_, null, 1)}
            </div>
          )}
          {result && status === "done" && (
            <div className="tool-call-result">{result}</div>
          )}
        </div>
      )}
    </div>
  )
}
