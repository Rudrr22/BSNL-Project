export default function StatCard({ icon: Icon, label, value, helper, tone = 'blue', trend }) {
  return (
    <article className={'stat-card tone-' + tone}>
      <div className="stat-icon" aria-hidden="true">{Icon ? <Icon size={22} /> : null}</div>
      <div className="stat-body">
        <span>{label}</span>
        <strong>{value}</strong>
        <p>{helper}</p>
      </div>
      {trend ? <div className="stat-trend">{trend}</div> : null}
    </article>
  )
}
