interface Props {
  activeActivity: string
  children: React.ReactNode
}

export default function Sidebar({ activeActivity, children }: Props) {
  if (!activeActivity) {
    return (
      <div className="sidebar">
        <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13 }}>
          点击活动栏图标开始
        </div>
      </div>
    )
  }

  return <div className="sidebar">{children}</div>
}
