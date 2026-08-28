'use client'
import { useEV } from '@/store/ev'
import { Icons } from './Icons'
import JarvisCore from './JarvisCore'

const ORB_LABEL: Record<string, string> = {
  idle: 'Připravena',
  listening: 'Poslouchám',
  thinking: 'Přemýšlím',
  speaking: 'Mluvím',
}

export default function HomePanel({
  onOpenChat,
  dimmed = false,
  briefing = '',
  needsTap = false,
  onStartVoice,
}: {
  onOpenChat: () => void
  dimmed?: boolean
  briefing?: string
  needsTap?: boolean
  onStartVoice?: () => void
}) {
  const orbState = useEV(s => s.orbState)
  const connStatus = useEV(s => s.connStatus)
  const system = useEV(s => s.system)
  const online = connStatus === 'connected'

  const hour = new Date().getHours()
  const hello = hour < 12 ? 'Dobré ráno' : hour < 18 ? 'Dobrý den' : 'Dobrý večer'

  return (
    <section
      className={`home-stage${needsTap ? ' home-stage-await' : ''}`}
      data-testid="home-stage"
      onClick={needsTap ? onStartVoice : undefined}
      style={dimmed ? { filter: 'saturate(0.85) brightness(0.72)' } : undefined}
    >
      <div className="home-orb">
        <JarvisCore state={orbState} />
      </div>

      <div className="home-copy">
        <div className="font-hud" style={{ color: 'var(--accent-light)', letterSpacing: '0.28em' }}>
          E.V. CORE
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight" style={{ color: 'var(--text)' }}>
          {hello}.
        </h1>
        {needsTap && (
          <p className="home-tap-hint" data-testid="home-tap-hint">
            Klepni kdekoli. Řeknu dobrý den.
          </p>
        )}
        <p className="text-sm sm:text-base max-w-xl leading-relaxed" style={{ color: 'var(--text-secondary)' }} data-testid="home-briefing">
          {briefing || 'Jsem online. Řekni, co máme řešit — nebo otevři chat.'}
        </p>
        <div className="flex items-center justify-center gap-2 flex-wrap">
          <span className="status-pill" style={{ color: online ? 'var(--green)' : 'var(--red)' }}>
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background: online ? 'var(--green)' : 'var(--red)',
                boxShadow: online ? '0 0 8px var(--green)' : 'none',
              }}
            />
            {online ? 'Online' : 'Offline'}
          </span>
          <span className="status-pill" style={{ color: 'var(--accent-light)' }}>
            {ORB_LABEL[orbState] ?? 'Připravena'}
          </span>
          {system.cpu > 0 && (
            <span className="status-pill" style={{ color: 'var(--muted)' }}>
              CPU {Math.round(system.cpu)}%
            </span>
          )}
        </div>
      </div>

      {!dimmed && (
      <button
        type="button"
        data-testid="open-chat"
        className="home-chat-fab"
        onClick={onOpenChat}
        aria-label="Otevřít chat"
      >
        <span className="home-chat-fab-icon">{Icons.chat}</span>
        <span>Chat</span>
      </button>
      )}
    </section>
  )
}
