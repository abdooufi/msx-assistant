import { useEffect, useState } from 'react'
import { listUnanswered, updateUnanswered, deleteUnanswered } from '../api'
import { Trash2, CheckCircle, Eye, MessageSquare, AlertCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useToast, ToastContainer } from '../components/Toast'

const STATUS_TABS = ['pending', 'reviewed', 'answered']

export default function UnansweredPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(null)
  const [tab, setTab] = useState('pending')
  const [noteMap, setNoteMap] = useState({})
  const toast = useToast()

  const fetchItems = async () => {
    setLoading(true)
    setFetchError(null)
    try { const r = await listUnanswered({ status: tab }); setItems(r.data) }
    catch (e) { setFetchError('Failed to load questions. Please try again.') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchItems() }, [tab])

  const handleUpdate = async (id, data) => {
    try {
      await updateUnanswered(id, data)
      toast.success(data.status ? `Marked as ${data.status}` : 'Note saved')
      fetchItems()
    } catch (e) {
      toast.error('Failed to update question')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this entry?')) return
    try {
      await deleteUnanswered(id)
      setItems((prev) => prev.filter((i) => i.id !== id))
      toast.success('Entry deleted')
    } catch (e) {
      toast.error('Failed to delete entry')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>Unanswered Questions</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>Questions the assistant couldn't answer well — review and add to FAQ/KB</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--bg-card)', padding: 4, borderRadius: 10, border: '1px solid var(--border)', width: 'fit-content' }}>
        {STATUS_TABS.map((s) => (
          <button key={s} onClick={() => setTab(s)} style={{ padding: '7px 18px', borderRadius: 8, background: tab === s ? 'var(--accent-dim)' : 'transparent', color: tab === s ? 'var(--accent)' : 'var(--text-muted)', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: tab === s ? 600 : 400, textTransform: 'capitalize', transition: 'all 0.15s' }}>
            {s}
          </button>
        ))}
      </div>

      {fetchError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          <AlertCircle size={16} /> {fetchError}
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Loading...</div>
      ) : items.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 60 }}>
          <MessageSquare size={36} style={{ marginBottom: 12, opacity: 0.3 }} />
          <div>No {tab} questions.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((item) => (
            <div key={item.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                    <span className={`badge badge-${item.status}`}>{item.status}</span>
                    <span className={`badge badge-${item.classification}`}>{item.classification?.replace('_', ' ')}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {item.created_at ? formatDistanceToNow(new Date(item.created_at), { addSuffix: true }) : ''}
                    </span>
                  </div>
                  <div style={{ fontWeight: 500, marginBottom: 8 }}>"{item.question}"</div>

                  {/* Admin note */}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      placeholder="Add admin note..."
                      value={noteMap[item.id] ?? item.admin_note ?? ''}
                      onChange={(e) => setNoteMap((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      style={{ flex: 1, fontSize: 13, padding: '7px 12px' }}
                    />
                    <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={() => handleUpdate(item.id, { admin_note: noteMap[item.id] ?? item.admin_note })}>
                      Save Note
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {item.status === 'pending' && (
                    <button className="btn btn-ghost" style={{ padding: '6px 10px' }} title="Mark reviewed" onClick={() => handleUpdate(item.id, { status: 'reviewed' })}>
                      <Eye size={14} />
                    </button>
                  )}
                  {item.status !== 'answered' && (
                    <button className="btn btn-ghost" style={{ padding: '6px 10px', color: 'var(--success)' }} title="Mark answered" onClick={() => handleUpdate(item.id, { status: 'answered' })}>
                      <CheckCircle size={14} />
                    </button>
                  )}
                  <button className="btn btn-danger" style={{ padding: '6px 10px' }} onClick={() => handleDelete(item.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
    </div>
  )
}
