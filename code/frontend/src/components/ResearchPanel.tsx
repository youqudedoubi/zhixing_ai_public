import { useEffect, useRef, useState, useCallback } from "react"
import ThinkingBlock from "./ThinkingBlock"

export interface ResearchMessage {
  agent_name: string
  content: string
  msg_type: string
  timestamp: string
}

interface Props {
  topic: string
  messages: ResearchMessage[]
  done: boolean
}

const AGENT_COLORS: Record<string, string> = {
  mentor_agent: "#7c9ef5",
  analyze_agent: "#6ec97a",
  critic_agent: "#e8a44a",
}

const AGENT_LABELS: Record<string, string> = {
  mentor_agent: "Mentor",
  analyze_agent: "Analyze",
  critic_agent: "Critic",
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts.slice(11, 19)
  return d.toLocaleTimeString("zh-CN", { hour12: false })
}

function agentColor(name: string): string {
  if (AGENT_COLORS[name]) return AGENT_COLORS[name]
  if (name.includes("mentor")) return AGENT_COLORS.mentor_agent
  if (name.includes("analyze")) return AGENT_COLORS.analyze_agent
  if (name.includes("critic")) return AGENT_COLORS.critic_agent
  return "#aaa"
}

function agentLabel(name: string): string {
  if (AGENT_LABELS[name]) return AGENT_LABELS[name]
  if (name.includes("mentor")) return "Mentor"
  if (name.includes("analyze")) return "Analyze"
  if (name.includes("critic")) return "Critic"
  return name
}

// ---------------------------------------------------------------------------
// Display model
// ---------------------------------------------------------------------------

interface ThinkingItem {
  type: "thinking"
  agent_name: string
  content: string
  streaming: boolean
  timestamp: string
}

interface MessageItem {
  type: "message"
  agent_name: string
  content: string
  streaming: boolean
  timestamp: string
}

interface ToolGroupItem {
  type: "tool_group"
  agent_name: string
  tools: Array<{ name: string; args: unknown }>
  timestamp: string
}

interface HandoffItem {
  type: "handoff"
  from: string
  to: string
  message: string
  timestamp: string
}

type DisplayItem = ThinkingItem | MessageItem | ToolGroupItem | HandoffItem

// ---------------------------------------------------------------------------
// buildDisplayItems: converts raw message stream into display model
// ---------------------------------------------------------------------------

function buildDisplayItems(messages: ResearchMessage[]): DisplayItem[] {
  const items: DisplayItem[] = []

  for (const msg of messages) {
    const { agent_name, content, msg_type, timestamp } = msg

    if (msg_type === "thinking_token") {
      const last = items[items.length - 1]
      if (last?.type === "thinking" && last.agent_name === agent_name && last.streaming) {
        last.content += content
      } else {
        items.push({ type: "thinking", agent_name, content, streaming: true, timestamp })
      }
    } else if (msg_type === "thinking_end") {
      for (let i = items.length - 1; i >= 0; i--) {
        if (items[i].type === "thinking" && items[i].agent_name === agent_name) {
          ;(items[i] as ThinkingItem).streaming = false
          break
        }
      }
    } else if (msg_type === "text_token") {
      const last = items[items.length - 1]
      if (last?.type === "message" && last.agent_name === agent_name && last.streaming) {
        last.content += content
      } else {
        items.push({ type: "message", agent_name, content, streaming: true, timestamp })
      }
    } else if (msg_type === "text_end") {
      for (let i = items.length - 1; i >= 0; i--) {
        if (items[i].type === "message" && items[i].agent_name === agent_name) {
          ;(items[i] as MessageItem).streaming = false
          break
        }
      }
    } else if (msg_type === "assistant") {
      items.push({ type: "message", agent_name, content, streaming: false, timestamp })
    } else if (msg_type === "tool_call") {
      const last = items[items.length - 1]
      let parsed: { name?: string; args?: unknown } = {}
      try { parsed = JSON.parse(content) } catch { parsed = { name: content } }
      const tool = { name: parsed.name ?? "tool", args: parsed.args }
      if (last?.type === "tool_group" && last.agent_name === agent_name) {
        last.tools.push(tool)
      } else {
        items.push({ type: "tool_group", agent_name, tools: [tool], timestamp })
      }
    } else if (msg_type === "handoff") {
      let from = agent_name, to = "", message = content
      try {
        const p = JSON.parse(content)
        from = p.from ?? agent_name
        to = p.to ?? ""
        message = p.message ?? content
      } catch { /* ignore */ }
      items.push({ type: "handoff", from, to, message, timestamp })
    }
  }

  return items
}

// ---------------------------------------------------------------------------
// ToolGroupBlock
// ---------------------------------------------------------------------------

function ToolGroupBlock({ group }: { group: ToolGroupItem }) {
  const [open, setOpen] = useState(false)
  const color = agentColor(group.agent_name)
  const label = agentLabel(group.agent_name)
  const count = group.tools.length

  return (
    <div className="research-tool-call">
      <button className="research-tool-toggle" onClick={() => setOpen((v) => !v)}>
        <span style={{ color, fontWeight: 500, marginRight: 4 }}>{label}</span>
        {open ? "▼" : "▶"} {count} 次工具调用
      </button>
      {open && (
        <div className="research-tool-body">
          {group.tools.map((t, i) => (
            <div key={i} className="research-tool-item">
              <span className="research-tool-name">[{t.name}]</span>
              {t.args != null && (
                <pre className="research-tool-args-inline">{JSON.stringify(t.args, null, 2)}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ResearchPanel
// ---------------------------------------------------------------------------

export default function ResearchPanel({ topic, messages, done }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const userScrolledRef = useRef(false)

  useEffect(() => {
    if (!userScrolledRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages.length])

  const handleScroll = useCallback(() => {
    const el = messagesContainerRef.current
    if (!el) return
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    userScrolledRef.current = !isNearBottom
  }, [])

  const items = buildDisplayItems(messages)

  return (
    <div className="research-panel">
      <div className="research-header">
        <span className="research-topic">研究：{topic}</span>
        {!done && <span className="research-status-dot" title="研究进行中" />}
        {done && <span className="research-done-badge">已完成</span>}
      </div>
      <div className="research-messages" ref={messagesContainerRef} onScroll={handleScroll}>
        {items.map((item, i) => {
          if (item.type === "tool_group") {
            return <ToolGroupBlock key={i} group={item} />
          }

          if (item.type === "thinking") {
            const color = agentColor(item.agent_name)
            return (
              <div key={i} style={{ flexShrink: 0 }}>
                <div className="research-agent-label" style={{ color }}>
                  {agentLabel(item.agent_name)}
                  <span className="research-msg-time">{formatTime(item.timestamp)}</span>
                </div>
                <ThinkingBlock content={item.content} streaming={item.streaming} />
              </div>
            )
          }

          if (item.type === "message") {
            const color = agentColor(item.agent_name)
            return (
              <div key={i} className="research-msg">
                <div className="research-msg-header" style={{ color }}>
                  {agentLabel(item.agent_name)}
                  <span className="research-msg-time">{formatTime(item.timestamp)}</span>
                  {item.streaming && <span className="thinking-indicator">...</span>}
                </div>
                <div className="research-msg-body">{item.content}</div>
              </div>
            )
          }

          if (item.type === "handoff") {
            const color = agentColor(item.from)
            return (
              <div key={i} className="research-handoff">
                <div className="research-handoff-header" style={{ color }}>
                  {agentLabel(item.from)} → {agentLabel(item.to)}
                  <span className="research-msg-time">{formatTime(item.timestamp)}</span>
                </div>
                <div className="research-handoff-body">{item.message}</div>
              </div>
            )
          }

          return null
        })}
        {!done && messages.length > 0 && (
          <div className="research-thinking">
            <span className="research-dot-anim" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}


