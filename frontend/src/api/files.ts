import type { FileEntry } from "../types/file"

const BASE = "/api/files"

export async function getRoot(): Promise<{ name: string; path: string }> {
  const res = await fetch(`${BASE}/root`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function listDir(path: string = ""): Promise<FileEntry[]> {
  const res = await fetch(`${BASE}/list?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function readFile(path: string): Promise<{ content: string }> {
  const res = await fetch(`${BASE}/read?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createFile(path: string, isFolder: boolean): Promise<FileEntry> {
  const res = await fetch(`${BASE}/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, is_folder: isFolder }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function saveFile(path: string, content: string): Promise<void> {
  const res = await fetch(`${BASE}/save`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function renameFile(oldPath: string, newName: string): Promise<FileEntry> {
  const res = await fetch(`${BASE}/rename`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: oldPath, new_name: newName }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteFile(path: string): Promise<void> {
  const res = await fetch(`${BASE}/delete`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function moveFile(src: string, dstFolder: string): Promise<void> {
  const res = await fetch(`${BASE}/move`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ src, dst_folder: dstFolder }),
  })
  if (!res.ok) throw new Error(await res.text())
}
