'use client'
import { useEffect, useState } from 'react'

interface Match { home: string; away: string; homeScore: string; awayScore: string; status: string; time: string }

const STATUS_ICON: Record<string, string> = {
  'Final': '✅', 'Full Time': '✅', 'In Progress': '🔴', 'Halftime': '⏸',
  'Scheduled': '🕐', 'Postponed': '📅',
}

const LEAGUE_MAP: Record<string, [string, string]> = {
  'premier': ['⚽', 'soccer/eng.1'],
  'champions': ['⚽', 'soccer/UEFA.CHAMPIONS'],
  'la liga': ['⚽', 'soccer/esp.1'],
  'nhl': ['🏒', 'hockey/nhl'],
  'nba': ['🏀', 'basketball/nba'],
}

function detectLeague(q: string): [string, string, string] {
  const lq = q.toLowerCase()
  for (const [key, [emoji, path]] of Object.entries(LEAGUE_MAP)) {
    if (lq.includes(key)) return [emoji, path, key]
  }
  return ['⚽', 'soccer/eng.1', 'Premier League']
}

export default function SportsWidget({ query }: { query: string }) {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [label, setLabel] = useState('')
  const [leagueEmoji, setLeagueEmoji] = useState('⚽')

  useEffect(() => {
    const [emoji, path, name] = detectLeague(query)
    setLeagueEmoji(emoji)
    setLabel(name.charAt(0).toUpperCase() + name.slice(1))
    setLoading(true)
    const ctrl = new AbortController()

    fetch(`https://site.api.espn.com/apis/site/v2/sports/${path}/scoreboard`, {
      headers: { 'User-Agent': 'Mozilla/5.0' }, signal: ctrl.signal,
    })
      .then(r => r.json())
      .then(d => {
        const evts = (d.events ?? []).slice(0, 6) as Array<Record<string, unknown>>
        setMatches(evts.map((ev: Record<string, unknown>) => {
          const comp = (ev.competitions as Array<Record<string, unknown>>)?.[0] ?? {}
          const statusObj = comp.status as { type?: { description?: string } } | undefined
          const status = statusObj?.type?.description ?? '?'
          const teams  = (comp.competitors as Array<Record<string, unknown>>) ?? []
          const home   = teams.find(t => t.homeAway === 'home') ?? teams[0] ?? {}
          const away   = teams.find(t => t.homeAway === 'away') ?? teams[1] ?? {}
          const dateStr = String(ev.date ?? '')
          let time = ''
          try {
            const dt = new Date(dateStr)
            time = `${dt.getDate()}.${dt.getMonth() + 1} ${dt.getHours().toString().padStart(2,'0')}:${dt.getMinutes().toString().padStart(2,'0')}`
          } catch {}
          return {
            home: String((home.team as Record<string, string>)?.displayName ?? '?'),
            away: String((away.team as Record<string, string>)?.displayName ?? '?'),
            homeScore: String(home.score ?? ''),
            awayScore: String(away.score ?? ''),
            status, time,
          }
        }))
      })
      .catch(() => {})
      .finally(() => setLoading(false))

    return () => ctrl.abort()
  }, [query])

  if (loading) return (
    <div className="flex items-center gap-2 py-2 text-sm" style={{ color: 'var(--muted)' }}>
      <div className="w-3 h-3 rounded-full border-2 anim-spin" style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }}/>
      Načítám výsledky…
    </div>
  )

  return (
    <div className="py-2">
      <div className="font-hud text-[9px] tracking-widest mb-2" style={{ color: 'var(--muted)' }}>
        {leagueEmoji} {label.toUpperCase()}
      </div>
      <div className="flex flex-col gap-1">
        {matches.map((m, i) => {
          const icon = STATUS_ICON[m.status] ?? '·'
          const hasScore = m.homeScore !== '' && m.awayScore !== ''
          return (
            <div key={i} className="flex items-center gap-2 text-xs font-mono py-0.5">
              <span className="text-[10px] w-4 shrink-0">{icon}</span>
              <span className="flex-1 truncate" style={{ color: 'var(--text)' }}>
                {m.home}
              </span>
              {hasScore ? (
                <span className="font-bold tracking-wider px-2" style={{ color: 'var(--cyan)' }}>
                  {m.homeScore} – {m.awayScore}
                </span>
              ) : (
                <span className="px-2" style={{ color: 'var(--muted)' }}>{m.time}</span>
              )}
              <span className="flex-1 truncate text-right" style={{ color: 'var(--text)' }}>
                {m.away}
              </span>
            </div>
          )
        })}
        {matches.length === 0 && (
          <div className="text-xs" style={{ color: 'var(--muted)' }}>Žádné aktuální zápasy.</div>
        )}
      </div>
    </div>
  )
}
