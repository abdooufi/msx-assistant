import { useEffect, useState } from 'react'
import { listFAQs, createFAQ, updateFAQ, deleteFAQ } from '../api'
import { Plus, Pencil, Trash2, Check, X, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react'

const EMPTY = { question: '', answer: '', category: 'general', is_active: true }

export default function FAQManager() {
  const [faqs, setFaqs] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState(EMPTY)
  const [editId, setEditId] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')

  const fetchFAQs = async () => {
    setLoading(true)
    try { const r = await listFAQs(); setFaqs(r.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchFAQs() }, [])

  const openCreate = () => { setForm(EMPTY); setEditId(null); setShowForm(true) }
  const openEdit = (faq) => { setForm({ question: faq.question, answer: faq.answer, category: faq.category, is_active: faq.is_active }); setEditId(faq.id); setShowForm(true) }
  const closeForm = () => { setShowForm(false); setEditId(null); setForm(EMPTY) }

  const handleSave = async () => {
    if (!form.question.trim() || !form.answer.trim()) return
    setSaving(true)
    try {
      if (editId) { await updateFAQ(editId, form) }
      else { await createFAQ(form) }
      await fetchFAQs()
      closeForm()
    } catch (e) { console.error(e) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this FAQ?')) return
    await deleteFAQ(id)
    setFaqs((prev) => prev.filter((f) => f.id !== id))
  }

  const handleToggle = async (faq) => {
    await updateFAQ(faq.id, { is_active: !faq.is_active })
    setFaqs((prev) => prev.map((f) => f.id === faq.id ? { ...f, is_active: !f.is_active } : f))
  }

  const filtered = faqs.filter((f) =>
    f.question.toLowerCase().includes(search.toLowerCase()) ||
    f.category.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>FAQ Manager</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>{faqs.length} entries</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add FAQ</button>
      </div>

      <input placeholder="Search FAQs..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 16, maxWidth: 340 }} />

      {/* Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20, border: '1px solid var(--accent-glow)' }}>
          <h3 style={{ marginBottom: 16, fontFamily: 'var(--font-display)' }}>{editId ? 'Edit FAQ' : 'New FAQ'}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <input placeholder="Category (e.g. support, sales)" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} style={{ flex: 1 }} />
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', color: 'var(--text-dim)', fontSize: 14, whiteSpace: 'nowrap' }}>
                <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} style={{ width: 'auto' }} />
                Active
              </label>
            </div>
            <input placeholder="Question" value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} />
            <textarea placeholder="Answer" value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} rows={4} style={{ resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={14} />}
                {editId ? 'Update' : 'Create'}
              </button>
              <button className="btn btn-ghost" onClick={closeForm}><X size={14} /> Cancel</button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Loading...</div>
      ) : filtered.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No FAQs found.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map((faq) => (
            <div key={faq.id} className="card" style={{ opacity: faq.is_active ? 1 : 0.5 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span className={`badge badge-${faq.category}`}>{faq.category}</span>
                    {!faq.is_active && <span className="badge" style={{ background: 'rgba(100,116,139,0.15)', color: 'var(--text-muted)' }}>Inactive</span>}
                  </div>
                  <div style={{ fontWeight: 500, marginBottom: 6 }}>Q: {faq.question}</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 13, lineHeight: 1.5 }}>A: {faq.answer}</div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={() => handleToggle(faq)} title="Toggle active">
                    {faq.is_active ? <ToggleRight size={16} color="var(--success)" /> : <ToggleLeft size={16} />}
                  </button>
                  <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={() => openEdit(faq)}>
                    <Pencil size={14} />
                  </button>
                  <button className="btn btn-danger" style={{ padding: '6px 10px' }} onClick={() => handleDelete(faq.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
