import { useState } from "react"
import Markdown from "react-markdown"

interface Props {
  content: string
  streaming: boolean
}

export default function ThinkingBlock({ content, streaming }: Props) {
  const [expanded, setExpanded] = useState(true)

  if (!content && !streaming) return null

  return (
    <div className="thinking-block">
      <div className="thinking-header" onClick={() => setExpanded(!expanded)}>
        <span className="thinking-chevron">{expanded ? "▾" : "▸"}</span>
        <span>思考过程</span>
        {streaming && <span className="thinking-indicator">...</span>}
      </div>
      {expanded && (
        <div className="thinking-content">
          {content ? <Markdown>{content}</Markdown> : (streaming ? "思考中..." : "")}
        </div>
      )}
    </div>
  )
}
