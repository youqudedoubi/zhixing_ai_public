import { useState, useCallback, useEffect, useRef } from "react"
import { listDir, createFile } from "../api/files"
import { InlineInputRow } from "./FileTree"
import type { FileEntry } from "../types/file"

function RenameInput({ value, onSubmit, onCancel }: { value: string; onSubmit: (v: string) => void; onCancel: () => void }) {
  return (
    <input
      className="rename-input"
      autoFocus
      defaultValue={value}
      onKeyDown={(e) => {
        if (e.key === "Enter") onSubmit((e.target as HTMLInputElement).value)
        if (e.key === "Escape") onCancel()
      }}
      onBlur={(e) => onSubmit(e.target.value)}
      onClick={(e) => e.stopPropagation()}
    />
  )
}

interface InlineInputInfo {
  type: "newFile" | "newFolder" | "rename"
  parentPath: string
  value?: string
}

interface Props {
  entry: FileEntry
  depth: number
  selectedPath: string | null
  onSelectFile: (path: string) => void
  onContextMenu: (e: React.MouseEvent, entry: FileEntry | null) => void
  refreshKey: number
  inlineInput: InlineInputInfo | null
  onInlineSubmit: (name: string) => void
  onDragStart: (e: React.DragEvent, entry: FileEntry) => void
  onDragOver: (e: React.DragEvent, entry: FileEntry) => void
  onDrop: (e: React.DragEvent, entry: FileEntry) => void
  onRefresh: () => void
}

export default function FileTreeNode({
  entry,
  depth,
  selectedPath,
  onSelectFile,
  onContextMenu,
  refreshKey,
  inlineInput,
  onInlineSubmit,
  onDragStart,
  onDragOver,
  onDrop,
  onRefresh,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<FileEntry[] | null>(null)
  const [loading, setLoading] = useState(false)
  const childrenLoadedRef = useRef(false)
  const prevRefreshKey = useRef(refreshKey)

  // reload children when refreshKey changes, keep old children visible during load
  useEffect(() => {
    if (prevRefreshKey.current !== refreshKey) {
      prevRefreshKey.current = refreshKey
      childrenLoadedRef.current = false
      if (expanded) {
        setLoading(true)
        listDir(entry.path)
          .then((data) => {
            setChildren(data)
            childrenLoadedRef.current = true
          })
          .catch(() => setChildren([]))
          .finally(() => setLoading(false))
      }
    }
  }, [refreshKey, expanded, entry.path])

  // auto-expand when inlineInput targets this folder
  useEffect(() => {
    if (inlineInput?.parentPath === entry.path && !expanded) {
      loadAndExpand()
    }
  }, [inlineInput?.parentPath])

  const loadAndExpand = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listDir(entry.path)
      setChildren(data)
      childrenLoadedRef.current = true
    } catch {
      setChildren([])
    } finally {
      setLoading(false)
      setExpanded(true)
    }
  }, [entry.path])

  const handleToggle = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation()
      if (!expanded) {
        setLoading(true)
        try {
          const data = await listDir(entry.path)
          setChildren(data)
          childrenLoadedRef.current = true
        } catch {
          setChildren([])
        } finally {
          setLoading(false)
        }
        setExpanded(true)
      } else {
        setExpanded(false)
      }
    },
    [expanded, entry.path],
  )

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      if (entry.type === "file") {
        onSelectFile(entry.path)
      } else {
        handleToggle(e)
      }
    },
    [entry, onSelectFile, handleToggle],
  )

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      onContextMenu(e, entry)
    },
    [entry, onContextMenu],
  )

  const handleInlineConfirm = useCallback(
    async (name: string) => {
      if (!name.trim()) {
        onInlineSubmit("")
        return
      }
      // for new file/folder inside this folder, create and reload
      if (inlineInput?.type !== "rename") {
        const p = entry.path + "/" + name.trim()
        await createFile(p, inlineInput!.type === "newFolder")
        // reload children
        try {
          const data = await listDir(entry.path)
          setChildren(data)
          childrenLoadedRef.current = true
        } catch {
          setChildren([])
        }
      }
      onInlineSubmit(name)
      onRefresh()
    },
    [entry.path, inlineInput, onInlineSubmit, onRefresh],
  )

  const isRenaming = inlineInput?.type === "rename" && inlineInput.parentPath === entry.path
  const icon = "📁"
  const isSelected = selectedPath === entry.path

  return (
    <>
      <div
        className={`file-tree-node${isSelected ? " selected" : ""}`}
        style={{ paddingLeft: depth * 16 + 8 }}
        draggable={entry.type === "file"}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        onDragStart={(e) => onDragStart(e, entry)}
        onDragOver={(e) => entry.type === "folder" ? onDragOver(e, entry) : undefined}
        onDrop={(e) => entry.type === "folder" ? onDrop(e, entry) : undefined}
      >
        <span
          className={`arrow${entry.type !== "folder" ? " empty" : ""}`}
          onClick={entry.type === "folder" ? handleToggle : undefined}
        >
          {loading ? "⏳" : expanded ? "▾" : "▸"}
        </span>
        <span className="file-icon">{entry.type === "folder" ? icon : "📄"}</span>
        {isRenaming ? (
          <RenameInput
            value={entry.name}
            onSubmit={onInlineSubmit}
            onCancel={() => onInlineSubmit("")}
          />
        ) : (
          <span className="node-name" title={entry.name}>
            {entry.name}
          </span>
        )}
      </div>
      {entry.type === "folder" && expanded && (
        <>
          {children && children.map((child) => (
            <FileTreeNode
              key={child.path}
              entry={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              onContextMenu={onContextMenu}
              refreshKey={refreshKey}
              inlineInput={inlineInput}
              onInlineSubmit={onInlineSubmit}
              onDragStart={onDragStart}
              onDragOver={onDragOver}
              onDrop={onDrop}
              onRefresh={onRefresh}
            />
          ))}
          {inlineInput?.parentPath === entry.path && inlineInput.type !== "rename" && (
            <InlineInputRow
              type={inlineInput.type}
              depth={depth + 1}
              onSubmit={handleInlineConfirm}
              onCancel={() => onInlineSubmit("")}
            />
          )}
        </>
      )}
    </>
  )
}
