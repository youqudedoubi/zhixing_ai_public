import type { TopicSummary, Topic } from "../types/chat"

const BASE = "/api/topics"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

export async function listTopics(): Promise<TopicSummary[]> {
  return request<TopicSummary[]>(BASE)
}

export async function getTopic(id: string): Promise<Topic> {
  return request<Topic>(`${BASE}/${id}`)
}

export async function createTopic(name?: string): Promise<Topic> {
  return request<Topic>(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name || null }),
  })
}

export async function renameTopic(id: string, newName: string): Promise<Topic> {
  return request<Topic>(`${BASE}/${id}/rename`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_name: newName }),
  })
}

export async function deleteTopic(id: string): Promise<void> {
  await request<{ ok: boolean }>(`${BASE}/${id}`, { method: "DELETE" })
}

export async function branchTopic(id: string, fromMessageIndex: number): Promise<Topic> {
  return request<Topic>(`${BASE}/${id}/branch?from_message_index=${fromMessageIndex}`, {
    method: "POST",
  })
}

export async function rollbackConversation(id: string, messageIndex: number): Promise<Topic> {
  return request<Topic>(`${BASE}/${id}/rollback_conversation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_index: messageIndex }),
  })
}

export async function rollbackFiles(id: string, messageIndex: number): Promise<void> {
  await request<{ ok: boolean }>(`${BASE}/${id}/rollback_files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_index: messageIndex }),
  })
}

export async function rollbackConversationAndFiles(id: string, messageIndex: number): Promise<Topic> {
  return request<Topic>(`${BASE}/${id}/rollback_conversation_and_files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_index: messageIndex }),
  })
}
