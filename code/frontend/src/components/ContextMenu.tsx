import { useEffect, useRef, useState } from "react"

export interface MenuItem {
  label: string
  onClick: () => void
  separator?: boolean
}

interface Props {
  x: number
  y: number
  items: MenuItem[]
  onClose: () => void
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [onClose])

  useEffect(() => {
    const handler = () => onClose()
    window.addEventListener("scroll", handler, true)
    return () => window.removeEventListener("scroll", handler, true)
  }, [onClose])

  const [adjX, setAdjX] = useState(x)
  const [adjY, setAdjY] = useState(y)

  useEffect(() => {
    if (ref.current) {
      const r = ref.current.getBoundingClientRect()
      setAdjX(Math.min(x, window.innerWidth - r.width - 4))
      setAdjY(Math.min(y, window.innerHeight - r.height - 4))
    }
  }, [x, y])

  return (
    <div className="context-menu" ref={ref} style={{ left: adjX, top: adjY }}>
      {items.map((item, i) => (
        <div key={i} className="menu-item" onClick={item.onClick}>
          {item.label}
        </div>
      ))}
    </div>
  )
}

interface ConfirmProps {
  title: string
  onOk: () => void
  onCancel: () => void
}

export function ConfirmDialog({ title, onOk, onCancel }: ConfirmProps) {
  const okRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    okRef.current?.focus()
  }, [])

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-title">{title}</div>
        <div className="dialog-btns">
          <button className="cancel-btn" onClick={onCancel}>
            取消
          </button>
          <button ref={okRef} className="ok-btn" onClick={onOk}>
            确定
          </button>
        </div>
      </div>
    </div>
  )
}
