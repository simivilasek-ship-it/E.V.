'use client'

import { useEffect, useState, useRef } from 'react'

interface NodeDef {
  x: number
  y: number
  label: string
  color: string
}

interface EdgeDef {
  from: string
  to: string
}

const NODES: Record<string, NodeDef> = {
  planner:  { x: 120, y: 60,  label: 'PLANNER',  color: '#0066ff' },
  router:   { x: 120, y: 160, label: 'ROUTER',   color: '#00d4ff' },
  executor: { x: 120, y: 260, label: 'EXECUTOR', color: '#00e5a0' },
  critic:   { x: 120, y: 360, label: 'CRITIC',   color: '#8b5cf6' },
  done:     { x: 280, y: 210, label: 'DONE',     color: '#00e5a0' },
}

const EDGES: EdgeDef[] = [
  { from: 'planner',  to: 'router' },
  { from: 'router',   to: 'executor' },
  { from: 'executor', to: 'critic' },
  { from: 'critic',   to: 'router' },
  { from: 'critic',   to: 'done' },
]

const NODE_W = 90
const NODE_H = 30

function getEdgePoints(fromNode: NodeDef, toNode: NodeDef) {
  const fx = fromNode.x
  const fy = fromNode.y
  const tx = toNode.x
  const ty = toNode.y

  // Exit from bottom of source node, enter top of target node (if same column)
  // Exit from right of source, enter left of target (if different column)
  let x1: number, y1: number, x2: number, y2: number
  if (Math.abs(fx - tx) > 10) {
    // horizontal-ish
    x1 = fx + NODE_W / 2
    y1 = fy
    x2 = tx - NODE_W / 2
    y2 = ty
  } else {
    // vertical
    x1 = fx
    y1 = fy + NODE_H / 2
    x2 = tx
    y2 = ty - NODE_H / 2
  }
  return { x1, y1, x2, y2 }
}

interface ArrowProps {
  from: string
  to: string
  active: boolean
}

function Arrow({ from, to, active }: ArrowProps) {
  const fromNode = NODES[from]
  const toNode = NODES[to]
  const { x1, y1, x2, y2 } = getEdgePoints(fromNode, toNode)
  const color = active ? '#00d4ff' : '#1a3050'

  return (
    <g>
      <defs>
        <marker
          id={`arrow-${from}-${to}`}
          markerWidth="6" markerHeight="6"
          refX="5" refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill={color} />
        </marker>
      </defs>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color}
        strokeWidth={active ? 2 : 1}
        markerEnd={`url(#arrow-${from}-${to})`}
        style={{ transition: 'stroke 0.4s, stroke-width 0.4s' }}
      />
    </g>
  )
}

interface NodeRectProps {
  id: string
  node: NodeDef
  active: string | null
  hovered: string | null
  onHover: (id: string | null) => void
}

function NodeRect({ id, node, active, hovered, onHover }: NodeRectProps) {
  const isActive = active === id
  const isHovered = hovered === id
  const color = node.color
  const glow = isActive ? `0 0 18px ${color}, 0 0 38px ${color}55` : 'none'
  const fillColor = isActive
    ? `${color}22`
    : isHovered
      ? 'rgba(0,212,255,0.08)'
      : 'rgba(11,18,32,0.96)'
  const stroke = isActive ? color : isHovered ? '#00b4ff' : '#1a3050'

  return (
    <g onMouseEnter={() => onHover(id)} onMouseLeave={() => onHover(null)} style={{ cursor: 'pointer' }}>
      {isActive && (
        <rect
          x={node.x - NODE_W / 2 - 4}
          y={node.y - NODE_H / 2 - 4}
          width={NODE_W + 8}
          height={NODE_H + 8}
          rx="8"
          fill="none"
          stroke={color}
          strokeWidth="1"
          opacity="0.3"
          style={{ filter: `blur(2px)` }}
        />
      )}
      <rect
        x={node.x - NODE_W / 2}
        y={node.y - NODE_H / 2}
        width={NODE_W}
        height={NODE_H}
        rx="10"
        fill={fillColor}
        stroke={stroke}
        strokeWidth={isActive || isHovered ? 2 : 1}
        style={{
          filter: isActive ? `drop-shadow(${glow})` : 'drop-shadow(0 0 8px rgba(0,0,0,0.12))',
          transition: 'all 0.25s ease',
        }}
      />
      <text
        x={node.x}
        y={node.y + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="9"
        fontFamily="'Courier New', monospace"
        letterSpacing="2"
        fill={isActive || isHovered ? color : '#7ea8d4'}
        style={{ transition: 'fill 0.25s ease' }}
      >
        {node.label}
      </text>
    </g>
  )
}

interface AgentGraphProps {
  active?: boolean
}

export default function AgentGraph({ active: tabActive }: AgentGraphProps) {
  const [activeNode, setActiveNode] = useState<string | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [log, setLog] = useState<string[]>([])
  const [status, setStatus] = useState<'connecting' | 'online' | 'offline'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)

  // Recording / replay state
  type RecordedEvent = { ts: number; type: 'node_enter'; node: string }
    | { ts: number; type: 'node_exit' }
    | { ts: number; type: 'reasoning'; text: string }
  const [recorded, setRecorded] = useState<RecordedEvent[]>([])
  const [playing, setPlaying] = useState(false)
  const [, setPlayIndex] = useState(0)
  const playTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!tabActive) return

    let ws: WebSocket
    let dead = false

    function connect() {
      if (dead) return
      try {
        const wsUrl = process.env.NODE_ENV === 'production'
          ? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/graph`
          : `ws://${location.hostname}:${location.port || 3000}/ws/graph`
        ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => setStatus('online')

        ws.onmessage = (e: MessageEvent) => {
          try {
            const event = JSON.parse(e.data)
            if (event.type === 'ready')      setStatus('online')
            if (event.type === 'node_enter') {
              setActiveNode(event.node)
              setRecorded(r => [...r, {ts: Date.now(), type: 'node_enter', node: event.node}])
            }
            if (event.type === 'node_exit')  {
              setActiveNode(null)
              setRecorded(r => [...r, {ts: Date.now(), type: 'node_exit'}])
            }
            if (event.type === 'reasoning')  {
              setLog(l => [...l.slice(-9), event.text])
              setRecorded(r => [...r, {ts: Date.now(), type: 'reasoning', text: event.text}])
            }
          } catch {}
        }

        ws.onerror = () => setStatus('offline')
        ws.onclose = () => {
          if (!dead) {
            setStatus('offline')
            setTimeout(connect, 5000)
          }
        }
      } catch {
        setStatus('offline')
      }
    }

    connect()

    return () => {
      dead = true
      if (wsRef.current) wsRef.current.close()
    }
  }, [tabActive])

  // Playback effect
  useEffect(() => {
    if (!playing) {
      if (playTimerRef.current) {
        window.clearInterval(playTimerRef.current)
        playTimerRef.current = null
      }
      return
    }
    if (recorded.length === 0) return
    // start timer to advance playIndex
    playTimerRef.current = window.setInterval(() => {
      setPlayIndex(i => {
        const ni = i + 1
        if (ni >= recorded.length) {
          setPlaying(false)
          return recorded.length - 1
        }
        const ev = recorded[ni]
        if (ev.type === 'node_enter') setActiveNode(ev.node)
        if (ev.type === 'node_exit') setActiveNode(null)
        if (ev.type === 'reasoning') setLog(l => [...l.slice(-9), ev.text])
        return ni
      })
    }, 800)

    return () => {
      if (playTimerRef.current) {
        window.clearInterval(playTimerRef.current)
        playTimerRef.current = null
      }
    }
  }, [playing, recorded])

  if (status === 'offline') {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: 300, gap: 12,
        fontFamily: "'Courier New', monospace",
      }}>
        <div style={{ fontSize: 32, color: '#1a3050' }}>⬡</div>
        <div style={{ color: '#4a6a8a', fontSize: 11, letterSpacing: '0.15em' }}>GRAPH OFFLINE</div>
        <div style={{ color: '#2a4060', fontSize: 10 }}>WebSocket /ws/graph nedostupný</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 20, padding: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
      {/* SVG Graf */}
      <div>
        <div style={{
          fontSize: 9, letterSpacing: '0.2em', color: '#4a6a8a',
          fontFamily: "'Courier New', monospace", marginBottom: 8,
        }}>
          AGENT GRAPH
          <span style={{
            marginLeft: 10,
            color: status === 'online' ? '#00e5a0' : '#ffb300',
            fontSize: 8,
          }}>
            ● {status.toUpperCase()}
          </span>
        </div>

        <svg
          width={340}
          height={440}
          style={{
            background: '#070b12',
            border: '1px solid #1a3050',
            borderRadius: 10,
            display: 'block',
          }}
        >
          {/* Hex grid background */}
          <defs>
            <pattern id="hex-bg" x="0" y="0" width="30" height="26" patternUnits="userSpaceOnUse">
              <path d="M15 0 L30 8 L30 18 L15 26 L0 18 L0 8 Z"
                fill="none" stroke="#0d1a2a" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="340" height="440" fill="url(#hex-bg)" opacity="0.6" />

          {/* Edges */}
          {EDGES.map(e => (
            <Arrow
              key={`${e.from}-${e.to}`}
              from={e.from}
              to={e.to}
              active={activeNode === e.from}
            />
          ))}

          {/* Nodes */}
          {Object.entries(NODES).map(([id, node]) => (
            <NodeRect
              key={id}
              id={id}
              node={node}
              active={activeNode}
              hovered={hoveredNode}
              onHover={setHoveredNode}
            />
          ))}
        </svg>
      </div>

      {/* Reasoning log */}
      <div style={{ flex: 1, minWidth: 200 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
          <button onClick={() => setPlaying(p => !p)} style={{ padding: '4px 8px', fontSize: 11 }}>{playing ? '⏸ Pause' : '▶️ Play'}</button>
          <button onClick={() => {
            setPlayIndex(i => {
              const ni = Math.max(0, i - 1)
              const ev = recorded[ni]
              if (ev?.type === 'node_enter') setActiveNode(ev.node)
              else if (ev?.type === 'node_exit') setActiveNode(null)
              return ni
            })
          }} style={{ padding: '4px 8px', fontSize: 11 }}>◀ Step</button>
          <button onClick={() => {
            setPlayIndex(i => {
              const ni = Math.min(recorded.length - 1, i + 1)
              const ev = recorded[ni]
              if (ev?.type === 'node_enter') setActiveNode(ev.node)
              else if (ev?.type === 'node_exit') setActiveNode(null)
              return ni
            })
          }} style={{ padding: '4px 8px', fontSize: 11 }}>Step ▷</button>
          <div style={{ marginLeft: 'auto', color: '#6b7280', fontSize: 11 }}>Events: {recorded.length}</div>
        </div>

        <div style={{
          fontSize: 9, letterSpacing: '0.2em', color: '#4a6a8a',
          fontFamily: "'Courier New', monospace", marginBottom: 8,
        }}>
          REASONING LOG
        </div>

        <div style={{
          background: '#050a15',
          border: '1px solid #1a3050',
          borderRadius: 8,
          padding: 12,
          minHeight: 200,
          maxHeight: 420,
          overflowY: 'auto',
          fontFamily: "'Courier New', monospace",
          fontSize: 11,
        }}>
          {log.length === 0 ? (
            <div style={{ color: '#2a4060', fontSize: 10 }}>
              Čekám na reasoning events…
            </div>
          ) : (
            log.map((line, i) => (
              <div key={i} style={{
                padding: '4px 0',
                borderBottom: '1px solid #0b1220',
                color: i === log.length - 1 ? '#00d4ff' : '#7ea8d4',
                lineHeight: 1.5,
              }}>
                <span style={{ color: '#2a4060', marginRight: 6 }}>›</span>
                {line}
              </div>
            ))
          )}
        </div>

        {/* Active node indicator */}
        {activeNode && (
          <div style={{
            marginTop: 12,
            padding: '8px 12px',
            background: `${NODES[activeNode]?.color}11`,
            border: `1px solid ${NODES[activeNode]?.color}44`,
            borderRadius: 6,
            fontFamily: "'Courier New', monospace",
            fontSize: 10,
            letterSpacing: '0.15em',
            color: NODES[activeNode]?.color,
          }}>
            ◎ ACTIVE: {activeNode.toUpperCase()}
          </div>
        )}
      </div>
    </div>
  )
}
