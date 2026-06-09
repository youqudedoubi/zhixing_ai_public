import Editor, { type OnMount } from "@monaco-editor/react"
import { useRef, useEffect } from "react"

interface Props {
  path: string
  content: string
  onChange: (value: string) => void
  onSave: () => void
}

export default function MarkdownEditor({
  path,
  content,
  onChange,
  onSave,
}: Props) {
  const onSaveRef = useRef(onSave)
  useEffect(() => {
    onSaveRef.current = onSave
  }, [onSave])

  const handleMount: OnMount = (editor) => {
    editor.addCommand(
      // Monaco KeyMod.CtrlCmd | Monaco.KeyCode.KeyS
      2048 | 49,
      () => onSaveRef.current(),
    )
  }

  const ext = path.split(".").pop()?.toLowerCase() || ""
  const language = ext === "md" ? "markdown" : ext === "json" ? "json" : ext === "py" ? "python" : "plaintext"

  return (
    <div className="editor-wrapper">
      <Editor
        height="100%"
        language={language}
        value={content}
        theme="vs"
        onChange={(v) => onChange(v || "")}
        onMount={handleMount}
        options={{
          fontSize: 14,
          fontFamily: "var(--mono)",
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          automaticLayout: true,
        }}
      />
    </div>
  )
}
