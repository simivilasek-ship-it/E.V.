import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(err) {
    return { error: err }
  }

  componentDidCatch(err, info) {
    console.error('JARVIS UI Error:', err, info)
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', height: '100%', gap: 16, padding: 32,
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: 'rgba(244,63,94,.1)', border: '1px solid rgba(244,63,94,.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24,
        }}>⚠</div>
        <div style={{ fontFamily: 'var(--font-hud)', fontSize: 13, color: 'var(--red)', letterSpacing: '.1em' }}>
          KOMPONENTA SELHALA
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text2)', maxWidth: 400, textAlign: 'center' }}>
          {this.state.error?.message || 'Neznámá chyba'}
        </div>
        <button
          onClick={() => this.setState({ error: null })}
          style={{
            padding: '7px 20px', borderRadius: 8, fontSize: 11, cursor: 'pointer',
            background: 'rgba(244,63,94,.1)', color: 'var(--red)',
            border: '1px solid rgba(244,63,94,.25)',
            fontFamily: 'var(--font-hud)', letterSpacing: '.1em',
          }}>
          ZKUSIT ZNOVU
        </button>
      </div>
    )
  }
}
