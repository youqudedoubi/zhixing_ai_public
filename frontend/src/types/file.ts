export interface FileEntry {
  name: string
  type: "file" | "folder"
  path: string
}

export interface FileNode extends FileEntry {
  children?: FileNode[]
  loaded: boolean
  expanded: boolean
}
