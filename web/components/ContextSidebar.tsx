'use client'
import { useState, useEffect } from 'react'

interface PcContext {
  active_window?: string
  windows?: string[]
  time?: string
  system?: {
    cpu?: number
    ram?: number
    disk?: number
    hostname?: string
    os?: string
  }
  error?: string
}

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8002'

function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.min(Math.max(value, 0), 100)
  const barColor = pct > 85 ? 'var(--red)' : pct > 65 ? 'var(--amber)' : color
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-[11px] font-mono">
        <span style={{ color: 'var(--muted)' }}>{label}</span>
        <span style={{ color: barColor }}>{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,.06)' }}>
        <div className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: barColor }} />
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-3.5 flex flex-col gap-2">
      <div className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

export default function ContextSidebar() {
  const [ctx, setCtx] = useState<PcContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastFetch, setLastFetch] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchContext = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/context`, { signal: AbortSignal.timeout(4000) })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data: PcContext = await r.json()
        if (!cancelled) { setCtx(data); setLastFetch(Date.now()); setLoading(false) }
      } catch {
        if (!cancelled) setLoading(false)
      }
    }
    fetchContext()
    const t = setInterval(fetchContext, 5000)
    return () => { cancelled = true; clearInterval(t) }
  }, [])

  const windows = (ctx?.windows ?? []).slice(0, 5)
  const sys = ctx?.system

  return (
    <aside
      className="flex flex-col h-full shrink-0 glass-panel overflow-hidden"
      style={{ width: 'var(--context-w)', borderLeft: '1px solid var(--border)' }}
    >
      <div className="shrink-0 px-4 py-3.5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
        <div>
          <div className="font-display text-sm font-semibold" style={{ color: 'var(--text)' }}>Kontext PC</div>
          <div className="text-[10px]" style={{ color: 'var(--muted)' }}>Live přehled</div>
        </div>
        {lastFetch && (
          <span className="w-2 h-2 rounded-full anim-pulse" style={{ background: 'var(--green)' }} />
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2.5">
        {loading && !ctx && (
          <div className="text-center py-8 text-xs" style={{ color: 'var(--muted)' }}>Načítám…</div>
        )}

        {ctx?.error && (
          <div className="card p-3 text-xs" style={{ color: 'var(--red)' }}>{ctx.error}</div>
        )}

        {ctx?.time && (
          <Section title="Čas">
            <div className="font-mono text-xs leading-relaxed" style={{ color: 'var(--accent-light)' }}>{ctx.time}</div>
          </Section>
        )}

        <Section title="Aktivní okno">
          <div className="text-xs leading-relaxed truncate" title={ctx?.active_window || '—'} style={{ color: 'var(--text)' }}>
            {ctx?.active_window || '—'}
          </div>
        </Section>

        {windows.length > 0 && (
          <Section title="Otevřená okna">
            <ul className="flex flex-col gap-1">
              {windows.map((w, i) => (
                <li key={i}
                  className="text-[11px] truncate px-2.5 py-1.5 rounded-lg"
                  style={{
                    background: i === 0 ? 'rgba(99,102,241,.08)' : 'rgba(255,255,255,.02)',
                    border: `1px solid ${i === 0 ? 'var(--border-accent)' : 'var(--border)'}`,
                    color: i === 0 ? 'var(--accent-light)' : 'var(--text-secondary)',
                  }}
                  title={w}>
                  {w}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {sys && (sys.cpu !== undefined || sys.ram !== undefined || sys.disk !== undefined) && (
          <Section title="Systém">
            <div className="flex flex-col gap-3">
              {sys.cpu !== undefined && <MetricBar label="CPU" value={sys.cpu} color="var(--accent-light)" />}
              {sys.ram !== undefined && <MetricBar label="RAM" value={sys.ram} color="var(--teal)" />}
              {sys.disk !== undefined && <MetricBar label="Disk" value={sys.disk} color="var(--purple)" />}
            </div>
            {sys.hostname && (
              <div className="font-mono text-[10px] pt-1 truncate" style={{ color: 'var(--muted)' }}>
                {sys.hostname}{sys.os ? ` · ${sys.os}` : ''}
              </div>
            )}
          </Section>
        )}

        {!loading && !ctx && (
          <div className="text-center py-6 text-xs" style={{ color: 'var(--muted)' }}>Backend nedostupný</div>
        )}
      </div>
    </aside>
  )
}
