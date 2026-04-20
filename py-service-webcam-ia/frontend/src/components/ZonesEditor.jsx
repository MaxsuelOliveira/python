import { useEffect, useMemo, useRef, useState } from 'react'

const MIN_SIZE = 0.04

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value))
}

function zoneStyle(zone) {
  return {
    left: `${zone.x * 100}%`,
    top: `${zone.y * 100}%`,
    width: `${zone.w * 100}%`,
    height: `${zone.h * 100}%`,
    borderColor: zone.color || '#60a5fa',
    boxShadow: `inset 0 0 0 1px ${zone.color || '#60a5fa'}55`,
  }
}

export default function ZonesEditor({ payload, onChange, preview, onSave }) {
  const [selectedId, setSelectedId] = useState(payload.zones[0]?.id || null)
  const [drag, setDrag] = useState(null)
  const stageRef = useRef(null)

  useEffect(() => {
    if (!payload.zones.some((zone) => zone.id === selectedId)) {
      setSelectedId(payload.zones[0]?.id || null)
    }
  }, [payload.zones, selectedId])

  const selectedZone = useMemo(
    () => payload.zones.find((zone) => zone.id === selectedId) || null,
    [payload.zones, selectedId],
  )

  function updateZone(id, patch) {
    onChange({
      ...payload,
      zones: payload.zones.map((zone) => zone.id === id ? { ...zone, ...patch } : zone),
    })
  }

  function addZone() {
    const zone = {
      id: `zone_${Math.random().toString(36).slice(2, 8)}`,
      name: `Zona ${payload.zones.length + 1}`,
      shape: 'rect',
      x: 0.15,
      y: 0.15,
      w: 0.3,
      h: 0.25,
      color: ['#f97316', '#22c55e', '#3b82f6', '#eab308', '#a855f7'][payload.zones.length % 5],
    }
    onChange({ ...payload, zones: [...payload.zones, zone] })
    setSelectedId(zone.id)
  }

  function duplicateZone(id) {
    const zone = payload.zones.find((item) => item.id === id)
    if (!zone) return
    const clone = {
      ...zone,
      id: `${zone.id}_copy_${Math.random().toString(36).slice(2, 5)}`,
      name: `${zone.name} (cópia)`,
      x: clamp(zone.x + 0.03),
      y: clamp(zone.y + 0.03),
    }
    onChange({ ...payload, zones: [...payload.zones, clone] })
    setSelectedId(clone.id)
  }

  function removeZone(id) {
    onChange({ ...payload, zones: payload.zones.filter((zone) => zone.id !== id) })
  }

  function getNormPoint(event) {
    const rect = stageRef.current?.getBoundingClientRect()
    if (!rect) return null
    return {
      x: clamp((event.clientX - rect.left) / rect.width),
      y: clamp((event.clientY - rect.top) / rect.height),
    }
  }

  function startDrag(event, zone, mode) {
    event.preventDefault()
    event.stopPropagation()
    const point = getNormPoint(event)
    if (!point) return
    setSelectedId(zone.id)
    setDrag({
      id: zone.id,
      mode,
      pointerStart: point,
      zoneStart: { x: zone.x, y: zone.y, w: zone.w, h: zone.h },
    })
  }

  useEffect(() => {
    function handleMove(event) {
      if (!drag) return
      const point = getNormPoint(event)
      if (!point) return
      const dx = point.x - drag.pointerStart.x
      const dy = point.y - drag.pointerStart.y
      const start = drag.zoneStart
      let next = { ...start }

      if (drag.mode === 'move') {
        next.x = clamp(start.x + dx, 0, 1 - start.w)
        next.y = clamp(start.y + dy, 0, 1 - start.h)
      }

      if (drag.mode === 'resize-se') {
        next.w = clamp(start.w + dx, MIN_SIZE, 1 - start.x)
        next.h = clamp(start.h + dy, MIN_SIZE, 1 - start.y)
      }

      if (drag.mode === 'resize-e') {
        next.w = clamp(start.w + dx, MIN_SIZE, 1 - start.x)
      }

      if (drag.mode === 'resize-s') {
        next.h = clamp(start.h + dy, MIN_SIZE, 1 - start.y)
      }

      if (drag.mode === 'resize-nw') {
        const newX = clamp(start.x + dx, 0, start.x + start.w - MIN_SIZE)
        const newY = clamp(start.y + dy, 0, start.y + start.h - MIN_SIZE)
        next.x = newX
        next.y = newY
        next.w = clamp(start.w + (start.x - newX), MIN_SIZE, 1 - newX)
        next.h = clamp(start.h + (start.y - newY), MIN_SIZE, 1 - newY)
      }

      updateZone(drag.id, {
        x: Number(next.x.toFixed(4)),
        y: Number(next.y.toFixed(4)),
        w: Number(next.w.toFixed(4)),
        h: Number(next.h.toFixed(4)),
      })
    }

    function handleUp() {
      setDrag(null)
    }

    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
    return () => {
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
    }
  }, [drag, payload])

  return (
    <div className="zones-layout">
      <section className="panel zones-list-panel">
        <div className="panel-header">
          <div>
            <h2>Editor de zonas</h2>
            <p className="muted">Desenhe e ajuste áreas sobre o frame da câmera.</p>
          </div>
          <button className="button" onClick={addZone}>Nova zona</button>
        </div>

        <div className="stack zones-stack">
          {payload.zones.map((zone) => (
            <button
              key={zone.id}
              className={`zone-card zone-list-item ${selectedId === zone.id ? 'active' : ''}`}
              onClick={() => setSelectedId(zone.id)}
            >
              <div className="event-top">
                <strong>{zone.name}</strong>
                <span className="pill" style={{ background: `${zone.color}22`, color: zone.color }}>{zone.id}</span>
              </div>
              <div className="muted small">x {zone.x.toFixed(2)} · y {zone.y.toFixed(2)} · w {zone.w.toFixed(2)} · h {zone.h.toFixed(2)}</div>
            </button>
          ))}
        </div>

        {selectedZone && (
          <div className="zone-form stack">
            <div className="panel-header compact-header">
              <h3>Ajustes da zona</h3>
              <div className="inline-actions">
                <button className="button" onClick={() => duplicateZone(selectedZone.id)}>Duplicar</button>
                <button className="button danger" onClick={() => removeZone(selectedZone.id)}>Remover</button>
              </div>
            </div>
            <label>Nome<input value={selectedZone.name} onChange={(e) => updateZone(selectedZone.id, { name: e.target.value })} /></label>
            <label>ID<input value={selectedZone.id} onChange={(e) => updateZone(selectedZone.id, { id: e.target.value.replace(/\s+/g, '_') })} /></label>
            <label>Cor<input type="color" value={selectedZone.color || '#3b82f6'} onChange={(e) => updateZone(selectedZone.id, { color: e.target.value })} /></label>
            <div className="quad-grid">
              <label>X<input type="number" step="0.01" min="0" max="1" value={selectedZone.x} onChange={(e) => updateZone(selectedZone.id, { x: clamp(Number(e.target.value), 0, 1) })} /></label>
              <label>Y<input type="number" step="0.01" min="0" max="1" value={selectedZone.y} onChange={(e) => updateZone(selectedZone.id, { y: clamp(Number(e.target.value), 0, 1) })} /></label>
              <label>W<input type="number" step="0.01" min="0.04" max="1" value={selectedZone.w} onChange={(e) => updateZone(selectedZone.id, { w: clamp(Number(e.target.value), MIN_SIZE, 1) })} /></label>
              <label>H<input type="number" step="0.01" min="0.04" max="1" value={selectedZone.h} onChange={(e) => updateZone(selectedZone.id, { h: clamp(Number(e.target.value), MIN_SIZE, 1) })} /></label>
            </div>
          </div>
        )}

        <div className="actions-row left-actions">
          <button className="button primary" onClick={onSave}>Salvar zonas</button>
        </div>
      </section>

      <section className="panel zones-canvas-panel">
        <div className="panel-header">
          <div>
            <h2>Preview visual</h2>
            <p className="muted">Arraste a zona para mover. Use os cantos e bordas para redimensionar.</p>
          </div>
        </div>

        <div className="zone-stage-shell">
          <div className="zone-stage" ref={stageRef}>
            {preview ? (
              <img className="video-image zone-stage-image" src={`data:image/jpeg;base64,${preview}`} alt="preview" draggable="false" />
            ) : (
              <div className="video-placeholder zone-stage-placeholder">Sem preview da câmera</div>
            )}

            {payload.zones.map((zone) => (
              <div
                key={zone.id}
                className={`zone-overlay ${selectedId === zone.id ? 'selected' : ''}`}
                style={zoneStyle(zone)}
                onPointerDown={(event) => startDrag(event, zone, 'move')}
                onClick={() => setSelectedId(zone.id)}
              >
                <div className="zone-overlay-label" style={{ background: zone.color || '#60a5fa' }}>
                  {zone.name}
                </div>
                <div className="zone-handle zone-handle-se" onPointerDown={(event) => startDrag(event, zone, 'resize-se')} />
                <div className="zone-handle zone-handle-e" onPointerDown={(event) => startDrag(event, zone, 'resize-e')} />
                <div className="zone-handle zone-handle-s" onPointerDown={(event) => startDrag(event, zone, 'resize-s')} />
                <div className="zone-handle zone-handle-nw" onPointerDown={(event) => startDrag(event, zone, 'resize-nw')} />
              </div>
            ))}
          </div>
        </div>

        <div className="muted small zone-help">
          Dica: use o frame atual para encaixar a área do sofá, cama ou quarto. Depois associe a zona às regras na tela de regras.
        </div>
      </section>
    </div>
  )
}
