import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Bot, Lock, User, Loader2 } from 'lucide-react'

export default function AdminLogin() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    const ok = await login(username, password)
    if (ok) navigate('/admin/dashboard')
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logoWrap}>
          <Bot size={32} color="#00c5ff" />
        </div>
        <h1 style={styles.title}>MSX Admin</h1>
        <p style={styles.sub}>Sign in to manage the assistant</p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <User size={15} style={styles.fieldIcon} />
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={styles.input}
            />
          </div>
          <div style={styles.field}>
            <Lock size={15} style={styles.fieldIcon} />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={styles.input}
            />
          </div>
          <button type="submit" disabled={isLoading} style={styles.btn}>
            {isLoading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : 'Sign In'}
          </button>
        </form>

        <a href="/" style={styles.backLink}>← Back to Chat</a>
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

const styles = {
  page: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: 20 },
  card: { background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 16, padding: '40px 36px', width: '100%', maxWidth: 380, textAlign: 'center' },
  logoWrap: { width: 60, height: 60, borderRadius: 14, background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' },
  title: { fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, marginBottom: 6 },
  sub: { color: 'var(--text-muted)', fontSize: 14, marginBottom: 28 },
  error: { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16, textAlign: 'left' },
  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  field: { position: 'relative' },
  fieldIcon: { position: 'absolute', left: 13, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' },
  input: { paddingLeft: 38 },
  btn: { marginTop: 4, padding: '12px', background: 'var(--accent)', color: '#000', borderRadius: 10, fontWeight: 600, fontSize: 15, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 },
  backLink: { display: 'inline-block', marginTop: 24, fontSize: 13, color: 'var(--text-muted)' },
}
