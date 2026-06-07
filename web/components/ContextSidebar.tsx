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

const API_BASE =
  process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8002'

function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.min(Math.max(value, 0), 100)
  const barColor = pct > 85 ? 'var(--red)' : pct > 65 ? 'var(--amber)' : color
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between font-mono text-[9px]">
        <span style={{ color: 'var(--muted)' }}>{label}</span>
        <span style={{ color: barColor }}>{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,.06)' }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: barColor, boxShadow: `0 0 6px ${barColor}` }}
        />
      </div>
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
        if (!cancelled) {
          setCtx(data)
          setLastFetch(Date.now())
          setLoading(false)
        }
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
      className="flex flex-col h-full shrink-0 overflow-hidden"
      style={{
        width: 240,
        background: 'rgba(4,9,16,.88)',
        borderLeft: '1px solid var(--border2)',
        backdropFilter: 'blur(20px)',
      }}
    >
      <div className="shrink-0 px-4 py-3 flex items-center justify-between"
        style={{ borderBottom: '1px solid var(--border2)' }}>
        <span className="font-hud text-[8px] tracking-[.2em]" style={{ color: 'var(--muted)' }}>
          KONTEXT PC
        </span>
        {lastFetch && (
          <span className="w-1.5 h-1.5 rounded-full anim-pulse" style={{ background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {loading && !ctx && (
          <div className="font-mono text-[10px] text-center py-6" style={{ color: 'var(--muted)' }}>
            Načítám kontext…
          </div>
        )}

        {ctx?.error && (
          <div className="card p-3 font-mono text-[10px]" style={{ color: 'var(--red)' }}>
            {ctx.error}
          </div>
        )}

        {/* Time */}
        {ctx?.time && (
          <div className="card p-3">
            <div className="font-hud text-[8px] tracking-[.15em] mb-1.5" style={{ color: 'var(--muted)' }}>
              ČAS
            </div>
            <div className="font-mono text-[11px] leading-relaxed" style={{ color: 'var(--cyan)' }}>
              {ctx.time}
            </div>
          </div>
        )}

        {/* Active window */}
        <div className="card p-3">
          <div className="font-hud text-[8px] tracking-[.15em] mb-1.5" style={{ color: 'var(--muted)' }}>
            AKTIVNÍ OKNO
          </div>
          <div className="font-mono text-[11px] leading-relaxed truncate" style={{ color: 'var(--text)' }}
            title={ctx?.active_window || '—'}>
            {ctx?.active_window || '—'}
          </div>
        </div>

        {/* Windows list */}
        {windows.length > 0 && (
          <div className="card p-3">
            <div className="font-hud text-[8px] tracking-[.15em] mb-2" style={{ color: 'var(--muted)' }}>
              OKNA
            </div>
            <ul className="flex flex-col gap-1.5">
              {windows.map((w, i) => (
                <li key={i} className="font-mono text-[10px] leading-snug truncate px-2 py-1 rounded-md"
                  style={{
                    background: i === 0 ? 'rgba(0,200,255,.06)' : 'rgba(255,255,255,.02)',
                    border: `1px solid ${i === 0 ? 'rgba(0,200,255,.12)' : 'rgba(255,255,255,.04)'}`,
                    color: i === 0 ? 'var(--cyan)' : 'var(--muted)',
                  }}
                  title={w}>
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* System metrics */}
        {sys && (sys.cpu !== undefined || sys.ram !== undefined || sys.disk !== undefined) && (
          <div className="card p-3 flex flex-col gap-2.5">
            <div className="font-hud text-[8px] tracking-[.15em]" style={{ color: 'var(--muted)' }}>
              SYSTÉM
            </div>
            {sys.cpu !== undefined && <MetricBar label="CPU" value={sys.cpu} color="var(--cyan)" />}
            {sys.ram !== undefined && <MetricBar label="RAM" value={sys.ram} color="var(--teal)" />}
            {sys.disk !== undefined && <MetricBar label="DISK" value={sys.disk} color="var(--purple)" />}
            {sys.hostname && (
              <div className="font-mono text-[9px] pt-1 truncate" style={{ color: 'var(--muted)' }}>
                {sys.hostname}
              </div>
            )}
          </div>
        )}

        {!loading && !ctx && (
          <div className="font-mono text-[10px] text-center py-4" style={{ color: 'var(--muted)' }}>
            Backend nedostupný
          </div>
        )}
      </div>
    </aside>
  )
}
