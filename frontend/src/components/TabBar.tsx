interface TabInfo {
  path: string
  name: string
  dirty: boolean
}

interface Props {
  tabs: TabInfo[]
  activePath: string | null
  onSelectTab: (path: string) => void
  onCloseTab: (path: string) => void
}

export default function TabBar({ tabs, activePath, onSelectTab, onCloseTab }: Props) {
  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <div
          key={tab.path}
          className={`tab${activePath === tab.path ? " active" : ""}`}
          onClick={() => onSelectTab(tab.path)}
        >
          <span className="tab-name">{tab.name}</span>
          <span className="dirty-dot">{tab.dirty ? "●" : "×"}</span>
          <button
            className="close-btn"
            onClick={(e) => {
              e.stopPropagation()
              onCloseTab(tab.path)
            }}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
