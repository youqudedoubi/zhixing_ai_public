import { useState, useEffect, useCallback, useRef } from "react"
import type { PatternItem } from "../types/simulation"
import {
  listConfigs,
  listPatterns,
  updateDefaultConfig,
  createConfig,
  renameConfig,
  updatePatternIntensity,
} from "../api/simulation"
import type { SimSSEEvent } from "../types/simulation"

interface Props {
  onOpenFile: (path: string) => void
}

const CATEGORIES = ["positive", "neutral", "negative"] as const
const CATEGORY_LABEL: Record<string, string> = {
  positive: "正面",
  negative: "负面",
  neutral: "中性",
}

export default function SimulationConfigPanel({ onOpenFile }: Props) {
  const [configs, setConfigs] = useState<string[]>([])
  const [selectedConfig, setSelectedConfig] = useState<string>("")
  const [patterns, setPatterns] = useState<PatternItem[]>([])
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<string>("")
  const [editingName, setEditingName] = useState(false)
  const [nameVal, setNameVal] = useState("")
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const abortRef = useRef<AbortController | null>(null)

  const loadConfigs = useCallback(async (keepSelected?: string) => {
    try {
      const list = await listConfigs()
      setConfigs(list)
      setSelectedConfig((prev) => {
        const target = keepSelected ?? prev
        return list.includes(target) ? target : (list[0] ?? "")
      })
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadConfigs()
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!selectedConfig) return
    listPatterns(selectedConfig).then(setPatterns).catch(() => setPatterns([]))
  }, [selectedConfig])

  const handleUpdateDefault = useCallback(async () => {
    if (loading) return
    abortRef.current?.abort()
    setLoading(true)
    setProgress("准备更新...")
    abortRef.current = new AbortController()
    try {
      await updateDefaultConfig((e: SimSSEEvent) => {
        if (e.type === "flow_done") setProgress(`${e.current}/${e.total} 已生成 ${e.pattern_name}`)
        else if (e.type === "done") setProgress("更新完成")
        else if (e.type === "error") setProgress(`错误: ${e.message}`)
      }, abortRef.current.signal)
      await loadConfigs(selectedConfig)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [loading, loadConfigs, selectedConfig])

  const handleCreateConfig = useCallback(async () => {
    if (loading) return
    try {
      const newName = await createConfig()
      await loadConfigs(newName)
    } catch (e: unknown) {
      setProgress(`错误: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [loading, loadConfigs])

  const handleRenameCommit = useCallback(async () => {
    const trimmed = nameVal.trim()
    setEditingName(false)
    if (!trimmed || trimmed === selectedConfig) return
    try {
      await renameConfig(selectedConfig, trimmed)
      await loadConfigs(trimmed)
    } catch (e: unknown) {
      setProgress(`重命名失败: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [nameVal, selectedConfig, loadConfigs])

  const handleIntensityChange = useCallback(
    async (pattern: PatternItem, value: number) => {
      setPatterns((prev) =>
        prev.map((p) => (p.rel_path === pattern.rel_path ? { ...p, intensity: value } : p))
      )
      try {
        await updatePatternIntensity(selectedConfig, pattern.rel_path, value)
      } catch { /* ignore */ }
    },
    [selectedConfig],
  )

  const toggleCollapse = (cat: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      next.has(cat) ? next.delete(cat) : next.add(cat)
      return next
    })
  }

  const grouped = patterns.reduce<Record<string, PatternItem[]>>((acc, p) => {
    if (!acc[p.category]) acc[p.category] = []
    acc[p.category].push(p)
    return acc
  }, {})

  return (
    <div className="sim-config-panel">
      <div className="sim-config-toolbar">
        <button className="sim-btn" onClick={handleUpdateDefault} disabled={loading}
          title="从 analysis/pattern/ 同步并重新生成思维流">
          更新默认配置
        </button>
        <button className="sim-btn" onClick={handleCreateConfig} disabled={loading}
          title="复制当前配置新建">
          新建配置
        </button>
      </div>

      {progress && <div className="sim-progress">{progress}</div>}

      {configs.length > 0 && (
        <div className="sim-config-select">
          {editingName ? (
            <input
              className="sim-config-name-input"
              value={nameVal}
              onChange={(e) => setNameVal(e.target.value)}
              onBlur={handleRenameCommit}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRenameCommit()
                if (e.key === "Escape") setEditingName(false)
              }}
              autoFocus
            />
          ) : configs.length > 1 ? (
            <select
              value={selectedConfig}
              onChange={(e) => setSelectedConfig(e.target.value)}
              onDoubleClick={() => { setNameVal(selectedConfig); setEditingName(true) }}
              className="sim-select"
            >
              {configs.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          ) : (
            <span
              className="sim-config-name"
              onDoubleClick={() => { setNameVal(selectedConfig); setEditingName(true) }}
              title="双击重命名"
            >
              {selectedConfig}
            </span>
          )}
        </div>
      )}

      <div className="sim-pattern-list">
        {CATEGORIES.map((cat) => {
          const items = grouped[cat] ?? []
          const isCollapsed = collapsed.has(cat)
          return (
            <div key={cat} className="sim-pattern-category">
              <div
                className="sim-category-label"
                onClick={() => toggleCollapse(cat)}
                style={{ cursor: "pointer", userSelect: "none" }}
              >
                <span className="sim-category-arrow">{isCollapsed ? "▶" : "▼"}</span>
                {CATEGORY_LABEL[cat]}
                <span className="sim-category-count">({items.length})</span>
              </div>
              {!isCollapsed && (
                items.length === 0
                  ? <div className="sim-empty-cat">（暂无）</div>
                  : items.map((p) => (
                    <PatternRow
                      key={p.rel_path}
                      pattern={p}
                      onIntensityChange={(v) => handleIntensityChange(p, v)}
                      onOpen={() => onOpenFile(`simulation/simulation_config/${selectedConfig}/${p.rel_path}`)}
                    />
                  ))
              )}
            </div>
          )
        })}
        {patterns.length === 0 && !loading && configs.length === 0 && (
          <div className="sim-empty">暂无模式，请先更新默认配置</div>
        )}
      </div>
    </div>
  )
}

function PatternRow({
  pattern,
  onIntensityChange,
  onOpen,
}: {
  pattern: PatternItem
  onIntensityChange: (v: number) => void
  onOpen: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [editVal, setEditVal] = useState(String(Math.round(pattern.intensity)))

  const commit = () => {
    const v = Math.max(0, Math.min(100, Number(editVal) || 0))
    onIntensityChange(v)
    setEditing(false)
  }

  return (
    <div className="sim-pattern-row" onClick={onOpen} title={pattern.name}>
      <span className="sim-pattern-name">{pattern.name}</span>
      <div className="sim-intensity-ctrl" onClick={(e) => e.stopPropagation()}>
        <input
          type="range" min={0} max={100}
          value={Math.round(pattern.intensity)}
          onChange={(e) => onIntensityChange(Number(e.target.value))}
          className="sim-slider"
        />
        {editing ? (
          <input
            className="sim-intensity-input"
            value={editVal}
            onChange={(e) => setEditVal(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => e.key === "Enter" && commit()}
            autoFocus
          />
        ) : (
          <span
            className="sim-intensity-num"
            onDoubleClick={() => { setEditVal(String(Math.round(pattern.intensity))); setEditing(true) }}
          >
            {Math.round(pattern.intensity)}
          </span>
        )}
      </div>
    </div>
  )
}
