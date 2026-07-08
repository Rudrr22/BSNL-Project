import { useEffect, useMemo, useState } from 'react'
import { Radio, ServerCrash, Maximize2, Minimize2 } from 'lucide-react'
import { logsSocketUrl } from '../utils/api'

const sampleLogs = [
  { severity: 'INFO', component: 'BTS_014', raw: 'Signal levels stable across Jaipur sector A' },
  { severity: 'WARNING', component: 'Router_7', raw: 'Latency spike detected on backhaul link' },
  { severity: 'CRITICAL', component: 'BTS_042', raw: 'Repeated call drops detected in handover window' },
]

export default function LogTicker({ initialLogs = [] }) {
  const [liveLogs, setLiveLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    let socket
    try {
      socket = new WebSocket(logsSocketUrl())
      socket.onopen = () => setConnected(true)
      socket.onclose = () => setConnected(false)
      socket.onerror = () => setConnected(false)
      socket.onmessage = (event) => {
        const log = JSON.parse(event.data)
        setLiveLogs((current) => [log, ...current].slice(0, 200)) // Keep up to 200 logs
      }
    } catch (error) {
      setConnected(false)
    }

    return () => {
      if (socket) socket.close()
    }
  }, [])

  const logs = useMemo(() => {
    const merged = [...liveLogs, ...initialLogs]
    return merged.length ? merged.slice(0, isExpanded ? 200 : 10) : sampleLogs
  }, [initialLogs, liveLogs, isExpanded])

  return (
    <>
      {isExpanded && (
        <div 
          onClick={() => setIsExpanded(false)}
          style={{ position: 'fixed', inset: 0, zIndex: 9998, background: 'rgba(2, 6, 23, 0.85)', backdropFilter: 'blur(8px)' }} 
        />
      )}
      <section 
        className="panel log-panel" 
        style={isExpanded ? {
          position: 'fixed',
          top: '5vh',
          left: '5vw',
          width: '90vw',
          height: '90vh',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 80px rgba(0,0,0,0.8)',
          border: '1px solid var(--blue)'
        } : {}}
      >
        <div className="section-heading">
          <div>
            <span className="eyebrow">Live stream</span>
            <h2>Network Log Ticker</h2>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span className={connected ? 'socket-state connected' : 'socket-state'}>
              {connected ? <Radio size={14} /> : <ServerCrash size={14} />}
              {connected ? 'Connected' : 'Preview mode'}
            </span>
            <button 
              onClick={() => setIsExpanded(!isExpanded)}
              className="ghost-button" 
              style={{ padding: '6px 12px', minHeight: '32px', fontSize: '12px' }}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              {isExpanded ? 'Close Full Window' : 'Full Window'}
            </button>
          </div>
        </div>

        <div className="log-list" style={isExpanded ? { 
          flex: 1, 
          overflowY: 'auto',
          paddingRight: '12px'
        } : {}}>
          {logs.map((log, index) => (
            <div className="log-row" key={(log.id || log.raw || index) + '-' + index}>
              <span className={'dot ' + String(log.severity || 'INFO').toLowerCase()} />
              <span className="log-severity">{log.severity || 'INFO'}</span>
              <span className="log-component">{log.component || 'Network'}</span>
              <span className="log-message">{log.raw || log.event_type || 'Waiting for incoming telemetry'}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
