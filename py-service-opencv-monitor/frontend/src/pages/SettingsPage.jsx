export default function SettingsPage({ settings, onChange, onSave }) {
  return (
    <div className="panel form-grid">
      <h2>Configurações</h2>
      <label>Fonte da câmera
        <input value={settings.camera.source} onChange={(e) => onChange({ ...settings, camera: { ...settings.camera, source: e.target.value } })} />
      </label>
      <label>Largura
        <input type="number" value={settings.camera.width} onChange={(e) => onChange({ ...settings, camera: { ...settings.camera, width: Number(e.target.value) } })} />
      </label>
      <label>Altura
        <input type="number" value={settings.camera.height} onChange={(e) => onChange({ ...settings, camera: { ...settings.camera, height: Number(e.target.value) } })} />
      </label>
      <label>FPS limite
        <input type="number" value={settings.camera.fps_limit} onChange={(e) => onChange({ ...settings, camera: { ...settings.camera, fps_limit: Number(e.target.value) } })} />
      </label>
      <label>Modelo YOLO
        <input value={settings.model.path} onChange={(e) => onChange({ ...settings, model: { ...settings.model, path: e.target.value } })} />
      </label>
      <label>Confidence
        <input type="number" step="0.01" value={settings.model.confidence} onChange={(e) => onChange({ ...settings, model: { ...settings.model, confidence: Number(e.target.value) } })} />
      </label>
      <label>IoU
        <input type="number" step="0.01" value={settings.model.iou} onChange={(e) => onChange({ ...settings, model: { ...settings.model, iou: Number(e.target.value) } })} />
      </label>
      <label>Classes monitoradas
        <input value={settings.model.classes.join(', ')} onChange={(e) => onChange({ ...settings, model: { ...settings.model, classes: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) } })} />
      </label>
      <div className="actions-row">
        <button className="button primary" onClick={onSave}>Salvar configurações</button>
      </div>
    </div>
  )
}
