import { useEffect, useState } from 'react'

const API = import.meta.env.PROD
  ? `${window.location.protocol}//${window.location.host}`
  : 'http://localhost:8002'

function MissionCard({ mission, onToggle }) {
  const progress = mission.progress || 0
  const col = progress === 100 ? '#10b981' : '#00d4ff'

  return (
    <div style={{
      background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8,
      padding: '14px 16px', marginBottom: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 14, color: '#e2f0ff', fontWeight: 600 }}>{mission.title}</div>
        <span style={{
          fontSize: 10, color: col, background: `${col}22`,
          padding: '2px 8px', borderRadius: 3, letterSpacing: '.08em',
        }}>
          {mission.done_count}/{mission.total_count}
        </span>
      </div>

      <div style={{ height: 3, background: '#1a3050', borderRadius: 2, marginBottom: 12 }}>
        <div style={{ width: `${progress}%`, height: '100%', background: col, borderRadius: 2, transition: 'width .4s' }} />
      </div>

      {mission.items?.map(item => (
        <div
          key={item.id}
          onClick={() => onToggle(mission.id, item.id)}
          style={{
            display: 'flex', gap: 10, alignItems: 'center', padding: '6px 0',
            cursor: 'pointer', borderBottom: '1px solid #0b1220',
          }}
        >
          <span style={{
            width: 18, height: 18, borderRadius: 3, flexShrink: 0,
            border: `1.5px solid ${item.done ? '#10b981' : '#1a3050'}`,
            background: item.done ? '#10b98122' : 'transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, color: '#10b981',
          }}>
            {item.done ? '✓' : ''}
          </span>
          <span style={{
            fontSize: 13, color: item.done ? '#475569' : '#e2f0ff',
            textDecoration: item.done ? 'line-through' : 'none',
          }}>
            {item.label}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function MissionControl() {
  const [missions, setMissions] = useState([])
  const [newTitle, setNewTitle] = useState('')

  const refresh = () => {
    fetch(`${API}/api/missions`).then(r => r.json())
      .then(d => setMissions(d.missions || []))
      .catch(() => {})
  }

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 10000)
    return () => clearInterval(iv)
  }, [])

  const toggle = (missionId, itemId) => {
    fetch(`${API}/api/missions/${missionId}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId }),
    }).then(() => refresh()).catch(() => {})
  }

  const create = () => {
    if (!newTitle.trim()) return
    fetch(`${API}/api/missions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    }).then(() => { setNewTitle(''); refresh() }).catch(() => {})
  }

  return (
    <div style={{ maxWidth: 600, width: '100%' }}>
      <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 12 }}>
        MISSION CONTROL
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && create()}
          placeholder="Nová mise, např. Release v6.0"
          style={{
            flex: 1, background: '#050a15', border: '1px solid #1a3050',
            borderRadius: 5, padding: '8px 12px', color: '#e2f0ff', fontSize: 12, outline: 'none',
          }}
        />
        <button onClick={create} style={{
          padding: '8px 14px', background: '#00d4ff22', border: '1px solid #00d4ff55',
          borderRadius: 5, color: '#00d4ff', fontSize: 11, cursor: 'pointer',
        }}>+ MISE</button>
      </div>

      {missions.length === 0
        ? <div style={{ color: '#2d3748', fontSize: 12 }}>Žádné aktivní mise</div>
        : missions.map(m => <MissionCard key={m.id} mission={m} onToggle={toggle} />)
      }
    </div>
  )
}
