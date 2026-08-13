'use client'
import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(e: Error): State { return { error: e } }
  componentDidCatch(e: Error, info: unknown) { console.error('E.V. UI Error:', e, info) }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-8">
        <div className="w-14 h-14 rounded-[14px] flex items-center justify-center text-2xl"
          style={{ background: 'rgba(244,63,94,.1)', border: '1px solid rgba(244,63,94,.25)' }}>⚠</div>
        <div className="font-hud text-sm tracking-widest" style={{ color: 'var(--red)' }}>KOMPONENTA SELHALA</div>
        <div className="font-mono text-[11px] text-center max-w-sm" style={{ color: 'var(--muted)' }}>
          {this.state.error.message}
        </div>
        <button onClick={() => this.setState({ error: null })}
          className="px-5 py-2 rounded-lg font-hud text-[11px] tracking-widest cursor-pointer transition-all"
          style={{ background: 'rgba(244,63,94,.1)', color: 'var(--red)', border: '1px solid rgba(244,63,94,.25)' }}>
          ZKUSIT ZNOVU
        </button>
      </div>
    )
  }
}
