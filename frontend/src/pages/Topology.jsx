import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, TrendingUp, XCircle } from 'lucide-react'
import { LineChart, Line, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../utils/api'
import indiaMapData from '../utils/indiaMapData'

const NODE_COLORS = { healthy: '#22c55e', warning: '#f59e0b', critical: '#ef4444' }
const NODE_SIZES = { tower: 11, router: 13, region: 15 }
const NODE_ICONS = { tower: '📡', router: '🔀', region: '📍' }

const REGION_COORDS = {
  Delhi:    { lat: 28.6139, lng: 77.2090 },
  Roorkee:  { lat: 29.8543, lng: 77.8880 },
  Jaipur:   { lat: 26.9124, lng: 75.7873 },
  Lucknow:  { lat: 26.8467, lng: 80.9462 },
  Mumbai:   { lat: 19.0760, lng: 72.8777 }
}

const REGION_STATE_IDS = {
  Delhi: 'dl',
  Roorkee: 'ut',
  Jaipur: 'rj',
  Lucknow: 'up',
  Mumbai: 'mh'
}

// ── TowerTrend: 12-hour sparkline for a selected tower node ───────────────
function TowerTrend({ component }) {
  const { data, isLoading } = useQuery({
    queryKey: ['towerTrend', component],
    queryFn: () => api.get(`/api/predictions/${encodeURIComponent(component)}/trend`).then(r => r.data),
    enabled: !!component,
    staleTime: 30000,
  })

  const trend = data?.trend || []

  return (
    <div className="detail-block" style={{ marginTop: '16px' }}>
      <h3 style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
        <TrendingUp size={15} /> 12-Hour Event Trend
      </h3>
      {isLoading ? (
        <div style={{ color: 'var(--muted)', fontSize: '13px' }}>Loading trend...</div>
      ) : trend.length === 0 ? (
        <div style={{ color: 'var(--muted)', fontSize: '13px' }}>No recent events</div>
      ) : (
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={trend} margin={{ top: 4, right: 4, left: -30, bottom: 0 }}>
            <Tooltip
              contentStyle={{ background: '#101827', border: '1px solid #263244', borderRadius: '6px', color: '#e5eefb', fontSize: '11px' }}
              formatter={(v) => [v, 'events']}
            />
            <Line type="monotone" dataKey="events" stroke="#38bdf8" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

export default function Topology() {
  const canvasRef = useRef(null)
  const animRef = useRef(null)
  const nodesRef = useRef([])
  const edgesRef = useRef([])
  const [selected, setSelected] = useState(null)
  const [hovered, setHovered] = useState(null)

  const { data } = useQuery({
    queryKey: ['topology'],
    queryFn: () => api.get('/api/topology').then(r => r.data),
    refetchInterval: 15000
  })

  // Initialize force simulation with geographic mapping
  useEffect(() => {
    if (!data) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.parentElement.offsetWidth
    const H = 600
    canvas.width = W * 2
    canvas.height = H * 2
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'
    ctx.scale(2, 2)

    // Calculate map fit scale and offsets (for centering India map in canvas)
    const scale = Math.min(W / 612, H / 696) * 0.82
    const dx = (W - 612 * scale) / 2
    const dy = (H - 696 * scale) / 2 - 20

    const projectLatLng = (lat, lng) => {
      // Calibrated projection formula
      const x = 14.7068 * lng - 947.1
      const y = -16.8485 * lat + 687.2
      return {
        x: x * scale + dx,
        y: y * scale + dy
      }
    }

    // Position nodes using geographic anchors for regions
    const nodes = data.nodes.map((n, i) => {
      if (n.type === 'region') {
        const coords = REGION_COORDS[n.label]
        if (coords) {
          const proj = projectLatLng(coords.lat, coords.lng)
          return {
            ...n,
            x: proj.x,
            y: proj.y,
            vx: 0, vy: 0
          }
        }
      }
      // For towers/routers, place them in a small orbit around their respective parent region
      let parentProj = null
      if (n.region) {
        const coords = REGION_COORDS[n.region]
        if (coords) {
          parentProj = projectLatLng(coords.lat, coords.lng)
        }
      }
      const basePos = parentProj || { x: W / 2, y: H / 2 }
      const angle = (i / data.nodes.length) * Math.PI * 2
      const radius = n.type === 'router' ? 25 : 45
      return {
        ...n,
        x: basePos.x + Math.cos(angle) * radius + (Math.random() - 0.5) * 15,
        y: basePos.y + Math.sin(angle) * radius + (Math.random() - 0.5) * 15,
        vx: 0, vy: 0
      }
    })

    const edges = data.edges.map(e => ({
      ...e,
      source: nodes.find(n => n.id === e.from),
      target: nodes.find(n => n.id === e.to)
    })).filter(e => e.source && e.target)

    nodesRef.current = nodes
    edgesRef.current = edges

    // Localized force layout simulation
    function simulate() {
      // Run 250 iterations for a highly relaxed, perfectly spaced network layout
      for (let iter = 0; iter < 250; iter++) {
        // Strong linear spring repulsion between all nodes to guarantee zero overlap
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[j].x - nodes[i].x
            const dy = nodes[j].y - nodes[i].y
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            const minAllowedDist = (nodes[i].type === 'region' || nodes[j].type === 'region') ? 54 : 42
            if (dist < minAllowedDist) {
              const force = (minAllowedDist - dist) * 0.24
              if (nodes[i].type !== 'region') {
                nodes[i].x -= (dx / dist) * force
                nodes[i].y -= (dy / dist) * force
              }
              if (nodes[j].type !== 'region') {
                nodes[j].x += (dx / dist) * force
                nodes[j].y += (dy / dist) * force
              }
            }
          }
        }
        // Moderate attraction along active edges to pull devices toward parent region
        for (const e of edges) {
          const dx = e.target.x - e.source.x
          const dy = e.target.y - e.source.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const targetDist = (e.source.type === 'region' || e.target.type === 'region') ? 50 : 38
          if (dist > targetDist) {
            const force = (dist - targetDist) * 0.045
            if (e.source.type !== 'region') {
              e.source.x += (dx / dist) * force
              e.source.y += (dy / dist) * force
            }
            if (e.target.type !== 'region') {
              e.target.x -= (dx / dist) * force
              e.target.y -= (dy / dist) * force
            }
          }
        }
        // Force regional anchor nodes to lock exactly onto their projected state lat/lng coords
        for (const n of nodes) {
          if (n.type === 'region') {
            const coords = REGION_COORDS[n.label]
            if (coords) {
              const proj = projectLatLng(coords.lat, coords.lng)
              n.x = proj.x
              n.y = proj.y
            }
          } else {
            // Contain tower/router nodes inside canvas bounds
            n.x = Math.max(25, Math.min(W - 25, n.x))
            n.y = Math.max(25, Math.min(H - 25, n.y))
          }
        }
      }
    }

    simulate()

    let tick = 0
    function draw() {
      tick++
      ctx.clearRect(0, 0, W, H)

      // Draw India Map Background
      ctx.save()
      ctx.translate(dx, dy)
      ctx.scale(scale, scale)
      
      indiaMapData.locations.forEach(loc => {
        const p = new Path2D(loc.path)
        const isActiveState = Object.values(REGION_STATE_IDS).includes(loc.id)
        
        ctx.fillStyle = isActiveState ? 'rgba(56, 189, 248, 0.04)' : 'rgba(13, 21, 35, 0.3)'
        ctx.fill(p)
        
        ctx.strokeStyle = isActiveState ? 'rgba(56, 189, 248, 0.22)' : 'rgba(38, 50, 68, 0.25)'
        ctx.lineWidth = isActiveState ? 1.4 : 0.8
        ctx.stroke(p)
      })
      ctx.restore()

      // Draw edges (network links)
      for (const e of edges) {
        ctx.beginPath()
        ctx.moveTo(e.source.x, e.source.y)
        ctx.lineTo(e.target.x, e.target.y)
        const isAffected = e.source.health === 'critical' || e.target.health === 'critical'
        ctx.strokeStyle = isAffected ? 'rgba(239, 68, 68, 0.45)' : 'rgba(56, 189, 248, 0.2)'
        ctx.lineWidth = isAffected ? 2 : 1.2
        if (isAffected) {
          ctx.setLineDash([4, 4])
          ctx.lineDashOffset = -tick * 0.4
        } else {
          ctx.setLineDash([])
        }
        ctx.stroke()
        ctx.setLineDash([])
      }

      // Draw nodes
      for (const n of nodes) {
        const size = NODE_SIZES[n.type] || 12
        const color = NODE_COLORS[n.health] || NODE_COLORS.healthy
        const isHov = hovered === n.id
        const isSel = selected?.id === n.id

        // Pulse ring for critical nodes
        if (n.health === 'critical') {
          const pulseSize = size + 4.5 + Math.sin(tick * 0.08) * 3
          ctx.beginPath()
          ctx.arc(n.x, n.y, pulseSize, 0, Math.PI * 2)
          ctx.fillStyle = '#ef444422'
          ctx.fill()
        }

        // Glow effect
        ctx.shadowBlur = isHov || isSel ? 10 : 0
        ctx.shadowColor = color

        // Node circle
        ctx.beginPath()
        ctx.arc(n.x, n.y, size + (isHov ? 2 : 0), 0, Math.PI * 2)
        ctx.fillStyle = isSel ? color : `${color}28`
        ctx.fill()
        ctx.strokeStyle = color
        ctx.lineWidth = isSel ? 2.5 : 1.5
        ctx.stroke()

        // Reset shadow
        ctx.shadowBlur = 0

        // Icon
        ctx.font = `${size * 0.9}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(NODE_ICONS[n.type] || '●', n.x, n.y)

        // Label
        ctx.font = '10px Inter, sans-serif'
        ctx.fillStyle = isHov || isSel ? '#e5eefb' : '#94a3b8'
        ctx.textAlign = 'center'
        ctx.fillText(n.label, n.x, n.y + size + 11)
      }

      animRef.current = requestAnimationFrame(draw)
    }

    draw()

    // Click handler
    const handleClick = (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      for (const n of nodes) {
        const dx = n.x - mx
        const dy = n.y - my
        const size = NODE_SIZES[n.type] || 12
        if (Math.sqrt(dx * dx + dy * dy) < size + 5) {
          setSelected(n)
          return
        }
      }
      setSelected(null)
    }

    const handleMove = (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      let found = null
      for (const n of nodes) {
        const dx = n.x - mx
        const dy = n.y - my
        const size = NODE_SIZES[n.type] || 12
        if (Math.sqrt(dx * dx + dy * dy) < size + 5) {
          found = n.id
          break
        }
      }
      setHovered(found)
      canvas.style.cursor = found ? 'pointer' : 'default'
    }

    canvas.addEventListener('click', handleClick)
    canvas.addEventListener('mousemove', handleMove)

    return () => {
      cancelAnimationFrame(animRef.current)
      canvas.removeEventListener('click', handleClick)
      canvas.removeEventListener('mousemove', handleMove)
    }
  }, [data, selected, hovered])

  return (
    <div className="page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">Infrastructure view</span>
        <h1>Network Topology</h1>
        <p>Interactive visualization of towers, routers, and regions. Click any node to inspect.</p>
      </header>

      <div className="topo-layout">
        <div className="panel topo-canvas-panel">
          <div className="topo-legend">
            <span><span className="legend-dot" style={{ background: '#22c55e' }} /> Healthy</span>
            <span><span className="legend-dot" style={{ background: '#f59e0b' }} /> Warning</span>
            <span><span className="legend-dot" style={{ background: '#ef4444' }} /> Critical</span>
            <span>📡 Tower</span>
            <span>🔀 Router</span>
            <span>📍 Region</span>
          </div>
          <canvas ref={canvasRef} />
        </div>

        <div className="panel topo-detail-panel">
          {selected ? (
            <>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">{selected.type}</span>
                  <h2>{selected.label}</h2>
                </div>
                {selected.health === 'critical' ? <XCircle color="#ef4444" size={22} /> :
                 selected.health === 'warning' ? <AlertTriangle color="#f59e0b" size={22} /> :
                 <CheckCircle2 color="#22c55e" size={22} />}
              </div>
              <div className="result-grid compact" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <span><strong>{selected.critical_count}</strong>Critical</span>
                <span><strong>{selected.warning_count}</strong>Warning</span>
                <span><strong>{selected.total_events}</strong>Total events</span>
                <span><strong className={`tone-${selected.health === 'critical' ? 'red' : selected.health === 'warning' ? 'amber' : 'green'}`}>{selected.health?.toUpperCase()}</strong>Status</span>
              </div>

              {/* 12-hour trend sparkline — uses /api/predictions/{id}/trend */}
              {selected.type === 'tower' && <TowerTrend component={selected.id} />}
            </>
          ) : (
            <div className="empty-state">Click a node on the graph to view details.</div>
          )}

          {data && (
            <div className="detail-block">
              <h3>Network Summary</h3>
              <p style={{ color: 'var(--muted)', fontSize: '14px' }}>
                {data.nodes?.filter(n => n.type === 'tower').length || 0} towers,{' '}
                {data.nodes?.filter(n => n.type === 'router').length || 0} routers,{' '}
                {data.nodes?.filter(n => n.type === 'region').length || 0} regions
              </p>
              <p style={{ color: 'var(--muted)', fontSize: '14px', marginTop: '8px' }}>
                {data.nodes?.filter(n => n.health === 'critical').length || 0} critical,{' '}
                {data.nodes?.filter(n => n.health === 'warning').length || 0} warning
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
