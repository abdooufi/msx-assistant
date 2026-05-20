import { useState, useRef, useEffect, useId } from 'react'
import { Send, Bot, User, Loader2, MessageSquare, Trash2, BookOpen, TrendingUp, Search } from 'lucide-react'
import { sendMessage, getCompanyChart, searchCompaniesPublic } from '../api'
import { formatDistanceToNow } from 'date-fns'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

// ─── Constants ───────────────────────────────────────────────────
const CLASSIFICATION_COLORS = {
  support:         'badge-support',
  sales:           'badge-sales',
  complaint:       'badge-complaint',
  general_inquiry: 'badge-general',
}
const SOURCE_LABELS = {
  faq:            '📋 FAQ',
  knowledge_base: '📚 Knowledge Base',
  ai_general:     '🤖 AI',
  fallback:       '⚠️ Offline',
}
const STORAGE_KEY = 'msx_chat_history'
const SESSION_KEY = 'msx_session_id'
const USER_KEY    = 'msx_user_name'

const CHART_STOP = new Set([
  'SHOW','CHART','GRAPH','PRICE','FOR','THE','AND','MSX','WHAT','HOW',
  'CAN','YOU','ME','MY','OF','IN','ON','AT','DRAW','PLOT','GET','THIS',
  'VIEW','STOCK','GIVE','A','AN','PLEASE','NEED','WANT','HISTORY',
  'HISTORICAL','WITH','FROM','IS','ARE','WAS','LAST','WEEK','MONTH',
  'YEAR','TODAY','DATA','TREND','PRICE',
])

// ─── Helpers ─────────────────────────────────────────────────────
function renderContent(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n/g, '<br />')
}

function extractChartSymbol(text) {
  if (!/\b(chart|graph|plot|trend)\b/i.test(text)) return null
  const words = text.toUpperCase().match(/\b([A-Z]{2,6})\b/g) || []
  return words.find(w => !CHART_STOP.has(w)) || null
}

// ─── Chart Tooltip ────────────────────────────────────────────────
function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: '#8b949e', marginBottom: 3 }}>{d.label}</div>
      <div style={{ color: '#00c5ff', fontWeight: 600 }}>Price: {d.price?.toFixed(4)}</div>
      {d.volume > 0 && <div style={{ color: '#6e7681', marginTop: 2 }}>Vol: {Number(d.volume).toLocaleString()}</div>}
    </div>
  )
}

// ─── StockChart ───────────────────────────────────────────────────
function StockChart({ chartData, symbol }) {
  const uid   = useId()
  const gradId = `cg_${uid.replace(/:/g, '')}`

  const raw  = Array.isArray(chartData) ? chartData : []
  const data = raw.map(d => ({
    label: d.Date
      ? (d.Date.length > 10 ? d.Date.substring(11, 16) : d.Date.substring(5))
      : '',
    price:  d.LTP ?? d.Value ?? 0,
    volume: d.Volume ?? 0,
  })).filter(d => d.price > 0)

  if (!data.length) return (
    <div style={{ padding: '16px 14px', color: '#6e7681', textAlign: 'center', fontSize: 13 }}>
      No chart data available for <strong style={{ color: '#e6edf3' }}>{symbol}</strong>
    </div>
  )

  const prices = data.map(d => d.price)
  const minP   = Math.min(...prices)
  const maxP   = Math.max(...prices)
  const latest = prices[prices.length - 1]
  const first  = prices[0]
  const pct    = first ? ((latest - first) / first * 100) : 0
  const isUp   = pct >= 0
  const color  = isUp ? '#10b981' : '#ef4444'

  return (
    <div style={cStyles.wrap}>
      <div style={cStyles.head}>
        <span style={cStyles.sym}>{symbol}</span>
        <span style={cStyles.price}>{latest?.toFixed(3)}</span>
        <span style={{ ...cStyles.pct, color }}>
          {isUp ? '+' : ''}{pct.toFixed(2)}%
        </span>
        <TrendingUp size={13} color={color} />
      </div>

      <ResponsiveContainer width="100%" height={150}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0}    />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" stroke="#161b22" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#4a5568' }}
            tickLine={false} axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minP * 0.9985, maxP * 1.0015]}
            tick={{ fontSize: 10, fill: '#4a5568' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => v.toFixed(3)}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#30363d', strokeWidth: 1 }} />
          <Area
            type="monotone" dataKey="price"
            stroke={color} strokeWidth={1.5}
            fill={`url(#${gradId})`}
            dot={false}
            activeDot={{ r: 3, fill: color, strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>

      <div style={cStyles.foot}>
        Low {minP?.toFixed(3)} · High {maxP?.toFixed(3)} · {data.length} points
      </div>
    </div>
  )
}

const cStyles = {
  wrap: { background: '#0d1117', borderRadius: 12, padding: '12px 14px', border: '1px solid #21262d' },
  head: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 },
  sym:  { fontWeight: 700, fontSize: 14, color: '#e6edf3' },
  price:{ fontSize: 22, fontWeight: 700, color: '#f0f6fc', lineHeight: 1 },
  pct:  { fontSize: 13, fontWeight: 600 },
  foot: { fontSize: 10, color: '#4a5568', textAlign: 'center', marginTop: 6 },
}

// ─── WelcomeScreen ────────────────────────────────────────────────
function WelcomeScreen({ onSubmit }) {
  const [name, setName] = useState('')
  const inputRef = useRef(null)
  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSubmit = () => {
    const trimmed = name.trim()
    if (!trimmed) return
    onSubmit(trimmed)
  }

  return (
    <div style={wStyles.overlay}>
      <div style={wStyles.card}>
        <div style={wStyles.logo}><Bot size={32} color="#00c5ff" /></div>
        <h2 style={wStyles.title}>Welcome to MSX Smart Assistant</h2>
        <p style={wStyles.sub}>
          Your AI-powered guide to the Muscat Stock Exchange.<br />
          Please tell us your name to get started.
        </p>
        <input
          ref={inputRef}
          placeholder="Your name..."
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          style={wStyles.input}
        />
        <button
          onClick={handleSubmit}
          disabled={!name.trim()}
          style={{ ...wStyles.btn, opacity: name.trim() ? 1 : 0.5 }}
        >
          Start Chatting →
        </button>
        <p style={wStyles.hint}>Powered by LocalAI · MSX.om</p>
      </div>
    </div>
  )
}

const wStyles = {
  overlay: { position: 'fixed', inset: 0, background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: 20 },
  card:    { background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 20, padding: '48px 40px', maxWidth: 440, width: '100%', textAlign: 'center', boxShadow: 'var(--shadow)' },
  logo:    { width: 72, height: 72, borderRadius: 18, background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' },
  title:   { fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, marginBottom: 12 },
  sub:     { color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.7, marginBottom: 28 },
  input:   { textAlign: 'center', fontSize: 16, padding: '12px 20px', borderRadius: 12, marginBottom: 14 },
  btn:     { width: '100%', padding: '13px', background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' },
  hint:    { marginTop: 20, fontSize: 12, color: 'var(--text-muted)' },
}

// ─── Main Chat Page ───────────────────────────────────────────────
export default function ChatPage() {
  const [userName, setUserName]     = useState(() => localStorage.getItem(USER_KEY) || '')
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [isLoading, setIsLoading]   = useState(false)
  const [sessionId, setSessionId]   = useState(() => localStorage.getItem(SESSION_KEY) || null)

  // Slash-command state
  const [slashQuery, setSlashQuery]     = useState('')
  const [slashResults, setSlashResults] = useState([])
  const [slashOpen, setSlashOpen]       = useState(false)
  const [slashLoading, setSlashLoading] = useState(false)
  const [slashIdx, setSlashIdx]         = useState(-1)

  const messagesEndRef = useRef(null)
  const inputRef       = useRef(null)

  // Load history
  useEffect(() => {
    if (!userName) return
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setMessages(parsed.map(m => ({ ...m, timestamp: new Date(m.timestamp) })))
        return
      } catch (_) {}
    }
    setMessages([{
      role: 'assistant',
      content: `👋 Hello **${userName}**! I'm the MSX Smart Assistant.\n\nI can help you with:\n- Live stock prices and market data\n- Company information and news\n- Dividends and financial reports\n\nTip: type **/** to search for a company symbol.\n\nWhat would you like to know?`,
      timestamp: new Date(),
      source: 'system',
    }])
  }, [userName])

  // Save history
  useEffect(() => {
    if (messages.length === 0 || !userName) return
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages, userName])

  // Save session
  useEffect(() => {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId)
  }, [sessionId])

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Slash search with debounce
  useEffect(() => {
    if (!slashOpen || slashQuery.length < 1) {
      if (slashQuery.length === 0) setSlashResults([])
      return
    }
    const timer = setTimeout(async () => {
      setSlashLoading(true)
      try {
        const res = await searchCompaniesPublic(slashQuery)
        setSlashResults(res.data || [])
        setSlashIdx(-1)
      } catch {
        setSlashResults([])
      } finally {
        setSlashLoading(false)
      }
    }, 200)
    return () => clearTimeout(timer)
  }, [slashQuery, slashOpen])

  // Close slash on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!e.target.closest('[data-slash-area]')) setSlashOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleWelcome = (name) => {
    localStorage.setItem(USER_KEY, name)
    setUserName(name)
  }

  const handleClearChat = () => {
    if (!confirm('Clear chat history?')) return
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([{
      role: 'assistant',
      content: `👋 Hi again **${userName}**! Chat history cleared. How can I help you?`,
      timestamp: new Date(),
      source: 'system',
    }])
  }

  // Input change — detect "/" for slash command
  const handleInputChange = (val) => {
    setInput(val)
    const idx = val.lastIndexOf('/')
    if (idx !== -1) {
      setSlashQuery(val.slice(idx + 1))
      setSlashOpen(true)
    } else {
      setSlashOpen(false)
      setSlashQuery('')
    }
  }

  // Select company from slash dropdown
  const handleSlashSelect = (company) => {
    setSlashOpen(false)
    setSlashResults([])
    setSlashQuery('')
    const idx = input.lastIndexOf('/')
    const base = idx > 0 ? input.slice(0, idx) : ''
    setInput(`${base}Show me chart for ${company.symbol}`)
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  // Keyboard: navigate slash dropdown or submit
  const handleKeyDown = (e) => {
    if (slashOpen && slashResults.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSlashIdx(i => Math.min(i + 1, slashResults.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSlashIdx(i => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Enter' && slashIdx >= 0) {
        e.preventDefault()
        handleSlashSelect(slashResults[slashIdx])
        return
      }
      if (e.key === 'Escape') {
        setSlashOpen(false)
        return
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = async (text) => {
    const message = (text || input).trim()
    if (!message || isLoading) return
    setSlashOpen(false)

    const userMsg = { role: 'user', content: message, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    // Start chart fetch in parallel if user asked for a chart
    const chartSymbol = extractChartSymbol(message)
    const chartPromise = chartSymbol
      ? getCompanyChart(chartSymbol).catch(() => null)
      : null

    try {
      const history = messages
        .filter(m => m.role !== 'system' && m.role !== 'chart')
        .slice(-8)
        .map(m => ({ role: m.role, content: m.content }))

      const res  = await sendMessage(message, sessionId, history)
      const data = res.data
      if (!sessionId) setSessionId(data.session_id)

      setMessages(prev => [...prev, {
        role:           'assistant',
        content:        data.reply,
        timestamp:      new Date(),
        source:         data.source,
        classification: data.classification,
        references:     data.references,
        confidence:     data.confidence,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role:      'assistant',
        content:   "⚠️ I'm having trouble connecting. Please try again or visit [www.msx.om](https://www.msx.om).",
        timestamp: new Date(),
        source:    'fallback',
      }])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }

    // Append chart message once data arrives
    if (chartPromise) {
      const chartRes = await chartPromise
      const chartData = chartRes?.data?.chart
      if (chartData?.length) {
        setMessages(prev => [...prev, {
          role:      'chart',
          symbol:    chartSymbol,
          chartData,
          timestamp: new Date(),
        }])
      }
    }
  }

  if (!userName) return <WelcomeScreen onSubmit={handleWelcome} />

  const hasHistory = messages.length > 1

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}><Bot size={22} color="#00c5ff" /></div>
          <div>
            <div style={styles.headerTitle}>MSX Smart Assistant</div>
            <div style={styles.headerSub}>
              <span style={styles.dot} /> Hello, <strong>{userName}</strong>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {hasHistory && (
            <button onClick={handleClearChat} style={styles.clearBtn} title="Clear chat history">
              <Trash2 size={14} /> Clear
            </button>
          )}
          <a href="/admin" style={styles.adminLink}>Admin →</a>
        </div>
      </header>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.map((msg, i) => {
          if (msg.role === 'chart') {
            return (
              <div key={i} style={{ ...styles.msgRow, justifyContent: 'flex-start' }}>
                <div style={{ ...styles.avatar, background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)' }}>
                  <TrendingUp size={15} color="#10b981" />
                </div>
                <div style={{ maxWidth: '80%', minWidth: 300 }}>
                  <div style={{ ...styles.bubble, ...styles.bubbleAI, padding: 0, overflow: 'hidden' }}>
                    <StockChart chartData={msg.chartData} symbol={msg.symbol} />
                  </div>
                  <div style={styles.msgMeta}>
                    <span style={styles.metaTime}>
                      {formatDistanceToNow(msg.timestamp, { addSuffix: true })}
                    </span>
                    <span style={styles.metaSource}>📈 Live Chart</span>
                  </div>
                </div>
              </div>
            )
          }

          return (
            <div key={i} style={{ ...styles.msgRow, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              {msg.role === 'assistant' && (
                <div style={styles.avatar}><Bot size={16} color="#00c5ff" /></div>
              )}
              <div style={{ maxWidth: '72%' }}>
                <div
                  style={{ ...styles.bubble, ...(msg.role === 'user' ? styles.bubbleUser : styles.bubbleAI) }}
                  dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }}
                />
                <div style={styles.msgMeta}>
                  <span style={styles.metaTime}>
                    {formatDistanceToNow(msg.timestamp, { addSuffix: true })}
                  </span>
                  {msg.source && msg.source !== 'system' && (
                    <span style={styles.metaSource}>{SOURCE_LABELS[msg.source] || msg.source}</span>
                  )}
                  {msg.classification && (
                    <span className={`badge ${CLASSIFICATION_COLORS[msg.classification] || 'badge-general'}`}>
                      {msg.classification.replace('_', ' ')}
                    </span>
                  )}
                </div>
                {msg.references?.length > 0 && (
                  <div style={styles.refs}>
                    <BookOpen size={11} />
                    {msg.references.slice(0, 2).map((r, ri) => (
                      <span key={ri} style={styles.refItem}>{r}</span>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div style={{ ...styles.avatar, background: 'var(--user-bubble)' }}>
                  <User size={16} color="#93c5fd" />
                </div>
              )}
            </div>
          )
        })}

        {isLoading && (
          <div style={{ ...styles.msgRow, justifyContent: 'flex-start' }}>
            <div style={styles.avatar}><Bot size={16} color="#00c5ff" /></div>
            <div style={{ ...styles.bubble, ...styles.bubbleAI, ...styles.typingBubble }}>
              <span style={styles.dot1} />
              <span style={{ ...styles.dot1, animationDelay: '0.2s' }} />
              <span style={{ ...styles.dot1, animationDelay: '0.4s' }} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick suggestions */}
      {messages.length === 1 && (
        <div style={styles.suggestions}>
          {[
            'Show chart for OQBI',
            'What is BKMB stock price?',
            'Show me MTEL dividends',
            'Top gainers today',
          ].map((s, i) => (
            <button key={i} style={styles.suggBtn} onClick={() => handleSend(s)}>
              <MessageSquare size={12} /> {s}
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div style={{ ...styles.inputArea, position: 'relative' }} data-slash-area>
        {/* Slash command dropdown */}
        {slashOpen && (
          <div style={slashStyles.panel}>
            <div style={slashStyles.header}>
              <Search size={11} style={{ flexShrink: 0 }} />
              Company symbol search
              <span style={{ marginLeft: 'auto', opacity: 0.5 }}>↑↓ navigate · Enter select · Esc close</span>
            </div>
            {slashLoading && (
              <div style={slashStyles.hint}><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Searching…</div>
            )}
            {!slashLoading && slashQuery.length === 0 && (
              <div style={slashStyles.hint}>Type a symbol or company name…</div>
            )}
            {!slashLoading && slashQuery.length > 0 && slashResults.length === 0 && (
              <div style={slashStyles.hint}>No companies found for "{slashQuery}"</div>
            )}
            {slashResults.map((c, i) => (
              <div
                key={c.symbol}
                style={{ ...slashStyles.item, background: i === slashIdx ? 'var(--bg-hover)' : 'transparent' }}
                onMouseDown={() => handleSlashSelect(c)}
                onMouseEnter={() => setSlashIdx(i)}
              >
                <span style={slashStyles.sym}>{c.symbol}</span>
                <span style={slashStyles.name}>{c.name}</span>
              </div>
            ))}
          </div>
        )}

        <div style={styles.inputWrapper}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any MSX company… or type / to search by symbol"
            rows={1}
            style={styles.textarea}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            style={{ ...styles.sendBtn, opacity: !input.trim() || isLoading ? 0.4 : 1 }}
          >
            {isLoading
              ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
              : <Send size={18} />}
          </button>
        </div>
        <div style={styles.inputHint}>
          Enter to send · Shift+Enter for new line · <strong>/</strong> to search companies
        </div>
      </div>

      <style>{`
        @keyframes spin    { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes pulse   { 0%,100%{opacity:0.3;transform:scale(0.8)} 50%{opacity:1;transform:scale(1)} }
        ul { padding-left: 18px; margin: 4px 0; }
        li { margin: 2px 0; }
        a  { color: var(--accent); }
      `}</style>
    </div>
  )
}

// ─── Slash styles ─────────────────────────────────────────────────
const slashStyles = {
  panel:  {
    position: 'absolute', bottom: '100%', left: 0, right: 0,
    marginBottom: 6, background: 'var(--bg-card)',
    border: '1px solid var(--border)', borderRadius: 12,
    maxHeight: 220, overflowY: 'auto', zIndex: 200,
    boxShadow: '0 -8px 28px rgba(0,0,0,0.45)',
  },
  header: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '7px 12px', fontSize: 11, color: 'var(--text-muted)',
    borderBottom: '1px solid var(--border)', background: 'var(--bg)',
  },
  hint:   { padding: '10px 14px', fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 },
  item:   { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 14px', cursor: 'pointer', transition: 'background 0.1s' },
  sym:    { fontWeight: 700, fontSize: 13, color: 'var(--accent)', minWidth: 54, flexShrink: 0 },
  name:   { fontSize: 12, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
}

// ─── Chat styles ──────────────────────────────────────────────────
const styles = {
  page:        { display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)', maxWidth: 860, margin: '0 auto' },
  header:      { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-card)' },
  headerLeft:  { display: 'flex', alignItems: 'center', gap: 12 },
  logo:        { width: 40, height: 40, borderRadius: 10, background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15 },
  headerSub:   { fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginTop: 1 },
  dot:         { width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' },
  clearBtn:    { display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer' },
  adminLink:   { fontSize: 13, color: 'var(--text-muted)', padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)', textDecoration: 'none' },
  messages:    { flex: 1, overflowY: 'auto', padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: 16 },
  msgRow:      { display: 'flex', gap: 10, alignItems: 'flex-end' },
  avatar:      { width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-dim)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  bubble:      { padding: '11px 15px', borderRadius: 14, fontSize: 14, lineHeight: 1.65 },
  bubbleUser:  { background: 'var(--user-bubble)', borderBottomRightRadius: 4, color: '#dbeafe' },
  bubbleAI:    { background: 'var(--ai-bubble)', border: '1px solid var(--border)', borderBottomLeftRadius: 4 },
  typingBubble:{ display: 'flex', gap: 5, alignItems: 'center', padding: '14px 18px' },
  dot1:        { width: 7, height: 7, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block', animation: 'pulse 1.2s ease-in-out infinite' },
  msgMeta:     { display: 'flex', alignItems: 'center', gap: 8, marginTop: 5, flexWrap: 'wrap' },
  metaTime:    { fontSize: 11, color: 'var(--text-muted)' },
  metaSource:  { fontSize: 11, color: 'var(--text-muted)' },
  refs:        { display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap', color: 'var(--text-muted)', fontSize: 11 },
  refItem:     { background: 'var(--bg-hover)', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border)' },
  suggestions: { padding: '0 16px 12px', display: 'flex', flexWrap: 'wrap', gap: 8 },
  suggBtn:     { display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 20, color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer' },
  inputArea:   { padding: '12px 16px 20px', borderTop: '1px solid var(--border)' },
  inputWrapper:{ display: 'flex', gap: 10, alignItems: 'flex-end' },
  textarea:    { flex: 1, resize: 'none', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 12, color: 'var(--text)', padding: '11px 14px', fontSize: 14, lineHeight: 1.5, maxHeight: 120, overflowY: 'auto' },
  sendBtn:     { width: 44, height: 44, borderRadius: 12, background: 'var(--accent)', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, border: 'none', cursor: 'pointer' },
  inputHint:   { marginTop: 6, fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' },
}
