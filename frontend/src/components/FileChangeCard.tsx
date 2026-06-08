import type { ModifiedFile } from "../types/chat"

interface Props {
  file: ModifiedFile
  onViewDiff: () => void
}

const changeLabels: Record<string, string> = {
  created: "新增",
  modified: "修改",
  deleted: "删除",
}

export default function FileChangeCard({ file, onViewDiff }: Props) {
  return (
    <div className="file-change-card" onClick={onViewDiff}>
      <span className={`file-change-badge ${file.change_type}`}>
        {changeLabels[file.change_type] || file.change_type}
      </span>
      <span className="file-change-path">
        {file.path}
      </span>
      <span className="file-change-state">已执行</span>
    </div>
  )
}
