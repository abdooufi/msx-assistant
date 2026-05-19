import { useEffect, useState } from 'react'
import axios from 'axios'
import { Plus, Pencil, Trash2, Check, X, Play, Loader2, ToggleLeft, ToggleRight, ChevronDown, ChevronUp } from 'lucide-react'

const api = axios.create({ baseURL: 'http://localhost:8001/api' })
api.interceptors.request.use(c => {
  const t = localStorage.getItem('msx_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

const EMPTY = {
  name: '', description: '', url: '', method: 'POST',
  body: '{\n  "Symbol": "{Symbol}"\n}',
  headers: '{}',
  keywords_en: '', keywords_ar: '',
  category: 'company', is_active: true,
}

const METHOD_COLORS = {
  GET:  { bg: 'rgba(16,185,129,0.15)', color: '#10b981' },
  POST: { bg: 'rgba(0,197,255,0.15)',  color: '#00c5ff' },
}

export default function EndpointManager() {
  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading]     = useState(true)
  const [form, setForm]           = useState(EMPTY)
  const [editId, setEditId]       = useState(null)
  const [showForm, setShowForm]   = useState(false)
  const [saving, setSaving]       = useState(false)
  const [search, setSearch]       = useState('')
  const [testSymbol, setTestSymbol] = useState('OQEP')
  const [testResults, setTestResults] = useState({})
  const [testingId, setTestingId] = useState(null)
  const [expanded, setExpanded]   = useState({})
  const [formError, setFormError] = useState('')

  const fetchEndpoints = async () => {
    setLoading(true)
    try { const r = await api.get('/endpoints'); setEndpoints(r.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchEndpoints() }, [])

  const openCreate = () => {
    setForm(EMPTY); setEditId(null); setFormError(''); setShowForm(true)
  }

  const openEdit = (ep) => {
    setForm({
      name: ep.name, description: ep.description || '',
      url: ep.url, method: ep.method,
      body: ep.body ? JSON.stringify(ep.body, null, 2) : '{}',
      headers: ep.headers ? JSON.stringify(ep.headers, null, 2) : '{}',
      keywords_en: (ep.keywords_en || []).join(', '),
      keywords_ar: (ep.keywords_ar || []).join('، '),
      category: ep.category, is_active: ep.is_active,
    })
    setEditId(ep.id); setFormError(''); setShowForm(true)
  }

  const closeForm = () => { setShowForm(false); setEditId(null); setForm(EMPTY); setFormError('') }

  const parseJSON = (str, field) => {
    try { return JSON.parse(str || '{}') }
    catch { setFormError(`Invalid JSON in ${field}`); return null }
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.url.trim()) {
      setFormError('Name and URL are required'); return
    }
    const body    = form.method === 'POST' ? parseJSON(form.body, 'Body') : null
    const headers = parseJSON(form.headers, 'Headers')
    if ((form.method === 'POST' && body === null) || headers === null) return

    setSaving(true)
    setFormError('')
    try {
      const payload = {
        name: form.name, description: form.description,
        url: form.url, method: form.method,
        body: form.method === 'POST' ? body : null,
        headers,
        keywords_en: form.keywords_en.split(',').map(k => k.trim()).filter(Boolean),
        keywords_ar: form.keywords_ar.split('،').map(k => k.trim()).filter(Boolean),
        category: form.category, is_active: form.is_active,
      }
      if (editId) await api.put(`/endpoints/${editId}`, payload)
      else        await api.post('/endpoints', payload)
      await fetchEndpoints()
      closeForm()
    } catch (e) {
      setFormError(e.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this endpoint?')) return
    await api.delete(`/endpoints/${id}`)
    setEndpoints(prev => prev.filter(e => e.id !== id))
  }

  const handleToggle = async (ep) => {
    await api.put(`/endpoints/${ep.id}`, { is_active: !ep.is_active })
    setEndpoints(prev => prev.map(e => e.id === ep.id ? { ...e, is_active: !e.is_active } : e))
  }

  const handleTest = async (ep) => {
    setTestingId(ep.id)
    try {
      const r = await api.post(`/endpoints/${ep.id}/test?symbol=${testSymbol}`)
      setTestResults(prev => ({ ...prev, [ep.id]: r.data }))
      setExpanded(prev => ({ ...prev, [ep.id]: true }))
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Test failed'
      setTestResults(prev => ({ ...prev, [ep.id]: { error: msg } }))
      setExpanded(prev => ({ ...prev, [ep.id]: true }))
    } finally { setTestingId(null) }
  }

  const filtered = endpoints.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase()) ||
    e.url.toLowerCase().includes(search.toLowerCase()) ||
    e.category.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>API Endpoints</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>
            {endpoints.length} endpoints · Dynamic data sources for the chatbot
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}><Plus size={16}/> Add Endpoint</button>
      </div>

      {/* Search + test symbol */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input placeholder="Search endpoints..." value={search} onChange={e => setSearch(e.target.value)} style={{ flex: 1, maxWidth: 340 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Test with symbol:</span>
          <input value={testSymbol} onChange={e => setTestSymbol(e.target.value.toUpperCase())} style={{ width: 100 }} />
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20, border: '1px solid var(--accent-glow)' }}>
          <h3 style={{ marginBottom: 16, fontFamily: 'var(--font-display)' }}>
            {editId ? '✏️ Edit Endpoint' : '➕ New Endpoint'}
          </h3>
          {formError && (
            <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5', padding: '8px 12px', borderRadius: 8, fontSize: 13, marginBottom: 12 }}>
              {formError}
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Name + Category */}
            <div style={{ display: 'flex', gap: 12 }}>
              <input placeholder="Endpoint name (e.g. Company Snapshot)" value={form.name} onChange={e => setForm({...form, name: e.target.value})} style={{ flex: 2 }} />
              <input placeholder="Category (e.g. company, market)" value={form.category} onChange={e => setForm({...form, category: e.target.value})} style={{ flex: 1 }} />
            </div>

            <input placeholder="Description (optional)" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />

            {/* Method + URL */}
            <div style={{ display: 'flex', gap: 10 }}>
              <select value={form.method} onChange={e => setForm({...form, method: e.target.value})} style={{ width: 100, flexShrink: 0 }}>
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
              <input
                placeholder="URL — use {Symbol} as placeholder, e.g. https://www.msx.om/snapshot.aspx/company"
                value={form.url}
                onChange={e => setForm({...form, url: e.target.value})}
                style={{ flex: 1 }}
              />
            </div>

            {/* POST Body */}
            {form.method === 'POST' && (
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                  Request Body (JSON) — use <code style={{ background: 'var(--bg-hover)', padding: '1px 5px', borderRadius: 4 }}>{'{Symbol}'}</code> as placeholder
                </div>
                <textarea
                  value={form.body}
                  onChange={e => setForm({...form, body: e.target.value})}
                  rows={4} style={{ fontFamily: 'monospace', fontSize: 13, resize: 'vertical' }}
                  placeholder={'{\n  "Symbol": "{Symbol}"\n}'}
                />
              </div>
            )}

            {/* Headers */}
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Extra Headers (JSON) — optional</div>
              <textarea value={form.headers} onChange={e => setForm({...form, headers: e.target.value})} rows={2} style={{ fontFamily: 'monospace', fontSize: 13, resize: 'vertical' }} placeholder='{}'/>
            </div>

            {/* Keywords */}
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                  🇬🇧 English Keywords (comma separated)
                </div>
                <input
                  placeholder="e.g. price, stock, dividend, financial"
                  value={form.keywords_en}
                  onChange={e => setForm({...form, keywords_en: e.target.value})}
                />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                  🇸🇦 Arabic Keywords (separated by ،)
                </div>
                <input
                  placeholder="مثال: سعر، توزيعات، مالية"
                  value={form.keywords_ar}
                  onChange={e => setForm({...form, keywords_ar: e.target.value})}
                  style={{ direction: 'rtl' }}
                />
              </div>
            </div>

            {/* Active toggle */}
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14, color: 'var(--text-dim)' }}>
              <input type="checkbox" checked={form.is_active} onChange={e => setForm({...form, is_active: e.target.checked})} style={{ width: 'auto' }}/>
              Active (chatbot will use this endpoint)
            </label>

            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }}/> : <Check size={14}/>}
                {editId ? 'Update' : 'Create'}
              </button>
              <button className="btn btn-ghost" onClick={closeForm}><X size={14}/> Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Endpoints list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading...</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          No endpoints yet. Add your first one!
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map(ep => (
            <div key={ep.id} className="card" style={{ opacity: ep.is_active ? 1 : 0.55 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Top row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                    <span style={{ ...METHOD_COLORS[ep.method], padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700, fontFamily: 'monospace' }}>
                      {ep.method}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{ep.name}</span>
                    <span className="badge" style={{ background: 'rgba(124,58,237,0.15)', color: '#a78bfa' }}>{ep.category}</span>
                    {!ep.is_active && <span className="badge" style={{ background: 'rgba(100,116,139,0.15)', color: 'var(--text-muted)' }}>Inactive</span>}
                  </div>

                  {/* URL */}
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent)', marginBottom: 6, wordBreak: 'break-all' }}>
                    {ep.url}
                  </div>

                  {/* Body */}
                  {ep.body && (
                    <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                      Body: {JSON.stringify(ep.body)}
                    </div>
                  )}

                  {/* Keywords */}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {(ep.keywords_en || []).map((kw, i) => (
                      <span key={i} style={{ background: 'rgba(0,197,255,0.1)', color: 'var(--accent)', padding: '2px 8px', borderRadius: 12, fontSize: 11 }}>
                        🇬🇧 {kw}
                      </span>
                    ))}
                    {(ep.keywords_ar || []).map((kw, i) => (
                      <span key={i} style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--warning)', padding: '2px 8px', borderRadius: 12, fontSize: 11, direction: 'rtl' }}>
                        🇸🇦 {kw}
                      </span>
                    ))}
                    {!(ep.keywords_en?.length) && !(ep.keywords_ar?.length) && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>⚡ Matches all queries</span>
                    )}
                  </div>

                  {/* Test result */}
                  {testResults[ep.id] && (
                    <div style={{ marginTop: 10 }}>
                      <button
                        onClick={() => setExpanded(prev => ({...prev, [ep.id]: !prev[ep.id]}))}
                        style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12, padding: 0, marginBottom: 6 }}
                      >
                        {expanded[ep.id] ? <ChevronUp size={12}/> : <ChevronDown size={12}/>}
                        Test Result ({testSymbol})
                      </button>
                      {expanded[ep.id] && (
                        <pre style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 12, fontSize: 11, overflow: 'auto', maxHeight: 200, color: 'var(--text-dim)', margin: 0 }}>
                          {JSON.stringify(testResults[ep.id], null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={() => handleToggle(ep)} title="Toggle active">
                      {ep.is_active ? <ToggleRight size={16} color="var(--success)"/> : <ToggleLeft size={16}/>}
                    </button>
                    <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={() => openEdit(ep)}>
                      <Pencil size={14}/>
                    </button>
                    <button className="btn btn-danger" style={{ padding: '6px 10px' }} onClick={() => handleDelete(ep.id)}>
                      <Trash2 size={14}/>
                    </button>
                  </div>
                  <button
                    className="btn btn-ghost"
                    style={{ padding: '6px 10px', fontSize: 11, color: 'var(--success)', borderColor: 'rgba(16,185,129,0.3)' }}
                    onClick={() => handleTest(ep)}
                    disabled={testingId === ep.id}
                  >
                    {testingId === ep.id ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }}/> : <Play size={12}/>}
                    Test
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
