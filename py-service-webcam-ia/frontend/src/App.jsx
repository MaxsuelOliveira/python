import { useEffect, useMemo, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import RulesPage from './pages/RulesPage'
import ZonesPage from './pages/ZonesPage'
import SettingsPage from './pages/SettingsPage'
import AlertsPage from './pages/AlertsPage'
import HistoryPage from './pages/HistoryPage'
import { apiGet, apiPost, apiPut } from './lib/api'

export default function App() {
  const [state, setState] = useState({ running: false, detections: [], recent_event_ids: [] })
  const [settings, setSettings] = useState({ camera: {}, model: { classes: [] }, alerts: {} })
  const [rulesPayload, setRulesPayload] = useState({ zones: [], rules: [] })
  const [events, setEvents] = useState([])
  const [message, setMessage] = useState('')

  async function loadAll() {
    const [stateData, settingsData, rulesData, eventsData] = await Promise.all([
      apiGet('/api/state'),
      apiGet('/api/settings'),
      apiGet('/api/rules'),
      apiGet('/api/events?limit=50'),
    ])
    setState(stateData)
    setSettings(settingsData)
    setRulesPayload(rulesData)
    setEvents(eventsData)
  }

  useEffect(() => {
    loadAll().catch(console.error)
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws`)
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data)
      if (data.type === 'state') setState(data.payload)
      if (data.type === 'event') setEvents((current) => [data.payload, ...current].slice(0, 200))
    }
    const ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('ping'), 5000)
    return () => {
      clearInterval(ping)
      ws.close()
    }
  }, [])

  async function saveRules() {
    await apiPut('/api/rules', rulesPayload)
    setMessage('Regras salvas com sucesso.')
  }

  async function saveSettings() {
    await apiPut('/api/settings', settings)
    setMessage('Configurações salvas com sucesso.')
  }

  async function testAlert(action) {
    await apiPost('/api/alerts/test', action)
    setMessage('Alerta de teste enviado.')
    const eventsData = await apiGet('/api/events?limit=50')
    setEvents(eventsData)
  }

  const topInfo = useMemo(() => (
    <div className="topbar">
      <div className="stat-card"><span>Status</span><strong>{state.running ? 'Monitorando' : 'Parado'}</strong></div>
      <div className="stat-card"><span>Detecções atuais</span><strong>{state.detections?.length || 0}</strong></div>
      <div className="stat-card"><span>Modelo</span><strong>{state.model_name || '-'}</strong></div>
      <div className="stat-card"><span>Último frame</span><strong>{state.latest_frame_ts ? new Date(state.latest_frame_ts).toLocaleTimeString() : '-'}</strong></div>
    </div>
  ), [state])

  return (
    <Layout>
      {topInfo}
      {message && <div className="toast">{message}</div>}
      <Routes>
        <Route path="/" element={<Dashboard state={state} rules={rulesPayload} events={events} />} />
        <Route path="/rules" element={<RulesPage payload={rulesPayload} onChange={setRulesPayload} onSave={saveRules} />} />
        <Route path="/zones" element={<ZonesPage payload={rulesPayload} onChange={setRulesPayload} state={state} />} />
        <Route path="/settings" element={<SettingsPage settings={settings} onChange={setSettings} onSave={saveSettings} />} />
        <Route path="/alerts" element={<AlertsPage onTestAlert={testAlert} />} />
        <Route path="/history" element={<HistoryPage events={events} />} />
      </Routes>
    </Layout>
  )
}
