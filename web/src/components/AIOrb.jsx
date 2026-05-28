import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useJarvis } from '../store/jarvis'
import * as THREE from 'three'

const ORB_COLORS = {
  idle:      [0.08, 0.33, 0.75],
  listening: [0.0,  0.83, 1.0],
  thinking:  [0.54, 0.30, 1.0],
  speaking:  [0.13, 0.90, 0.42],
}

const VERTEX_SHADER = `
  uniform float uTime;
  uniform float uAmplitude;
  varying vec3 vNormal;
  varying vec3 vPosition;

  vec3 mod289(vec3 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314*r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g  = step(x0.yzx, x0.xyz);
    vec3 l  = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0,i1.z,i2.z,1.0)) +
      i.y + vec4(0.0,i1.y,i2.y,1.0)) +
      i.x + vec4(0.0,i1.x,i2.x,1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy,h.x);
    vec3 p1 = vec3(a0.zw,h.y);
    vec3 p2 = vec3(a1.xy,h.z);
    vec3 p3 = vec3(a1.zw,h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)), 0.0);
    m = m*m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
  }

  void main() {
    vNormal   = normal;
    vPosition = position;
    float noise = snoise(position * 1.5 + uTime * 0.4) * uAmplitude;
    vec3 displaced = position + normal * noise;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
  }
`

const FRAGMENT_SHADER = `
  uniform vec3  uColor;
  uniform float uTime;
  uniform float uOpacity;
  varying vec3  vNormal;
  varying vec3  vPosition;

  void main() {
    vec3 light = normalize(vec3(1.0, 2.0, 3.0));
    float diff = max(dot(vNormal, light), 0.0) * 0.6 + 0.4;
    vec3 rim   = uColor * pow(1.0 - max(dot(vNormal, vec3(0,0,1)), 0.0), 2.5) * 1.8;
    vec3 col   = uColor * diff + rim;
    float pulse = 0.85 + 0.15 * sin(uTime * 2.0);
    gl_FragColor = vec4(col * pulse, uOpacity);
  }
`

function OrbMesh({ state }) {
  const mesh  = useRef()
  const color = ORB_COLORS[state] || ORB_COLORS.idle
  const amplitude = { idle: 0.18, listening: 0.38, thinking: 0.28, speaking: 0.45 }[state] || 0.18

  const uniforms = useMemo(() => ({
    uTime:      { value: 0 },
    uColor:     { value: new THREE.Vector3(...color) },
    uAmplitude: { value: amplitude },
    uOpacity:   { value: 0.92 },
  }), [state])

  useFrame(({ clock }) => {
    uniforms.uTime.value = clock.getElapsedTime()
    uniforms.uColor.value.set(...ORB_COLORS[state])
    uniforms.uAmplitude.value = amplitude
    if (mesh.current) {
      mesh.current.rotation.y += 0.004
      mesh.current.rotation.x += 0.001
    }
  })

  return (
    <mesh ref={mesh}>
      <icosahedronGeometry args={[1.6, 64]} />
      <shaderMaterial
        vertexShader={VERTEX_SHADER}
        fragmentShader={FRAGMENT_SHADER}
        uniforms={uniforms}
        transparent
        side={THREE.FrontSide}
      />
    </mesh>
  )
}

function Particles() {
  const points = useRef()
  const geo = useMemo(() => {
    const count = 600
    const pos   = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 2.5 + Math.random() * 3.5
      const θ = Math.random() * Math.PI * 2
      const φ = Math.random() * Math.PI
      pos[i*3]   = r * Math.sin(φ) * Math.cos(θ)
      pos[i*3+1] = r * Math.sin(φ) * Math.sin(θ)
      pos[i*3+2] = r * Math.cos(φ)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    return g
  }, [])

  useFrame(({ clock }) => {
    if (points.current) points.current.rotation.y = clock.getElapsedTime() * 0.06
  })

  return (
    <points ref={points} geometry={geo}>
      <pointsMaterial size={0.018} color="#00d4ff" transparent opacity={0.5} sizeAttenuation />
    </points>
  )
}

export default function AIOrb({ size = 280 }) {
  const orbState = useJarvis(s => s.orbState)

  return (
    <div style={{ width: size, height: size }} className="relative">
      {/* Glow ring */}
      <div className="absolute inset-0 rounded-full" style={{
        background: `radial-gradient(circle, rgba(0,212,255,0.12) 0%, transparent 70%)`,
        animation: 'pulse-glow 3s ease-in-out infinite',
      }} />
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1.2} color="#00d4ff" />
        <pointLight position={[-5, -3, -5]} intensity={0.5} color="#7c4dff" />
        <OrbMesh state={orbState} />
        <Particles />
      </Canvas>
      {/* State label */}
      <div className="absolute bottom-2 left-0 right-0 text-center">
        <span className="text-xs font-mono tracking-widest" style={{
          color: { idle:'#4a6080', listening:'#00d4ff', thinking:'#7c4dff', speaking:'#00e676' }[orbState]
        }}>
          {{ idle:'○ IDLE', listening:'◉ LISTENING', thinking:'◎ THINKING', speaking:'● SPEAKING' }[orbState]}
        </span>
      </div>
    </div>
  )
}
