import { useMemo } from "react"
import { diffLines } from "diff"

interface Props {
  filePath: string
  oldContent: string
  newContent: string
}

interface DiffLine {
  type: "add" | "remove" | "context"
  text: string
  lineNum?: number
}

export default function DiffView({ filePath, oldContent, newContent }: Props) {
  const lines = useMemo(() => {
    const changes = diffLines(oldContent, newContent)
    const result: DiffLine[] = []
    let oldLine = 1
    let newLine = 1

    for (const part of changes) {
      if (part.added) {
        for (const line of part.value.split("\n")) {
          if (line === "" && part.value.endsWith("\n")) continue
          result.push({ type: "add", text: line, lineNum: newLine++ })
        }
      } else if (part.removed) {
        for (const line of part.value.split("\n")) {
          if (line === "" && part.value.endsWith("\n")) continue
          result.push({ type: "remove", text: line, lineNum: oldLine++ })
        }
      } else {
        for (const line of part.value.split("\n")) {
          if (line === "" && part.value.endsWith("\n")) continue
          result.push({ type: "context", text: line })
          oldLine++
          newLine++
        }
      }
    }
    return result
  }, [oldContent, newContent])

  return (
    <div className="diff-view">
      <div className="diff-header">
        <span className="diff-file-path">{filePath}</span>
        <span className="diff-summary">
          <span className="diff-added">+{lines.filter(l => l.type === "add").length}</span>
          {" "}
          <span className="diff-removed">-{lines.filter(l => l.type === "remove").length}</span>
        </span>
      </div>
      <div className="diff-lines">
        {lines.map((line, i) => (
          <div key={i} className={`diff-line ${line.type}`}>
            <span className="diff-prefix">
              {line.type === "add" ? "+" : line.type === "remove" ? "-" : " "}
            </span>
            <span className="diff-text">{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
