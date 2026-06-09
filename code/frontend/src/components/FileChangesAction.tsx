import type { FileChangeActionData, ModifiedFile } from "../types/chat"
import FileChangeCard from "./FileChangeCard"

interface Props {
  data: FileChangeActionData
  onViewDiff: (file: ModifiedFile) => void
}

export default function FileChangesAction({ data, onViewDiff }: Props) {
  return (
    <div className="file-changes-container">
      {data.files.map((file) => (
        <FileChangeCard
          key={file.path}
          file={file}
          onViewDiff={() => onViewDiff(file)}
        />
      ))}
    </div>
  )
}
