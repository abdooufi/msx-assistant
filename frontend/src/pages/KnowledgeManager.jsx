import { useEffect, useState } from 'react'
import { listKnowledge, createKnowledge, updateKnowledge, deleteKnowledge } from '../api'
import { Plus, Pencil, Trash2, Check, X, Tag, Loader2 } from 'lucide-react'

const EMPTY = { title: '', content: '', category: 'general', tags: [], source: '' }

export default function KnowledgeManager() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState(EMPTY)
  const [tagInput, setTagInput] = useState('')
  const [editId, setEditId] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')

  const fetchDocs = async () => {
    setLoading(true)
    try { const r = await listKnowledge({ limit: 100 }); setDocs(r.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchDocs() }, [])

  const openCreate = () => { setForm(EMPTY); setTagInput(''); setEditId(null); setShowForm(true) }
  const openEdit = (doc) => {
    setForm({ title: doc.title, content: doc.content, category: doc.category, tags: doc.tags, source: doc.source || '' })
    setTagInput('')
    setEditId(doc.id)
    setShowForm(true)
  }
  const closeForm = () => { setShowForm(false); setEditId(null); setForm(EMPTY) }

  const addTag = () => {
    const t = tagInput.trim()
    if (t && !form.tags.includes(t)) setForm((f) => ({ ...f, tags: [...f.tags, t] }))
    setTagInput('')
  }

  const removeTag = (tag) => setForm((f) => ({ ...f, tags: f.tags.filter((t) => t !== tag) }))

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) return
    setSaving(true)
    try {
      if (editId) { await updateKnowledge(editId, form) }
      else { await createKnowledge(form) }
      await fetchDocs()
      closeForm()
    } catch (e) { console.error(e) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this article?')) return
    await deleteKnowledge(id)
    setDocs((prev) => prev.filter((d) => d.id !== id))
  }

  const filtered = docs.filter((d) =>
    d.title.toLowerCase().includes(search.toLowerCase()) ||
    d.category.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>Knowledge Base</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>{docs.length} articles</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add Article</button>
      </div>

      <input placeholder="Search articles..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 16, maxWidth: 340 }} />

      {/* Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20, border: '1px solid var(--accent-glow)' }}>
          <h3 style={{ marginBottom: 16, fontFamily: 'var(--font-display)' }}>{editId ? 'Edit Article' : 'New Article'}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} style={{ flex: 2 }} />
              <input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} style={{ flex: 1 }} />
            </div>
            <textarea placeholder="Content (paste article, policy, documentation, etc.)" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} rows={6} style={{ resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <input placeholder="Add tag..." value={tagInput} onChange={(e) => setTagInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())} style={{ flex: 1 }} />
              <button className="btn btn-ghost" onClick={addTag}><Tag size={14} /> Add Tag</button>
            </div>
            {form.tags.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {form.tags.map((t) => (
                  <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'var(--accent-dim)', color: 'var(--accent)', padding: '3px 10px', borderRadius: 20, fontSize: 12 }}>
                    {t} <X size={11} style={{ cursor: 'pointer' }} onClick={() => removeTag(t)} />
                  </span>
                ))}
              </div>
            )}
            <input placeholder="Source URL (optional)" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
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
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No articles found. Add your first one!</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map((doc) => (
            <div key={doc.id} className="card">
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                    <span className="badge" style={{ background: 'rgba(124,58,237,0.15)', color: '#a78bfa' }}>{doc.category}</span>
                    {doc.tags.map((t) => (
                      <span key={t} style={{ background: 'var(--accent-dim)', color: 'var(--accent)', padding: '1px 8px', borderRadius: 20, fontSize: 11 }}>{t}</span>
                    ))}
                  </div>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{doc.title}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.5 }}>
                    {doc.content.length > 160 ? doc.content.slice(0, 160) + '...' : doc.content}
                  </div>
                  {doc.source && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Source: {doc.source}</div>}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={() => openEdit(doc)}><Pencil size={14} /></button>
                  <button className="btn btn-danger" style={{ padding: '6px 10px' }} onClick={() => handleDelete(doc.id)}><Trash2 size={14} /></button>
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
