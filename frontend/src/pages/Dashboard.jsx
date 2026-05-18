import { useEffect, useState } from 'react'
import { getStats } from '../api'
import { MessageSquare, BookOpen, HelpCircle, AlertCircle, TrendingUp, RefreshCw } from 'lucide-react'

const StatCard = ({ icon: Icon, label, value, color = 'var(--accent)' }) => (
  <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
    <div style={{ width: 48, height: 48, borderRadius: 12, background: `${color}20`, border: `1px solid ${color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Icon size={22} color={color} />
    </div>
    <div>
      <div style={{ fontSize: 26, fontWeight: 700, fontFamily: 'var(--font-display)' }}>{value ?? '—'}</div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</div>
    </div>
  </div>
)

const CLASS_COLORS = { support: '#00c5ff', sales: '#10b981', complaint: '#ef4444', general_inquiry: '#94a3b8' }

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = async () => {
    setLoading(true)
    try {
      const res = await getStats()
      setStats(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchStats() }, [])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>Dashboard</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>Overview of MSX Assistant activity</p>
        </div>
        <button className="btn btn-ghost" onClick={fetchStats}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 60 }}>Loading stats...</div>
      ) : (
        <>
          {/* Stat cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
            <StatCard icon={MessageSquare} label="Total Conversations" value={stats?.total_conversations} color="#00c5ff" />
            <StatCard icon={TrendingUp} label="Total Messages" value={stats?.total_messages} color="#7c3aed" />
            <StatCard icon={AlertCircle} label="Unanswered (Pending)" value={stats?.unanswered_count} color="#f59e0b" />
            <StatCard icon={HelpCircle} label="FAQ Entries" value={stats?.faq_count} color="#10b981" />
            <StatCard icon={BookOpen} label="Knowledge Articles" value={stats?.knowledge_count} color="#ec4899" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Classification breakdown */}
            <div className="card">
              <h3 style={{ fontFamily: 'var(--font-display)', marginBottom: 16, fontSize: 15 }}>Query Classifications</h3>
              {Object.entries(stats?.classification_breakdown || {}).length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No data yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {Object.entries(stats?.classification_breakdown || {}).map(([k, v]) => {
                    const total = Object.values(stats.classification_breakdown).reduce((a, b) => a + b, 0)
                    const pct = total ? Math.round((v / total) * 100) : 0
                    return (
                      <div key={k}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                          <span style={{ textTransform: 'capitalize' }}>{k.replace('_', ' ')}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{v} ({pct}%)</span>
                        </div>
                        <div style={{ height: 6, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: CLASS_COLORS[k] || '#64748b', borderRadius: 3, transition: 'width 0.5s ease' }} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Top KB categories */}
            <div className="card">
              <h3 style={{ fontFamily: 'var(--font-display)', marginBottom: 16, fontSize: 15 }}>Knowledge Base Categories</h3>
              {stats?.top_categories?.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No knowledge base articles yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {stats?.top_categories?.map((cat) => (
                    <div key={cat.category} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bg-hover)', borderRadius: 8 }}>
                      <span style={{ fontSize: 14, textTransform: 'capitalize' }}>{cat.category}</span>
                      <span style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 600 }}>{cat.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
