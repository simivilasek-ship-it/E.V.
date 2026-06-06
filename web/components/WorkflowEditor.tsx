'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

type NodeType = 'trigger' | 'condition' | 'action' | 'delay' | 'notify'

interface WorkflowNode {
  id: string
  type: NodeType
  x: number
  y: number
  label: string
  config: Record<string, string>
}

interface WorkflowEdge {
  id: string
  from: string
  to: string
  label?: string
}

interface Workflow {
  id: string
  name: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

const NODE_W = 110
const NODE_H = 40

const NODE_COLORS: Record<NodeType, string> = {
  trigger:   '#0066ff',
  condition: '#f59e0b',
  action:    '#00e5a0',
  delay:     '#8b5cf6',
  notify:    '#f97316',
}

const NODE_LABELS: Record<NodeType, string> = {
  trigger:   'TRIGGER',
  condition: 'CONDITION',
  action:    'ACTION',
  delay:     'DELAY',
  notify:    'NOTIFY',
}

function jitterOffset(): number {
  return (Math.random() - 0.5) * 80
}

const NODE_CONFIG_FIELDS: Record<NodeType, { key: string; label: string }[]> = {
  trigger:   [{ key: 'event', label: 'Event name' }],
  condition: [{ key: 'expression', label: 'Expression' }],
  action:    [{ key: 'command', label: 'Command' }],
  delay:     [{ key: 'seconds', label: 'Seconds' }],
  notify:    [{ key: 'message', label: 'Message' }],
}

function genId(): string {
  return Math.random().toString(36).slice(2, 10)
}

function bezierPath(x1: number, y1: number, x2: number, y2: number): string {
  const cx = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`
}

interface DragState {
  nodeId: string
  offsetX: number
  offsetY: number
}

interface ConnectState {
  fromId: string
}

export default function WorkflowEditor() {
  const [workflow, setWorkflow] = useState<Workflow>({
    id: genId(),
    name: 'New Workflow',
    nodes: [],
    edges: [],
  })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [drag, setDrag] = useState<DragState | null>(null)
  const [connecting, setConnecting] = useState<ConnectState | null>(null)
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [saveStatus, setSaveStatus] = useState<string>('')
  const svgRef = useRef<SVGSVGElement>(null)

  const selectedNode = workflow.nodes.find(n => n.id === selectedId) ?? null

  function toSvgCoords(clientX: number, clientY: number): { x: number; y: number } {
    const svg = svgRef.current
    if (!svg) return { x: clientX, y: clientY }
    const rect = svg.getBoundingClientRect()
    return { x: clientX - rect.left, y: clientY - rect.top }
  }

  function handleNodeMouseDown(e: React.MouseEvent, nodeId: string) {
    if (connecting) return
    e.stopPropagation()
    const { x, y } = toSvgCoords(e.clientX, e.clientY)
    const node = workflow.nodes.find(n => n.id === nodeId)
    if (!node) return
    setDrag({ nodeId, offsetX: x - node.x, offsetY: y - node.y })
    setSelectedId(nodeId)
  }

  const handleSvgMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const pos = toSvgCoords(e.clientX, e.clientY)
    setMousePos(pos)
    if (!drag) return
    setWorkflow(w => ({
      ...w,
      nodes: w.nodes.map(n =>
        n.id === drag.nodeId
          ? { ...n, x: pos.x - drag.offsetX, y: pos.y - drag.offsetY }
          : n,
      ),
    }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drag])

  function handleSvgMouseUp() {
    setDrag(null)
  }

  function handleSvgClick() {
    if (!connecting) setSelectedId(null)
    setConnecting(null)
  }

  function handleOutputDotMouseDown(e: React.MouseEvent, nodeId: string) {
    e.stopPropagation()
    setConnecting({ fromId: nodeId })
  }

  function handleInputDotMouseUp(e: React.MouseEvent, nodeId: string) {
    e.stopPropagation()
    if (!connecting || connecting.fromId === nodeId) {
      setConnecting(null)
      return
    }
    const exists = workflow.edges.some(
      ed => ed.from === connecting.fromId && ed.to === nodeId,
    )
    if (!exists) {
      const newEdge: WorkflowEdge = { id: genId(), from: connecting.fromId, to: nodeId }
      setWorkflow(w => ({ ...w, edges: [...w.edges, newEdge] }))
    }
    setConnecting(null)
  }

  function addNode(type: NodeType) {
    const svg = svgRef.current
    const cx = svg ? svg.clientWidth / 2 : 300
    const cy = svg ? svg.clientHeight / 2 : 250
    const newNode: WorkflowNode = {
      id: genId(), type,
      x: cx + jitterOffset(),
      y: cy + jitterOffset(),
      label: NODE_LABELS[type],
      config: {},
    }
    setWorkflow(w => ({ ...w, nodes: [...w.nodes, newNode] }))
    setSelectedId(newNode.id)
  }

  function deleteSelected() {
    if (!selectedId) return
    setWorkflow(w => ({
      ...w,
      nodes: w.nodes.filter(n => n.id !== selectedId),
      edges: w.edges.filter(e => e.from !== selectedId && e.to !== selectedId),
    }))
    setSelectedId(null)
  }

  function updateSelectedLabel(label: string) {
    if (!selectedId) return
    setWorkflow(w => ({
      ...w,
      nodes: w.nodes.map(n => n.id === selectedId ? { ...n, label } : n),
    }))
  }

  function updateSelectedConfig(key: string, value: string) {
    if (!selectedId) return
    setWorkflow(w => ({
      ...w,
      nodes: w.nodes.map(n =>
        n.id === selectedId ? { ...n, config: { ...n.config, [key]: value } } : n,
      ),
    }))
  }

  async function handleSave() {
    try {
      const res = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      })
      setSaveStatus(res.ok ? 'Saved ✓' : 'Error ✗')
    } catch {
      setSaveStatus('Offline ✗')
    }
    setTimeout(() => setSaveStatus(''), 2000)
  }

  async function handleLoad() {
    try {
      const res = await fetch('/api/workflows')
      if (res.ok) {
        const data = await res.json() as Workflow[]
        if (data.length > 0) setWorkflow(data[0])
      } else {
        setSaveStatus('Load error ✗')
      }
    } catch {
      setSaveStatus('Offline ✗')
    }
    setTimeout(() => setSaveStatus(''), 2000)
  }

  function handleExport() {
    const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${workflow.name.replace(/\s+/g, '_')}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleImport() {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const parsed = JSON.parse(reader.result as string) as Workflow
          setWorkflow(parsed)
          setSelectedId(null)
        } catch {
          setSaveStatus('Invalid JSON ✗')
          setTimeout(() => setSaveStatus(''), 2000)
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }

  function handleClear() {
    setWorkflow(w => ({ id: genId(), name: w.name, nodes: [], edges: [] }))
    setSelectedId(null)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      if (!selectedId) return
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      deleteSelected()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  const mono: React.CSSProperties = { fontFamily: "'Courier New', monospace" }

  const btnStyle: React.CSSProperties = {
    background: '#0b1220', border: '1px solid #1a3050', borderRadius: 4,
    color: '#7ea8d4', padding: '4px 10px', fontSize: 11, cursor: 'pointer', ...mono,
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', minHeight: 500,
      background: '#070b12', color: '#7ea8d4', ...mono,
      userSelect: drag ? 'none' : 'auto',
    }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 12px', borderBottom: '1px solid #1a3050', flexWrap: 'wrap',
      }}>
        <input
          value={workflow.name}
          onChange={e => setWorkflow(w => ({ ...w, name: e.target.value }))}
          style={{
            background: '#0b1220', border: '1px solid #1a3050', borderRadius: 4,
            color: '#00d4ff', padding: '4px 8px', fontSize: 12, ...mono, width: 180,
          }}
        />
        <button style={btnStyle} onClick={handleSave}>Save</button>
        <button style={btnStyle} onClick={handleLoad}>Load</button>
        <button style={btnStyle} onClick={handleExport}>Export JSON</button>
        <button style={btnStyle} onClick={handleImport}>Import JSON</button>
        <button style={{ ...btnStyle, color: '#f97316', borderColor: '#3a2010' }} onClick={handleClear}>Clear</button>
        {saveStatus && (
          <span style={{ fontSize: 11, color: saveStatus.includes('✓') ? '#00e5a0' : '#f97316' }}>
            {saveStatus}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Panel */}
        <div style={{
          width: 120, borderRight: '1px solid #1a3050',
          padding: 10, display: 'flex', flexDirection: 'column', gap: 6,
          background: '#050a15',
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.2em', color: '#4a6a8a', marginBottom: 4 }}>
            ADD NODE
          </div>
          {(Object.keys(NODE_COLORS) as NodeType[]).map(type => (
            <button
              key={type}
              onClick={() => addNode(type)}
              style={{
                background: `${NODE_COLORS[type]}15`,
                border: `1px solid ${NODE_COLORS[type]}44`,
                borderRadius: 5, color: NODE_COLORS[type],
                padding: '7px 4px', fontSize: 10, cursor: 'pointer',
                letterSpacing: '0.1em', ...mono,
              }}
            >
              {NODE_LABELS[type]}
            </button>
          ))}
          <div style={{ marginTop: 'auto', fontSize: 8, color: '#2a4060', lineHeight: 1.5 }}>
            Klikni pro přidání uzlu na canvas
          </div>
        </div>

        {/* Canvas SVG */}
        <svg
          ref={svgRef}
          style={{
            flex: 1, display: 'block',
            background: '#070b12',
            cursor: drag ? 'grabbing' : connecting ? 'crosshair' : 'default',
          }}
          onMouseMove={handleSvgMouseMove}
          onMouseUp={handleSvgMouseUp}
          onClick={handleSvgClick}
        >
          <defs>
            <pattern id="wf-hex" x="0" y="0" width="30" height="26" patternUnits="userSpaceOnUse">
              <path d="M15 0 L30 8 L30 18 L15 26 L0 18 L0 8 Z"
                fill="none" stroke="#0d1a2a" strokeWidth="0.5" />
            </pattern>
            {workflow.nodes.map(n => (
              <marker
                key={`mk-${n.id}`}
                id={`wf-arrow-${n.id}`}
                markerWidth="6" markerHeight="6"
                refX="5" refY="3" orient="auto"
              >
                <path d="M0,0 L6,3 L0,6 Z" fill={NODE_COLORS[n.type]} />
              </marker>
            ))}
          </defs>
          <rect width="100%" height="100%" fill="url(#wf-hex)" opacity="0.6" />

          {/* Edges */}
          {workflow.edges.map(edge => {
            const fn = workflow.nodes.find(n => n.id === edge.from)
            const tn = workflow.nodes.find(n => n.id === edge.to)
            if (!fn || !tn) return null
            return (
              <g key={edge.id}>
                <path
                  d={bezierPath(fn.x + NODE_W / 2, fn.y, tn.x - NODE_W / 2, tn.y)}
                  fill="none"
                  stroke={NODE_COLORS[fn.type]}
                  strokeWidth={1.5}
                  strokeOpacity={0.75}
                  markerEnd={`url(#wf-arrow-${fn.id})`}
                  style={{ transition: 'stroke 0.3s' }}
                />
                {edge.label && (
                  <text
                    x={(fn.x + NODE_W / 2 + tn.x - NODE_W / 2) / 2}
                    y={(fn.y + tn.y) / 2 - 7}
                    textAnchor="middle" fontSize="9"
                    fontFamily="'Courier New', monospace"
                    fill={NODE_COLORS[fn.type]} opacity={0.8}
                  >
                    {edge.label}
                  </text>
                )}
                {/* Click to delete edge */}
                <path
                  d={bezierPath(fn.x + NODE_W / 2, fn.y, tn.x - NODE_W / 2, tn.y)}
                  fill="none" stroke="transparent" strokeWidth={10}
                  style={{ cursor: 'pointer' }}
                  onClick={e => {
                    e.stopPropagation()
                    setWorkflow(w => ({ ...w, edges: w.edges.filter(ed => ed.id !== edge.id) }))
                  }}
                />
              </g>
            )
          })}

          {/* Live connection line */}
          {connecting && (() => {
            const fn = workflow.nodes.find(n => n.id === connecting.fromId)
            if (!fn) return null
            return (
              <path
                d={bezierPath(fn.x + NODE_W / 2, fn.y, mousePos.x, mousePos.y)}
                fill="none"
                stroke={NODE_COLORS[fn.type]}
                strokeWidth={1.5}
                strokeDasharray="5 4"
                opacity={0.6}
                style={{ pointerEvents: 'none' }}
              />
            )
          })()}

          {/* Nodes */}
          {workflow.nodes.map(node => {
            const isSel = node.id === selectedId
            const color = NODE_COLORS[node.type]
            return (
              <g
                key={node.id}
                onMouseDown={e => handleNodeMouseDown(e, node.id)}
                style={{ cursor: drag?.nodeId === node.id ? 'grabbing' : 'grab' }}
              >
                {isSel && (
                  <rect
                    x={node.x - NODE_W / 2 - 5} y={node.y - NODE_H / 2 - 5}
                    width={NODE_W + 10} height={NODE_H + 10}
                    rx="10" fill="none"
                    stroke={color} strokeWidth={1} opacity={0.25}
                    style={{ filter: 'blur(3px)', pointerEvents: 'none' }}
                  />
                )}
                <rect
                  x={node.x - NODE_W / 2} y={node.y - NODE_H / 2}
                  width={NODE_W} height={NODE_H}
                  rx="7"
                  fill={isSel ? `${color}20` : '#0b1220'}
                  stroke={isSel ? color : '#1a3050'}
                  strokeWidth={isSel ? 2 : 1}
                  style={{
                    filter: isSel ? `drop-shadow(0 0 8px ${color}77)` : 'none',
                    transition: 'all 0.3s',
                  }}
                />
                <text
                  x={node.x} y={node.y - 5}
                  textAnchor="middle" dominantBaseline="middle"
                  fontSize="9" fontFamily="'Courier New', monospace" letterSpacing="1.5"
                  fill={isSel ? color : '#7ea8d4'}
                  style={{ transition: 'fill 0.3s', pointerEvents: 'none' }}
                >
                  {node.label}
                </text>
                <text
                  x={node.x} y={node.y + 9}
                  textAnchor="middle" dominantBaseline="middle"
                  fontSize="7" fontFamily="'Courier New', monospace"
                  fill={`${color}88`}
                  style={{ pointerEvents: 'none' }}
                >
                  {node.type}
                </text>
                {/* Input dot */}
                <circle
                  cx={node.x - NODE_W / 2} cy={node.y} r={5}
                  fill="#0b1220" stroke={color} strokeWidth={1.5}
                  style={{ cursor: 'crosshair' }}
                  onMouseUp={e => handleInputDotMouseUp(e, node.id)}
                />
                {/* Output dot */}
                <circle
                  cx={node.x + NODE_W / 2} cy={node.y} r={5}
                  fill={color} stroke={color} strokeWidth={1}
                  style={{ cursor: 'crosshair' }}
                  onMouseDown={e => handleOutputDotMouseDown(e, node.id)}
                />
              </g>
            )
          })}

          {workflow.nodes.length === 0 && (
            <text
              x="50%" y="50%"
              textAnchor="middle" dominantBaseline="middle"
              fontSize="11" fontFamily="'Courier New', monospace"
              fill="#1a3050" letterSpacing="3"
            >
              KLIKNI NA TYP UZLU VLEVO PRO PŘIDÁNÍ
            </text>
          )}
        </svg>

        {/* Right Panel */}
        <div style={{
          width: 210, borderLeft: '1px solid #1a3050',
          padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
          overflowY: 'auto', background: '#050a15',
        }}>
          <div style={{ fontSize: 9, letterSpacing: '0.2em', color: '#4a6a8a' }}>
            NODE EDITOR
          </div>
          {selectedNode ? (
            <>
              <div>
                <div style={{ fontSize: 9, color: '#4a6a8a', marginBottom: 4 }}>LABEL</div>
                <input
                  value={selectedNode.label}
                  onChange={e => updateSelectedLabel(e.target.value)}
                  style={{
                    background: '#0b1220', border: '1px solid #1a3050', borderRadius: 4,
                    color: NODE_COLORS[selectedNode.type], padding: '4px 8px',
                    fontSize: 11, width: '100%', ...mono, boxSizing: 'border-box',
                  }}
                />
              </div>
              {NODE_CONFIG_FIELDS[selectedNode.type].map(field => (
                <div key={field.key}>
                  <div style={{ fontSize: 9, color: '#4a6a8a', marginBottom: 4 }}>
                    {field.label.toUpperCase()}
                  </div>
                  <input
                    value={selectedNode.config[field.key] ?? ''}
                    onChange={e => updateSelectedConfig(field.key, e.target.value)}
                    placeholder={field.label}
                    style={{
                      background: '#0b1220', border: '1px solid #1a3050', borderRadius: 4,
                      color: '#7ea8d4', padding: '4px 8px',
                      fontSize: 11, width: '100%', ...mono, boxSizing: 'border-box',
                    }}
                  />
                </div>
              ))}
              <div style={{
                padding: '4px 8px',
                background: `${NODE_COLORS[selectedNode.type]}11`,
                border: `1px solid ${NODE_COLORS[selectedNode.type]}33`,
                borderRadius: 4, fontSize: 9,
                color: NODE_COLORS[selectedNode.type], letterSpacing: '0.1em',
              }}>
                TYPE: {selectedNode.type.toUpperCase()}
              </div>
              <button
                onClick={deleteSelected}
                style={{
                  background: '#140808', border: '1px solid #3a1010', borderRadius: 4,
                  color: '#f97316', padding: '5px 8px', fontSize: 10,
                  cursor: 'pointer', ...mono,
                }}
              >
                DELETE NODE
              </button>
            </>
          ) : (
            <div style={{ fontSize: 10, color: '#2a4060' }}>
              Vyber uzel pro editaci.{'\n'}Klikni na output dot (pravý kroužek) a přetáhni na input dot (levý kroužek) jiného uzlu pro propojení.
            </div>
          )}

          {workflow.edges.length > 0 && (
            <>
              <div style={{ height: 1, background: '#1a3050', margin: '4px 0' }} />
              <div style={{ fontSize: 9, letterSpacing: '0.2em', color: '#4a6a8a', marginBottom: 2 }}>
                CONNECTIONS ({workflow.edges.length})
              </div>
              {workflow.edges.map(edge => {
                const fn = workflow.nodes.find(n => n.id === edge.from)
                const tn = workflow.nodes.find(n => n.id === edge.to)
                if (!fn || !tn) return null
                return (
                  <div key={edge.id} style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    fontSize: 9, color: '#4a6a8a',
                  }}>
                    <span style={{ color: NODE_COLORS[fn.type], maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {fn.label}
                    </span>
                    <span>→</span>
                    <span style={{ color: NODE_COLORS[tn.type], maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {tn.label}
                    </span>
                    <button
                      onClick={() => setWorkflow(w => ({ ...w, edges: w.edges.filter(e => e.id !== edge.id) }))}
                      style={{
                        marginLeft: 'auto', background: 'none', border: 'none',
                        color: '#4a3030', cursor: 'pointer', fontSize: 14, padding: 0, lineHeight: 1,
                      }}
                      title="Remove connection"
                    >
                      ×
                    </button>
                  </div>
                )
              })}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
