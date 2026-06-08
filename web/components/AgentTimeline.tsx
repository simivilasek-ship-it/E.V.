'use client'

import { useEffect, useState } from 'react'
import { useJarvis } from '@/store/jarvis'
import { apiUrl } from '@/lib/api'

const STEP_COLORS: Record<string, string> = {
  plan:    'var(--purple)',
  route:   'var(--cyan)',
  execute: 'var(--green)',
  critic:  'var(--amber)',
  react:   'var(--blue)',
  done:    'var(--green)',
  error:   'var(--red)',
  answer:  'var(--cyan)',
}

const STEP_ICONS: Record<string, string> = {
  plan: '🧠', route: '🔀', execute: '⚡', critic: '🔍',
  react: '🔄', done: '✅', error: '❌', answer: '💬',
}

interface Step {
  type: string
  message: string
  status: string
  tool?: string
  detail?: string | object
  duration_ms?: number
}

interface Run {
  task: string
  agent_type: string
  status: string
  started_at: number | string
  duration_ms?: number
  steps?: Step[]
  answer?: string
}

interface StepNodeProps {
  step: Step
  index: number
  total: number
}

function StepNode({ step, index, total }: StepNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const col = STEP_COLORS[step.type] || 'var(--muted)'
  const durationMs = step.duration_ms ? `${Math.round(step.duration_ms)}ms` : ''

  return (
    <div style={{ display: 'flex', gap: 0, marginBottom: 0 }}>
      {/* Osa + tečka */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32, flexShrink: 0 }}>
        <div style={{
          width: 12, height: 12, borderRadius: '50%', background: col, flexShrink: 0,
          boxShadow: `0 0 8px color-mix(in srgb, ${col} 53%, transparent)`, marginTop: 10,
          border: step.status === 'running' ? `2px solid white` : 'none',
        }} />
        {index < total - 1 && (
          <div style={{ width: 2, flex: 1, background: `color-mix(in srgb, ${col} 27%, transparent)`, minHeight: 20 }} />
        )}
      </div>

      {/* Obsah */}
      <div
        onClick={() => step.detail && setExpanded(!expanded)}
        style={{
          flex: 1, background: 'var(--bg-hud)', border: `1px solid color-mix(in srgb, ${col} 20%, transparent)`,
          borderRadius: 6, padding: '8px 12px', marginLeft: 8, marginBottom: 6,
          cursor: step.detail ? 'pointer' : 'default',
          transition: 'border-color .2s',
        }}
        onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) =>
          step.detail && (e.currentTarget.style.borderColor = `color-mix(in srgb, ${col} 53%, transparent)`)}
        onMouseLeave={(e: React.MouseEvent<HTMLDivElement>) =>
          (e.currentTarget.style.borderColor = `color-mix(in srgb, ${col} 20%, transparent)`)}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 13 }}>{STEP_ICONS[step.type] || '•'}</span>
            <span style={{ fontSize: 11, color: col, letterSpacing: '.1em', textTransform: 'uppercase' }}>
              {step.type}
            </span>
            {step.tool && (
              <span style={{ fontSize: 10, color: 'var(--muted)', background: 'var(--bg-elevated)', borderRadius: 3, padding: '1px 6px' }}>
                {step.tool}
              </span>
            )}
          </div>
          <span style={{ fontSize: 10, color: 'var(--muted)' }}>{durationMs}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text)', marginTop: 4, lineHeight: 1.5 }}>
          {step.message}
        </div>
        {expanded && step.detail && (
          <div style={{
            marginTop: 6, padding: '6px 8px', background: 'var(--bg)', borderRadius: 4,
            fontSize: 11, color: 'var(--text2)', whiteSpace: 'pre-wrap', fontFamily: 'IBM Plex Mono, monospace',
          }}>
            {typeof step.detail === 'string' ? step.detail : JSON.stringify(step.detail, null, 2)}
          </div>
        )}
      </div>
    </div>
  )
}

interface RunCardProps {
  run: Run
}

function RunCard({ run }: RunCardProps) {
  const dur = run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : '—'
  const statusColor = run.status === 'done' ? 'var(--green)' : run.status === 'error' ? 'var(--red)' : 'var(--amber)'

  return (
    <div style={{ background: 'var(--bg-hud)', border: '1px solid var(--border-hud)', borderRadius: 8, padding: '14px 16px', marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500, marginBottom: 2 }}>
            {run.task}
          </div>
          <div style={{ fontSize: 10, color: 'var(--muted)' }}>
            {run.agent_type} · {new Date(run.started_at).toLocaleTimeString()} · {dur}
          </div>
        </div>
        <span style={{
          padding: '2px 8px', borderRadius: 3, fontSize: 10,
          background: `color-mix(in srgb, ${statusColor} 13%, transparent)`, color: statusColor,
        }}>
          {run.status?.toUpperCase()}
        </span>
      </div>
      {run.steps?.map((s, i) => (
        <StepNode key={i} step={s} index={i} total={run.steps!.length} />
      ))}
      {run.answer && (
        <div style={{
          marginTop: 8, padding: '8px 10px', background: 'var(--bg)', borderRadius: 6,
          fontSize: 12, color: 'var(--green)', borderLeft: '2px solid var(--green)',
        }}>
          {run.answer}
        </div>
      )}
    </div>
  )
}

export default function AgentTimeline() {
  const logs = useJarvis((s: { logs: Array<{ text?: string }> }) => s.logs)
  const [runs, setRuns] = useState<Run[]>([])
  const [live, setLive] = useState<Run | null>(null)  // probíhající run

  // Parsuj logy a WS eventy na timeline události
  useEffect(() => {
    const agentLogs = logs.filter((l: { text?: string }) =>
      l.text && (l.text.includes('[Graf]') || l.text.includes('ReAct') ||
                 l.text.includes('Plánuji') || l.text.includes('Executor') ||
                 l.text.includes('Critic') || l.text.includes('Router'))
    )
    if (!agentLogs.length) return

    // Seskup do runů podle timestamps
    const newLive: Run = {
      task: 'Probíhá…', agent_type: 'graf', status: 'running',
      started_at: Date.now(),
      steps: agentLogs.slice(-12).map((l: { text?: string }) => ({
        type: l.text!.includes('Plánuji') ? 'plan'
             : l.text!.includes('Router') ? 'route'
             : l.text!.includes('Executor') ? 'execute'
             : l.text!.includes('Critic') ? 'critic'
             : 'react',
        message: l.text!.replace(/\[.*?\]\s*/, '').slice(0, 120),
        status: 'done',
      })),
    }
    setLive(newLive)
  }, [logs])

  // Načti historii z API
  useEffect(() => {
    fetch(apiUrl('/api/agent/timeline')).then(r => r.json())
      .then((d: { runs?: Run[] }) => setRuns(d.runs || []))
      .catch(() => {})
  }, [])

  const allRuns: Run[] = [
    ...(live ? [live] : []),
    ...runs,
  ]

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <div style={{ color: 'var(--muted)', fontSize: 9, letterSpacing: '.15em' }}>
          AGENT TIMELINE — plán · kroky · akce · výsledky · kritika
        </div>
        {live && (
          <span style={{ fontSize: 10, color: 'var(--amber)', animation: 'pulse 1s infinite' }}>
            ● LIVE
          </span>
        )}
      </div>

      {allRuns.length === 0 ? (
        <div style={{
          background: 'var(--bg-hud)', border: '1px solid var(--border-hud)', borderRadius: 8,
          padding: '40px 20px', textAlign: 'center', color: 'var(--muted)', fontSize: 12,
        }}>
          Žádné agentní úlohy zatím.<br />
          <span style={{ fontSize: 11, marginTop: 6, display: 'block' }}>
            Zkus: „najdi ceny GPU a ulož je“ nebo „porovnej Python vs JavaScript“
          </span>
        </div>
      ) : (
        allRuns.map((r, i) => <RunCard key={i} run={r} />)
      )}
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    </div>
  )
}
