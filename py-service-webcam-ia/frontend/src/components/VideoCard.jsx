export default function VideoCard({ state, rules }) {
  const imageSrc = state?.latest_preview_b64 ? `data:image/jpeg;base64,${state.latest_preview_b64}` : null

  return (
    <section className="panel video-panel">
      <div className="panel-header">
        <h2>Monitor ao vivo</h2>
        <span className="pill">{state?.running ? 'Ativo' : 'Parado'}</span>
      </div>
      <div className="video-wrapper">
        {imageSrc ? <img src={imageSrc} alt="preview" className="video-image" /> : <div className="video-placeholder">Aguardando frames...</div>}
      </div>
      <div className="info-grid compact">
        <div><strong>Fonte:</strong> {state?.source}</div>
        <div><strong>Modelo:</strong> {state?.model_name}</div>
        <div><strong>FPS:</strong> {state?.fps?.toFixed?.(1) ?? 0}</div>
        <div><strong>Regras ativas:</strong> {rules?.rules?.filter(r => r.enabled).length ?? 0}</div>
      </div>
    </section>
  )
}
