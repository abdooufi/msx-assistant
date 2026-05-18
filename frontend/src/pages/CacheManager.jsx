import { useEffect, useState } from 'react'
import axios from 'axios'
import { RefreshCw, Trash2, Database, Loader2, CheckCircle, AlertCircle } from 'lucide-react'

const api = axios.create({ baseURL: 'http://localhost:8001/api' })
api.interceptors.request.use(c => {
  const t = localStorage.getItem('msx_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

export default function CacheManager() {
  const [stats, setStats]           = useState(null)
  const [loading, setLoading]       = useState(true)
  const [clearing, setClearing]     = useState(false)
  const [symbol, setSymbol]         = useState('')
  const [message, setMessage]       = useState(null)

  const fetchStats = async () => {
    setLoading(true)
    try {
      const r = await api.get('/admin/cache/stats')
      setStats(r.data)
    } catch (e) {
      setStats({ status: 'unavailable' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchStats() }, [])

  const clearAll = async () => {
    if (!confirm('Clear ALL cache entries?')) return
    setClearing(true)
    try {
      const r = await api.delete('/admin/cache')
      setMessage({ type: 'success', text: r.data.message })
      fetchStats()
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to clear cache' })
    } finally {
      setClearing(false) }
  }

  const clearSymbol = async () => {
    if (!symbol.trim()) return
    setClearing(true)
    try {
      const r = await api.delete(`/admin/cache/${symbol.trim().toUpperCase()}`)
      setMessage({ type: 'success', text: r.data.message })
      setSymbol('')
      fetchStats()
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to clear symbol cache' })
    } finally { setClearing(false) }
  }

  const isConnected = stats?.status === 'connected'

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>Cache Manager</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>
            Redis cache for MSX.om API responses
          </p>
        </div>
        <button className="btn btn-ghost" onClick={fetchStats} disabled={loading}>
          <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
        </button>
      </div>

      {/* Status message */}
      {message && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', borderRadius: 10, marginBottom: 20,
          background: message.type === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
          border: `1px solid ${message.type === 'success' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
          color: message.type === 'success' ? 'var(--success)' : 'var(--danger)',
        }}>
          {message.type === 'success' ? <CheckCircle size={16}/> : <AlertCircle size={16}/>}
          {message.text}
          <button onClick={() => setMessage(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Stats card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <Database size={18} color="var(--accent)" />
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 16 }}>Redis Status</h3>
            <span style={{
              marginLeft: 'auto', fontSize: 12, padding: '3px 10px', borderRadius: 20,
              background: isConnected ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
              color: isConnected ? 'var(--success)' : 'var(--danger)',
            }}>
              ● {stats?.status || 'checking...'}
            </span>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>
              <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          ) : !isConnected ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: 10 }}>
              Redis is not running. Start it with:
              <pre style={{ background: 'var(--bg)', padding: 10, borderRadius: 8, marginTop: 8, fontSize: 12 }}>
                docker run -d --name msx_redis -p 6379:6379 redis:7-alpine
              </pre>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                ['Total Keys',      stats?.total_keys],
                ['MSX Cache Keys',  stats?.msx_keys],
                ['Used Memory',     stats?.used_memory],
                ['Peak Memory',     stats?.peak_memory],
                ['Max Memory',      stats?.maxmemory],
                ['Eviction Policy', stats?.eviction_policy],
              ].map(([label, val]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{val ?? '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cache control card */}
        <div className="card">
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 16, marginBottom: 20 }}>Cache Control</h3>

          {/* Clear by symbol */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
              Clear cache for a specific symbol
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <input
                placeholder="e.g. OQEP"
                value={symbol}
                onChange={e => setSymbol(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === 'Enter' && clearSymbol()}
                style={{ flex: 1 }}
              />
              <button
                className="btn btn-ghost"
                onClick={clearSymbol}
                disabled={!symbol.trim() || clearing}
                style={{ color: 'var(--warning)', borderColor: 'rgba(245,158,11,0.3)', whiteSpace: 'nowrap' }}
              >
                {clearing ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Trash2 size={14} />}
                Clear {symbol || 'Symbol'}
              </button>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 20 }}>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
              Clear all cached data (forces fresh API calls)
            </div>
            <button
              className="btn btn-danger"
              onClick={clearAll}
              disabled={clearing || !isConnected}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {clearing ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Trash2 size={14} />}
              Clear All Cache
            </button>
          </div>

          {/* TTL reference */}
          <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>Cache TTL by data type</div>
            {[
              ['Company Snapshot',  '5 min'],
              ['Last 20 Trades',    '1 min'],
              ['News',              '10 min'],
              ['Financial / Dividends', '1 hour'],
              ['Board / Subsidiaries',  '1 day'],
            ].map(([label, ttl]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ color: 'var(--text-dim)' }}>{label}</span>
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{ttl}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
