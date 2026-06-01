'use client'
// TODO: migrate from web_vite_backup/src/components/MemoryGraph.jsx
export default function MemoryGraph(props: Record<string, unknown>) {
  return (
    <div className="card p-6 flex items-center justify-center gap-3 text-sm"
      style={{ color: 'var(--muted)', minHeight: 200 }}>
      <div className="w-2 h-2 rounded-full anim-pulse" style={{ background: 'var(--cyan)' }}/>
      MemoryGraph — migrace probíhá…
    </div>
  )
}
