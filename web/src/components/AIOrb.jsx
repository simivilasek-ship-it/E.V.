import { useRef, useMemo, useEffect, Component } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useJarvis } from '../store/jarvis'
import * as THREE from 'three'

// ── Canvas 2D orb — 3D fallback bez WebGL ────────────────────
// Phong shading, latitude čáry, spekulár, rim light, perspektivní prsteny.
// Funguje v Qt WebEngine i bez GPU.

const C2D_STATE = {
  idle:      { r: 0,   g: 133, b: 204, speed: 0.4,  amp: 5  },
  listening: { r: 0,   g: 212, b: 255, speed: 1.8,  amp: 11 },
  thinking:  { r: 139, g: 92,  b: 246, speed: 1.2,  amp: 8  },
  speaking:  { r: 0,   g: 230, b: 118, speed: 2.4,  amp: 14 },
}

// Vygeneruje body noise-distorted sphere silhouette
function spherePath(ctx, cx, cy, R, amp, t) {
  const pts = 200
  ctx.beginPath()
  for (let i = 0; i <= pts; i++) {
    const θ = (i / pts) * Math.PI * 2
    const n =
      Math.sin(θ * 2 + t * 0.7)  * 0.35 +
      Math.sin(θ * 3 - t * 1.1)  * 0.28 +
      Math.sin(θ * 5 + t * 0.55) * 0.20 +
      Math.sin(θ * 7 - t * 0.9)  * 0.12 +
      Math.sin(θ * 11 + t * 1.4) * 0.05
    const r = R + n * amp
    const x = cx + Math.cos(θ) * r
    const y = cy + Math.sin(θ) * r
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
  }
  ctx.closePath()
}

function Canvas2DOrb({ size = 290, orbState = 'idle' }) {
  const canvasRef = useRef()
  const stateRef  = useRef(orbState)
  stateRef.current = orbState

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const cx  = size / 2
    const cy  = size / 2
    const R   = size * 0.36
    let raf   = 0
    let t     = 0

    function draw() {
      const s   = C2D_STATE[stateRef.current] || C2D_STATE.idle
      const col = `${s.r},${s.g},${s.b}`
      const { r, g, b, amp, speed } = s
      t += 0.016 * speed

      ctx.clearRect(0, 0, size, size)

      // ── 1. Atmosférická záře ──────────────────────────────────
      const atmo = ctx.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 2.0)
      atmo.addColorStop(0, `rgba(${col},0.18)`)
      atmo.addColorStop(0.6, `rgba(${col},0.06)`)
      atmo.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = atmo
      ctx.fillRect(0, 0, size, size)

      // ── 2. Sphere silhouette (noise displaced) ───────────────
      spherePath(ctx, cx, cy, R, amp, t)

      // Phong diffuse fill: světlo z top-left → tmavé v bottom-right
      const lx = cx - R * 0.32
      const ly = cy - R * 0.38
      const diff = ctx.createRadialGradient(lx, ly, 0, cx, cy, R * 1.15)
      diff.addColorStop(0.00, `rgba(${Math.min(255,r+110)},${Math.min(255,g+75)},${Math.min(255,b+55)},1.0)`)
      diff.addColorStop(0.28, `rgba(${r},${g},${b},0.97)`)
      diff.addColorStop(0.65, `rgba(${Math.round(r*0.38)},${Math.round(g*0.32)},${Math.round(b*0.28)},0.95)`)
      diff.addColorStop(1.00, `rgba(${Math.round(r*0.08)},${Math.round(g*0.06)},${Math.round(b*0.06)},0.92)`)
      ctx.fillStyle = diff
      ctx.fill()

      // ── 3. Rim light (Fresnel — záře na okrajích) ────────────
      spherePath(ctx, cx, cy, R, amp, t)
      ctx.strokeStyle = `rgba(${col},0.75)`
      ctx.lineWidth   = 3.5
      ctx.shadowColor = `rgb(${col})`
      ctx.shadowBlur  = 28
      ctx.stroke()
      ctx.shadowBlur  = 0

      // ── 4. Latitude čáry uvnitř sphere (3D mřížka) ──────────
      ctx.save()
      spherePath(ctx, cx, cy, R, amp, t)
      ctx.clip()

      // Rotující osa sklonu pro pocit rotace
      const tilt = Math.sin(t * 0.25) * 0.18  // osa se mírně kývá

      ctx.strokeStyle = `rgba(${col},0.18)`
      ctx.lineWidth   = 0.8
      ctx.shadowBlur  = 0
      // 5 horizontálních kruhů = 5 zeměpisných šířek
      for (let li = -2; li <= 2; li++) {
        const yOff  = (li / 2.8) * R
        const halfW = Math.sqrt(Math.max(0, R * R - yOff * yOff))
        const scaleY = 0.22 + Math.abs(Math.cos(t * 0.5 + li))  * 0.12
        ctx.beginPath()
        ctx.ellipse(cx, cy + yOff, halfW, halfW * scaleY, tilt, 0, Math.PI * 2)
        ctx.stroke()
      }

      // 3 poledníky (vertikální oblouky jako meridians)
      for (let mi = 0; mi < 3; mi++) {
        const angle = t * 0.3 + (mi / 3) * Math.PI
        ctx.beginPath()
        ctx.ellipse(cx, cy, R * Math.abs(Math.cos(angle)), R, Math.sin(angle) * 0.5, 0, Math.PI * 2)
        ctx.stroke()
      }
      ctx.restore()

      // ── 5. Spekulární odraz — Phong ──────────────────────────
      // Primární highlight (rozmazaná elipsa)
      const hs = ctx.createRadialGradient(lx, ly, 0, lx + R * 0.12, ly + R * 0.1, R * 0.3)
      hs.addColorStop(0,   'rgba(255,255,255,0.60)')
      hs.addColorStop(0.4, 'rgba(255,255,255,0.18)')
      hs.addColorStop(1,   'rgba(255,255,255,0)')
      ctx.fillStyle = hs
      ctx.beginPath()
      ctx.ellipse(lx + R * 0.06, ly + R * 0.05, R * 0.24, R * 0.15, -0.4, 0, Math.PI * 2)
      ctx.fill()

      // Sekundární miniaturní odlesk
      const hs2 = ctx.createRadialGradient(lx - R * 0.04, ly - R * 0.06, 0, lx, ly, R * 0.09)
      hs2.addColorStop(0, 'rgba(255,255,255,0.50)')
      hs2.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = hs2
      ctx.beginPath()
      ctx.arc(lx, ly, R * 0.08, 0, Math.PI * 2)
      ctx.fill()

      // ── 6. Orbitální prsteny s perspektivou ─────────────────
      ctx.save()
      ctx.translate(cx, cy)

      // Prsten 1 — nakloněný a rotující
      const r1angle = t * 0.45
      const r1tilt  = 0.25 + Math.sin(t * 0.3) * 0.15
      ctx.strokeStyle = `rgba(${col},0.45)`
      ctx.lineWidth   = 1.2
      ctx.shadowColor = `rgb(${col})`
      ctx.shadowBlur  = 10
      ctx.beginPath()
      ctx.ellipse(0, 0, R * 1.30, R * 1.30 * r1tilt, r1angle, 0, Math.PI * 2)
      ctx.stroke()

      // Prsten 2 — opačný směr, jiný sklon
      const r2angle = -t * 0.28
      const r2tilt  = 0.18 + Math.cos(t * 0.4) * 0.10
      ctx.strokeStyle = `rgba(${col},0.25)`
      ctx.lineWidth   = 0.8
      ctx.shadowBlur  = 6
      ctx.beginPath()
      ctx.ellipse(0, 0, R * 1.45, R * 1.45 * r2tilt, r2angle, 0, Math.PI * 2)
      ctx.stroke()
      ctx.shadowBlur = 0
      ctx.restore()

      raf = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(raf)
  }, [size])

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ display: 'block' }}
    />
  )
}

// ErrorBoundary — zachytí WebGL chybu a zobrazí Canvas 2D orb
class OrbErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { failed: false } }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) {
      return <Canvas2DOrb size={this.props.size} orbState={this.props.orbState} />
    }
    return this.props.children
  }
}

const STATE = {
  idle:      { color: [0.0, 0.52, 0.92], amp: 0.12, speed: 0.5,  bloom: 0.3 },
  listening: { color: [0.0, 0.83, 1.0],  amp: 0.28, speed: 2.2,  bloom: 0.7 },
  thinking:  { color: [0.54, 0.36, 1.0], amp: 0.20, speed: 1.4,  bloom: 0.5 },
  speaking:  { color: [0.13, 0.90, 0.42],amp: 0.38, speed: 2.8,  bloom: 0.9 },
}

const VERT = `
  uniform float uTime;
  uniform float uAmp;
  uniform float uSpeed;
  varying vec3 vNormal;
  varying float vDisp;

  //  Simplex 3D noise (ashima-arts)
  vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
  vec4 mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
  vec4 permute(vec4 x){return mod289(((x*34.)+1.)*x);}
  vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-.85373472095314*r;}
  float snoise(vec3 v){
    const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);
    vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);
    vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;
    vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);
    vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;
    i=mod289(i);
    vec4 p=permute(permute(permute(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
    float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;
    vec4 j=p-49.*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);
    vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);
    vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
    vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));
    vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
    vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
    vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
    vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;
    return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
  }

  void main(){
    vNormal = normal;
    float t = uTime * uSpeed;
    float n = snoise(position * 1.8 + t * 0.3) * uAmp
            + snoise(position * 3.2 + t * 0.5) * uAmp * 0.4;
    vDisp = n;
    vec3 displaced = position + normal * n;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
  }
`

const FRAG = `
  uniform vec3  uColor;
  uniform float uTime;
  uniform float uBloom;
  varying vec3  vNormal;
  varying float vDisp;

  void main(){
    vec3 light = normalize(vec3(1.,2.,3.));
    float diff = clamp(dot(vNormal, light), 0., 1.) * .5 + .5;

    // Rim light (edge glow)
    vec3 viewDir = normalize(vec3(0.,0.,1.));
    float rim = pow(1. - clamp(dot(vNormal, viewDir), 0., 1.), 2.8);

    // Displacement-based highlight
    float highlight = clamp(vDisp * 3., 0., 1.);

    vec3 baseColor = uColor * diff;
    vec3 rimColor  = uColor * rim * 2.0 * uBloom;
    vec3 hlColor   = vec3(1.) * highlight * .25;
    vec3 final     = baseColor + rimColor + hlColor;

    // Inner breathe pulse
    float pulse = .88 + .12 * sin(uTime * 1.8);
    final *= pulse;

    gl_FragColor = vec4(final, .95);
  }
`

function lerp3(a, b, t) {
  return a.map((v, i) => v + (b[i] - v) * t)
}

function OrbMesh({ stateKey }) {
  const mesh   = useRef()
  const target = STATE[stateKey] || STATE.idle
  const cur    = useRef({ color: [...target.color], amp: target.amp, bloom: target.bloom })

  const uniforms = useMemo(() => ({
    uTime:  { value: 0 },
    uColor: { value: new THREE.Vector3(...target.color) },
    uAmp:   { value: target.amp },
    uSpeed: { value: target.speed },
    uBloom: { value: target.bloom },
  }), [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    uniforms.uTime.value = t

    // Smooth color/amp transition
    const speed = 0.05
    cur.current.color = lerp3(cur.current.color, target.color, speed)
    cur.current.amp   += (target.amp   - cur.current.amp)   * speed
    cur.current.bloom += (target.bloom - cur.current.bloom) * speed

    uniforms.uColor.value.set(...cur.current.color)
    uniforms.uAmp.value   = cur.current.amp
    uniforms.uSpeed.value = target.speed
    uniforms.uBloom.value = cur.current.bloom

    if (mesh.current) {
      mesh.current.rotation.y += 0.003
      mesh.current.rotation.x  = Math.sin(t * 0.3) * 0.08
    }
  })

  return (
    <mesh ref={mesh}>
      <icosahedronGeometry args={[1.55, 80]} />
      <shaderMaterial
        vertexShader={VERT}
        fragmentShader={FRAG}
        uniforms={uniforms}
        transparent
      />
    </mesh>
  )
}

// Floating ring around the orb
function Ring({ stateKey }) {
  const ref = useRef()
  const col = STATE[stateKey]?.color || [0,0.52,0.92]
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.rotation.z = clock.getElapsedTime() * 0.4
      ref.current.rotation.x = Math.PI / 2 + Math.sin(clock.getElapsedTime() * 0.5) * 0.15
    }
  })
  return (
    <mesh ref={ref}>
      <torusGeometry args={[2.1, 0.012, 16, 120]} />
      <meshBasicMaterial color={new THREE.Color(...col)} transparent opacity={0.35} />
    </mesh>
  )
}

// Outer glow sphere
function GlowSphere({ stateKey }) {
  const ref = useRef()
  const col = STATE[stateKey]?.color || [0,0.52,0.92]
  useFrame(({ clock }) => {
    if (ref.current) {
      const p = 0.85 + 0.15 * Math.sin(clock.getElapsedTime() * 1.8)
      ref.current.material.opacity = p * 0.08
    }
  })
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[2.0, 32, 32]} />
      <meshBasicMaterial color={new THREE.Color(...col)} transparent opacity={0.08} side={THREE.BackSide} />
    </mesh>
  )
}

// Particles orbiting
function Particles({ stateKey }) {
  const ref  = useRef()
  const spd  = STATE[stateKey]?.speed || 0.5
  const col  = STATE[stateKey]?.color || [0,0.52,0.92]

  const geo = useMemo(() => {
    const n = 500, pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      const r = 2.4 + Math.random() * 1.8
      const θ = Math.random() * Math.PI * 2
      const φ = Math.acos(2 * Math.random() - 1)
      pos[i*3]   = r * Math.sin(φ) * Math.cos(θ)
      pos[i*3+1] = r * Math.sin(φ) * Math.sin(θ)
      pos[i*3+2] = r * Math.cos(φ)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    return g
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * spd * 0.07
  })

  return (
    <points ref={ref} geometry={geo}>
      <pointsMaterial
        size={0.022}
        color={new THREE.Color(...col)}
        transparent opacity={0.55}
        sizeAttenuation
      />
    </points>
  )
}

const STATE_LABELS = {
  idle: '○  IDLE', listening: '◉  LISTENING',
  thinking: '◎  THINKING', speaking: '●  SPEAKING',
}
const STATE_COLORS = {
  idle: '#3a5a78', listening: '#00d4ff', thinking: '#8b5cf6', speaking: '#00e676',
}

export default function AIOrb({ size = 290 }) {
  const orbState = useJarvis(s => s.orbState)

  return (
    <div style={{ width: size, position: 'relative' }}>
      {/* Outer glow ring — CSS */}
      <div style={{
        position: 'absolute', inset: -20, borderRadius: '50%', zIndex: 0,
        background: `radial-gradient(circle, ${STATE_COLORS[orbState]}18 0%, transparent 65%)`,
        transition: 'background 1.2s ease',
        animation: 'breathe 3s ease-in-out infinite',
      }} />

      <div style={{ width: size, height: size, position: 'relative', zIndex: 1 }}>
        <OrbErrorBoundary size={size} orbState={orbState}>
          <Canvas camera={{ position: [0, 0, 5], fov: 42 }} gl={{ antialias: true, alpha: true }}>
            <ambientLight intensity={0.15} />
            <pointLight position={[4, 6, 4]} intensity={1.4} color={`rgb(${STATE[orbState]?.color.map(v=>Math.round(v*255)).join(',')})`} />
            <pointLight position={[-4,-4,-6]} intensity={0.5} color="#8b5cf6" />
            <GlowSphere stateKey={orbState} />
            <OrbMesh     stateKey={orbState} />
            <Ring        stateKey={orbState} />
            <Particles   stateKey={orbState} />
          </Canvas>
        </OrbErrorBoundary>
      </div>

      {/* State label */}
      <div style={{
        textAlign: 'center', fontSize: 10, letterSpacing: '.18em',
        color: STATE_COLORS[orbState],
        marginTop: 8,
        transition: 'color .8s ease',
        textShadow: `0 0 12px ${STATE_COLORS[orbState]}88`,
      }}>
        {STATE_LABELS[orbState]}
      </div>
    </div>
  )
}
