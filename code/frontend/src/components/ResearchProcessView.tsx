import { useState } from "react"
import ThinkingBlock from "./ThinkingBlock"

interface ProcessEntry {
  agent_name: string
  type: string
  timestamp: string
  content: unknown
  reasoning?: string
}

interface Props {
  entries: ProcessEntry[]
}

interface ThinkingItem { type: "thinking"; agent_name: string; content: string; streaming: boolean; timestamp: string }
interface MessageItem { type: "message"; agent_name: string; content: string; streaming: boolean; timestamp: string }
interface ToolGroupItem { type: "tool_group"; agent_name: string; tools: Array<{ name: string; args: unknown }>; timestamp: string }
interface HandoffItem { type: "handoff"; from: string; to: string; message: string; timestamp: string }
type DisplayItem = ThinkingItem | MessageItem | ToolGroupItem | HandoffItem

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

function convertEntriesToDisplayItems(entries: ProcessEntry[]): DisplayItem[] {
  const items: DisplayItem[] = []
  for (const entry of entries) {
    if (entry.type === "assistant") {
      if (entry.reasoning) {
        items.push({ type: "thinking", agent_name: entry.agent_name, content: entry.reasoning, streaming: false, timestamp: entry.timestamp })
      }
      const text = typeof entry.content === "string" ? entry.content : JSON.stringify(entry.content, null, 2)
      items.push({ type: "message", agent_name: entry.agent_name, content: text, streaming: false, timestamp: entry.timestamp })
    } else if (entry.type === "handoff") {
      const obj = typeof entry.content === "object" && entry.content !== null ? (entry.content as Record<string, unknown>) : {}
      items.push({ type: "handoff", from: String(obj.from ?? entry.agent_name), to: String(obj.to ?? ""), message: String(obj.message ?? ""), timestamp: entry.timestamp })
    } else if (entry.type === "tool_call") {
      const obj = typeof entry.content === "object" && entry.content !== null ? (entry.content as Record<string, unknown>) : {}
      const tool = { name: String(obj.name ?? "tool"), args: obj.args }
      const last = items[items.length - 1]
      if (last?.type === "tool_group" && last.agent_name === entry.agent_name) {
        last.tools.push(tool)
      } else {
        items.push({ type: "tool_group", agent_name: entry.agent_name, tools: [tool], timestamp: entry.timestamp })
      }
    }
  }
  return items
}

export default function ResearchProcessView({ entries }: Props) {
  const items = convertEntriesToDisplayItems(entries)

  return (
    <div className="research-panel">
      <div className="research-header">
        <span className="research-topic">研究过程回放</span>
      </div>
      <div className="research-messages">
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
                <ThinkingBlock content={item.content} streaming={false} />
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
      </div>
    </div>
  )
}
