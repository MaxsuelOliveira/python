import { NavLink } from 'react-router-dom'

const items = [
  ['/', 'Dashboard'],
  ['/rules', 'Regras'],
  ['/zones', 'Zonas'],
  ['/settings', 'Configurações'],
  ['/alerts', 'Alertas'],
  ['/history', 'Histórico'],
]

export default function Layout({ children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Environment Monitor</div>
        <nav className="nav">
          {items.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  )
}
