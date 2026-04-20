import { useState } from 'react'

export default function AlertsPage({ onTestAlert }) {
  const [action, setAction] = useState({ type: 'webhook', enabled: true, url: 'https://example.com/webhook' })

  return (
    <div className="panel form-grid">
      <h2>Integrações / Alertas</h2>
      <label>Tipo
        <select value={action.type} onChange={(e) => setAction({ ...action, type: e.target.value })}>
          <option value="webhook">Webhook</option>
          <option value="slack">Slack</option>
          <option value="telegram">Telegram</option>
          <option value="email">Email</option>
        </select>
      </label>
      {action.type === 'webhook' && (
        <label>URL
          <input value={action.url || ''} onChange={(e) => setAction({ ...action, url: e.target.value })} />
        </label>
      )}
      {action.type === 'slack' && (
        <label>Slack webhook URL
          <input value={action.webhook_url || ''} onChange={(e) => setAction({ ...action, webhook_url: e.target.value })} />
        </label>
      )}
      {action.type === 'telegram' && (
        <>
          <label>Bot token
            <input value={action.bot_token || ''} onChange={(e) => setAction({ ...action, bot_token: e.target.value })} />
          </label>
          <label>Chat ID
            <input value={action.chat_id || ''} onChange={(e) => setAction({ ...action, chat_id: e.target.value })} />
          </label>
        </>
      )}
      {action.type === 'email' && (
        <>
          <label>SMTP host
            <input value={action.smtp_host || 'smtp.gmail.com'} onChange={(e) => setAction({ ...action, smtp_host: e.target.value })} />
          </label>
          <label>SMTP port
            <input type="number" value={action.smtp_port || 587} onChange={(e) => setAction({ ...action, smtp_port: Number(e.target.value) })} />
          </label>
          <label>Usuário
            <input value={action.username || ''} onChange={(e) => setAction({ ...action, username: e.target.value })} />
          </label>
          <label>Senha
            <input type="password" value={action.password || ''} onChange={(e) => setAction({ ...action, password: e.target.value })} />
          </label>
          <label>De
            <input value={action.from_email || ''} onChange={(e) => setAction({ ...action, from_email: e.target.value })} />
          </label>
          <label>Para
            <input value={(action.to || ['']).join(', ')} onChange={(e) => setAction({ ...action, to: e.target.value.split(',').map((v) => v.trim()) })} />
          </label>
        </>
      )}
      <div className="actions-row">
        <button className="button primary" onClick={() => onTestAlert(action)}>Enviar teste</button>
      </div>
    </div>
  )
}
