'use client'
import { useEffect, useRef, useState } from 'react'

interface Metrics { cpu: number; ram: number; disk: number; cpu_temp: number | null; gpu: { usage: number | null; name: string | null } | null }

function MiniBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value))
  const warn = pct > 90 ? '#f43f5e' : pct > 75 ? '#f59e0b' : color
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] w-10 shrink-0" style={{ color: 'var(--muted)' }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,.06)' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: warn, boxShadow: `0 0 6px ${warn}` }}/>
      </div>
      <span className="font-mono text-xs w-10 text-right" style={{ color: warn }}>{pct}%</span>
    </div>
  )
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null
  const W = 120, H = 28
  const max = Math.max(...data, 1)
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * W},${H - (v / max) * (H - 2) - 1}`).join(' ')
  return (
    <svg width={W} height={H} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ filter: `drop-shadow(0 0 3px ${color})` }}/>
    </svg>
  )
}

export default function SystemWidget() {
  const [metrics, setMetrics] = useState<Metrics>({ cpu: 0, ram: 0, disk: 0, cpu_temp: null, gpu: null })
  const [cpuHist, setCpuHist] = useState<number[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8002/ws/agents')
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.type === 'metrics') {
          setMetrics({ cpu: d.cpu, ram: d.ram, disk: d.disk, cpu_temp: d.cpu_temp ?? null, gpu: d.gpu ?? null })
          setCpuHist(h => [...h.slice(-29), d.cpu])
        }
      } catch {}
    }
    return () => ws.close()
  }, [])

  return (
    <div className="py-2 flex flex-col gap-2.5">
      <MiniBar label="CPU" value={metrics.cpu} color="var(--cyan)" />
      <MiniBar label="RAM" value={metrics.ram} color="var(--purple)" />
      <MiniBar label="Disk" value={metrics.disk} color="var(--green)" />
      {metrics.gpu?.usage != null && <MiniBar label="GPU" value={metrics.gpu.usage} color="var(--amber)" />}

      {cpuHist.length > 3 && (
        <div className="flex items-center gap-3 mt-1">
          <span className="font-hud text-[8px] tracking-widest" style={{ color: 'var(--muted)' }}>CPU HISTORY</span>
          <Sparkline data={cpuHist} color="var(--cyan)" />
          {metrics.cpu_temp != null && (
            <span className="font-mono text-xs ml-auto" style={{ color: metrics.cpu_temp > 85 ? 'var(--red)' : 'var(--muted)' }}>
              🌡️ {metrics.cpu_temp}°C
            </span>
          )}
        </div>
      )}
      {metrics.gpu?.name && (
        <div className="font-mono text-[10px]" style={{ color: 'var(--muted)' }}>{metrics.gpu.name}</div>
      )}
    </div>
  )
}
