import { useState, useCallback, useRef, useEffect } from "react"
import TabBar from "./TabBar"
import MarkdownEditor from "./MarkdownEditor"
import DiffView from "./DiffView"
import ResearchPanel, { type ResearchMessage } from "./ResearchPanel"
import ResearchProcessView from "./ResearchProcessView"
import LogChart from "./LogChart"
import SimulationTreeView from "./SimulationTreeView"
import { readFile, saveFile } from "../api/files"
import type { SimulationNode } from "../types/simulation"

interface TabInfo {
  path: string
  name: string
  dirty: boolean
  content: string
  // research tab fields
  tabType?: "file" | "research" | "log-chart" | "simulation" | "diff"
  researchTopic?: string
  researchMessages?: ResearchMessage[]
  researchDone?: boolean
  // log-chart tab fields
  logContent?: string
  logPatternName?: string
  // simulation tab fields
  simulationRoot?: SimulationNode | null
  simulationName?: string
  simulationMaxBranches?: number
  simulationMaxSteps?: number
  // diff tab fields
  diffFilePath?: string
  diffOldContent?: string
  diffNewContent?: string
}

interface DiffInfo {
  filePath: string
  oldContent: string
  newContent: string
}

interface Props {
  activePath: string | null
  onActivePathChange: (path: string | null) => void
  diffInfo: DiffInfo | null
  onCloseDiff: () => void
  fileTreeVersion: number
  // research tab control
  researchTabId?: string | null
  researchTopic?: string
  researchMessages?: ResearchMessage[]
  researchDone?: boolean
  // simulation tab control
  simulationTabId?: string | null
  simulationRoot?: SimulationNode | null
  simulationName?: string
  simulationMaxBranches?: number
  simulationMaxSteps?: number
}

export default function ContentArea({ activePath, onActivePathChange, diffInfo, onCloseDiff, fileTreeVersion, researchTabId, researchTopic, researchMessages, researchDone, simulationTabId, simulationRoot, simulationName, simulationMaxBranches, simulationMaxSteps }: Props) {
  const [tabs, setTabs] = useState<TabInfo[]>([])
  const [tabContents, setTabContents] = useState<Map<string, string>>(new Map())
  const [error, setError] = useState<string | null>(null)
  const [showProcessPreview, setShowProcessPreview] = useState(false)
  const tabContentsRef = useRef(tabContents)
  tabContentsRef.current = tabContents
  const tabsRef = useRef(tabs)
  tabsRef.current = tabs
  // Track the last research tab we switched to, so we only auto-switch when a
  // genuinely new research task starts, not on every streaming message update.
  const lastSwitchedResearchTabRef = useRef<string | null>(null)

  // Sync research tab when props change
  useEffect(() => {
    if (!researchTabId || !researchTopic) return
    const isNewResearch = researchTabId !== lastSwitchedResearchTabRef.current
    if (isNewResearch) {
      lastSwitchedResearchTabRef.current = researchTabId
    }
    setTabs((prev) => {
      const existing = prev.find((t) => t.path === researchTabId)
      if (!existing) {
        return [...prev, {
          path: researchTabId,
          name: `研究: ${researchTopic}`,
          dirty: false,
          content: "",
          tabType: "research",
          researchTopic,
          researchMessages: researchMessages ?? [],
          researchDone: researchDone ?? false,
        }]
      }
      return prev.map((t) =>
        t.path === researchTabId
          ? { ...t, researchMessages: researchMessages ?? t.researchMessages, researchDone: researchDone ?? t.researchDone }
          : t
      )
    })
    // Only auto-switch to the research tab when a new research task is created,
    // not on every streaming message update. The user is free to browse other
    // tabs while research runs in the background.
    if (isNewResearch) {
      onActivePathChange(researchTabId)
    }
  }, [researchTabId, researchTopic, researchMessages, researchDone])

  // Sync simulation tab when props change
  useEffect(() => {
    if (!simulationTabId) return
    setTabs((prev) => {
      const existing = prev.find((t) => t.path === simulationTabId)
      if (!existing) {
        return [...prev, {
          path: simulationTabId,
          name: `模拟: ${simulationName ?? "结果"}`,
          dirty: false,
          content: "",
          tabType: "simulation",
          simulationRoot: simulationRoot ?? null,
          simulationName,
          simulationMaxBranches: simulationMaxBranches ?? 2,
          simulationMaxSteps: simulationMaxSteps ?? 3,
        }]
      }
      return prev.map((t) =>
        t.path === simulationTabId
          ? { ...t, simulationRoot: simulationRoot ?? t.simulationRoot, simulationName: simulationName ?? t.simulationName, simulationMaxBranches: simulationMaxBranches ?? t.simulationMaxBranches, simulationMaxSteps: simulationMaxSteps ?? t.simulationMaxSteps }
          : t
      )
    })
    onActivePathChange(simulationTabId)
  }, [simulationTabId, simulationRoot, simulationName, simulationMaxBranches, simulationMaxSteps])

  // Sync diff view as a tab when diffInfo changes
  useEffect(() => {
    if (!diffInfo) return
    const tabPath = `diff:${diffInfo.filePath}`
    setTabs((prev) => {
      const existing = prev.find((t) => t.path === tabPath)
      if (existing) {
        // Update existing diff tab with new content
        return prev.map((t) =>
          t.path === tabPath
            ? { ...t, diffOldContent: diffInfo.oldContent, diffNewContent: diffInfo.newContent }
            : t,
        )
      }
      return [...prev, {
        path: tabPath,
        name: `diff: ${diffInfo.filePath.split("/").pop() || diffInfo.filePath}`,
        dirty: false,
        content: "",
        tabType: "diff",
        diffFilePath: diffInfo.filePath,
        diffOldContent: diffInfo.oldContent,
        diffNewContent: diffInfo.newContent,
      }]
    })
    onActivePathChange(tabPath)
  }, [diffInfo])

  const openFile = useCallback(
    async (path: string) => {
      const existing = tabs.find((t) => t.path === path)
      if (existing) {
        onActivePathChange(path)
        return
      }
      try {
        const data = await readFile(path)
        const content = data.content
        setError(null)
        setTabs((prev) => [
          ...prev,
          { path, name: path.split("/").pop() || path, dirty: false, content },
        ])
        setTabContents((prev) => {
          const next = new Map(prev)
          next.set(path, content)
          tabContentsRef.current = next
          return next
        })
        onActivePathChange(path)
      } catch {
        setError(`无法读取文件: ${path}`)
      }
    },
    [tabs, onActivePathChange],
  )

  // Re-validate open file tabs when file tree is refreshed (e.g. after AI modification or rollback).
  // Clean tabs are updated from disk. Dirty tabs are protected — the user's unsaved edits are
  // not overwritten — but a warning is shown if the disk version has diverged.
  useEffect(() => {
    if (fileTreeVersion === 0) return
    const fileTabs = tabsRef.current.filter((t) => !t.tabType || t.tabType === "file")
    fileTabs.forEach(async (tab) => {
      try {
        const data = await readFile(tab.path)
        if (tab.dirty) {
          // Tab has unsaved changes. Check whether the file on disk was modified
          // externally while the user was editing.
          const editorContent = tabContentsRef.current.get(tab.path)
          if (editorContent !== undefined && editorContent !== data.content) {
            setError(`文件 "${tab.path}" 在外部被修改。你的未保存编辑已保留，但保存后将覆盖外部修改的内容。`)
          }
        } else {
          setTabContents((prev) => {
            const next = new Map(prev)
            next.set(tab.path, data.content)
            return next
          })
          // Update the original content baseline (so dirty detection stays accurate)
          setTabs((prev) =>
            prev.map((t) =>
              t.path === tab.path ? { ...t, content: data.content } : t,
            ),
          )
        }
      } catch {
        // File no longer exists — keep the old content visible so the user can
        // still read/copy it (the file may have been renamed rather than deleted).
        // Update only the tab name to signal the stale state.
        setTabs((prev) =>
          prev.map((t) =>
            t.path === tab.path
              ? { ...t, name: `${t.name} (已移除)`, dirty: false }
              : t,
          ),
        )
        setError(`文件不存在: ${tab.path}`)
      }
    })
  }, [fileTreeVersion])

  useEffect(() => {
    if (activePath && !tabs.some((t) => t.path === activePath)) {
      // Don't try to open special tabs as files
      if (!activePath.startsWith("simulation:") && !activePath.startsWith("research:") && !activePath.startsWith("diff:")) {
        openFile(activePath)
      }
    }
  }, [activePath])

  const handleContentChange = useCallback(
    (path: string, value: string) => {
      setTabContents((prev) => {
        const next = new Map(prev)
        next.set(path, value)
        return next
      })
      setTabs((prev) =>
        prev.map((t) => {
          if (t.path !== path) return t
          return { ...t, dirty: value !== t.content }
        }),
      )
    },
    [],
  )

  const saveFnRef = useRef<(path: string) => Promise<void>>(
    async () => {}
  )

  const handleSave = useCallback(
    async (path: string) => {
      const content = tabContentsRef.current.get(path)
      if (content === undefined) return
      try {
        await saveFile(path, content)
        setError(null)
        setTabs((prev) =>
          prev.map((t) => (t.path === path ? { ...t, dirty: false, content } : t)),
        )
      } catch {
        setError(`保存失败: ${path}`)
      }
    },
    [],
  )
  saveFnRef.current = handleSave

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        // Only save regular file tabs (not research / simulation / log-chart)
        const activeTab = tabsRef.current.find((t) => t.path === activePath)
        if (activeTab?.tabType && activeTab.tabType !== "file") return
        // Don't intercept Ctrl+S when focus is in chat input or other panels
        const target = e.target as HTMLElement | null
        if (target?.closest(".chat-panel")) return
        e.preventDefault()
        if (activePath) saveFnRef.current(activePath)
      }
    },
    [activePath],
  )

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  const handleCloseTab = useCallback(
    (path: string) => {
      const closingTab = tabs.find((t) => t.path === path)
      setTabs((prev) => prev.filter((t) => t.path !== path))
      setTabContents((prev) => {
        const next = new Map(prev)
        next.delete(path)
        return next
      })
      if (closingTab?.tabType === "diff") {
        onCloseDiff()
      }
      if (activePath === path) {
        const idx = tabs.findIndex((t) => t.path === path)
        const remaining = tabs.filter((t) => t.path !== path)
        if (remaining.length > 0) {
          const nextIdx = Math.min(idx, remaining.length - 1)
          onActivePathChange(remaining[nextIdx].path)
        } else {
          onActivePathChange(null)
        }
      }
    },
    [activePath, tabs, onActivePathChange, onCloseDiff],
  )

  const handleSelectTab = useCallback(
    (path: string) => {
      setShowProcessPreview(false)
      onActivePathChange(path)
    },
    [onActivePathChange],
  )

  // Detect if active file is a log.md
  const isLogMd = activePath?.endsWith("/log.md") || activePath === "log.md"

  // Detect if active file is a simulation result JSON
  const isSimResultJson = !!activePath && /simulation_result\/[^/]+\.json$/.test(activePath.replace(/\\/g, "/"))
  const simResultContent = isSimResultJson ? (tabContents.get(activePath!) ?? "") : ""
  let simResultData: { root: SimulationNode | null; max_branches: number; max_steps: number; name?: string } | null = null
  if (isSimResultJson && simResultContent) {
    try {
      const parsed = JSON.parse(simResultContent)
      simResultData = { root: parsed.root ?? null, max_branches: parsed.max_branches ?? 2, max_steps: parsed.max_steps ?? 3, name: parsed.name }
    } catch { /* ignore */ }
  }

  const handleOpenSimResultPreview = useCallback(() => {
    if (!activePath || !simResultData) return
    const previewTabId = `simulation:preview:${activePath}`
    const existing = tabs.find((t) => t.path === previewTabId)
    if (existing) { onActivePathChange(previewTabId); return }
    const fileName = activePath.replace(/\\/g, "/").split("/").pop()?.replace(".json", "") ?? "结果"
    setTabs((prev) => [...prev, {
      path: previewTabId,
      name: `模拟: ${simResultData!.name ?? fileName}`,
      dirty: false, content: "",
      tabType: "simulation",
      simulationRoot: simResultData!.root,
      simulationName: simResultData!.name ?? fileName,
      simulationMaxBranches: simResultData!.max_branches,
      simulationMaxSteps: simResultData!.max_steps,
    }])
    onActivePathChange(previewTabId)
  }, [activePath, simResultData, tabs, onActivePathChange])

  const handleOpenLogChart = useCallback(() => {
    if (!activePath) return
    const chartTabId = `log-chart:${activePath}`
    const existing = tabs.find((t) => t.path === chartTabId)
    if (existing) {
      onActivePathChange(chartTabId)
      return
    }
    // Derive pattern name from path: analysis/pattern/{category}/{slug}/log.md
    const parts = activePath.replace(/\\/g, "/").split("/")
    const slugIdx = parts.indexOf("log.md") - 1
    const patternName = slugIdx >= 0 ? parts[slugIdx] : "模式"
    const logContent = tabContents.get(activePath) ?? ""
    setTabs((prev) => [
      ...prev,
      {
        path: chartTabId,
        name: `📈 ${patternName}`,
        dirty: false,
        content: "",
        tabType: "log-chart",
        logContent,
        logPatternName: patternName,
      },
    ])
    onActivePathChange(chartTabId)
  }, [activePath, tabs, tabContents, onActivePathChange])

  const activeTab = tabs.find((t) => t.path === activePath)

  // Determine if active tab is a research_process.json for preview
  const isProcessJson = activePath?.endsWith("research_process.json") ?? false
  const processJsonContent = isProcessJson ? (tabContents.get(activePath!) ?? "") : ""
  let processEntries: unknown[] = []
  if (isProcessJson && processJsonContent) {
    try { processEntries = JSON.parse(processJsonContent) } catch { /* ignore */ }
  }

  const renderActiveContent = () => {
    if (!activePath || !activeTab) {
      return <div className="editor-empty">打开文件以开始编辑</div>
    }
    // Research live tab
    if (activeTab.tabType === "research") {
      return (
        <ResearchPanel
          topic={activeTab.researchTopic ?? ""}
          messages={activeTab.researchMessages ?? []}
          done={activeTab.researchDone ?? false}
        />
      )
    }
    // Simulation tree tab
    if (activeTab.tabType === "simulation") {
      return (
        <SimulationTreeView
          root={activeTab.simulationRoot ?? null}
          title={activeTab.simulationName}
          maxBranches={activeTab.simulationMaxBranches ?? 2}
          maxSteps={activeTab.simulationMaxSteps ?? 3}
        />
      )
    }
    // Log chart tab
    if (activeTab.tabType === "log-chart") {
      return (
        <LogChart
          content={activeTab.logContent ?? ""}
          patternName={activeTab.logPatternName ?? "模式"}
        />
      )
    }
    // Diff tab
    if (activeTab.tabType === "diff") {
      return (
        <DiffView
          filePath={activeTab.diffFilePath ?? ""}
          oldContent={activeTab.diffOldContent ?? ""}
          newContent={activeTab.diffNewContent ?? ""}
        />
      )
    }
    // research_process.json preview
    if (isProcessJson && showProcessPreview && processEntries.length > 0) {
      return <ResearchProcessView entries={processEntries as Parameters<typeof ResearchProcessView>[0]["entries"]} />
    }
    return (
      <MarkdownEditor
        key={activePath}
        path={activePath}
        content={tabContents.get(activePath) || ""}
        onChange={(v) => handleContentChange(activePath, v)}
        onSave={() => saveFnRef.current(activePath)}
      />
    )
  }

  return (
    <div className="content-area">
      {error && <div className="content-error">{error}</div>}
      <TabBar
        tabs={tabs.map((t) => ({ path: t.path, name: t.name, dirty: t.dirty }))}
        activePath={activePath}
        onSelectTab={handleSelectTab}
        onCloseTab={handleCloseTab}
      />
      {isLogMd && (
        <div className="content-toolbar">
          <button className="content-toolbar-btn" onClick={handleOpenLogChart}>
            📈 预览强度变化
          </button>
        </div>
      )}
      {isSimResultJson && simResultData?.root && (
        <div className="content-toolbar">
          <button className="content-toolbar-btn" onClick={handleOpenSimResultPreview}>
            🌳 预览树状图
          </button>
        </div>
      )}
      {isProcessJson && (
        <div className="content-toolbar">
          <button
            className="content-toolbar-btn"
            onClick={() => setShowProcessPreview((v) => !v)}
          >
            {showProcessPreview ? "📄 查看原始 JSON" : "▶ 预览回放"}
          </button>
        </div>
      )}
      {renderActiveContent()}
    </div>
  )
}
