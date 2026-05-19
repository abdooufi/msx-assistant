import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  Bot, LayoutDashboard, MessageSquareOff, BookOpen,
  HelpCircle, LogOut, ExternalLink, Building2, Plug, Database, Settings2
} from 'lucide-react'

const NAV = [
  { to: '/admin/dashboard',   icon: LayoutDashboard,  label: 'Dashboard' },
  { to: '/admin/faq',         icon: HelpCircle,        label: 'FAQ Manager' },
  { to: '/admin/knowledge',   icon: BookOpen,          label: 'Knowledge Base' },
  { to: '/admin/companies',   icon: Building2,         label: 'Companies' },
  { to: '/admin/endpoints',   icon: Plug,              label: 'API Endpoints' },
  { to: '/admin/cache',       icon: Database,          label: 'Cache Manager' },
  { to: '/admin/unanswered',  icon: MessageSquareOff,  label: 'Unanswered' },
  { to: '/admin/ai-settings', icon: Settings2,         label: 'AI Provider' },
]

export default function AdminLayout() {
  const { logout } = useAuth()
  const navigate   = useNavigate()

  return (
    <div style={styles.layout}>
      <aside style={styles.sidebar}>
        <div style={styles.brand}>
          <div style={styles.brandIcon}><Bot size={20} color="#00c5ff"/></div>
          <div>
            <div style={styles.brandName}>MSX</div>
            <div style={styles.brandSub}>Admin Panel</div>
          </div>
        </div>

        <nav style={styles.nav}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to}
              style={({ isActive }) => ({ ...styles.navItem, ...(isActive ? styles.navActive : {}) })}>
              <Icon size={17}/> {label}
            </NavLink>
          ))}
        </nav>

        <div style={styles.sidebarBottom}>
          <a href="/" target="_blank" style={styles.navItem}>
            <ExternalLink size={17}/> View Chat
          </a>
          <button
            onClick={() => { logout(); navigate('/admin/login') }}
            style={{ ...styles.navItem, cursor: 'pointer', border: 'none', background: 'none', width: '100%', color: '#fca5a5' }}>
            <LogOut size={17}/> Logout
          </button>
        </div>
      </aside>

      <main style={styles.main}><Outlet/></main>
    </div>
  )
}

const styles = {
  layout:        { display: 'flex', height: '100vh', overflow: 'hidden' },
  sidebar:       { width: 220, background: 'var(--bg-card)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', padding: '20px 12px', flexShrink: 0 },
  brand:         { display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 20px', marginBottom: 8, borderBottom: '1px solid var(--border)' },
  brandIcon:     { width: 36, height: 36, borderRadius: 9, background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  brandName:     { fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16 },
  brandSub:      { fontSize: 11, color: 'var(--text-muted)' },
  nav:           { display: 'flex', flexDirection: 'column', gap: 2, flex: 1 },
  navItem:       { display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8, color: 'var(--text-muted)', fontSize: 14, textDecoration: 'none', transition: 'all 0.15s' },
  navActive:     { background: 'var(--accent-dim)', color: 'var(--accent)', fontWeight: 500 },
  sidebarBottom: { borderTop: '1px solid var(--border)', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 2 },
  main:          { flex: 1, overflowY: 'auto', padding: '28px 32px' },
}
