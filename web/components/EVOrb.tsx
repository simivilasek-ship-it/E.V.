'use client'
import type { OrbState } from '@/store/ev'

interface EVOrbProps {
  state?: OrbState
  size?: 'sm' | 'md' | 'lg'
}

const SIZE_MAP = {
  sm: { outer: 32, inner: 24, font: 10, ring: 2 },
  md: { outer: 48, inner: 36, font: 13, ring: 3 },
  lg: { outer: 120, inner: 96, font: 28, ring: 6 },
}

const WAVE_ANGLES = [-50, 0, 50]

export default function EVOrb({ state = 'idle', size = 'sm' }: EVOrbProps) {
  const s = SIZE_MAP[size]
  const isThinking = state === 'thinking'
  const isSpeaking = state === 'speaking'
  const isListening = state === 'listening'

  return (
    <div
      className="relative shrink-0 flex items-center justify-center"
      style={{ width: s.outer, height: s.outer }}
      aria-label={`E.V. — ${state}`}
    >
      {/* Outer spin ring — thinking state */}
      {isThinking && (
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background:
              'conic-gradient(from 0deg, transparent 60%, rgba(99,102,241,.8) 80%, rgba(167,139,250,.9) 92%, transparent 100%)',
            animation: 'ev-think 0.9s linear infinite',
          }}
        />
      )}

      {/* Listening: cyan border pulse */}
      {isListening && (
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: `${s.ring}px solid rgba(56,189,248,.55)`,
            animation: 'ev-pulse 1s ease-in-out infinite',
          }}
        />
      )}

      {/* Speaking: 3 wave bars — each bar uses a wrapper for rotation + inner div for scale */}
      {isSpeaking &&
        WAVE_ANGLES.map((deg, i) => (
          <div
            key={i}
            className="absolute"
            style={{
              width: s.ring,
              height: s.outer * 0.5,
              left: '50%',
              top: '50%',
              marginLeft: -(s.ring / 2),
              marginTop: -(s.outer * 0.25),
              transform: `rotate(${deg}deg) translateY(-${s.outer * 0.38}px)`,
              transformOrigin: `${s.ring / 2}px ${s.outer * 0.25 + s.outer * 0.38}px`,
            }}
          >
            <div
              style={{
                width: '100%',
                height: '100%',
                borderRadius: s.ring,
                background:
                  'linear-gradient(to top, rgba(99,102,241,.3), rgba(129,140,248,.85))',
                animation: 'ev-wave 0.5s ease-in-out infinite',
                animationDelay: `${i * 0.13}s`,
              }}
            />
          </div>
        ))}

      {/* Core orb */}
      <div
        className={`relative flex items-center justify-center rounded-full select-none ${
          state === 'idle'
            ? 'ev-orb-idle'
            : state === 'thinking'
            ? 'ev-orb-think'
            : 'ev-orb-speak'
        }`}
        style={{
          width: s.inner,
          height: s.inner,
          background:
            'linear-gradient(135deg, var(--accent) 0%, #4f46e5 55%, #7c3aed 100%)',
          borderRadius: '50%',
        }}
      >
        <span
          className="font-bold text-white select-none"
          style={{
            fontSize: s.font,
            letterSpacing: size === 'lg' ? '0.06em' : '0.02em',
            fontFamily: 'var(--font-display, Inter, sans-serif)',
            lineHeight: 1,
          }}
        >
          EV
        </span>
      </div>
    </div>
  )
}
