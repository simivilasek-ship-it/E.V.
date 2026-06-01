'use client'
import { useEffect, useState } from 'react'

interface WeatherData {
  name: string; country: string
  temp: number; feels: number
  desc: string; emoji: string
  humidity: number; wind: number
  precip?: number
}

const WMO: Record<number, [string, string]> = {
  0:[' ☀️','Jasno'], 1:['🌤️','Převážně jasno'], 2:['⛅','Polojasno'], 3:['☁️','Zataženo'],
  45:['🌫️','Mlha'], 51:['🌦️','Mrholení'], 61:['🌧️','Déšť'], 63:['🌧️','Déšť'],
  65:['🌧️','Silný déšť'], 71:['🌨️','Sníh'], 80:['🌦️','Přeháňky'], 95:['⛈️','Bouřka'],
}

export default function WeatherWidget({ query }: { query: string }) {
  const [data, setData] = useState<WeatherData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const city = query.replace(/^(počasí|pocasi|weather)\s*/i, '').trim() || 'Praha'

  useEffect(() => {
    setLoading(true); setError('')
    const ctrl = new AbortController()

    ;(async () => {
      try {
        // Geocoding
        const geo = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=cs&format=json`,
          { signal: ctrl.signal }
        ).then(r => r.json())
        const loc = geo.results?.[0]
        if (!loc) { setError(`Město "${city}" nenalezeno`); setLoading(false); return }

        // Weather
        const w = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,precipitation,weather_code&timezone=auto&wind_speed_unit=kmh`,
          { signal: ctrl.signal }
        ).then(r => r.json())
        const cur = w.current ?? {}
        const code = cur.weather_code ?? 0
        const [emoji, desc] = WMO[code] ?? ['🌡️', `kód ${code}`]
        setData({
          name: loc.name, country: loc.country ?? '',
          temp: Math.round(cur.temperature_2m ?? 0),
          feels: Math.round(cur.apparent_temperature ?? 0),
          desc, emoji,
          humidity: cur.relative_humidity_2m ?? 0,
          wind: Math.round(cur.wind_speed_10m ?? 0),
          precip: cur.precipitation,
        })
      } catch (e: unknown) {
        if ((e as Error).name !== 'AbortError') setError('Načítání selhalo')
      } finally { setLoading(false) }
    })()
    return () => ctrl.abort()
  }, [city])

  if (loading) return (
    <div className="flex items-center gap-2 py-2 text-sm" style={{ color: 'var(--muted)' }}>
      <div className="w-3 h-3 rounded-full border-2 anim-spin" style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }}/>
      Načítám počasí…
    </div>
  )

  if (error) return (
    <div className="py-2 text-sm" style={{ color: 'var(--red)' }}>{error}</div>
  )

  if (!data) return null

  return (
    <div className="py-2">
      {/* Header */}
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-3xl">{data.emoji}</span>
        <div>
          <div className="font-semibold text-base" style={{ color: 'var(--text)' }}>
            {data.name}{data.country ? `, ${data.country}` : ''}
          </div>
          <div className="text-sm" style={{ color: 'var(--muted)' }}>{data.desc}</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-3xl font-bold font-mono" style={{ color: 'var(--cyan)' }}>
            {data.temp}°C
          </div>
          <div className="text-xs" style={{ color: 'var(--muted)' }}>pocitová {data.feels}°C</div>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 text-xs font-mono" style={{ color: 'var(--muted)' }}>
        <span>💧 {data.humidity}%</span>
        <span>💨 {data.wind} km/h</span>
        {data.precip != null && data.precip > 0 && <span>🌧️ {data.precip} mm</span>}
      </div>
    </div>
  )
}
