'use client'
import { useEffect, useState } from 'react'

const ZONES: Record<string, string> = {
  'tokio': 'Asia/Tokyo', 'tokyo': 'Asia/Tokyo',
  'new york': 'America/New_York', 'new_york': 'America/New_York',
  'london': 'Europe/London', 'londyn': 'Europe/London',
  'berlin': 'Europe/Berlin', 'berlín': 'Europe/Berlin',
  'paris': 'Europe/Paris', 'pariz': 'Europe/Paris',
  'dubai': 'Asia/Dubai',
  'sydney': 'Australia/Sydney',
  'los angeles': 'America/Los_Angeles',
  'chicago': 'America/Chicago',
  'moscow': 'Europe/Moscow', 'moskva': 'Europe/Moscow',
  'beijing': 'Asia/Shanghai', 'peking': 'Asia/Shanghai',
}

function detectZone(query: string): [string, string] {
  const lq = query.toLowerCase()
  for (const [key, tz] of Object.entries(ZONES)) {
    if (lq.includes(key)) return [key.charAt(0).toUpperCase() + key.slice(1), tz]
  }
  return ['Praha', 'Europe/Prague']
}

export default function ClockWidget({ query }: { query: string }) {
  const [cityName, tz] = detectZone(query)
  const [time, setTime] = useState('')
  const [date, setDate] = useState('')

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      setTime(now.toLocaleTimeString('cs-CZ', { timeZone: tz, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
      setDate(now.toLocaleDateString('cs-CZ', { timeZone: tz, weekday: 'long', day: 'numeric', month: 'long' }))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [tz])

  return (
    <div className="py-3 flex items-center gap-6">
      <div>
        <div className="font-hud text-[10px] tracking-widest mb-1" style={{ color: 'var(--muted)' }}>
          🕐 {cityName.toUpperCase()}
        </div>
        <div className="font-mono text-4xl font-bold tracking-tight" style={{ color: 'var(--cyan)', textShadow: '0 0 20px rgba(0,200,255,.4)' }}>
          {time}
        </div>
        <div className="font-mono text-xs mt-1 capitalize" style={{ color: 'var(--muted)' }}>
          {date}
        </div>
      </div>
    </div>
  )
}
