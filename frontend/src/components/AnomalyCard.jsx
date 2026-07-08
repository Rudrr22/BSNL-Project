import { CheckCircle2, CircleAlert, MapPin, RadioTower } from 'lucide-react'

const severityTone = {
  CRITICAL: 'critical',
  WARNING: 'warning',
  INFO: 'info',
}

export default function AnomalyCard({ anomaly, onAcknowledge, compact = false }) {
  const tone = severityTone[anomaly?.severity] || 'info'

  return (
    <article className={'anomaly-card ' + tone + (compact ? ' compact' : '')}>
      <div className="anomaly-header">
        <span className={'severity-pill ' + tone}>
          <CircleAlert size={14} />
          {anomaly?.severity || 'INFO'}
        </span>
        <span className={anomaly?.acknowledged ? 'ack acknowledged' : 'ack'}>
          <CheckCircle2 size={14} />
          {anomaly?.acknowledged ? 'Acknowledged' : 'Open'}
        </span>
      </div>

      <h3>{anomaly?.event_type || anomaly?.component || 'Network anomaly'}</h3>
      <p>{anomaly?.description || 'No description has been generated yet.'}</p>

      <div className="anomaly-meta">
        <span><RadioTower size={14} /> {anomaly?.component || 'Unknown component'}</span>
        <span><MapPin size={14} /> {anomaly?.region || 'Region pending'}</span>
      </div>

      {!compact && (
        <div className="anomaly-actions">
          <div>
            <strong>Suggested action</strong>
            <p>{anomaly?.suggested_action || 'Review recent logs and assign field verification.'}</p>
          </div>
          {!anomaly?.acknowledged && onAcknowledge ? (
            <button className="ghost-button" type="button" onClick={() => onAcknowledge(anomaly.id)}>
              Acknowledge
            </button>
          ) : null}
        </div>
      )}
    </article>
  )
}
