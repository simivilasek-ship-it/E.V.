import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function Stars() {
  const points = useRef()
  const geo = useMemo(() => {
    const count = 1500
    const pos   = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i*3]   = (Math.random() - 0.5) * 40
      pos[i*3+1] = (Math.random() - 0.5) * 40
      pos[i*3+2] = (Math.random() - 0.5) * 40
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    return g
  }, [])

  useFrame(({ clock }) => {
    if (points.current) {
      points.current.rotation.y = clock.getElapsedTime() * 0.015
      points.current.rotation.x = clock.getElapsedTime() * 0.005
    }
  })

  return (
    <points ref={points} geometry={geo}>
      <pointsMaterial size={0.04} color="#1a3050" transparent opacity={0.8} sizeAttenuation />
    </points>
  )
}

function Grid() {
  const lines = useRef()
  useFrame(({ clock }) => {
    if (lines.current) lines.current.rotation.x = clock.getElapsedTime() * 0.02
  })
  return (
    <group ref={lines}>
      <gridHelper args={[40, 40, '#0d2040', '#0d2040']} position={[0, -8, 0]} />
    </group>
  )
}

export default function ParticleBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
      <Canvas camera={{ position: [0, 0, 12], fov: 60 }}>
        <Stars />
        <Grid />
      </Canvas>
    </div>
  )
}
