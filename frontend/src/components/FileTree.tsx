import { useState, useCallback, useEffect } from "react"
import FileTreeNode from "./FileTreeNode"
import ContextMenu, { ConfirmDialog } from "./ContextMenu"
import type { MenuItem } from "./ContextMenu"
import { listDir, createFile, deleteFile, moveFile, renameFile, getRoot } from "../api/files"
import type { FileEntry } from "../types/file"

interface Props {
  refreshKey: number
  selectedPath: string | null
  onSelectFile: (path: string) => void
  onRefresh: () => void
}

export default function FileTree({
  refreshKey,
  selectedPath,
  onSelectFile,
  onRefresh,
}: Props) {
  const [rootEntries, setRootEntries] = useState<FileEntry[]>([])
  const [rootName, setRootName] = useState("ROOT")
  const [rootExpanded, setRootExpanded] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ctxMenu, setCtxMenu] = useState<{
    x: number; y: number; entry: FileEntry | null
  } | null>(null)
  const [inlineInput, setInlineInput] = useState<{
    type: "newFile" | "newFolder" | "rename"
    parentPath: string
    value?: string
  } | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<FileEntry | null>(null)

  useEffect(() => {
    setError(null)
    getRoot()
      .then((r) => setRootName(r.name))
      .catch(() => setError("无法连接到后端服务"))
    listDir("")
      .then((data) => { setRootEntries(data); setError(null) })
      .catch(() => { setRootEntries([]); setError("无法加载文件列表") })
  }, [refreshKey])

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, entry: FileEntry | null) => {
      setCtxMenu({ x: e.clientX, y: e.clientY, entry })
    },
    [],
  )

  const closeContextMenu = useCallback(() => setCtxMenu(null), [])

  const handleInlineSubmit = useCallback(
    async (name: string) => {
      if (!inlineInput) return
      if (!name.trim()) {
        setInlineInput(null)
        return
      }
      if (inlineInput.type === "rename") {
        await renameFile(inlineInput.parentPath, name.trim())
      } else if (!inlineInput.parentPath) {
        // root-level: create here
        const p = name.trim()
        await createFile(p, inlineInput.type === "newFolder")
      }
      // folder-level creation is handled by FileTreeNode
      setInlineInput(null)
      onRefresh()
    },
    [inlineInput, onRefresh],
  )

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteConfirm) return
    await deleteFile(deleteConfirm.path)
    setDeleteConfirm(null)
    onRefresh()
  }, [deleteConfirm, onRefresh])

  const handleContextMenuBlank = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest(".file-tree-node")) return
      e.preventDefault()
      setCtxMenu({ x: e.clientX, y: e.clientY, entry: null })
    },
    [],
  )

  const menuItems: MenuItem[] = []
  if (ctxMenu?.entry) {
    const entry = ctxMenu.entry
    menuItems.push(
      {
        label: "重命名",
        onClick: () => {
          closeContextMenu()
          setInlineInput({ type: "rename", parentPath: entry.path, value: entry.name })
        },
      },
      {
        label: "删除",
        onClick: () => {
          closeContextMenu()
          setDeleteConfirm(entry)
        },
      },
    )
    if (entry.type === "folder") {
      menuItems.push(
        {
          label: "新建文件",
          onClick: () => {
            closeContextMenu()
            setInlineInput({ type: "newFile", parentPath: entry.path })
          },
        },
        {
          label: "新建文件夹",
          onClick: () => {
            closeContextMenu()
            setInlineInput({ type: "newFolder", parentPath: entry.path })
          },
        },
      )
    }
  } else if (ctxMenu) {
    menuItems.push(
      {
        label: "新建文件",
        onClick: () => {
          closeContextMenu()
          setInlineInput({ type: "newFile", parentPath: "" })
        },
      },
      {
        label: "新建文件夹",
        onClick: () => {
          closeContextMenu()
          setInlineInput({ type: "newFolder", parentPath: "" })
        },
      },
    )
  }

  const handleDragStart = useCallback((e: React.DragEvent, entry: FileEntry) => {
    e.dataTransfer.setData("text/plain", entry.path)
    e.dataTransfer.effectAllowed = "move"
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, _entry: FileEntry) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent, entry: FileEntry) => {
      e.preventDefault()
      const src = e.dataTransfer.getData("text/plain")
      if (!src || entry.type !== "folder") return
      await moveFile(src, entry.path)
      onRefresh()
    },
    [onRefresh],
  )

  return (
    <>
      <div className="sidebar-header">资源管理器</div>
      {error && <div className="file-tree-error">{error}</div>}
      <div className="file-tree" onContextMenu={handleContextMenuBlank}>
        <div
          className="file-tree-node"
          style={{ paddingLeft: 8 }}
          onClick={() => setRootExpanded((x) => !x)}
        >
          <span className="arrow">{rootExpanded ? "▾" : "▸"}</span>
          <span className="file-icon">📁</span>
          <span className="node-name" title={rootName}>{rootName}</span>
        </div>
        {rootExpanded && (
          <>
            {inlineInput?.parentPath === "" && (
              <InlineInputRow
                type={inlineInput.type}
                depth={1}
                value={inlineInput.value}
                onSubmit={handleInlineSubmit}
                onCancel={() => setInlineInput(null)}
              />
            )}
            {rootEntries.map((entry) => (
              <FileTreeNode
                key={entry.path}
                entry={entry}
                depth={1}
                selectedPath={selectedPath}
                onSelectFile={onSelectFile}
                onContextMenu={handleContextMenu}
                refreshKey={refreshKey}
                inlineInput={inlineInput}
                onInlineSubmit={handleInlineSubmit}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onRefresh={onRefresh}
              />
            ))}
          </>
        )}
      </div>

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={menuItems}
          onClose={closeContextMenu}
        />
      )}

      {deleteConfirm && (
        <ConfirmDialog
          title={`确定删除 "${deleteConfirm.name}"？`}
          onOk={handleDeleteConfirm}
          onCancel={() => setDeleteConfirm(null)}
        />
      )}
    </>
  )
}

export function InlineInputRow({
  type,
  depth,
  value,
  onSubmit,
  onCancel,
}: {
  type: string
  depth: number
  value?: string
  onSubmit: (name: string) => void
  onCancel: () => void
}) {
  const icon = type === "newFolder" ? "📁" : type === "rename" ? "📄" : "📄"
  const placeholder = type === "newFolder" ? "文件夹名称" : type === "rename" ? "" : "文件名称"

  return (
    <div className="inline-input-row" style={{ paddingLeft: depth * 16 + 8 + 18 }}>
      <span className="file-icon" style={{ width: 18, marginRight: 4, flexShrink: 0 }}>
        {icon}
      </span>
      <input
        autoFocus
        defaultValue={value || ""}
        placeholder={placeholder}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit((e.target as HTMLInputElement).value)
          if (e.key === "Escape") onCancel()
        }}
        onBlur={(e) => onSubmit(e.target.value)}
      />
    </div>
  )
}
