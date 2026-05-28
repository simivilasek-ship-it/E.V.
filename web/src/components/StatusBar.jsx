import { useAppStore } from '../store/appStore'

export default function StatusBar() {
  const { ollama, model, cpu, ram, disk, connected } = useAppStore()
  const dot = (ok) => (
    <span style={{
      display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
      background: ok ? '#10b981' : '#ef4444', marginRight: 5,
    }} />
  )
  const bar = (v, warn=75, danger=90) => {
    const color = v > danger ? '#ef4444' : v > warn ? '#fbbf24' : '#00d4ff'
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ width: 60, height: 3, background: '#1a3050', borderRadius: 2 }}>
          <div style={{ width: `${v}%`, height: '100%', background: color, borderRadius: 2, transition: 'width .5s' }} />
        </div>
        <span style={{ fontSize: 10, color: '#7ea8d4', minWidth: 32 }}>{v}%</span>
      </div>
    )
  }

  return (
    <header style={{
      background: '#0b1220', borderBottom: '1px solid #1a3050',
      padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 20,
      fontFamily: 'Courier New, monospace',
    }}>
      <span style={{ color: '#00d4ff', fontWeight: 'bold', letterSpacing: 4, fontSize: 14 }}>
        J A R V I S
      </span>
      <span style={{ fontSize: 11, color: '#7ea8d4' }}>
        {dot(ollama)} Ollama · {model}
      </span>
      <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#475569' }}>
        <span>CPU {bar(cpu)}</span>
        <span>RAM {bar(ram)}</span>
        <span>Disk {bar(disk, 80, 95)}</span>
      </div>
      <a href="http://localhost:8002" target="_blank" style={{ marginLeft: 'auto', fontSize: 10, color: '#475569', textDecoration: 'none' }}>
        dashboard ↗
      </a>
    </header>
  )
}
