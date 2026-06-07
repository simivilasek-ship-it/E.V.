'use client'
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'jarvis-onboarding-v1'

type Step = { id: string; label: string; ok: boolean | null; hint: string }

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8002'

export default function OnboardingWizard() {
  const [open, setOpen] = useState(false)
  const [steps, setSteps] = useState<Step[]>([
    { id: 'ollama', label: 'Ollama (lokální LLM)', ok: null, hint: 'Volitelné — bez Ollama funguje lokální router' },
    { id: 'snap', label: 'Snap (instalace aplikací)', ok: null, hint: 'Pro „stahni spotify“ a podobné příkazy' },
    { id: 'mic', label: 'Mikrofon v prohlížeči', ok: null, hint: 'Povol přístup k mikrofonu pro hlas' },
  ])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (localStorage.getItem(STORAGE_KEY)) return
    setOpen(true)
    runChecks()
  }, [])

  async function runChecks() {
    let backend: { ollama?: boolean; snap?: boolean } = {}
    try {
      const r = await fetch(`${API_BASE}/api/onboarding`, { signal: AbortSignal.timeout(4000) })
      if (r.ok) backend = await r.json()
    } catch { /* backend offline */ }

    let micOk = false
    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(t => t.stop())
        micOk = true
      }
    } catch {
      micOk = false
    }

    setSteps([
      { id: 'ollama', label: 'Ollama (lokální LLM)', ok: !!backend.ollama, hint: 'Volitelné — bez Ollama funguje lokální router' },
      { id: 'snap', label: 'Snap (instalace aplikací)', ok: !!backend.snap, hint: 'Pro „stahni spotify“ a podobné příkazy' },
      { id: 'mic', label: 'Mikrofon v prohlížeči', ok: micOk, hint: 'Povol přístup k mikrofonu pro hlas' },
    ])
  }

  function finish() {
    localStorage.setItem(STORAGE_KEY, '1')
    setOpen(false)
  }

  if (!open) return null

  const requiredOk = steps.filter(s => s.id === 'snap').every(s => s.ok !== false)

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      style={{ background: 'rgba(10,11,16,.85)', backdropFilter: 'blur(10px)' }}>
      <div className="w-full max-w-md rounded-2xl glass-panel p-6 anim-slide-up"
        style={{ boxShadow: '0 24px 64px rgba(0,0,0,.5)' }}>
        <h2 className="font-display text-lg font-semibold mb-1">Vítej v JARVIS</h2>
        <p className="text-sm mb-5" style={{ color: 'var(--muted)' }}>
          Rychlá kontrola prostředí — můžeš přeskočit a doladit později v Nastavení.
        </p>

        <ul className="flex flex-col gap-3 mb-6">
          {steps.map(s => (
            <li key={s.id} className="card p-3 flex gap-3 items-start">
              <span className="text-lg shrink-0 mt-0.5">
                {s.ok === null ? '⏳' : s.ok ? '✅' : '⚠️'}
              </span>
              <div>
                <div className="text-sm font-medium">{s.label}</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>{s.hint}</div>
              </div>
            </li>
          ))}
        </ul>

        <div className="flex gap-2 justify-end">
          <button type="button" onClick={runChecks} className="btn-ghost px-4 py-2 text-sm">
            Zkontrolovat znovu
          </button>
          <button type="button" onClick={finish} className="btn-primary px-4 py-2 text-sm">
            {requiredOk ? 'Začít' : 'Přeskočit'}
          </button>
        </div>
      </div>
    </div>
  )
}
