import { useState } from "react"

interface Props {
  topicName: string
  onNewTopic: () => void
  onToggleHistory: () => void
  onRename: (name: string) => void
}

export default function TopicHeader({ topicName, onNewTopic, onToggleHistory, onRename }: Props) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(topicName)

  const handleDoubleClick = () => {
    setEditValue(topicName)
    setEditing(true)
  }

  const handleSubmit = () => {
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== topicName) {
      onRename(trimmed)
    }
    setEditing(false)
  }

  return (
    <div className="chat-header">
      <div className="chat-header-left">
        {editing ? (
          <input
            className="chat-topic-name-input"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSubmit}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit()
              if (e.key === "Escape") setEditing(false)
            }}
            autoFocus
          />
        ) : (
          <span className="chat-topic-name" onDoubleClick={handleDoubleClick} title="双击编辑话题名">
            {topicName}
          </span>
        )}
      </div>
      <div className="chat-header-right">
        <button className="chat-header-btn" onClick={onNewTopic} title="新建对话">
          +
        </button>
        <button className="chat-header-btn" onClick={onToggleHistory} title="历史对话">
          🕐
        </button>
      </div>
    </div>
  )
}
