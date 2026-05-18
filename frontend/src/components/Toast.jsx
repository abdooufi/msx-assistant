import { useState, useCallback } from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

const ICONS = {
  success: CheckCircle,
  error:   XCircle,
  info:    Info,
}

const COLORS = {
  success: { bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)', icon: '#10b981', text: '#6ee7b7' },
  error:   { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.35)',  icon: '#ef4444', text: '#fca5a5' },
  info:    { bg: 'var(--bg-card)',         border: 'var(--border)',          icon: 'var(--accent)', text: 'var(--text)' },
}

function Toast({ id, message, type, onDismiss }) {
  const Icon = ICONS[type] || Info
  const c    = COLORS[type] || COLORS.info
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '12px 16px', borderRadius: 10, minWidth: 260, maxWidth: 360,
      background: c.bg, border: `1px solid ${c.border}`,
      boxShadow: 'var(--shadow)', animation: 'toast-in 0.2s ease',
    }}>
      <Icon size={16} color={c.icon} style={{ marginTop: 1, flexShrink: 0 }} />
      <span style={{ flex: 1, fontSize: 13, lineHeight: 1.5, color: c.text }}>{message}</span>
      <button
        onClick={() => onDismiss(id)}
        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--text-muted)', flexShrink: 0 }}
      >
        <X size={13} />
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      {toasts.map(t => (
        <Toast key={t.id} {...t} onDismiss={onDismiss} />
      ))}
    </div>
  )
}

export function useToast() {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const show = useCallback((message, type = 'info', duration = 3500) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration)
    return id
  }, [])

  return {
    toasts,
    dismiss,
    success: (msg) => show(msg, 'success'),
    error:   (msg) => show(msg, 'error'),
    info:    (msg) => show(msg, 'info'),
  }
}
