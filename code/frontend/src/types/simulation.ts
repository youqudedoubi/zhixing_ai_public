export interface SimulationNode {
  id: string
  pattern_name: string
  phase: string
  content: string
  parent_id: string | null
  children: SimulationNode[]
}

export interface SimulationResult {
  id: string
  name: string
  config_name: string
  situation: string
  max_branches: number
  max_steps: number
  alpha: number
  created_at: string
  root: SimulationNode | null
}

export interface SimulationSession {
  id: string
  name: string
  created_at: string
  result_id: string | null
}

export interface PatternItem {
  rel_path: string
  name: string
  category: string
  intensity: number
}

export type SimSSEEvent =
  | { type: "flow_done"; pattern_name: string; current: number; total: number }
  | { type: "flow_error"; pattern_name: string; error: string }
  | { type: "done"; message: string }
  | { type: "sim_status"; message: string }
  | { type: "simulation_start"; max_branches: number; max_steps: number }
  | { type: "node_start"; node_id: string; pattern_name: string; phase: string; parent_id: string }
  | { type: "node_done"; node_id: string; content: string }
  | { type: "simulation_done"; result_id: string }
  | { type: "error"; message: string }
