'use client'
import { useState, useEffect, useRef } from 'react'
import { useJarvis } from '@/store/jarvis'
import { apiUrl } from '@/lib/api'

interface SttHealth {
  engine?: string
  language?: string
  available?: boolean
}

interface TtsHealth {
  engine?: string
  voice?: string
  rate?: number
  available?: boolean
}

interface WakeWordHealth {
  enabled?: boolean
  available?: boolean
}

interface VoiceHealth {
  stt?: SttHealth
  tts?: TtsHealth
  wake_word?: WakeWordHealth
  duplex?: { enabled?: boolean }
}

const BAR_COUNT = 9

function StatusDot({ ok }: { ok?: boolean }) {
  return (
    <span
      className="w-2 h-2 rounded-full shrink-0"
      style={{
        background: ok === undefined ? 'var(--muted)' : ok ? 'var(--green)' : 'var(--red)',
        boxShadow: ok ? '0 0 6px var(--green)' : 'none',
        transition: 'background 0.3s',
      }}
    />
  )
}

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      aria-label="Toggle"
      style={{ width: 40, height: 22, position: 'relative', cursor: 'pointer', border: 'none', background: 'transparent', padding: 0 }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 11,
          background: checked ? 'var(--accent)' : 'var(--border)',
          transition: 'background 0.2s',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 3,
          left: checked ? 21 : 3,
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: 'white',
          transition: 'left 0.2s',
          boxShadow: '0 1px 4px rgba(0,0,0,.3)',
        }}
      />
    </button>
  )
}

const hasSpeechRecognition = () =>
  typeof window !== 'undefined' &&
  ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

export default function VoicePanel() {
  const [health, setHealth] = useState<VoiceHealth>({})
  const [loading, setLoading] = useState(true)
  const [offline, setOffline] = useState(false)
  const [recording, setRecording] = useState(false)
  const [duplex, setDuplex] = useState(false)
  const [bars, setBars] = useState<number[]>(Array(BAR_COUNT).fill(4))
  const [testResponse, setTestResponse] = useState<string | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const animFrameRef = useRef<number | null>(null)
  const animTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const addToast = useJarvis(s => s.addToast)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(apiUrl('/api/health/check'))
        if (!res.ok) throw new Error('not ok')
        const data = await res.json()
        const voice: VoiceHealth = data.voice ?? {}
        setHealth(voice)
        setDuplex(voice.duplex?.enabled ?? false)
        setOffline(false)
      } catch {
        setOffline(true)
      } finally {
        setLoading(false)
      }
    }
    poll()
    const id = setInterval(poll, 10_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const stopAnim = () => {
      if (animFrameRef.current !== null) cancelAnimationFrame(animFrameRef.current)
      if (animTimeoutRef.current !== null) clearTimeout(animTimeoutRef.current)
    }

    const stopAudio = () => {
      streamRef.current?.getTracks().forEach(t => t.stop())
      streamRef.current = null
      audioCtxRef.current?.close()
      audioCtxRef.current = null
      analyserRef.current = null
    }

    if (!recording) {
      stopAnim()
      stopAudio()
      setBars(Array(BAR_COUNT).fill(4))
      return
    }

    let usedRealAnalyser = false

    const startRealAnalyser = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        streamRef.current = stream
        const ctx = new AudioContext()
        audioCtxRef.current = ctx
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 64
        analyserRef.current = analyser
        ctx.createMediaStreamSource(stream).connect(analyser)

        const dataArray = new Uint8Array(analyser.frequencyBinCount)
        usedRealAnalyser = true

        const tick = () => {
          if (!analyserRef.current) return
          analyserRef.current.getByteFrequencyData(dataArray)
          const step = Math.floor(dataArray.length / BAR_COUNT)
          setBars(
            Array(BAR_COUNT)
              .fill(0)
              .map((_, i) => {
                const raw = dataArray[i * step] ?? 0
                return Math.max(4, Math.floor((raw / 255) * 30))
              })
          )
          animFrameRef.current = requestAnimationFrame(tick)
        }
        animFrameRef.current = requestAnimationFrame(tick)
      } catch {
        if (!usedRealAnalyser) startFallbackAnim()
      }
    }

    const startFallbackAnim = () => {
      const tick = () => {
        setBars(Array(BAR_COUNT).fill(0).map(() => Math.floor(Math.random() * 26) + 4))
        animTimeoutRef.current = setTimeout(() => {
          animFrameRef.current = requestAnimationFrame(tick)
        }, 80)
      }
      animFrameRef.current = requestAnimationFrame(tick)
    }

    startRealAnalyser()

    return () => {
      stopAnim()
      stopAudio()
    }
  }, [recording])

  const toggleDuplex = async () => {
    const next = !duplex
    try {
      await fetch(apiUrl('/api/settings'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_ws_enabled: next, duplex_audio_enabled: next }),
      })
      setDuplex(next)
      addToast(next ? 'Duplex zapnut' : 'Duplex vypnut', 'success', 2000)
    } catch {
      addToast('Chyba při ukládání nastavení', 'error', 3000)
    }
  }

  const _sendTextTest = async () => {
    setRecording(true)
    try {
      const res = await fetch(apiUrl('/api/chat/message'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: 'Jaký je dnešní datum?' }),
      })
      const data = await res.json()
      setTestResponse(data.response ?? data.message ?? JSON.stringify(data))
    } catch {
      setTestResponse('Chyba: API není dostupné.')
    } finally {
      setTestLoading(false)
      setRecording(false)
    }
  }

  const sendTest = async () => {
    setTestLoading(true)
    setTestResponse(null)

    if (hasSpeechRecognition()) {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      const recognition = new SR()
      recognition.lang = health?.stt?.language || 'cs-CZ'
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      setRecording(true)
      setTestResponse('Poslouchám…')

      recognition.onresult = async (event: any) => {
        const transcript = event.results[0][0].transcript
        setTestResponse(`STT: "${transcript}" — odesílám…`)
        try {
          const res = await fetch(apiUrl('/api/chat/message'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: transcript }),
          })
          const data = await res.json()
          setTestResponse(`STT: "${transcript}"\n\nJARVIS: ${data.response ?? data.message ?? ''}`)
        } catch {
          setTestResponse(`STT: "${transcript}" — API nedostupné`)
        }
        setRecording(false)
        setTestLoading(false)
      }

      recognition.onerror = (event: any) => {
        setTestResponse(`STT chyba: ${event.error}. Zkus: "Jaký je dnešní datum?"`)
        setRecording(false)
        setTestLoading(false)
        _sendTextTest()
      }

      recognition.onend = () => {
        if (testLoading) {
          setRecording(false)
          setTestLoading(false)
        }
      }

      recognition.start()
    } else {
      await _sendTextTest()
    }
  }

  if (offline && !loading) {
    return (
      <div className="card p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="w-4 h-4 shrink-0"
            style={{ color: 'var(--amber)' }}
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span className="font-semibold text-sm" style={{ color: 'var(--amber)' }}>
            Hlasové API není dostupné
          </span>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
          Hlas není nakonfigurován nebo backend není spuštěn. Spusťte{' '}
          <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'rgba(255,255,255,.08)' }}>
            python3 jarvis.py
          </code>{' '}
          a obnovte stránku.
        </p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          Pro offline STT nainstalujte Vosk:{' '}
          <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'rgba(255,255,255,.08)' }}>
            pip install vosk
          </code>
        </p>
      </div>
    )
  }

  return (
    <div className="card p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-4 h-4 shrink-0" style={{ color: 'var(--accent-light)' }}>
            <path d="M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z" />
            <path d="M19 10v1a7 7 0 01-14 0v-1" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
          <h2 className="font-display text-sm font-bold tracking-wide" style={{ color: 'var(--text)' }}>
            Hlas
          </h2>
        </div>
        {loading && (
          <span className="text-[11px] font-mono" style={{ color: 'var(--muted)' }}>
            načítám…
          </span>
        )}
      </div>

      {/* Mic level visualizer */}
      <div
        className="flex items-end justify-center gap-1 rounded-xl px-4"
        style={{
          background: recording ? 'rgba(99,102,241,.08)' : 'rgba(255,255,255,.03)',
          border: `1px solid ${recording ? 'var(--accent)' : 'var(--border)'}`,
          minHeight: 56,
          paddingTop: 14,
          paddingBottom: 14,
          transition: 'border-color 0.2s, background 0.2s',
        }}
      >
        {bars.map((h, i) => (
          <div
            key={i}
            style={{
              width: 5,
              height: h,
              borderRadius: 3,
              background: recording ? 'var(--accent)' : 'var(--muted)',
              transition: recording ? 'height 0.08s ease' : 'height 0.3s ease',
              opacity: recording ? 1 : 0.35,
            }}
          />
        ))}
        {recording && (
          <span
            className="ml-3 text-xs font-mono"
            style={{ color: 'var(--accent-light)', animation: 'pulseDot 1s infinite' }}
          >
            Nahrávám…
          </span>
        )}
      </div>

      {/* Engine status rows */}
      <div className="flex flex-col gap-1.5">
        {[
          {
            label: 'STT engine',
            dot: health.stt?.available,
            value: health.stt?.engine
              ? `${health.stt.engine}${health.stt.language ? ` · ${health.stt.language}` : ''}`
              : '—',
          },
          {
            label: 'TTS engine',
            dot: health.tts?.available,
            value: health.tts?.engine
              ? `${health.tts.engine}${health.tts.voice ? ` · ${health.tts.voice}` : ''}${health.tts.rate ? ` · ${health.tts.rate}×` : ''}`
              : '—',
          },
          {
            label: 'Wake word',
            dot: health.wake_word?.available && health.wake_word?.enabled,
            value: health.wake_word?.enabled
              ? 'aktivní'
              : health.wake_word?.available
              ? 'vypnuto'
              : '—',
          },
          {
            label: 'Prohlížeč STT',
            dot: hasSpeechRecognition(),
            value: hasSpeechRecognition()
              ? 'Dostupné (Web Speech API)'
              : 'Nedostupné — použij Chrome',
          },
        ].map(({ label, dot, value }) => (
          <div
            key={label}
            className="flex items-center justify-between text-xs py-1.5 px-3 rounded-lg"
            style={{ background: 'rgba(255,255,255,.03)' }}
          >
            <span style={{ color: 'var(--muted)' }}>{label}</span>
            <span className="flex items-center gap-2">
              <StatusDot ok={dot} />
              <span className="font-mono" style={{ color: 'var(--text)' }}>
                {value}
              </span>
            </span>
          </div>
        ))}
      </div>

      {/* Duplex toggle */}
      <div
        className="flex items-center justify-between px-3 py-2.5 rounded-xl"
        style={{ background: 'rgba(255,255,255,.03)', border: '1px solid var(--border)' }}
      >
        <div>
          <div className="text-xs font-semibold" style={{ color: 'var(--text)' }}>
            Duplex stream
          </div>
          <div className="text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
            Souběžný mikrofon + reproduktor (/ws/audio)
          </div>
        </div>
        <ToggleSwitch checked={duplex} onChange={toggleDuplex} />
      </div>

      {/* Test button */}
      <button
        onClick={sendTest}
        disabled={testLoading}
        className="btn-primary flex items-center justify-center gap-2 py-2.5 text-sm disabled:opacity-60"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-4 h-4 shrink-0">
          <path d="M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z" />
          <path d="M19 10v1a7 7 0 01-14 0v-1" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
        {testLoading
          ? (hasSpeechRecognition() ? 'Poslouchám…' : 'Nahrávám testovací větu…')
          : (hasSpeechRecognition() ? 'Spustit nahrávání' : 'Odeslat testovací větu')}
      </button>

      {/* Inline response */}
      {testResponse && (
        <div
          className="rounded-xl p-3 text-xs leading-relaxed"
          style={{
            background: 'rgba(52,211,153,.06)',
            border: '1px solid rgba(52,211,153,.2)',
            color: 'var(--text)',
          }}
        >
          <span
            className="font-mono text-[10px] block mb-1.5 uppercase tracking-wide"
            style={{ color: 'var(--green)' }}
          >
            JARVIS odpověděl:
          </span>
          {testResponse}
        </div>
      )}
    </div>
  )
}
