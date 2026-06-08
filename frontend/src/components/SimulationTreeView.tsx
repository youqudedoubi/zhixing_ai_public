import { useCallback, useEffect } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  Position,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import type { SimulationNode } from "../types/simulation"

interface Props {
  root: SimulationNode | null
  title?: string
  maxBranches: number
  maxSteps: number
}

const NODE_WIDTH = 200
const NODE_HEIGHT = 72
const H_GAP = 60
const BASE_SLOT_HEIGHT = 110

function hashColor(name: string): { bg: string; border: string; text: string } {
  if (!name) return { bg: "#f1f5f9", border: "#94a3b8", text: "#334155" }
  let h = 0
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h)
  const hue = Math.abs(h) % 360
  return {
    bg: `hsl(${hue},50%,93%)`,
    border: `hsl(${hue},50%,52%)`,
    text: `hsl(${hue},50%,22%)`,
  }
}

function nodePosition(id: string, maxBranches: number, maxSteps: number): { x: number; y: number } {
  const segs = id.split(".")
  const depth = segs.length - 1
  const totalH = Math.pow(maxBranches, maxSteps) * BASE_SLOT_HEIGHT
  if (depth === 0) return { x: 0, y: totalH / 2 - NODE_HEIGHT / 2 }
  const x = depth * (NODE_WIDTH + H_GAP)
  let y = 0
  const branches = segs.slice(1).map(Number)
  for (let i = 0; i < branches.length; i++) {
    y += (branches[i] - 1) * (totalH / Math.pow(maxBranches, i + 1))
  }
  y += totalH / Math.pow(maxBranches, depth) / 2 - NODE_HEIGHT / 2
  return { x, y }
}

type SimNodeData = {
  label: string
  phase: string
  content: string
  isRoot: boolean
}

function SimNodeCard({ data, selected, dragging }: { data: SimNodeData; selected?: boolean; dragging?: boolean }) {
  const showPopup = selected && !dragging
  const c = data.isRoot ? { bg: "#f1f5f9", border: "#94a3b8", text: "#334155" } : hashColor(data.label)
  const label = data.isRoot ? "起点" : data.label
  const previewLen = data.isRoot ? 28 : 20
  const preview = data.content.slice(0, previewLen) + (data.content.length > previewLen ? "…" : "")
  return (
    <div className="sim-node-card" style={{ background: c.bg, borderLeft: `4px solid ${c.border}` }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0, pointerEvents: "none" }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0, pointerEvents: "none" }} />
      <div className="sim-node-header">
        <span className="sim-node-name" style={{ color: c.text }}>{label}</span>
        {!data.isRoot && data.phase && <span className="sim-node-phase" style={{ color: c.border }}>· {data.phase}</span>}
      </div>
      <div className="sim-node-preview" style={{ color: c.text }}>{preview}</div>
      {showPopup && (
        <div className="sim-popup" style={{ position: "absolute", top: "100%", left: "100%", marginTop: 6, zIndex: 10 }}>
          <div className="sim-popup-header">
            <span className="sim-popup-title">{label}</span>
            {!data.isRoot && data.phase && <span className="sim-popup-phase">· {data.phase}</span>}
          </div>
          <div className="sim-popup-body">{data.content}</div>
        </div>
      )}
    </div>
  )
}

const nodeTypes: NodeTypes = { simNode: SimNodeCard as NodeTypes[string] }

function collectNodesEdges(
  node: SimulationNode, maxBranches: number, maxSteps: number,
  nodes: Node[], edges: Edge[],
): void {
  const pos = nodePosition(node.id, maxBranches, maxSteps)
  nodes.push({
    id: node.id, type: "simNode", position: pos,
    sourcePosition: Position.Right, targetPosition: Position.Left,
    data: { label: node.pattern_name || "情境", phase: node.phase, content: node.content, isRoot: node.id === "1" } as SimNodeData,
  })
  for (const child of node.children) {
    edges.push({ id: `${node.id}-${child.id}`, source: node.id, target: child.id, type: "smoothstep" })
    collectNodesEdges(child, maxBranches, maxSteps, nodes, edges)
  }
}

export default function SimulationTreeView({ root, title, maxBranches, maxSteps }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const rebuild = useCallback(() => {
    if (!root) { setNodes([]); setEdges([]); return }
    const nn: Node[] = [], ee: Edge[] = []
    collectNodesEdges(root, maxBranches, maxSteps, nn, ee)
    setNodes(nn); setEdges(ee)
  }, [root, maxBranches, maxSteps, setNodes, setEdges])

  useEffect(() => { rebuild() }, [rebuild])

  if (!root) return <div className="sim-tree-empty"><span>暂无模拟结果</span></div>

  return (
    <div className="sim-tree-view">
      {title && <div className="sim-tree-title">{title}</div>}
      <ReactFlow
        nodes={nodes} edges={edges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.35, maxZoom: 0.85 }}
        minZoom={0.1} maxZoom={2}
      >
        <Background /><Controls /><MiniMap />
      </ReactFlow>
    </div>
  )
}
