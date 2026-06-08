'use client'

import { useEffect, useState } from 'react'
import { apiUrl } from '@/lib/api'

interface ChecklistItem { id: string; label: string; done: boolean }
interface Mission {
  id: string
  title: string
  progress: number
  done_count: number
  total_count: number
  items: ChecklistItem[]
}

export default function MissionChecklist() {
  const [missions, setMissions] = useState<Mission[]>([])
  const [newTitle, setNewTitle] = useState('')

  const refresh = () => {
    fetch(apiUrl('/api/missions/checklist'))
      .then(r => r.json())
      .then(d => setMissions(d.missions || []))
      .catch(() => {})
  }

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 10000)
    return () => clearInterval(iv)
  }, [])

  const toggle = (missionId: string, itemId: string) => {
    fetch(apiUrl(`/api/missions/checklist/${missionId}/toggle`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId }),
    }).then(() => refresh()).catch(() => {})
  }

  const create = () => {
    if (!newTitle.trim()) return
    fetch(apiUrl('/api/missions/checklist'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    }).then(() => { setNewTitle(''); refresh() }).catch(() => {})
  }

  return (
    <div className="w-full max-w-xl font-mono">
      <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>Mission Control — checklist</div>

      <div className="flex gap-2 mb-4">
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && create()}
          placeholder="Nová mise, např. Release v6.0"
          className="flex-1 bg-transparent border rounded px-3 py-2 text-sm outline-none"
          style={{ borderColor: 'var(--border)' }}
        />
        <button onClick={create} className="btn-primary text-xs px-3">+ Mise</button>
      </div>

      {missions.length === 0 ? (
        <div className="text-sm" style={{ color: 'var(--muted)' }}>Žádné aktivní mise</div>
      ) : missions.map(m => (
        <div key={m.id} className="card p-4 mb-3">
          <div className="flex justify-between items-center mb-2">
            <div className="font-semibold">{m.title}</div>
            <span className="text-[10px] px-2 py-0.5 rounded" style={{ color: 'var(--cyan)', background: 'rgba(0,212,255,.1)' }}>
              {m.done_count}/{m.total_count}
            </span>
          </div>
          <div className="h-1 rounded mb-3" style={{ background: 'var(--border)' }}>
            <div className="h-full rounded transition-all" style={{ width: `${m.progress}%`, background: 'var(--cyan)' }} />
          </div>
          {m.items?.map(item => (
            <div
              key={item.id}
              onClick={() => toggle(m.id, item.id)}
              className="flex gap-3 items-center py-1.5 cursor-pointer border-b"
              style={{ borderColor: 'var(--border)' }}
            >
              <span
                className="w-4 h-4 rounded border flex items-center justify-center text-[10px] shrink-0"
                style={{
                  borderColor: item.done ? 'var(--green)' : 'var(--border)',
                  color: 'var(--green)',
                  background: item.done ? 'rgba(16,185,129,.15)' : 'transparent',
                }}
              >{item.done ? '✓' : ''}</span>
              <span className={item.done ? 'line-through opacity-50' : ''}>{item.label}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
