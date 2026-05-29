import { useRef, useMemo } from 'react'
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

export default function ParticleBackground() {
  return (
    <div style={{ position:'fixed', inset:0, pointerEvents:'none', zIndex:0 }}>
      <Canvas camera={{ position:[0,0,14], fov:60 }} gl={{ alpha:true }}>
        <Stars />
      </Canvas>
    </div>
  )
}
