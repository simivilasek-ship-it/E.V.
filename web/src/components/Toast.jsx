import { useJarvis } from '../store/jarvis'

const TYPE_STYLE = {
  info:    { border: 'rgba(0,212,255,.3)',  color: '#00d4ff', bg: 'rgba(0,212,255,.08)' },
  success: { border: 'rgba(0,229,160,.3)',  color: '#00e5a0', bg: 'rgba(0,229,160,.08)' },
  error:   { border: 'rgba(255,51,102,.3)', color: '#ff3366', bg: 'rgba(255,51,102,.08)' },
  warning: { border: 'rgba(255,179,0,.3)',  color: '#ffb300', bg: 'rgba(255,179,0,.08)'  },
}

export default function ToastContainer() {
  const toasts      = useJarvis(s => s.toasts)
  const removeToast = useJarvis(s => s.removeToast)

  return (
    <div style={{
      position: 'fixed', bottom: 80, right: 16,
      display: 'flex', flexDirection: 'column-reverse', gap: 8,
      zIndex: 1000, pointerEvents: 'none',
    }}>
      {toasts.map(t => {
        const st = TYPE_STYLE[t.type] || TYPE_STYLE.info
        return (
          <div key={t.id}
            onClick={() => removeToast(t.id)}
            style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              padding: '10px 14px', borderRadius: 8,
              background: st.bg, border: `1px solid ${st.border}`,
              color: st.color, backdropFilter: 'blur(12px)',
              boxShadow: `0 0 16px ${st.border}`,
              animation: 'fadeUp .3s ease-out',
              pointerEvents: 'all', cursor: 'pointer',
              maxWidth: 320, letterSpacing: '.04em',
            }}>
            {t.message}
          </div>
        )
      })}
    </div>
  )
}
