import { useState, useEffect, useRef, useCallback } from "react"
import type { TopicSummary } from "../types/chat"

interface Props {
  topics: TopicSummary[]
  currentTopicId: string | null
  show: boolean
  onClose: () => void
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}

export default function HistoryPanel({
  topics,
  currentTopicId,
  show,
  onClose,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!show) {
      setEditingId(null)
      setDeletingId(null)
    }
  }, [show])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    if (show) {
      document.addEventListener("mousedown", handleClick)
      return () => document.removeEventListener("mousedown", handleClick)
    }
  }, [show, onClose])

  const startEdit = useCallback((id: string, name: string) => {
    setEditingId(id)
    setEditValue(name)
  }, [])

  const submitEdit = useCallback(() => {
    if (editingId && editValue.trim()) {
      onRename(editingId, editValue.trim())
    }
    setEditingId(null)
  }, [editingId, editValue, onRename])

  if (!show) return null

  return (
    <div className="history-panel" ref={panelRef}>
      <div className="history-panel-header">历史对话</div>
      <button className="history-new-btn" onClick={onNew}>
        + 新建对话
      </button>
      <div className="history-list">
        {topics.map((t) => (
          <div
            key={t.id}
            className={`history-item${t.id === currentTopicId ? " active" : ""}`}
          >
            {editingId === t.id ? (
              <input
                className="history-rename-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={submitEdit}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitEdit()
                  if (e.key === "Escape") setEditingId(null)
                }}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span className="history-item-name" onClick={() => onSelect(t.id)}>
                {t.topic_name}
              </span>
            )}
            <div className="history-item-actions">
              <button
                className="history-action-btn"
                title="重命名"
                onClick={(e) => { e.stopPropagation(); startEdit(t.id, t.topic_name) }}
              >
                编辑
              </button>
              <button
                className="history-action-btn danger"
                title="删除"
                onClick={(e) => {
                  e.stopPropagation()
                  if (deletingId === t.id) {
                    onDelete(t.id)
                    setDeletingId(null)
                  } else {
                    setDeletingId(t.id)
                  }
                }}
              >
                {deletingId === t.id ? "确认删除" : "删除"}
              </button>
            </div>
          </div>
        ))}
        {topics.length === 0 && (
          <div className="history-empty">暂无历史对话</div>
        )}
      </div>
    </div>
  )
}
