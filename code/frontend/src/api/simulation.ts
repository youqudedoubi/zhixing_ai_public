import type { PatternItem, SimulationResult, SimulationSession, SimSSEEvent } from "../types/simulation"

const BASE = "/api/simulation"

export async function listConfigs(): Promise<string[]> {
  const res = await fetch(`${BASE}/configs`)
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.configs
}

export async function updateDefaultConfig(
  onEvent: (e: SimSSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/configs/default/update`, { method: "POST", signal })
  if (!res.ok) throw new Error(await res.text())
  await consumeSSE(res, onEvent)
}

export async function renameConfig(oldName: string, newName: string): Promise<string> {
  const res = await fetch(`${BASE}/configs/${encodeURIComponent(oldName)}/rename`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_name: newName }),
  })
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.config_name
}

export async function createConfig(): Promise<string> {
  const res = await fetch(`${BASE}/configs`, { method: "POST" })
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.config_name
}

export async function listPatterns(configName: string): Promise<PatternItem[]> {
  const res = await fetch(`${BASE}/configs/${encodeURIComponent(configName)}/patterns`)
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.patterns
}

export async function updatePatternIntensity(
  configName: string,
  relPath: string,
  intensity: number,
): Promise<void> {
  const res = await fetch(`${BASE}/configs/${encodeURIComponent(configName)}/patterns/intensity`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rel_path: relPath, intensity }),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function runSimulation(
  params: {
    session_id: string
    config_name: string
    situation: string
    max_branches: number
    max_steps: number
    alpha: number
  },
  onEvent: (e: SimSSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  })
  if (!res.ok) throw new Error(await res.text())
  await consumeSSE(res, onEvent)
}

export async function listSessions(): Promise<SimulationSession[]> {
  const res = await fetch(`${BASE}/sessions`)
  if (!res.ok) throw new Error(await res.text())
  const data = await res.json()
  return data.sessions
}

export async function createSession(name: string): Promise<SimulationSession> {
  const res = await fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function renameSession(sessionId: string, name: string): Promise<SimulationSession> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/rename`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(await res.text())
}

export async function getResult(resultId: string): Promise<SimulationResult> {
  const res = await fetch(`${BASE}/results/${resultId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

async function consumeSSE(res: Response, onEvent: (e: SimSSEEvent) => void): Promise<void> {
  const reader = res.body?.getReader()
  if (!reader) return
  const decoder = new TextDecoder()
  let buf = ""
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split("\n")
    buf = lines.pop() ?? ""
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as SimSSEEvent
          onEvent(event)
        } catch { /* ignore */ }
      }
    }
  }
}
