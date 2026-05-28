import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useAppStore } from '../store/appStore'
import * as THREE from 'three'

function Orb({ thinking }) {
  const meshRef = useRef()
  const glowRef = useRef()

  const geometry = useMemo(() => {
    const g = new THREE.IcosahedronGeometry(1.2, 4)
    return g
  }, [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const speed = thinking ? 2.5 : 0.4
    meshRef.current.rotation.y = t * speed * 0.3
    meshRef.current.rotation.x = Math.sin(t * 0.2) * 0.15
    const scale = 1 + Math.sin(t * (thinking ? 3 : 1)) * (thinking ? 0.05 : 0.02)
    meshRef.current.scale.setScalar(scale)
    if (glowRef.current) {
      glowRef.current.scale.setScalar(scale * 1.3 + Math.sin(t * 2) * 0.05)
    }
  })

  return (
    <group>
      {/* Outer glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[1.4, 32, 32]} />
        <meshBasicMaterial
          color={thinking ? '#00ffcc' : '#00d4ff'}
          transparent opacity={0.06} side={THREE.BackSide}
        />
      </mesh>
      {/* Main orb */}
      <mesh ref={meshRef} geometry={geometry}>
        <meshPhongMaterial
          color={thinking ? '#00ffcc' : '#0088cc'}
          emissive={thinking ? '#004433' : '#001133'}
          specular="#00d4ff"
          shininess={120}
          wireframe={false}
        />
      </mesh>
      {/* Wireframe overlay */}
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#00d4ff" wireframe transparent opacity={0.12} />
      </mesh>
    </group>
  )
}

function Particles() {
  const points = useRef()
  const positions = useMemo(() => {
    const arr = new Float32Array(600)
    for (let i = 0; i < 600; i++) {
      arr[i] = (Math.random() - 0.5) * 8
    }
    return arr
  }, [])

  useFrame((s) => {
    points.current.rotation.y = s.clock.elapsedTime * 0.03
  })

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#1a4a6a" size={0.03} />
    </points>
  )
}

export default function OrbScene() {
  const thinking = useAppStore(s => s.thinking)

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400 }}>
      <Canvas camera={{ position: [0, 0, 4], fov: 50 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1.2} color="#00d4ff" />
        <pointLight position={[-5, -3, -5]} intensity={0.4} color="#0055aa" />
        <Orb thinking={thinking} />
        <Particles />
      </Canvas>
    </div>
  )
}
