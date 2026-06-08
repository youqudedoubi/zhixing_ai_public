import { useState } from "react"
import SimulationConfigPanel from "./SimulationConfigPanel"
import SimulationRunPanel from "./SimulationRunPanel"
import type { SimulationNode } from "../types/simulation"

interface Props {
  onOpenFile: (path: string) => void
  onOpenSimulation: (resultId: string, nodes: SimulationNode | null, name: string, maxBranches: number, maxSteps: number) => void
}

export default function SimulationSidebar({ onOpenFile, onOpenSimulation }: Props) {
  const [tab, setTab] = useState<"config" | "run">("config")

  return (
    <div className="sim-sidebar">
      <div className="sim-tabs">
        <button
          className={`sim-tab ${tab === "config" ? "active" : ""}`}
          onClick={() => setTab("config")}
        >
          模拟配置
        </button>
        <button
          className={`sim-tab ${tab === "run" ? "active" : ""}`}
          onClick={() => setTab("run")}
        >
          情境模拟
        </button>
      </div>
      <div className="sim-tab-content">
        {tab === "config" ? (
          <SimulationConfigPanel onOpenFile={onOpenFile} />
        ) : (
          <SimulationRunPanel onOpenFile={onOpenFile} onOpenSimulation={onOpenSimulation} />
        )}
      </div>
    </div>
  )
}
