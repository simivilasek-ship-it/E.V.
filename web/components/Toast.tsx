'use client'
import { useJarvis } from '@/store/jarvis'

const TYPE_STYLE: Record<string, { bg: string; border: string; color: string }> = {
  success: { bg: 'rgba(34,211,165,.08)', border: 'rgba(34,211,165,.25)', color: '#22d3a5' },
  warning: { bg: 'rgba(245,158,11,.08)', border: 'rgba(245,158,11,.25)', color: '#f59e0b' },
  error:   { bg: 'rgba(244,63,94,.08)',  border: 'rgba(244,63,94,.25)',  color: '#f43f5e' },
  info:    { bg: 'rgba(0,200,255,.08)',  border: 'rgba(0,200,255,.25)',  color: '#00c8ff' },
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
            className="flex items-center gap-2 px-4 py-2.5 rounded-[10px] font-mono text-[11px] pointer-events-auto anim-slide-up max-w-xs"
            style={{
              background: `${style.bg} rgba(4,9,16,.8)`,
              backdropFilter: 'blur(24px)',
              border: `1px solid ${style.border}`,
              color: style.color,
              boxShadow: '0 8px 24px rgba(0,0,0,.4)',
            }}
            onClick={() => removeToast(t.id)}>
            <span className="flex-1">{t.message}</span>
          </div>
        )
      })}
    </div>
  )
}
