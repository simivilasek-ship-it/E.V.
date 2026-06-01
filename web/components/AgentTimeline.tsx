'use client'

import { useEffect, useState } from 'react'
import { useJarvis } from '@/store/jarvis'

const API = ''

const STEP_COLORS: Record<string, string> = {
  plan:    '#8b5cf6',
  route:   '#00d4ff',
  execute: '#10b981',
  critic:  '#f59e0b',
  react:   '#3b82f6',
  done:    '#10b981',
  error:   '#ef4444',
  answer:  '#00d4ff',
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
  const col = STEP_COLORS[step.type] || '#4a6a8a'
  const durationMs = step.duration_ms ? `${Math.round(step.duration_ms)}ms` : ''

  return (
    <div style={{ display: 'flex', gap: 0, marginBottom: 0 }}>
      {/* Osa + tečka */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32, flexShrink: 0 }}>
        <div style={{
          width: 12, height: 12, borderRadius: '50%', background: col, flexShrink: 0,
          boxShadow: `0 0 8px ${col}88`, marginTop: 10,
          border: step.status === 'running' ? `2px solid white` : 'none',
        }} />
        {index < total - 1 && (
          <div style={{ width: 2, flex: 1, background: `${col}44`, minHeight: 20 }} />
        )}
      </div>

      {/* Obsah */}
      <div
        onClick={() => step.detail && setExpanded(!expanded)}
        style={{
          flex: 1, background: '#0b1220', border: `1px solid ${col}33`,
          borderRadius: 6, padding: '8px 12px', marginLeft: 8, marginBottom: 6,
          cursor: step.detail ? 'pointer' : 'default',
          transition: 'border-color .2s',
        }}
        onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) =>
          step.detail && (e.currentTarget.style.borderColor = col + '88')}
        onMouseLeave={(e: React.MouseEvent<HTMLDivElement>) =>
          (e.currentTarget.style.borderColor = col + '33')}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 13 }}>{STEP_ICONS[step.type] || '•'}</span>
            <span style={{ fontSize: 11, color: col, letterSpacing: '.1em', textTransform: 'uppercase' }}>
              {step.type}
            </span>
            {step.tool && (
              <span style={{ fontSize: 10, color: '#475569', background: '#1a3050', borderRadius: 3, padding: '1px 6px' }}>
                {step.tool}
              </span>
            )}
          </div>
          <span style={{ fontSize: 10, color: '#2d3748' }}>{durationMs}</span>
        </div>
        <div style={{ fontSize: 12, color: '#e2f0ff', marginTop: 4, lineHeight: 1.5 }}>
          {step.message}
        </div>
        {expanded && step.detail && (
          <div style={{
            marginTop: 6, padding: '6px 8px', background: '#050a15', borderRadius: 4,
            fontSize: 11, color: '#7ea8d4', whiteSpace: 'pre-wrap', fontFamily: 'monospace',
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
  const statusColor = run.status === 'done' ? '#10b981' : run.status === 'error' ? '#ef4444' : '#fbbf24'

  return (
    <div style={{ background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8, padding: '14px 16px', marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 13, color: '#e2f0ff', fontWeight: 500, marginBottom: 2 }}>
            {run.task}
          </div>
          <div style={{ fontSize: 10, color: '#475569' }}>
            {run.agent_type} · {new Date(run.started_at).toLocaleTimeString()} · {dur}
          </div>
        </div>
        <span style={{
          padding: '2px 8px', borderRadius: 3, fontSize: 10,
          background: statusColor + '22', color: statusColor,
        }}>
          {run.status?.toUpperCase()}
        </span>
      </div>
      {run.steps?.map((s, i) => (
        <StepNode key={i} step={s} index={i} total={run.steps!.length} />
      ))}
      {run.answer && (
        <div style={{
          marginTop: 8, padding: '8px 10px', background: '#050a15', borderRadius: 6,
          fontSize: 12, color: '#10b981', borderLeft: '2px solid #10b981',
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
    fetch(`${API}/api/agent/timeline`).then(r => r.json())
      .then((d: { runs?: Run[] }) => setRuns(d.runs || []))
      .catch(() => {})
  }, [])

  const allRuns: Run[] = [
    ...(live ? [live] : []),
    ...runs,
  ]

  return (
    <div style={{ fontFamily: 'var(--font-mono,monospace)', color: '#e2f0ff' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em' }}>
          AGENT TIMELINE — plán · kroky · akce · výsledky · kritika
        </div>
        {live && (
          <span style={{ fontSize: 10, color: '#fbbf24', animation: 'pulse 1s infinite' }}>
            ● LIVE
          </span>
        )}
      </div>

      {allRuns.length === 0 ? (
        <div style={{
          background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8,
          padding: '40px 20px', textAlign: 'center', color: '#2d3748', fontSize: 12,
        }}>
          Žádné agentní úlohy zatím.<br />
          <span style={{ fontSize: 11, marginTop: 6, display: 'block' }}>
            Zkus: „najdi ceny GPU a ulož je" nebo „porovnej Python vs JavaScript"
          </span>
        </div>
      ) : (
        allRuns.map((r, i) => <RunCard key={i} run={r} />)
      )}
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    </div>
  )
}
