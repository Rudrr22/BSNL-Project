import { useQuery } from '@tanstack/react-query'
import { MapPin, SignalHigh, SignalLow, SignalMedium, Wifi } from 'lucide-react'
import { api } from '../utils/api'
import indiaMapData from '../utils/indiaMapData'

const HEALTH_COLORS = { Good: '#22c55e', Fair: '#f59e0b', Poor: '#ef4444', 'No data': '#64748b' }

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

export default function Coverage() {
  const { data } = useQuery({
    queryKey: ['heatmap'],
    queryFn: () => api.get('/api/heatmap').then(r => r.data),
    refetchInterval: 15000
  })

  const regions = data?.regions || {}
  const regionList = Object.entries(regions).sort((a, b) => a[1].health_score - b[1].health_score)

  return (
    <div className="page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">Signal intelligence</span>
        <h1>Coverage & Signal Heatmap</h1>
        <p>Regional signal strength, health scores, and coverage quality across the BSNL network.</p>
      </header>

      {/* Map Visualization */}
      <div className="panel heatmap-container">
        <div className="section-heading">
          <div><span className="eyebrow">Geographic view</span><h2>Signal Strength Map</h2></div>
          <Wifi size={18} />
        </div>
        <div className="india-map" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '10px 0' }}>
          <svg viewBox="0 0 612 696" style={{ width: '100%', maxHeight: '580px' }} xmlns="http://www.w3.org/2000/svg">
            {/* Draw all states of India */}
            {indiaMapData.locations.map(loc => {
              // Find if this state matches any of our active regions
              const activeRegionEntry = Object.entries(REGION_STATE_IDS).find(([_, stateId]) => stateId === loc.id)
              const regionName = activeRegionEntry ? activeRegionEntry[0] : null
              const r = regionName ? regions[regionName] : null
              
              let fill = 'rgba(26, 43, 67, 0.15)'
              let stroke = 'rgba(38, 50, 68, 0.35)'
              let strokeWidth = '0.8'
              
              if (r) {
                const color = HEALTH_COLORS[r.signal_quality] || '#64748b'
                fill = `${color}18`
                stroke = color
                strokeWidth = '1.8'
              }
              
              return (
                <path
                  key={loc.id}
                  d={loc.path}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  style={{ transition: 'all 0.25s ease' }}
                />
              )
            })}

            {/* Draw geographic markers exactly at projected coordinates */}
            {regionList.map(([name, r]) => {
              const color = HEALTH_COLORS[r.signal_quality] || '#64748b'
              const coords = REGION_COORDS[name]
              if (!coords) return null
              
              // Project lat/lng to SVG space 612x696
              const x = 14.7068 * coords.lng - 947.1
              const y = -16.8485 * coords.lat + 687.2
              
              return (
                <g key={name} className="map-marker-group" style={{ cursor: 'pointer' }}>
                  {/* Glowing pulse ring */}
                  <circle
                    cx={x}
                    cy={y}
                    r="14"
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    opacity="0.8"
                  >
                    <animate attributeName="r" values="8;22;8" dur="2.5s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2.5s" repeatCount="indefinite" />
                  </circle>
                  
                  {/* Center solid dot */}
                  <circle
                    cx={x}
                    cy={y}
                    r="6"
                    fill={color}
                  />

                  {/* Label background for readability */}
                  <rect
                    x={x + 12}
                    y={y - 18}
                    width={name.length * 6.5 + 54}
                    height="22"
                    rx="4"
                    fill="rgba(8, 13, 20, 0.88)"
                    stroke="rgba(38, 50, 68, 0.7)"
                    strokeWidth="0.8"
                  />
                  
                  {/* Text label */}
                  <text
                    x={x + 18}
                    y={y - 3}
                    fill="#e5eefb"
                    fontSize="10.5"
                    fontFamily="Inter, sans-serif"
                    fontWeight="bold"
                  >
                    {name} <tspan fill={color} fontWeight="900">{r.avg_rssi ? `${r.avg_rssi} dBm` : 'N/A'}</tspan>
                  </text>
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      {/* Region Cards */}
      <div className="coverage-grid">
        {regionList.map(([name, r]) => {
          const color = HEALTH_COLORS[r.signal_quality] || '#64748b'
          return (
            <div key={name} className="panel region-card">
              <div className="region-header">
                <div>
                  <div className="region-name"><MapPin size={16} color={color} /> {name}</div>
                  <span className="signal-badge" style={{ color, background: `${color}18` }}>
                    {r.signal_quality === 'Good' ? <SignalHigh size={14} /> :
                     r.signal_quality === 'Fair' ? <SignalMedium size={14} /> :
                     <SignalLow size={14} />}
                    {r.signal_quality}
                  </span>
                </div>
                <div className="health-ring" style={{ '--health-color': color, '--health-pct': `${r.health_score}%` }}>
                  <span>{r.health_score}</span>
                </div>
              </div>

              <div className="region-stats">
                <div className="region-stat">
                  <span>Avg RSSI</span>
                  <strong style={{ color }}>{r.avg_rssi ? `${r.avg_rssi} dBm` : '—'}</strong>
                </div>
                <div className="region-stat">
                  <span>Critical</span>
                  <strong className="tone-red">{r.critical_count}</strong>
                </div>
                <div className="region-stat">
                  <span>Warnings</span>
                  <strong className="tone-amber">{r.warning_count}</strong>
                </div>
                <div className="region-stat">
                  <span>Total Logs</span>
                  <strong>{r.total_logs}</strong>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="panel" style={{ padding: '14px 20px' }}>
        <div className="topo-legend">
          <span>Signal Quality Thresholds:</span>
          <span><span className="legend-dot" style={{ background: '#22c55e' }} /> Good (RSSI {'>'} -75 dBm)</span>
          <span><span className="legend-dot" style={{ background: '#f59e0b' }} /> Fair (-85 to -75 dBm)</span>
          <span><span className="legend-dot" style={{ background: '#ef4444' }} /> Poor ({'<'} -85 dBm)</span>
        </div>
      </div>
    </div>
  )
}
