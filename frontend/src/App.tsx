import { useState, useCallback } from "react"
import { Allotment } from "allotment"
import "allotment/dist/style.css"
import ActivityBar from "./components/ActivityBar"
import Sidebar from "./components/Sidebar"
import FileTree from "./components/FileTree"
import ContentArea from "./components/ContentArea"
import ChatPanel from "./components/ChatPanel"
import SimulationSidebar from "./components/SimulationSidebar"
import type { ResearchMessage } from "./components/ResearchPanel"
import type { SimulationNode } from "./types/simulation"

interface DiffInfo {
  filePath: string
  oldContent: string
  newContent: string
}

interface ResearchTabState {
  tabId: string
  topic: string
  messages: ResearchMessage[]
  done: boolean
}

interface SimulationTabState {
  tabId: string
  resultId: string
  root: SimulationNode | null
  name: string
  maxBranches: number
  maxSteps: number
}

export default function App() {
  const [activeActivity, setActiveActivity] = useState("explorer")
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [diffInfo, setDiffInfo] = useState<DiffInfo | null>(null)
  const [researchTab, setResearchTab] = useState<ResearchTabState | null>(null)
  const [simulationTab, setSimulationTab] = useState<SimulationTabState | null>(null)

  const handleSelectActivity = useCallback((id: string) => {
    setActiveActivity((prev) => (prev === id ? "" : id))
  }, [])

  const handleSelectFile = useCallback((path: string) => {
    setSelectedPath(path)
    setActiveFilePath(path)
    setDiffInfo(null)
  }, [])

  const handleRefresh = useCallback(() => {
    setRefreshKey((k) => k + 1)
  }, [])

  const handleDiffView = useCallback(
    (filePath: string, oldContent: string, newContent: string) => {
      setDiffInfo({ filePath, oldContent, newContent })
    },
    [],
  )

  const handleFileChanged = useCallback(() => {
    setRefreshKey((k) => k + 1)
  }, [])

  const handleResearchUpdate = useCallback(
    (tabId: string, topic: string, messages: ResearchMessage[], done: boolean) => {
      setResearchTab({ tabId, topic, messages, done })
    },
    [],
  )

  const handleOpenSimulation = useCallback(
    (resultId: string, root: SimulationNode | null, name: string, maxBranches: number, maxSteps: number) => {
      const tabId = `simulation:${resultId}`
      setSimulationTab({ tabId, resultId, root, name, maxBranches, maxSteps })
      setActiveFilePath(tabId)
    },
    [],
  )

  return (
    <div className="app-shell">
      <Allotment>
        {/* Activity Bar */}
        <Allotment.Pane preferredSize={48} maxSize={48} minSize={48}>
          <ActivityBar active={activeActivity} onSelect={handleSelectActivity} />
        </Allotment.Pane>

        {/* Sidebar */}
        {activeActivity && (
          <Allotment.Pane preferredSize={260} minSize={160} maxSize={500}>
            <Sidebar activeActivity={activeActivity}>
              {/* Both panels stay mounted to preserve internal state (e.g. file
                  tree expanded nodes) across activity switches. CSS display
                  toggling avoids the re-mount / re-fetch cycle. */}
              <div style={{ display: activeActivity === "explorer" ? "block" : "none" }}>
                <FileTree
                  refreshKey={refreshKey}
                  selectedPath={selectedPath}
                  onSelectFile={handleSelectFile}
                  onRefresh={handleRefresh}
                />
              </div>
              <div style={{ display: activeActivity === "simulation" ? "block" : "none" }}>
                <SimulationSidebar
                  onOpenFile={handleSelectFile}
                  onOpenSimulation={handleOpenSimulation}
                />
              </div>
            </Sidebar>
          </Allotment.Pane>
        )}

        {/* Content Area */}
        <Allotment.Pane>
          <ContentArea
            activePath={activeFilePath}
            onActivePathChange={setActiveFilePath}
            diffInfo={diffInfo}
            onCloseDiff={() => setDiffInfo(null)}
            fileTreeVersion={refreshKey}
            researchTabId={researchTab?.tabId ?? null}
            researchTopic={researchTab?.topic}
            researchMessages={researchTab?.messages}
            researchDone={researchTab?.done}
            simulationTabId={simulationTab?.tabId ?? null}
            simulationRoot={simulationTab?.root ?? null}
            simulationName={simulationTab?.name}
            simulationMaxBranches={simulationTab?.maxBranches ?? 2}
            simulationMaxSteps={simulationTab?.maxSteps ?? 3}
          />
        </Allotment.Pane>

        {/* Chat Panel */}
        <Allotment.Pane preferredSize={360} minSize={200} maxSize={600}>
          <ChatPanel
            onDiffView={handleDiffView}
            onFileChanged={handleFileChanged}
            onResearchUpdate={handleResearchUpdate}
          />
        </Allotment.Pane>
      </Allotment>
    </div>
  )
}
