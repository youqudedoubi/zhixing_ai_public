interface Props {
  show: boolean
  onCopy: () => void
  onBranch: () => void
  onClose: () => void
}

export default function BranchMenu({ show, onCopy, onBranch, onClose }: Props) {
  if (!show) return null

  return (
    <div className="branch-menu">
      <button className="branch-menu-item" onClick={() => { onCopy(); onClose() }}>
        复制
      </button>
      <button className="branch-menu-item" onClick={() => { onBranch(); onClose() }}>
        创建分支
      </button>
    </div>
  )
}
