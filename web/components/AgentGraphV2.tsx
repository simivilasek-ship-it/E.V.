'use client'

import { useEffect, useRef, useState } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────────
type EventType = 'node_enter' | 'node_exit' | 'reasoning' | 'ready' | 'ping'
type ReasoningType = 'thought' | 'action' | 'observation' | 'result'

interface GraphEvent {
  type: EventType
  node?: string
  text?: string
  ts?: number
}

interface ReasoningStep {
  id: string
  type: ReasoningType
  text: string
  ts: number
  node: string
}

interface TimelineEntry {
  node: string
  ts: number
  color: string
}

// ── Static graph layout (compatible with AgentGraph) ──────────────────────────
interface NodeDef {
  x: number
  y: number
  label: string
  color: string
}

const NODES: Record<string, NodeDef> = {
  planner:  { x: 120, y: 60,  label: 'PLANNER',  color: 'var(--accent)' },
  router:   { x: 120, y: 160, label: 'ROUTER',   color: 'var(--cyan)' },
  executor: { x: 120, y: 260, label: 'EXECUTOR', color: 'var(--green)' },
  critic:   { x: 120, y: 360, label: 'CRITIC',   color: 'var(--purple)' },
  done:     { x: 280, y: 210, label: 'DONE',     color: 'var(--green)' },
  error:    { x: 280, y: 310, label: 'ERROR',    color: 'var(--red, #f87171)' },
  ready:    { x: 280, y: 110, label: 'READY',    color: 'var(--amber)' },
}

/** Maps backend-emitted node IDs to NODES keys. */
const NODE_ALIAS: Record<string, string> = {
  planning:  'planner',
  executing: 'executor',
  routing:   'router',
}

const EDGES: { from: string; to: string }[] = [
  { from: 'planner',  to: 'router' },
  { from: 'router',   to: 'executor' },
  { from: 'executor', to: 'critic' },
  { from: 'critic',   to: 'router' },
  { from: 'critic',   to: 'done' },
]

const NODE_W = 90
const NODE_H = 30

const REASONING_META: Record<ReasoningType, { icon: string; color: string }> = {
  thought:     { icon: '🤔', color: 'var(--cyan)' },
  action:      { icon: '🔧', color: 'var(--amber)' },
  observation: { icon: '👁️', color: 'var(--purple)' },
  result:      { icon: '✅', color: 'var(--green)' },
}

function genId(): string {
  return Math.random().toString(36).slice(2, 10)
}

function detectReasoningType(text: string): ReasoningType {
  const lower = text.toLowerCase()
  if (lower.startsWith('action') || lower.startsWith('tool') || lower.startsWith('call')) return 'action'
  if (lower.startsWith('observ') || lower.startsWith('result') || lower.startsWith('output')) return 'observation'
  if (lower.startsWith('final') || lower.startsWith('done') || lower.startsWith('answer')) return 'result'
  return 'thought'
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getEdgeCentre(from: string, to: string): { cx: number; cy: number } {
  const fn = NODES[from]
  const tn = NODES[to]
  if (!fn || !tn) return { cx: 0, cy: 0 }
  const isHorizontal = Math.abs(fn.x - tn.x) > 10
  if (isHorizontal) {
    return { cx: (fn.x + NODE_W / 2 + tn.x - NODE_W / 2) / 2, cy: (fn.y + tn.y) / 2 }
  }
  return { cx: fn.x, cy: (fn.y + NODE_H / 2 + tn.y - NODE_H / 2) / 2 }
}

// ── Sub-components ─────────────────────────────────────────────────────────────
interface EdgeProps {
  from: string
  to: string
  active: boolean
}

function AnimatedEdge({ from, to, active }: EdgeProps) {
  const fn = NODES[from]
  const tn = NODES[to]
  if (!fn || !tn) return null

  let x1: number, y1: number, x2: number, y2: number
  if (Math.abs(fn.x - tn.x) > 10) {
    x1 = fn.x + NODE_W / 2; y1 = fn.y
    x2 = tn.x - NODE_W / 2; y2 = tn.y
  } else {
    x1 = fn.x; y1 = fn.y + NODE_H / 2
    x2 = tn.x; y2 = tn.y - NODE_H / 2
  }

  const color = active ? 'var(--cyan)' : 'var(--border-hud)'
  const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

  return (
    <g>
      <defs>
        <marker
          id={`v2-arrow-${from}-${to}`}
          markerWidth="6" markerHeight="6"
          refX="5" refY="3" orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" style={{ fill: color }} />
        </marker>
      </defs>
      {/* Base line */}
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        strokeWidth={active ? 2 : 1}
        markerEnd={`url(#v2-arrow-${from}-${to})`}
        style={{ stroke: color, transition: 'stroke 0.4s, stroke-width 0.4s' }}
      />
      {/* Animated flow dots */}
      {active && (
        <line
          x1={x1} y1={y1} x2={x2} y2={y2}
          strokeWidth={3}
          strokeDasharray={`4 ${length}`}
          strokeLinecap="round"
          opacity={0.8}
          style={{ stroke: 'var(--cyan)' }}
        >
          <animate
            attributeName="stroke-dashoffset"
            from={length + 4}
            to={0}
            dur="0.8s"
            repeatCount="indefinite"
          />
        </line>
      )}
    </g>
  )
}

interface NodeBadgeProps {
  id: string
  node: NodeDef
  active: string | null
  passCount: number
}

function NodeBadge({ id, node, active, passCount }: NodeBadgeProps) {
  const isActive = active === id
  const color = node.color

  return (
    <g>
      {isActive && (
        <rect
          x={node.x - NODE_W / 2 - 5} y={node.y - NODE_H / 2 - 5}
          width={NODE_W + 10} height={NODE_H + 10}
          rx="9"
          style={{ fill: 'none', stroke: color, strokeWidth: 1, opacity: 0.3, filter: 'blur(2px)' }}
        />
      )}
      <rect
        x={node.x - NODE_W / 2} y={node.y - NODE_H / 2}
        width={NODE_W} height={NODE_H}
        rx="6"
        strokeWidth={isActive ? 2 : 1}
        style={{
          fill: isActive ? `color-mix(in srgb, ${color} 13%, transparent)` : 'var(--bg-hud)',
          stroke: isActive ? color : 'var(--border-hud)',
          filter: isActive ? `drop-shadow(0 0 12px color-mix(in srgb, ${color} 60%, transparent))` : 'none',
          transition: 'all 0.4s',
        }}
      />
      <text
        x={node.x} y={node.y + 1}
        textAnchor="middle" dominantBaseline="middle"
        fontSize="9" fontFamily="'Courier New', monospace" letterSpacing="2"
        style={{ fill: isActive ? color : 'var(--text2)', transition: 'fill 0.4s' }}
      >
        {node.label}
      </text>
      {/* Pass count badge */}
      {passCount > 0 && (
        <g>
          <circle
            cx={node.x + NODE_W / 2 - 2} cy={node.y - NODE_H / 2 + 2}
            r={8}
            style={{ fill: 'var(--bg-hud)', stroke: color, strokeWidth: 1 }}
          />
          <text
            x={node.x + NODE_W / 2 - 2} y={node.y - NODE_H / 2 + 3}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="7" fontFamily="'Courier New', monospace"
            style={{ fill: color }}
          >
            {passCount > 99 ? '99+' : passCount}
          </text>
        </g>
      )}
    </g>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
interface AgentGraphV2Props {
  active?: boolean
}

export default function AgentGraphV2({ active: tabActive }: AgentGraphV2Props) {
  const [activeNode, setActiveNode] = useState<string | null>(null)
  const [status, setStatus] = useState<'connecting' | 'online' | 'offline'>('connecting')
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([])
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [passCounts, setPassCounts] = useState<Record<string, number>>({})
  const [stepIndex, setStepIndex] = useState(0)
  const [stepTotal, setStepTotal] = useState(0)
  const [stepStartTs, setStepStartTs] = useState<number | null>(null)
  const [elapsedSec, setElapsedSec] = useState<number>(0)
  const [showDebug, setShowDebug] = useState(false)
  const [lastEvent, setLastEvent] = useState<GraphEvent | null>(null)
  const [recorded, setRecorded] = useState<GraphEvent[]>([])
  const [replaying, setReplaying] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const reasoningEndRef = useRef<HTMLDivElement>(null)
  const replayTimerRef = useRef<number | null>(null)
  const replayIndexRef = useRef(0)

  const currentNode = activeNode ?? 'idle'

  // ── WebSocket ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!tabActive) return
    let dead = false

    function applyEvent(event: GraphEvent) {
      // Resolve backend node alias to UI node key
      if (event.node && NODE_ALIAS[event.node]) {
        event = { ...event, node: NODE_ALIAS[event.node] }
      }
      setLastEvent(event)
      if (event.type === 'ready') setStatus('online')
      if (event.type === 'node_enter' && event.node) {
        setActiveNode(event.node)
        setStepIndex(i => i + 1)
        setStepTotal(i => Math.max(i, i + 1))
        setStepStartTs(Date.now())
        setPassCounts(c => ({ ...c, [event.node!]: (c[event.node!] ?? 0) + 1 }))
        const nodeColor = NODES[event.node]?.color ?? 'var(--text2)'
        setTimeline(t => [
          ...t.filter(e => Date.now() - e.ts < 30 * 60 * 1000),
          { node: event.node!, ts: event.ts ?? Date.now(), color: nodeColor },
        ])
      }
      if (event.type === 'node_exit') {
        setActiveNode(null)
        if (stepStartTs) setElapsedSec(+(( Date.now() - stepStartTs) / 1000).toFixed(1))
      }
      if (event.type === 'reasoning' && event.text) {
        const rType = detectReasoningType(event.text)
        const step: ReasoningStep = {
          id: genId(),
          type: rType,
          text: event.text,
          ts: event.ts ?? Date.now(),
          node: activeNode ?? 'unknown',
        }
        setReasoningSteps(s => [...s.slice(-49), step])
      }
    }

    function connect() {
      if (dead) return
      try {
        const wsUrl = process.env.NODE_ENV === 'production'
          ? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/graph`
          : `ws://${location.hostname}:${location.port || 3000}/ws/graph`
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws
        ws.onopen = () => setStatus('online')
        ws.onmessage = (e: MessageEvent) => {
          try {
            const event = JSON.parse(e.data as string) as GraphEvent
            setRecorded(r => [...r, { ...event, ts: event.ts ?? Date.now() }])
            applyEvent(event)
          } catch { /* ignore parse errors */ }
        }
        ws.onerror = () => setStatus('offline')
        ws.onclose = () => {
          if (!dead) { setStatus('offline'); setTimeout(connect, 5000) }
        }
      } catch {
        setStatus('offline')
      }
    }
    connect()
    return () => {
      dead = true
      wsRef.current?.close()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabActive])

  // Auto-scroll reasoning
  useEffect(() => {
    reasoningEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [reasoningSteps])

  // ── Replay ─────────────────────────────────────────────────────────────────
  function startReplay() {
    if (recorded.length === 0) return
    setReplaying(true)
    replayIndexRef.current = 0
    replayTimerRef.current = window.setInterval(() => {
      const idx = replayIndexRef.current
      if (idx >= recorded.length) {
        setReplaying(false)
        if (replayTimerRef.current) window.clearInterval(replayTimerRef.current)
        return
      }
      // replay apply (simplified — no re-accumulate passCounts for replay)
      const ev = recorded[idx]
      if (ev.type === 'node_enter' && ev.node) setActiveNode(ev.node)
      if (ev.type === 'node_exit') setActiveNode(null)
      replayIndexRef.current = idx + 1
    }, 600)
  }

  useEffect(() => {
    if (!replaying) {
      if (replayTimerRef.current) window.clearInterval(replayTimerRef.current)
    }
  }, [replaying])

  const [timelineNow, setTimelineNow] = useState(0)
  useEffect(() => {
    const tick = () => setTimelineNow(Date.now())
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  // ── Offline state ──────────────────────────────────────────────────────────
  if (status === 'offline') {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: 300, gap: 12,
        fontFamily: "'Courier New', monospace",
      }}>
        <div style={{ fontSize: 32, color: 'var(--border-hud)' }}>⬡</div>
        <div style={{ color: 'var(--muted)', fontSize: 11, letterSpacing: '0.15em' }}>GRAPH OFFLINE</div>
        <div style={{ color: 'var(--border-hud)', fontSize: 10 }}>WebSocket /ws/graph nedostupný</div>
      </div>
    )
  }

  const mono: React.CSSProperties = { fontFamily: "'Courier New', monospace" }

  // Timeline: last 30 min, show last 60 entries max
  const timelineSlice = timeline.slice(-60)
  const timelineWindowMs = 30 * 60 * 1000

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, ...mono }}>
      {/* Step counter */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '6px 16px', borderBottom: '1px solid var(--border-hud)',
        background: 'var(--bg-hud)',
      }}>
        <span style={{ fontSize: 11, color: 'var(--muted)', letterSpacing: '0.15em' }}>
          AGENT GRAPH V2
        </span>
        <span style={{
          marginLeft: 8, fontSize: 11, color: 'var(--cyan)',
          background: 'color-mix(in srgb, var(--cyan) 7%, transparent)',
          border: '1px solid color-mix(in srgb, var(--cyan) 20%, transparent)',
          borderRadius: 4, padding: '2px 8px',
        }}>
          Krok {stepIndex}/{stepTotal} · {elapsedSec}s
        </span>
        <span style={{
          fontSize: 8, letterSpacing: '0.1em',
          color: status === 'online' ? 'var(--green)' : 'var(--amber)',
          marginLeft: 'auto',
        }}>
          ● {status.toUpperCase()}
        </span>
        <button
          onClick={() => setShowDebug(d => !d)}
          style={{
            background: showDebug ? 'var(--border-hud)' : 'var(--bg-hud)',
            border: '1px solid var(--border-hud)', borderRadius: 4,
            color: 'var(--text2)', padding: '2px 8px', fontSize: 10,
            cursor: 'pointer', ...mono,
          }}
        >
          DEBUG
        </button>
      </div>

      <div style={{ display: 'flex', gap: 20, padding: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* SVG Graph */}
        <div>
          <svg
            width={340} height={440}
            style={{
              background: 'var(--bg-hud)',
              border: '1px solid var(--border-hud)',
              borderRadius: 10,
              display: 'block',
            }}
          >
            <defs>
              <pattern id="v2-hex-bg" x="0" y="0" width="30" height="26" patternUnits="userSpaceOnUse">
                <path d="M15 0 L30 8 L30 18 L15 26 L0 18 L0 8 Z"
                  fill="none" strokeWidth="0.5" style={{ stroke: 'var(--bg-hud)' }} />
              </pattern>
            </defs>
            <rect width="340" height="440" fill="url(#v2-hex-bg)" opacity="0.6" />

            {EDGES.map(e => (
              <AnimatedEdge
                key={`${e.from}-${e.to}`}
                from={e.from} to={e.to}
                active={activeNode === e.from}
              />
            ))}

            {Object.entries(NODES).map(([id, node]) => (
              <NodeBadge
                key={id} id={id} node={node}
                active={activeNode}
                passCount={passCounts[id] ?? 0}
              />
            ))}
          </svg>
        </div>

        {/* Right column */}
        <div style={{ flex: 1, minWidth: 220, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Reasoning chain */}
          <div>
            <div style={{ fontSize: 9, letterSpacing: '0.2em', color: 'var(--muted)', marginBottom: 8 }}>
              REASONING CHAIN
            </div>
            <div style={{
              background: 'var(--bg-hud)',
              border: '1px solid var(--border-hud)',
              borderRadius: 8,
              padding: 10,
              minHeight: 180,
              maxHeight: 300,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}>
              {reasoningSteps.length === 0 ? (
                <div style={{ color: 'var(--border-hud)', fontSize: 10 }}>
                  Čekám na reasoning events…
                </div>
              ) : (
                reasoningSteps.map(step => {
                  const meta = REASONING_META[step.type]
                  return (
                    <div key={step.id} style={{
                      background: `color-mix(in srgb, ${meta.color} 6%, transparent)`,
                      border: `1px solid color-mix(in srgb, ${meta.color} 20%, transparent)`,
                      borderRadius: 6,
                      padding: '6px 10px',
                    }}>
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 3,
                      }}>
                        <span style={{ fontSize: 10, color: meta.color }}>
                          {meta.icon} {step.type.toUpperCase()}
                        </span>
                        <span style={{ fontSize: 8, color: 'var(--muted)' }}>
                          {formatTime(step.ts)}
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.5 }}>
                        {step.text}
                      </div>
                      {step.node && step.node !== 'unknown' && (
                        <div style={{ fontSize: 8, color: `color-mix(in srgb, ${NODES[step.node]?.color ?? 'var(--muted)'} 60%, transparent)`, marginTop: 3 }}>
                          @ {step.node}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
              <div ref={reasoningEndRef} />
            </div>
          </div>

          {/* Active node indicator */}
          {activeNode && (
            <div style={{
              padding: '8px 12px',
              background: `color-mix(in srgb, ${NODES[activeNode]?.color ?? 'var(--text2)'} 7%, transparent)`,
              border: `1px solid color-mix(in srgb, ${NODES[activeNode]?.color ?? 'var(--text2)'} 27%, transparent)`,
              borderRadius: 6, fontSize: 10, letterSpacing: '0.15em',
              color: NODES[activeNode]?.color ?? 'var(--text2)',
            }}>
              ◎ ACTIVE: {activeNode.toUpperCase()}
            </div>
          )}

          {/* Debug panel */}
          {showDebug && (
            <div style={{
              background: 'var(--bg-hud)', border: '1px solid var(--border-hud)',
              borderRadius: 8, padding: 10,
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 8,
              }}>
                <span style={{ fontSize: 9, letterSpacing: '0.2em', color: 'var(--muted)' }}>
                  DEBUG — LAST EVENT
                </span>
                <button
                  onClick={startReplay}
                  disabled={replaying || recorded.length === 0}
                  style={{
                    background: replaying ? 'var(--border-hud)' : 'var(--bg-hud)',
                    border: '1px solid var(--border-hud)', borderRadius: 4,
                    color: replaying ? 'var(--muted)' : 'var(--cyan)',
                    padding: '2px 8px', fontSize: 9, cursor: replaying ? 'default' : 'pointer',
                    ...mono,
                  }}
                >
                  {replaying ? 'Replaying…' : `▶ Replay (${recorded.length})`}
                </button>
              </div>
              <pre style={{
                margin: 0, fontSize: 9, color: 'var(--muted)',
                overflowX: 'auto', maxHeight: 120,
                whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              }}>
                {lastEvent ? JSON.stringify(lastEvent, null, 2) : 'No events yet'}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div style={{
        borderTop: '1px solid var(--border-hud)',
        padding: '8px 16px',
        background: 'var(--bg-hud)',
      }}>
        <div style={{ fontSize: 9, letterSpacing: '0.2em', color: 'var(--muted)', marginBottom: 6 }}>
          TIMELINE — posledních 30 min
        </div>
        <div style={{
          position: 'relative', height: 28,
          background: 'var(--bg-hud)', border: '1px solid var(--border-hud)',
          borderRadius: 6, overflow: 'hidden',
        }}>
          {/* Time axis labels */}
          {[-30, -20, -10, 0].map(mins => (
            <span key={mins} style={{
              position: 'absolute',
              left: `${((timelineWindowMs + mins * 60000) / timelineWindowMs) * 100}%`,
              bottom: 2, fontSize: 7, color: 'var(--border-hud)',
              transform: 'translateX(-50%)',
              ...mono,
            }}>
              {mins === 0 ? 'now' : `${mins}m`}
            </span>
          ))}
          {timelineSlice.map(entry => {
            const age = timelineNow - entry.ts
            if (age > timelineWindowMs) return null
            const leftPct = ((timelineWindowMs - age) / timelineWindowMs) * 100
            return (
              <div
                key={`${entry.node}-${entry.ts}`}
                title={`${entry.node} @ ${formatTime(entry.ts)}`}
                style={{
                  position: 'absolute',
                  left: `${leftPct}%`,
                  top: 4,
                  width: 6, height: 14,
                  background: entry.color,
                  borderRadius: 2,
                  opacity: 0.8,
                  transform: 'translateX(-50%)',
                }}
              />
            )
          })}
          {timelineSlice.length === 0 && (
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: 9, color: 'var(--border-hud)', ...mono,
            }}>
              žádné průchody
            </div>
          )}
        </div>

        {/* Pass counts */}
        <div style={{ display: 'flex', gap: 10, marginTop: 6, flexWrap: 'wrap' }}>
          {Object.entries(NODES).map(([id, node]) => (
            <div key={id} style={{
              fontSize: 8, color: `color-mix(in srgb, ${node.color} 80%, transparent)`,
              background: `color-mix(in srgb, ${node.color} 6%, transparent)`,
              border: `1px solid color-mix(in srgb, ${node.color} 19%, transparent)`,
              borderRadius: 4, padding: '2px 6px',
              ...mono,
            }}>
              {node.label}: {passCounts[id] ?? 0}×
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
