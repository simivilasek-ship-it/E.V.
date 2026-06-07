'use client'
import { useJarvis } from '@/store/jarvis'

const TYPE_STYLE: Record<string, { accent: string; bg: string }> = {
  success: { accent: 'var(--green)', bg: 'rgba(52,211,153,.1)' },
  warning: { accent: 'var(--amber)', bg: 'rgba(251,191,36,.1)' },
  error:   { accent: 'var(--red)',   bg: 'rgba(248,113,113,.1)' },
  info:    { accent: 'var(--accent-light)', bg: 'rgba(99,102,241,.1)' },
}

export default function ToastContainer() {
  const toasts     = useJarvis(s => s.toasts)
  const removeToast = useJarvis(s => s.removeToast)

  return (
    <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50 pointer-events-none">
      {toasts.map(t => {
        const style = TYPE_STYLE[t.type] ?? TYPE_STYLE.info
        return (
          <div key={t.id}
            className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm pointer-events-auto anim-slide-up max-w-sm glass-panel cursor-pointer"
            style={{
              borderLeft: `3px solid ${style.accent}`,
              background: `${style.bg}`,
            }}
            onClick={() => removeToast(t.id)}>
            <span className="flex-1" style={{ color: 'var(--text)' }}>{t.message}</span>
          </div>
        )
      })}
    </div>
  )
}
