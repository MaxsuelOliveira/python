import { useMemo, useState } from 'react'

function emptyRule() {
  return {
    id: `rule_${Math.random().toString(36).slice(2, 8)}`,
    name: 'Nova regra',
    enabled: true,
    cooldown_seconds: 20,
    condition: {
      type: 'object_in_zone',
      object: 'dog',
      zone_id: 'sofa_area',
      min_confidence: 0.45,
      min_overlap: 0.15,
      for_frames: 4,
    },
    actions: [{ type: 'websocket' }, { type: 'snapshot' }],
  }
}

export default function RuleEditor({ payload, onChange, onSave }) {
  const [selectedId, setSelectedId] = useState(payload.rules[0]?.id || null)
  const selected = useMemo(() => payload.rules.find((r) => r.id === selectedId) || payload.rules[0], [payload, selectedId])

  function updateRule(nextRule) {
    const rules = payload.rules.map((rule) => rule.id === nextRule.id ? nextRule : rule)
    onChange({ ...payload, rules })
  }

  function addRule() {
    const rule = emptyRule()
    onChange({ ...payload, rules: [...payload.rules, rule] })
    setSelectedId(rule.id)
  }

  function removeRule(id) {
    const rules = payload.rules.filter((rule) => rule.id !== id)
    onChange({ ...payload, rules })
    setSelectedId(rules[0]?.id || null)
  }

  return (
    <div className="two-col">
      <section className="panel">
        <div className="panel-header">
          <h2>Regras</h2>
          <button className="button" onClick={addRule}>Nova regra</button>
        </div>
        <div className="stack">
          {payload.rules.map((rule) => (
            <div key={rule.id} className={rule.id === selected?.id ? 'list-item active' : 'list-item'} onClick={() => setSelectedId(rule.id)}>
              <div>
                <strong>{rule.name}</strong>
                <div className="small muted">{rule.condition.type}</div>
              </div>
              <span className="pill">{rule.enabled ? 'ON' : 'OFF'}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        {selected ? (
          <div className="form-grid">
            <label>Nome
              <input value={selected.name} onChange={(e) => updateRule({ ...selected, name: e.target.value })} />
            </label>
            <label>ID
              <input value={selected.id} onChange={(e) => updateRule({ ...selected, id: e.target.value })} />
            </label>
            <label>Habilitada
              <select value={String(selected.enabled)} onChange={(e) => updateRule({ ...selected, enabled: e.target.value === 'true' })}>
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </select>
            </label>
            <label>Cooldown (s)
              <input type="number" value={selected.cooldown_seconds} onChange={(e) => updateRule({ ...selected, cooldown_seconds: Number(e.target.value) })} />
            </label>
            <label>Tipo de condição
              <select value={selected.condition.type} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, type: e.target.value } })}>
                <option value="object_present">Object present</option>
                <option value="object_in_zone">Object in zone</option>
                <option value="object_absent">Object absent</option>
                <option value="overlap">Overlap</option>
              </select>
            </label>
            <label>Objeto
              <input value={selected.condition.object || ''} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, object: e.target.value } })} />
            </label>
            <label>Zona
              <select value={selected.condition.zone_id || ''} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, zone_id: e.target.value } })}>
                {payload.zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
              </select>
            </label>
            <label>Confiança mínima
              <input type="number" step="0.01" value={selected.condition.min_confidence || 0.45} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, min_confidence: Number(e.target.value) } })} />
            </label>
            <label>Overlap mínimo
              <input type="number" step="0.01" value={selected.condition.min_overlap || 0.15} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, min_overlap: Number(e.target.value) } })} />
            </label>
            <label>Frames mínimos
              <input type="number" value={selected.condition.for_frames || 1} onChange={(e) => updateRule({ ...selected, condition: { ...selected.condition, for_frames: Number(e.target.value) } })} />
            </label>
          </div>
        ) : <div className="muted">Crie uma regra para começar.</div>}
        <div className="actions-row">
          {selected && <button className="button danger" onClick={() => removeRule(selected.id)}>Excluir</button>}
          <button className="button primary" onClick={onSave}>Salvar tudo</button>
        </div>
      </section>
    </div>
  )
}
