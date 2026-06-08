'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiUrl } from '@/lib/api'

type AgentMode = 'single' | 'multi' | 'parallel'

interface MissionStep {
  id: string
  description: string
  due_date?: string | null
  status: string
  result?: string | null
  attempts: number
}

interface Mission {
  id: string
  title: string
  description: string
  deadline?: string | null
  status: string
  agent_mode?: AgentMode
  steps: MissionStep[]
}

const MODE_LABELS: Record<AgentMode, string> = {
  single: 'Single (ReAct)',
  multi: 'Multi-agent',
  parallel: 'Multi parallel',
}

export default function MissionPanel() {
  const [missions, setMissions] = useState<Mission[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [deadline, setDeadline] = useState('')
  const [agentMode, setAgentMode] = useState<AgentMode>('multi')
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    try {
      const r = await fetch(apiUrl('/api/missions'))
      const d = await r.json()
      setMissions(Array.isArray(d.missions) ? d.missions : [])
    } catch {
      setMissions([])
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function createMission() {
    if (!title.trim()) return
    setLoading(true)
    setMsg('')
    try {
      const r = await fetch(apiUrl('/api/missions'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          deadline: deadline || null,
          agent_mode: agentMode,
        }),
      })
      const d = await r.json()
      if (d.ok) {
        setMsg('Mise vytvořena ✓')
        setTitle('')
        setDescription('')
        setDeadline('')
        load()
      } else {
        setMsg(d.error || 'Chyba')
      }
    } catch {
      setMsg('API nedostupné')
    } finally {
      setLoading(false)
    }
  }

  async function missionAction(id: string, action: 'pause' | 'resume' | 'delete') {
    const method = action === 'delete' ? 'DELETE' : 'PUT'
    const path = action === 'delete'
      ? `/api/missions/${id}`
      : `/api/missions/${id}/${action}`
    await fetch(apiUrl(path), { method })
    load()
  }

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="card p-5 flex flex-col gap-3">
        <h3 className="font-hud text-[9px] tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
          Autonomní mise — LLM plánování
        </h3>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Název mise"
          className="text-sm px-3 py-2 rounded-lg font-mono w-full"
          style={{ background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Popis — co má JARVIS dlouhodobě splnit"
          rows={3}
          className="text-sm px-3 py-2 rounded-lg font-mono w-full resize-y"
          style={{ background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />
        <div className="flex gap-2 flex-wrap items-center">
          <input
            type="date"
            value={deadline}
            onChange={e => setDeadline(e.target.value)}
            className="text-sm px-3 py-2 rounded-lg font-mono"
            style={{ background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)', color: 'var(--text)' }}
          />
          <select
            value={agentMode}
            onChange={e => setAgentMode(e.target.value as AgentMode)}
            className="text-sm px-3 py-2 rounded-lg font-mono"
            style={{ background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)', color: 'var(--cyan)' }}
          >
            {(Object.keys(MODE_LABELS) as AgentMode[]).map(m => (
              <option key={m} value={m}>{MODE_LABELS[m]}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={createMission}
            disabled={loading}
            className="px-4 py-2 rounded-lg text-xs font-hud"
            style={{ background: 'rgba(0,200,255,.12)', border: '1px solid var(--cyan)', color: 'var(--cyan)' }}
          >
            Vytvořit misi
          </button>
        </div>
        {msg && <p className="text-xs font-mono" style={{ color: 'var(--muted)' }}>{msg}</p>}
      </div>

      {missions.map(m => {
        const done = m.steps.filter(s => s.status === 'done').length
        const total = m.steps.length
        const pct = total ? Math.round((done / total) * 100) : 0
        return (
          <div key={m.id} className="card p-5 flex flex-col gap-3">
            <div className="flex justify-between items-start gap-2 flex-wrap">
              <div>
                <div className="font-mono text-sm" style={{ color: 'var(--text)' }}>{m.title}</div>
                <div className="text-[10px] font-mono mt-1" style={{ color: 'var(--muted)' }}>
                  {m.status} · {MODE_LABELS[m.agent_mode || 'single']} · {m.id}
                </div>
              </div>
              <div className="flex gap-1">
                {m.status === 'active' && (
                  <button type="button" onClick={() => missionAction(m.id, 'pause')} className="text-[10px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>Pause</button>
                )}
                {m.status === 'paused' && (
                  <button type="button" onClick={() => missionAction(m.id, 'resume')} className="text-[10px] px-2 py-1 rounded border" style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }}>Resume</button>
                )}
                <button type="button" onClick={() => missionAction(m.id, 'delete')} className="text-[10px] px-2 py-1 rounded border" style={{ borderColor: 'var(--red)', color: 'var(--red)' }}>Smazat</button>
              </div>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,.06)' }}>
              <div className="h-full transition-all" style={{ width: `${pct}%`, background: 'var(--cyan)' }} />
            </div>
            <div className="text-[10px] font-mono" style={{ color: 'var(--muted)' }}>{done}/{total} kroků ({pct}%)</div>
            <div className="flex flex-col gap-1">
              {m.steps.map(s => (
                <div key={s.id} className="text-[11px] font-mono px-2 py-1.5 rounded flex gap-2" style={{ background: 'rgba(255,255,255,.03)', border: '1px solid var(--border2)' }}>
                  <span style={{ color: s.status === 'done' ? 'var(--green)' : s.status === 'running' ? 'var(--cyan)' : 'var(--muted)', minWidth: 52 }}>{s.status}</span>
                  <span style={{ color: 'var(--text)' }}>{s.description}</span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
