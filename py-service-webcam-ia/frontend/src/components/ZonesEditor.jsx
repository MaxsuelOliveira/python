export default function ZonesEditor({ payload, onChange, preview }) {
  function updateZone(id, field, value) {
    onChange({
      ...payload,
      zones: payload.zones.map((zone) => zone.id === id ? { ...zone, [field]: value } : zone),
    })
  }

  function addZone() {
    onChange({
      ...payload,
      zones: [...payload.zones, {
        id: `zone_${Math.random().toString(36).slice(2, 8)}`,
        name: 'Nova zona',
        shape: 'rect',
        x: 0.1,
        y: 0.1,
        w: 0.3,
        h: 0.3,
        color: '#f97316',
      }],
    })
  }

  return (
    <div className="two-col">
      <section className="panel">
        <div className="panel-header">
          <h2>Zonas</h2>
          <button className="button" onClick={addZone}>Nova zona</button>
        </div>
        <div className="stack">
          {payload.zones.map((zone) => (
            <div key={zone.id} className="zone-card">
              <label>Nome<input value={zone.name} onChange={(e) => updateZone(zone.id, 'name', e.target.value)} /></label>
              <label>ID<input value={zone.id} onChange={(e) => updateZone(zone.id, 'id', e.target.value)} /></label>
              <div className="quad-grid">
                <label>X<input type="number" step="0.01" min="0" max="1" value={zone.x} onChange={(e) => updateZone(zone.id, 'x', Number(e.target.value))} /></label>
                <label>Y<input type="number" step="0.01" min="0" max="1" value={zone.y} onChange={(e) => updateZone(zone.id, 'y', Number(e.target.value))} /></label>
                <label>W<input type="number" step="0.01" min="0" max="1" value={zone.w} onChange={(e) => updateZone(zone.id, 'w', Number(e.target.value))} /></label>
                <label>H<input type="number" step="0.01" min="0" max="1" value={zone.h} onChange={(e) => updateZone(zone.id, 'h', Number(e.target.value))} /></label>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="panel-header">
          <h2>Preview</h2>
        </div>
        {preview ? <img className="video-image" src={`data:image/jpeg;base64,${preview}`} alt="preview" /> : <div className="video-placeholder">Sem preview</div>}
        <p className="muted">Nesta versão, o ajuste de zonas é por coordenadas normalizadas. O backend já consome as zonas em tempo real.</p>
      </section>
    </div>
  )
}
