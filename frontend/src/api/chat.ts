import type { SSEEvent } from "../types/chat"

export async function sendMessage(
  topicId: string,
  content: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`/api/topics/${topicId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal,
  })
  if (!res.ok) {
    throw new Error(await res.text())
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() || ""

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as SSEEvent
          onEvent(event)
          if (event.type === "done" || event.type === "error") {
            await reader.cancel()
            return
          }
        } catch {
          // skip malformed events
        }
      }
    }
  }
}
