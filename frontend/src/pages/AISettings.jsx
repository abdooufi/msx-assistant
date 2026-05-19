import { useEffect, useState } from 'react'
import axios from 'axios'
import { Bot, Cpu, Key, Save, Zap, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { useToast, ToastContainer } from '../components/Toast'

const api = axios.create({ baseURL: 'http://localhost:8001/api' })
api.interceptors.request.use(c => {
  const t = localStorage.getItem('msx_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

const PROVIDERS = [
  {
    id: 'ollama',
    label: 'Local Ollama',
    desc: 'Self-hosted LLM via Ollama (qwen2.5, llama3, etc.)',
    icon: Cpu,
    color: '#22c55e',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek API',
    desc: 'DeepSeek cloud API — deepseek-chat / deepseek-reasoner',
    icon: Bot,
    color: '#00c5ff',
  },
]

export default function AISettings() {
  const toast = useToast()

  const [form, setForm]       = useState({
    provider:          'ollama',
    deepseek_api_key:  '',
    deepseek_model:    'deepseek-chat',
    deepseek_base_url: 'https://api.deepseek.com/v1',
  })
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [testing, setTesting]   = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [showKey, setShowKey]   = useState(false)

  useEffect(() => {
    api.get('/admin/ai-settings')
      .then(r => setForm(f => ({ ...f, ...r.data })))
      .catch(() => toast.error('Failed to load AI settings'))
      .finally(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setTestResult(null)
    try {
      await api.post('/admin/ai-settings', form)
      toast.success(`Provider switched to ${form.provider === 'deepseek' ? 'DeepSeek' : 'Local Ollama'}`)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const r = await api.post('/admin/ai-settings/test')
      setTestResult(r.data)
      if (r.data.ok) toast.success(`Connection OK — ${r.data.provider}: ${r.data.model}`)
      else           toast.error(`Connection failed: ${r.data.error}`)
    } catch (e) {
      setTestResult({ ok: false, error: e.message })
      toast.error('Test request failed')
    } finally {
      setTesting(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
      <Loader2 size={28} className="spin" color="var(--accent)"/>
    </div>
  )

  return (
    <div style={{ maxWidth: 640 }}>
      <ToastContainer/>

      <h2 style={s.heading}>AI Provider Settings</h2>
      <p style={s.sub}>Choose which AI backend powers the chatbot. Changes take effect immediately.</p>

      {/* Provider cards */}
      <div style={s.providerRow}>
        {PROVIDERS.map(p => {
          const Icon    = p.icon
          const active  = form.provider === p.id
          return (
            <button key={p.id} onClick={() => setForm(f => ({ ...f, provider: p.id }))}
              style={{ ...s.providerCard, ...(active ? { borderColor: p.color, background: p.color + '14' } : {}) }}>
              <div style={{ ...s.providerIcon, background: p.color + '22', color: p.color }}>
                <Icon size={20}/>
              </div>
              <div style={{ flex: 1, textAlign: 'left' }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: active ? p.color : 'var(--text)' }}>{p.label}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{p.desc}</div>
              </div>
              <div style={{ ...s.radio, ...(active ? { borderColor: p.color } : {}) }}>
                {active && <div style={{ ...s.radioDot, background: p.color }}/>}
              </div>
            </button>
          )
        })}
      </div>

      {/* DeepSeek config — only shown when deepseek selected */}
      {form.provider === 'deepseek' && (
        <div style={s.section}>
          <div style={s.sectionTitle}><Key size={14}/> DeepSeek Configuration</div>

          <label style={s.label}>API Key</label>
          <div style={{ position: 'relative' }}>
            <input
              type={showKey ? 'text' : 'password'}
              value={form.deepseek_api_key}
              onChange={e => setForm(f => ({ ...f, deepseek_api_key: e.target.value }))}
              placeholder="sk-..."
              style={s.input}
            />
            <button onClick={() => setShowKey(v => !v)} style={s.eyeBtn}>
              {showKey ? '🙈' : '👁'}
            </button>
          </div>
          <p style={s.hint}>
            Get your key at{' '}
            <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer"
               style={{ color: 'var(--accent)' }}>platform.deepseek.com</a>
          </p>

          <label style={s.label}>Model</label>
          <select value={form.deepseek_model}
            onChange={e => setForm(f => ({ ...f, deepseek_model: e.target.value }))}
            style={s.input}>
            <option value="deepseek-chat">deepseek-chat (recommended)</option>
            <option value="deepseek-reasoner">deepseek-reasoner (DeepSeek R1)</option>
          </select>

          <label style={s.label}>Base URL</label>
          <input
            value={form.deepseek_base_url}
            onChange={e => setForm(f => ({ ...f, deepseek_base_url: e.target.value }))}
            placeholder="https://api.deepseek.com/v1"
            style={s.input}
          />
          <p style={s.hint}>Leave as default unless using a DeepSeek-compatible proxy.</p>
        </div>
      )}

      {/* Actions */}
      <div style={s.actions}>
        <button onClick={save} disabled={saving} style={s.btnPrimary}>
          {saving ? <Loader2 size={15} className="spin"/> : <Save size={15}/>}
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        <button onClick={test} disabled={testing} style={s.btnSecondary}>
          {testing ? <Loader2 size={15} className="spin"/> : <Zap size={15}/>}
          {testing ? 'Testing…' : 'Test Connection'}
        </button>
      </div>

      {/* Test result */}
      {testResult && (
        <div style={{ ...s.testBox, borderColor: testResult.ok ? '#22c55e' : '#f87171',
                      background: testResult.ok ? '#22c55e12' : '#f8717112' }}>
          {testResult.ok
            ? <><CheckCircle size={16} color="#22c55e"/><span style={{ color: '#22c55e' }}>
                Connected — <strong>{testResult.provider}</strong> / {testResult.model}
                {testResult.reply && <> · "{testResult.reply}"</>}
              </span></>
            : <><XCircle size={16} color="#f87171"/><span style={{ color: '#f87171' }}>
                {testResult.error || 'Connection failed'}
              </span></>
          }
        </div>
      )}
    </div>
  )
}

const s = {
  heading:      { fontSize: 22, fontWeight: 700, marginBottom: 6 },
  sub:          { color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 },
  providerRow:  { display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 },
  providerCard: { display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px',
                  borderRadius: 10, border: '1.5px solid var(--border)',
                  background: 'var(--bg-card)', cursor: 'pointer', transition: 'all 0.15s' },
  providerIcon: { width: 38, height: 38, borderRadius: 9,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  radio:        { width: 18, height: 18, borderRadius: '50%', border: '2px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  radioDot:     { width: 8, height: 8, borderRadius: '50%' },
  section:      { background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: 10, padding: '18px 20px', marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 8 },
  sectionTitle: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 13,
                  fontWeight: 600, color: 'var(--accent)', marginBottom: 4 },
  label:        { fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' },
  input:        { width: '100%', padding: '9px 12px', borderRadius: 7,
                  border: '1px solid var(--border)', background: 'var(--bg)',
                  color: 'var(--text)', fontSize: 14, boxSizing: 'border-box' },
  hint:         { fontSize: 12, color: 'var(--text-muted)', margin: '2px 0 0' },
  eyeBtn:       { position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', fontSize: 16 },
  actions:      { display: 'flex', gap: 10, marginBottom: 16 },
  btnPrimary:   { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px',
                  borderRadius: 8, background: 'var(--accent)', color: '#000',
                  fontWeight: 600, fontSize: 14, border: 'none', cursor: 'pointer' },
  btnSecondary: { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px',
                  borderRadius: 8, background: 'var(--bg-card)', color: 'var(--text)',
                  fontWeight: 500, fontSize: 14, border: '1px solid var(--border)', cursor: 'pointer' },
  testBox:      { display: 'flex', alignItems: 'center', gap: 8, padding: '12px 14px',
                  borderRadius: 8, border: '1px solid', fontSize: 13 },
}
