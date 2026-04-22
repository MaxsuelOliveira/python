export default function EventList({ events }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Eventos recentes</h2>
      </div>
      <div className="event-list">
        {events.length === 0 && <div className="muted">Nenhum evento registrado.</div>}
        {events.map((event) => (
          <article key={event.id} className="event-card">
            <div className="event-top">
              <strong>{event.rule_name}</strong>
              <span className="pill">{event.event_type}</span>
            </div>
            <div className="muted small">{new Date(event.timestamp).toLocaleString()}</div>
            <div className="small">Confiança: {event.confidence ?? 'n/a'}</div>
            {event.snapshot_path && (
              <a href={`/api/snapshots/${event.snapshot_path}`} target="_blank" rel="noreferrer" className="link">
                Abrir snapshot
              </a>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
