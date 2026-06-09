import { useCallback } from "react"

interface Props {
  active: string
  onSelect: (id: string) => void
}

const activities = [
  { id: "explorer", label: "资源管理器", icon: "📁" },
  { id: "simulation", label: "情境模拟", icon: "🎯" },
]

export default function ActivityBar({ active, onSelect }: Props) {
  const handleClick = useCallback(
    (id: string) => {
      onSelect(id)
    },
    [onSelect],
  )

  return (
    <div className="activity-bar">
      {activities.map((a) => (
        <button
          key={a.id}
          className={`icon-btn${active === a.id ? " active" : ""}`}
          title={a.label}
          onClick={() => handleClick(a.id)}
        >
          {a.icon}
        </button>
      ))}
    </div>
  )
}
