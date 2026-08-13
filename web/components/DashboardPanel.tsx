'use client'
import { useEffect, useState, useCallback } from 'react'
import { useEV } from '@/store/ev'
import { apiUrl } from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────
interface BackgroundJob {
  name: string
  next_run: string
  last_run?: string
  runs: number
  errors?: number
}

interface AuditEntry {
  ts: string
  action: string
  approved?: boolean
  permission?: string
  result?: string
}

interface DashData {
  jobs?: BackgroundJob[]
  audit?: AuditEntry[]
  summary?: string
}

// ── Stat card ─────────────────────────────────────────────────────────────
function StatCard({ label, value, unit, color, max = 100 }: {
  label: string; value: number; unit?: string; color: string; max?: number
}) {
  const pct = Math.min((value / max) * 100, 100)
  const displayColor = value > 85 ? 'var(--red)' : value > 65 ? 'var(--amber)' : color

  return (
    <div className="panel" style={{ padding: '16px 20px', flex: 1, minWidth: 130 }}>
      <div className="panel-title" style={{ marginBottom: 12 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 28, fontWeight: 600, color: displayColor, lineHeight: 1 }}>
          {value.toFixed(1)}
        </span>
        {unit && <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: 'var(--muted)' }}>{unit}</span>}
      </div>
      <div style={{ marginTop: 10, height: 3, borderRadius: 2, background: 'rgba(255,255,255,.06)' }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${pct}%`,
          background: displayColor,
          boxShadow: `0 0 6px ${displayColor}`,
          transition: 'width 0.6s ease, background 0.3s',
        }} />
      </div>
    </div>
  )
}

// ── Agent badge ───────────────────────────────────────────────────────────
function AgentBadge({ name, status }: { name: string; status: string }) {
  const statusColor = status === 'ok' || status === 'running' ? 'var(--green)'
    : status === 'error' ? 'var(--red)' : 'var(--amber)'
  return (
    <span className="metric-badge" style={{ color: statusColor, borderColor: `${statusColor}33` }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: statusColor, flexShrink: 0 }} />
      {name}
    </span>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
export default function DashboardPanel() {
  const system  = useEV(s => s.system)
  const agents  = useEV(s => s.agents)

  const [data, setData]       = useState<DashData>({})
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const [jobsRes, auditRes] = await Promise.allSettled([
        fetch(apiUrl('/api/scheduler/jobs')),
        fetch(apiUrl('/api/audit?limit=20')),
      ])
      const jobs  = jobsRes.status  === 'fulfilled' && jobsRes.value.ok  ? await jobsRes.value.json()  : []
      const audit = auditRes.status === 'fulfilled' && auditRes.value.ok ? await auditRes.value.json() : []
      setData({ jobs: Array.isArray(jobs) ? jobs : jobs.jobs ?? [], audit: Array.isArray(audit) ? audit : audit.entries ?? [] })
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backend offline')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const t = setInterval(fetchData, 30_000)
    return () => clearInterval(t)
  }, [fetchData])

  const fetchSummary = async () => {
    setSummaryLoading(true)
    try {
      const r = await fetch(apiUrl('/api/activity/report?format=md'))
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      setData(prev => ({ ...prev, summary: d.markdown || d.summary_text || 'Žádná aktivita dnes.' }))
    } catch (e) {
      setData(prev => ({ ...prev, summary: `⚠ ${e instanceof Error ? e.message : 'error'}` }))
    } finally {
      setSummaryLoading(false)
    }
  }

  const cpu  = system?.cpu  ?? 0
  const ram  = system?.ram  ?? 0
  const disk = system?.disk ?? 0
  const load = system?.load ?? 0

  const SectionHead = ({ title, action }: { title: string; action?: React.ReactNode }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
      <span className="panel-title">{title}</span>
      {action}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* ── System metrics ─────────────────────────────────── */}
      <div>
        <SectionHead title="System Metrics" />
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <StatCard label="CPU"  value={cpu}  unit="%" color="var(--metric-cpu)"  />
          <StatCard label="RAM"  value={ram}  unit="%" color="var(--metric-ram)"  />
          <StatCard label="DISK" value={disk} unit="%" color="var(--metric-disk)" />
          <StatCard label="LOAD" value={load} unit=""  color="var(--metric-load)" max={8} />
        </div>
      </div>

      {/* ── Monitoring agents ──────────────────────────────── */}
      {agents && Object.keys(agents).length > 0 && (
        <div>
          <SectionHead title="Monitoring Agents" />
          <div className="panel" style={{ padding: '10px 14px', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {Object.entries(agents).map(([name, st]: [string, unknown]) => (
              <AgentBadge key={name} name={name} status={String((st as {status?: string})?.status ?? 'ok')} />
            ))}
            {Object.keys(agents).length === 0 && (
              <span style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>No agents running</span>
            )}
          </div>
        </div>
      )}

      {/* ── Work summary ───────────────────────────────────── */}
      <div>
        <SectionHead
          title="Work Timeline (Dnes)"
          action={
            <button
              className="btn-hud"
              onClick={fetchSummary}
              disabled={summaryLoading}
            >
              {summaryLoading ? '⏳' : '↻'} {summaryLoading ? 'Načítám…' : 'Shrnutí (Alt+D)'}
            </button>
          }
        />
        {data.summary ? (
          <div className="panel" style={{ padding: '12px 14px', fontSize: 12, color: 'var(--text2)', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
            {data.summary}
          </div>
        ) : (
          <div className="panel" style={{ padding: '12px 14px', fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>
            Klikni na „Shrnutí" nebo stiskni Alt+D
          </div>
        )}
      </div>

      {/* ── Background jobs ────────────────────────────────── */}
      <div>
        <SectionHead title="Background Jobs" />
        <div className="panel" style={{ overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: 24, textAlign: 'center' }}>
              <div className="skeleton" style={{ height: 12, margin: '0 auto', maxWidth: 200 }} />
            </div>
          ) : error ? (
            <div style={{ padding: 16, fontSize: 12, color: 'var(--amber)' }}>⚠ {error}</div>
          ) : (data.jobs ?? []).length === 0 ? (
            <div style={{ padding: 16, fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>No scheduled jobs</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-hud)' }}>
                  {['JOB', 'NEXT RUN', 'LAST RUN', 'RUNS', 'ERRORS'].map(h => (
                    <th key={h} className="panel-title" style={{ padding: '6px 12px', textAlign: 'left', fontWeight: 400 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data.jobs ?? []).map((job, i) => (
                  <tr key={job.name} style={{ borderBottom: i < (data.jobs!.length - 1) ? '1px solid var(--border)' : 'none' }}>
                    <td style={{ padding: '7px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--text)' }}>{job.name}</td>
                    <td style={{ padding: '7px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--cyan)' }}>{job.next_run}</td>
                    <td style={{ padding: '7px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--text2)' }}>{job.last_run ?? '—'}</td>
                    <td style={{ padding: '7px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--text2)', textAlign: 'right' }}>{job.runs}</td>
                    <td style={{ padding: '7px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: (job.errors ?? 0) > 0 ? 'var(--red)' : 'var(--muted)', textAlign: 'right' }}>
                      {job.errors ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Audit log ──────────────────────────────────────── */}
      <div>
        <SectionHead title="Audit Log (Poslední akce)" />
        <div className="panel" style={{ overflow: 'hidden', maxHeight: 280 }}>
          {(data.audit ?? []).length === 0 ? (
            <div style={{ padding: 16, fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>No audit entries</div>
          ) : (
            <div style={{ overflowY: 'auto', maxHeight: 280 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-hud)', zIndex: 1 }}>
                  <tr style={{ borderBottom: '1px solid var(--border-hud)' }}>
                    {['TIME', 'ACTION', 'STATUS', 'PERMISSION', 'RESULT'].map(h => (
                      <th key={h} className="panel-title" style={{ padding: '6px 12px', textAlign: 'left', fontWeight: 400 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.audit ?? []).map((entry, i) => {
                    const approved = entry.approved
                    const statusColor = approved === true ? 'var(--green)' : approved === false ? 'var(--red)' : 'var(--muted)'
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '6px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{entry.ts}</td>
                        <td style={{ padding: '6px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--text)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{entry.action}</td>
                        <td style={{ padding: '6px 12px' }}>
                          <span className="metric-badge" style={{ color: statusColor, borderColor: `${statusColor}33` }}>
                            {approved === true ? 'OK' : approved === false ? 'DENIED' : '—'}
                          </span>
                        </td>
                        <td style={{ padding: '6px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: 'var(--text2)' }}>{entry.permission ?? '—'}</td>
                        <td style={{ padding: '6px 12px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: 'var(--text2)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{entry.result ?? ''}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
