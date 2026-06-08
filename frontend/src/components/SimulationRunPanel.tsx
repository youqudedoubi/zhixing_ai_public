import { useState, useEffect, useCallback, useRef } from "react"
import type { SimulationSession, SimSSEEvent, SimulationNode } from "../types/simulation"
import {
  listConfigs,
  listSessions,
  createSession,
  renameSession,
  deleteSession,
  runSimulation,
  getResult,
} from "../api/simulation"

interface Props {
  onOpenFile: (path: string) => void
  onOpenSimulation: (resultId: string, nodes: SimulationNode | null, name: string, maxBranches: number, maxSteps: number) => void
}

export default function SimulationRunPanel({ onOpenFile, onOpenSimulation }: Props) {
  const [configs, setConfigs] = useState<string[]>([])
  const [sessions, setSessions] = useState<SimulationSession[]>([])
  const [currentSession, setCurrentSession] = useState<SimulationSession | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [nameVal, setNameVal] = useState("")
  const [editingHistoryId, setEditingHistoryId] = useState<string | null>(null)
  const [historyNameVal, setHistoryNameVal] = useState("")

  const [selectedConfig, setSelectedConfig] = useState("")
  const [situation, setSituation] = useState("")
  const [maxBranches, setMaxBranches] = useState(2)
  const [maxSteps, setMaxSteps] = useState(3)
  const [alpha, setAlpha] = useState(0.6)

  const [running, setRunning] = useState(false)
  const [runningSessionId, setRunningSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState("")
  const [doneResultId, setDoneResultId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const [, setLiveNodes] = useState<Map<string, SimulationNode>>(new Map())
  const [, setRootNode] = useState<SimulationNode | null>(null)

  useEffect(() => {
    listConfigs().then((list) => {
      setConfigs(list)
      if (list.length > 0) setSelectedConfig(list[0])
    }).catch(() => {})

    listSessions().then((list) => {
      setSessions(list)
      if (list.length > 0) {
        const latest = list[list.length - 1]
        setCurrentSession(latest)
        setDoneResultId(latest.result_id ?? null)
      } else {
        const name = `模拟 ${new Date().toLocaleDateString("zh-CN")}`
        createSession(name).then((session) => {
          setSessions([session])
          setCurrentSession(session)
        }).catch(() => {})
      }
    }).catch(() => {})

    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const handleNewSession = useCallback(async () => {
    abortRef.current?.abort()
    const name = `模拟 ${new Date().toLocaleDateString("zh-CN")}`
    const session = await createSession(name)
    setSessions((prev) => [...prev, session])
    setCurrentSession(session)
    setDoneResultId(null)
    setLiveNodes(new Map())
    setRootNode(null)
    setStatus("")
  }, [])

  const handleRenameSession = useCallback(async () => {
    if (!currentSession || !nameVal.trim()) return
    const updated = await renameSession(currentSession.id, nameVal.trim())
    setCurrentSession(updated)
    setSessions((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
    setEditingName(false)
  }, [currentSession, nameVal])

  const handleHistoryRename = useCallback(async (sessionId: string) => {
    if (!historyNameVal.trim()) { setEditingHistoryId(null); return }
    const updated = await renameSession(sessionId, historyNameVal.trim())
    setSessions((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
    if (currentSession?.id === sessionId) setCurrentSession(updated)
    setEditingHistoryId(null)
  }, [historyNameVal, currentSession])

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    await deleteSession(sessionId)
    setSessions((prev) => prev.filter((s) => s.id !== sessionId))
    if (currentSession?.id === sessionId) {
      setCurrentSession(null)
      setDoneResultId(null)
    }
  }, [currentSession])

  const handleSelectSession = useCallback(async (session: SimulationSession) => {
    abortRef.current?.abort()
    setCurrentSession(session)
    setShowHistory(false)
    setDoneResultId(session.result_id ?? null)
    setStatus("")
    if (session.result_id) {
      try {
        const result = await getResult(session.result_id)
        onOpenSimulation(session.result_id, result.root, result.name, result.max_branches, result.max_steps)
      } catch { /* ignore */ }
    }
  }, [onOpenSimulation])

  const handleRun = useCallback(async () => {
    if (!currentSession || !situation.trim() || !selectedConfig || running) return
    setRunning(true)
    setRunningSessionId(currentSession.id)
    setDoneResultId(null)
    setStatus("启动模拟...")
    setLiveNodes(new Map())
    setRootNode(null)
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    const root: SimulationNode = { id: "1", pattern_name: "", phase: "", content: situation, parent_id: null, children: [] }
    setRootNode(root)
    const nodesMap = new Map<string, SimulationNode>([["1", root]])
    const tabName = currentSession.name
    onOpenSimulation(`sim-live-${currentSession.id}`, root, tabName, maxBranches, maxSteps)
    try {
      await runSimulation(
        { session_id: currentSession.id, config_name: selectedConfig, situation: situation.trim(), max_branches: maxBranches, max_steps: maxSteps, alpha },
        (e: SimSSEEvent) => {
          if (e.type === "sim_status") {
            setStatus(e.message)
          } else if (e.type === "node_start") {
            const newNode: SimulationNode = { id: e.node_id, pattern_name: e.pattern_name, phase: e.phase, content: "生成中...", parent_id: e.parent_id, children: [] }
            nodesMap.set(e.node_id, newNode)
            const parent = nodesMap.get(e.parent_id)
            if (parent) parent.children = [...parent.children, newNode]
            setLiveNodes(new Map(nodesMap))
            onOpenSimulation(`sim-live-${currentSession.id}`, JSON.parse(JSON.stringify(root)) as SimulationNode, tabName, maxBranches, maxSteps)
          } else if (e.type === "node_done") {
            const node = nodesMap.get(e.node_id)
            if (node) {
              node.content = e.content
              setLiveNodes(new Map(nodesMap))
              onOpenSimulation(`sim-live-${currentSession.id}`, JSON.parse(JSON.stringify(root)) as SimulationNode, tabName, maxBranches, maxSteps)
            }
          } else if (e.type === "simulation_done") {
            setDoneResultId(e.result_id)
            setStatus("模拟完成")
            setSessions((prev) => prev.map((s) => s.id === currentSession.id ? { ...s, result_id: e.result_id } : s))
            setCurrentSession((prev) => prev ? { ...prev, result_id: e.result_id } : prev)
            onOpenSimulation(`sim-live-${currentSession.id}`, JSON.parse(JSON.stringify(root)) as SimulationNode, tabName, maxBranches, maxSteps)
          } else if (e.type === "error") {
            setStatus(`错误: ${e.message}`)
          }
        },
        abortRef.current.signal,
      )
    } catch { /* ignore */ } finally {
      setRunning(false)
      setRunningSessionId(null)
    }
  }, [currentSession, situation, selectedConfig, maxBranches, maxSteps, alpha, running, onOpenSimulation])

  const handleViewResult = useCallback(async () => {
    if (!doneResultId) return
    try {
      const result = await getResult(doneResultId)
      onOpenFile(`simulation/simulation_result/${doneResultId}.json`)
      onOpenSimulation(doneResultId, result.root, result.name, result.max_branches, result.max_steps)
    } catch { /* ignore */ }
  }, [doneResultId, onOpenSimulation, onOpenFile])

  return (
    <div className="sim-run-panel">
      <div className="sim-run-header">
        {editingName && currentSession ? (
          <input className="sim-name-input" value={nameVal} onChange={(e) => setNameVal(e.target.value)}
            onBlur={handleRenameSession} onKeyDown={(e) => e.key === "Enter" && handleRenameSession()} autoFocus />
        ) : (
          <span className="sim-session-name" onDoubleClick={() => { if (currentSession) { setNameVal(currentSession.name); setEditingName(true) } }}>
            {currentSession?.name ?? "未选择模拟"}
          </span>
        )}
        <div className="sim-header-btns">
          <button className="sim-icon-btn" onClick={handleNewSession} title="新建模拟">+</button>
          <button className="sim-icon-btn" onClick={() => setShowHistory((v) => !v)} title="历史模拟">🕐</button>
        </div>
      </div>

      {showHistory && (
        <div className="sim-history">
          {sessions.length === 0 && <div className="sim-empty">暂无历史模拟</div>}
          {[...sessions].reverse().map((s) => (
            <div key={s.id} className={`sim-history-item ${currentSession?.id === s.id ? "active" : ""}`}>
              {editingHistoryId === s.id ? (
                <input className="sim-history-name-input" value={historyNameVal}
                  onChange={(e) => setHistoryNameVal(e.target.value)}
                  onBlur={() => handleHistoryRename(s.id)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleHistoryRename(s.id); if (e.key === "Escape") setEditingHistoryId(null) }}
                  autoFocus onClick={(e) => e.stopPropagation()} />
              ) : (
                <span className="sim-history-name" onClick={() => handleSelectSession(s)} title={s.result_id ? "点击查看结果" : "点击选择"}>
                  {runningSessionId === s.id && <span className="sim-running-icon">⟳</span>}
                  {s.name}
                </span>
              )}
              <div className="sim-history-actions">
                <button className="sim-icon-btn" title="重命名"
                  onClick={(e) => { e.stopPropagation(); setHistoryNameVal(s.name); setEditingHistoryId(s.id) }}>✎</button>
                <button className="sim-icon-btn" title="删除记录"
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id) }}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!showHistory && (
        <div className="sim-params">
          <div className="sim-field">
            <label>配置</label>
            <select value={selectedConfig} onChange={(e) => setSelectedConfig(e.target.value)} className="sim-select">
              {configs.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="sim-field">
            <label>情境</label>
            <textarea className="sim-textarea" value={situation} onChange={(e) => setSituation(e.target.value)} placeholder="描述当前情境..." rows={3} />
          </div>
          <div className="sim-field-row">
            <div className="sim-field">
              <label>最大分支数</label>
              <input type="number" className="sim-number-input" value={maxBranches} min={1} max={5} onChange={(e) => setMaxBranches(Number(e.target.value))} />
            </div>
            <div className="sim-field">
              <label>最大步数</label>
              <input type="number" className="sim-number-input" value={maxSteps} min={1} max={10} onChange={(e) => setMaxSteps(Number(e.target.value))} />
            </div>
          </div>
          <div className="sim-field">
            <label>情境匹配度权重 α = {alpha.toFixed(2)}</label>
            <input type="range" min={0} max={1} step={0.05} value={alpha} onChange={(e) => setAlpha(Number(e.target.value))} className="sim-slider" />
            <div className="sim-alpha-hint">
              <span>情境匹配度 {(alpha * 100).toFixed(0)}%</span>
              <span>存在程度 {((1 - alpha) * 100).toFixed(0)}%</span>
            </div>
          </div>
          {status && <div className={`sim-status ${status === "模拟完成" ? "sim-status-done" : ""}`}>{status}</div>}
          <div className="sim-run-btns">
            {doneResultId ? (
              <button className="sim-btn sim-btn-primary" onClick={handleViewResult}>查看模拟结果</button>
            ) : (
              <button className={`sim-btn sim-btn-primary ${running ? "sim-btn-running" : ""}`} onClick={handleRun}
                disabled={running || !currentSession || !situation.trim() || !selectedConfig}>
                {running ? <><span className="sim-spinner" />模拟中...</> : "开始模拟"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

