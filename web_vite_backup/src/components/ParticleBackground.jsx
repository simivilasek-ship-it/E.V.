import { useRef, useMemo, Component } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function Stars() {
  const ref = useRef()
  const geo = useMemo(() => {
    const n = 1200, pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      pos[i*3]   = (Math.random() - .5) * 50
      pos[i*3+1] = (Math.random() - .5) * 50
      pos[i*3+2] = (Math.random() - .5) * 50
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    return g
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * .012
  })

  return (
    <points ref={ref} geometry={geo}>
      <pointsMaterial size={.03} color="#0a3060" transparent opacity={.7} sizeAttenuation />
    </points>
  )
}

// CSS fallback — jednoduché tečky bez WebGL
function CSSStars() {
  const stars = useMemo(() =>
    Array.from({ length: 80 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      s: Math.random() * 2 + 0.5,
      o: Math.random() * 0.4 + 0.1,
      d: Math.random() * 3 + 2,
    })), [])
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      {stars.map(s => (
        <div key={s.id} style={{
          position: 'absolute',
          left: `${s.x}%`, top: `${s.y}%`,
          width: s.s, height: s.s,
          borderRadius: '50%',
          background: '#0a4080',
          opacity: s.o,
          animation: `starTwinkle ${s.d}s ease-in-out infinite`,
        }} />
      ))}
      <style>{`@keyframes starTwinkle{0%,100%{opacity:.1}50%{opacity:.5}}`}</style>
    </div>
  )
}

class StarsErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { failed: false } }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <CSSStars />
    return this.props.children
  }
}

export default function ParticleBackground() {
  return (
    <StarsErrorBoundary>
      <div style={{ position:'fixed', inset:0, pointerEvents:'none', zIndex:0 }}>
        <Canvas camera={{ position:[0,0,14], fov:60 }} gl={{ alpha:true }}>
          <Stars />
        </Canvas>
      </div>
    </StarsErrorBoundary>
  )
}
