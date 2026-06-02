'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { apiUrl } from '@/lib/api'

const GROUP_COLORS: Record<string, string> = {
  memory:         '#00d4ff',
  conversation:   '#8b5cf6',
  daily_summary:  '#10b981',
  user:           '#f59e0b',
  fact:           '#ef4444',
  task:           '#3b82f6',
}

function color(group: string): string {
  return GROUP_COLORS[group] || '#4a6a8a'
}

interface MemoryNode {
  id: string
  label: string
  group: string
  importance: number
  tags?: string[]
}

interface MemoryLink {
  source: string
  target: string
}

interface NodePos {
  x: number
  y: number
  vx: number
  vy: number
}

// Miniaturní force simulace bez D3
function useForce(
  nodes: MemoryNode[],
  links: MemoryLink[],
  w: number,
  h: number
): Record<string, NodePos> {
  const [pos, setPos] = useState<Record<string, NodePos>>({})

  useEffect(() => {
    if (!nodes.length) return
    // Inicializace pozic
    const p: Record<string, NodePos> = {}
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * Math.PI * 2
      const r = Math.min(w, h) * 0.32
      p[n.id] = {
        x: w / 2 + Math.cos(angle) * r * (0.5 + Math.random() * 0.5),
        y: h / 2 + Math.sin(angle) * r * (0.5 + Math.random() * 0.5),
        vx: 0, vy: 0,
      }
    })

    let frame = 0
    let raf: number
    function tick() {
      frame++
      // Repulze
      const ids = nodes.map(n => n.id)
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const a = p[ids[i]], b = p[ids[j]]
          const dx = b.x - a.x, dy = b.y - a.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 1200 / (dist * dist)
          const fx = (dx / dist) * force, fy = (dy / dist) * force
          a.vx -= fx; a.vy -= fy
          b.vx += fx; b.vy += fy
        }
      }
      // Atrakce po linkách
      links.forEach(l => {
        const a = p[l.source], b = p[l.target]
        if (!a || !b) return
        const dx = b.x - a.x, dy = b.y - a.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = (dist - 100) * 0.035
        a.vx += (dx / dist) * force; a.vy += (dy / dist) * force
        b.vx -= (dx / dist) * force; b.vy -= (dy / dist) * force
      })
      // Centrum gravitace + damping + bounds
      const cx = w / 2, cy = h / 2
      ids.forEach(id => {
        const n = p[id]
        n.vx += (cx - n.x) * 0.006
        n.vy += (cy - n.y) * 0.006
        n.vx *= 0.78; n.vy *= 0.78
        n.x = Math.max(40, Math.min(w - 40, n.x + n.vx))
        n.y = Math.max(40, Math.min(h - 40, n.y + n.vy))
      })

      if (frame % 2 === 0) setPos({ ...p })
      if (frame < 180) raf = requestAnimationFrame(tick)
      else setPos({ ...p })
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [nodes.length, links.length, w, h])

  return pos
}

export default function MemoryGraph() {
  const [data,     setData]    = useState<{ nodes: MemoryNode[], links: MemoryLink[] }>({ nodes: [], links: [] })
  const [loading,  setLoading] = useState(true)
  const [selected, setSelected] = useState<MemoryNode | null>(null)
  const [search,   setSearch]  = useState('')
  const svgRef = useRef<SVGSVGElement>(null)
  const W = 640, H = 480

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await fetch(apiUrl('/api/memory/graph')).then(r => r.json())
      setData(d)
    } catch { setData({ nodes: [], links: [] }) }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = search
    ? data.nodes.filter(n => n.label.toLowerCase().includes(search.toLowerCase()))
    : data.nodes

  const visIds = new Set(filtered.map(n => n.id))
  const visLinks = data.links.filter(l => visIds.has(l.source) && visIds.has(l.target))

  const pos = useForce(filtered, visLinks, W, H)

  return (
    <div style={{ fontFamily: 'var(--font-mono,monospace)', color: '#e2f0ff' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em' }}>
          MEMORY GRAPH — {data.nodes.length} uzlů · {data.links.length} vztahů
        </div>
        <input
          value={search}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
          placeholder="Hledat v paměti…"
          style={{
            marginLeft: 'auto', background: '#0b1220', border: '1px solid #1a3050',
            borderRadius: 6, color: '#e2f0ff', padding: '4px 10px', fontSize: 11,
            outline: 'none', width: 200,
          }}
        />
        <button onClick={load} style={{
          background: '#0b1220', border: '1px solid #1a3050', borderRadius: 6,
          color: '#00d4ff', fontSize: 11, padding: '4px 10px', cursor: 'pointer',
        }}>↺</button>
      </div>

      {/* Legenda */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
        {Object.entries(GROUP_COLORS).map(([g, c]) => (
          <span key={g} style={{ fontSize: 10, color: '#475569', display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
            {g}
          </span>
        ))}
      </div>

      {/* SVG graf */}
      <div style={{ background: '#050a15', borderRadius: 8, border: '1px solid #1a3050', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>
            Načítám paměť…
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2d3748' }}>
            {search ? 'Nic nenalezeno' : 'Paměť je prázdná'}
          </div>
        ) : (
          <svg ref={svgRef} width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
            {/* Hrany */}
            {visLinks.map((l, i) => {
              const a = pos[l.source], b = pos[l.target]
              if (!a || !b) return null
              return (
                <line key={i}
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke="#1a3050" strokeWidth={1} strokeOpacity={0.7}
                />
              )
            })}
            {/* Uzly */}
            {filtered.map(n => {
              const p = pos[n.id]
              if (!p) return null
              const r   = 6 + n.importance * 10
              const col = color(n.group)
              const sel = selected?.id === n.id
              return (
                <g key={n.id}
                  onClick={() => setSelected(sel ? null : n)}
                  style={{ cursor: 'pointer' }}>
                  {sel && (
                    <circle cx={p.x} cy={p.y} r={r + 6}
                      fill="none" stroke={col} strokeWidth={1.5} strokeOpacity={0.5}
                      style={{ filter: `drop-shadow(0 0 6px ${col})` }}
                    />
                  )}
                  <circle cx={p.x} cy={p.y} r={r}
                    fill={col} fillOpacity={0.85}
                    style={{ filter: `drop-shadow(0 0 ${sel ? 10 : 4}px ${col})` }}
                  />
                  <text x={p.x} y={p.y + r + 11}
                    textAnchor="middle" fontSize={8} fill="#7ea8d4"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}>
                    {n.label.slice(0, 22)}{n.label.length > 22 ? '…' : ''}
                  </text>
                </g>
              )
            })}
          </svg>
        )}
      </div>

      {/* Detail vybraného uzlu */}
      {selected && (
        <div style={{ marginTop: 10, background: '#0b1220', border: `1px solid ${color(selected.group)}44`,
          borderRadius: 8, padding: '12px 14px' }}>
          <div style={{ color: color(selected.group), fontSize: 10, letterSpacing: '.1em', marginBottom: 6 }}>
            DETAIL VZPOMÍNKY
          </div>
          <div style={{ fontSize: 12, color: '#e2f0ff', marginBottom: 6 }}>{selected.label}</div>
          <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#475569' }}>
            <span>důležitost: <span style={{ color: '#00d4ff' }}>{selected.importance}</span></span>
            <span>skupina: <span style={{ color: color(selected.group) }}>{selected.group}</span></span>
            {selected.tags && selected.tags.length > 0 && (
              <span>tagy: {selected.tags.map(t => (
                <span key={t} style={{ background: '#1a3050', borderRadius: 3, padding: '1px 5px', marginLeft: 4 }}>{t}</span>
              ))}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
