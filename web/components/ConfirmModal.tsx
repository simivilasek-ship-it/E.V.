'use client'
import { useJarvis } from '@/store/jarvis'

const ACTION_LABELS: Record<string, string> = {
  delete_file: 'Smazat soubor',
  shutdown: 'Vypnout počítač',
  restart: 'Restartovat počítač',
  run_command: 'Spustit příkaz',
  shell: 'Shell příkaz',
  install_app: 'Instalovat aplikaci',
}

export default function ConfirmModal() {
  const pending = useJarvis(s => s.pendingConfirm)
  const respond = useJarvis(s => s.respondConfirm)

  if (!pending) return null

  const label = ACTION_LABELS[pending.action] ?? pending.action
  const details = Object.entries(pending.params || {})
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(' · ')

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(2,6,14,.82)', backdropFilter: 'blur(10px)' }}>
      <div className="w-full max-w-md rounded-2xl overflow-hidden anim-slide-up"
        style={{
          background: 'rgba(6,12,26,.98)',
          border: '1px solid rgba(244,63,94,.35)',
          boxShadow: '0 24px 64px rgba(0,0,0,.65)',
        }}>
        <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(244,63,94,.15)' }}>
          <div className="font-hud text-[9px] tracking-[.2em] mb-2" style={{ color: 'var(--red)' }}>
            POTVRZENÍ AKCE
          </div>
          <div className="text-base font-semibold" style={{ color: 'var(--text)' }}>{label}</div>
          {details && (
            <div className="mt-2 font-mono text-[11px] leading-relaxed" style={{ color: 'var(--muted)' }}>
              {details}
            </div>
          )}
        </div>
        <div className="px-5 py-4 flex gap-3 justify-end">
          <button
            onClick={() => respond(false)}
            className="px-4 py-2 rounded-lg font-mono text-[11px] tracking-wide"
            style={{ background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.1)', color: 'var(--muted)' }}>
            Zamítnout
          </button>
          <button
            onClick={() => respond(true)}
            className="px-4 py-2 rounded-lg font-mono text-[11px] tracking-wide font-semibold"
            style={{ background: 'rgba(244,63,94,.15)', border: '1px solid rgba(244,63,94,.4)', color: 'var(--red)' }}>
            Povolit
          </button>
        </div>
      </div>
    </div>
  )
}
