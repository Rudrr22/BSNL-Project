import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts'
import { Activity, BarChart3, Clock, Gauge, Phone, PhoneOff, Signal, TrendingUp, Zap } from 'lucide-react'
import { api } from '../utils/api'

const COLORS = { critical: '#ef4444', warning: '#f59e0b', info: '#22c55e' }

export default function KPIs() {
  const { data: kpiData } = useQuery({
    queryKey: ['kpiOverview'],
    queryFn: () => api.get('/api/kpis/overview').then(r => r.data),
    refetchInterval: 20000
  })

  const { data: callData } = useQuery({
    queryKey: ['callDrops'],
    queryFn: () => api.get('/api/kpis/call-drops').then(r => r.data),
    refetchInterval: 20000
  })

  const { data: predData } = useQuery({
    queryKey: ['predictions'],
    queryFn: () => api.get('/api/predictions').then(r => r.data),
    refetchInterval: 15000
  })

  const { data: corrData } = useQuery({
    queryKey: ['correlations'],
    queryFn: () => api.get('/api/correlations').then(r => r.data),
    refetchInterval: 20000
  })

  const severity = kpiData?.severity_trend || []
  const latency = kpiData?.latency_by_region || []
  const availability = kpiData?.tower_availability || []
  const drops = callData?.call_drops || []
  const predictions = predData?.predictions || []
  const correlations = corrData?.correlations || []

  return (
    <div className="page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">Comprehensive analytics</span>
        <h1>Network KPI Dashboard</h1>
        <p>Real-time performance indicators, failure predictions, call drops, and anomaly correlations.</p>
      </header>

      {/* Predictions Row */}
      <section className="panel">
        <div className="section-heading">
          <div><span className="eyebrow">Predictive intelligence</span><h2>Failure Risk Assessment</h2></div>
          <Zap size={18} />
        </div>
        <div className="prediction-grid">
          {predictions.slice(0, 6).map(p => (
            <div key={p.component} className={`prediction-card ${p.risk_level.toLowerCase()}`}>
              <div className="pred-header">
                <strong>{p.component}</strong>
                <span className={`severity-pill ${p.risk_level.toLowerCase()}`}>{p.risk_score}%</span>
              </div>
              <div className="pred-body">
                <span className="pred-region">{p.region}</span>
                <span>ETA: {p.predicted_eta}</span>
                <span>Mode: {p.likely_failure_mode}</span>
                <span>Accel: {p.acceleration}x</span>
              </div>
              <div className="risk-bar">
                <div className="risk-fill" style={{ width: `${p.risk_score}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Charts Row */}
      <div className="dashboard-grid">
        {/* Severity Trend */}
        <section className="panel chart-panel">
          <div className="section-heading">
            <div><span className="eyebrow">12-hour window</span><h2>Severity Trend</h2></div>
            <TrendingUp size={18} />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={severity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3a" />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: '#101827', border: '1px solid #263244', borderRadius: '8px', color: '#e5eefb' }} />
              <Legend />
              <Area type="monotone" dataKey="critical" stackId="1" stroke="#ef4444" fill="#ef444433" />
              <Area type="monotone" dataKey="warning" stackId="1" stroke="#f59e0b" fill="#f59e0b33" />
              <Area type="monotone" dataKey="info" stackId="1" stroke="#22c55e" fill="#22c55e33" />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        {/* Latency by Region */}
        <section className="panel chart-panel">
          <div className="section-heading">
            <div><span className="eyebrow">Regional performance</span><h2>Avg Latency (ms)</h2></div>
            <Clock size={18} />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={latency}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3a" />
              <XAxis dataKey="region" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: '#101827', border: '1px solid #263244', borderRadius: '8px', color: '#e5eefb' }} />
              <Bar dataKey="avg_latency_ms" radius={[6, 6, 0, 0]}>
                {latency.map((entry, i) => (
                  <Cell key={i} fill={entry.avg_latency_ms > 200 ? '#ef4444' : entry.avg_latency_ms > 100 ? '#f59e0b' : '#38bdf8'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      {/* Call Drops + Tower Availability */}
      <div className="dashboard-grid">
        {/* Call Drop Rate */}
        <section className="panel">
          <div className="section-heading">
            <div><span className="eyebrow">TRAI compliance</span><h2>Call Drop Rates</h2></div>
            <PhoneOff size={18} />
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tower</th>
                  <th>Region</th>
                  <th>Drop Rate</th>
                  <th>Status</th>
                  <th>Handovers</th>
                </tr>
              </thead>
              <tbody>
                {drops.map(d => (
                  <tr key={d.component}>
                    <td><strong>{d.component}</strong></td>
                    <td>{d.region}</td>
                    <td>
                      <span style={{
                        color: d.drop_rate_percent > 5 ? '#ef4444' : d.drop_rate_percent > 2 ? '#f59e0b' : '#22c55e',
                        fontWeight: 700
                      }}>
                        {d.drop_rate_percent}%
                      </span>
                    </td>
                    <td>
                      <span className={`severity-pill ${d.status.toLowerCase()}`}>
                        {d.trai_compliant ? '✓' : '✗'} {d.status}
                      </span>
                    </td>
                    <td>{d.total_handovers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: '12px', marginTop: '10px' }}>
            TRAI threshold: 2% maximum call drop rate
          </div>
        </section>

        {/* Tower Availability */}
        <section className="panel">
          <div className="section-heading">
            <div><span className="eyebrow">Uptime tracking</span><h2>Tower Availability</h2></div>
            <Gauge size={18} />
          </div>
          <div className="availability-list">
            {availability.map(t => (
              <div key={t.component} className="avail-row">
                <div className="avail-info">
                  <strong>{t.component}</strong>
                  <span>{t.down_events} downtime events</span>
                </div>
                <div className="avail-bar-track">
                  <div className="avail-bar-fill" style={{
                    width: `${t.availability_percent}%`,
                    background: t.availability_percent > 99 ? '#22c55e' : t.availability_percent > 95 ? '#f59e0b' : '#ef4444'
                  }} />
                </div>
                <strong style={{
                  color: t.availability_percent > 99 ? '#22c55e' : t.availability_percent > 95 ? '#f59e0b' : '#ef4444',
                  minWidth: '52px', textAlign: 'right'
                }}>
                  {t.availability_percent}%
                </strong>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Anomaly Correlations */}
      {correlations.length > 0 && (
        <section className="panel">
          <div className="section-heading">
            <div><span className="eyebrow">Pattern detection</span><h2>Anomaly Correlations</h2></div>
            <Activity size={18} />
          </div>
          <div className="correlation-list">
            {correlations.slice(0, 5).map((c, i) => (
              <div key={i} className="correlation-card">
                <div className="corr-header">
                  <span className={`severity-pill ${c.severity?.toLowerCase()}`}>{c.type}</span>
                  <span style={{ color: 'var(--muted)', fontSize: '13px' }}>{c.event_count} events in {c.time_window_minutes}min</span>
                </div>
                <p style={{ margin: '8px 0', color: 'var(--text)' }}>{c.description}</p>
                <div className="corr-tags">
                  {c.affected_components.map(comp => (
                    <span key={comp} className="corr-tag">{comp}</span>
                  ))}
                  {c.affected_regions.map(reg => (
                    <span key={reg} className="corr-tag region-tag">{reg}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
