import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, MessageSquare, Trash2, BookOpen } from 'lucide-react'
import { sendMessage } from '../api'
import { formatDistanceToNow } from 'date-fns'

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

const STORAGE_KEY  = 'msx_chat_history'
const SESSION_KEY  = 'msx_session_id'
const USER_KEY     = 'msx_user_name'

const MAX_MESSAGE_LENGTH = 2000

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

function hasArabic(text) {
  return /[؀-ۿ]/.test(text)
}

// ─── Render markdown-lite (XSS-safe) ─────────────────────────────
function renderContent(text) {
  const safe = escapeHtml(text)
  return safe
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(.*?)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*?<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n/g, '<br />')
}

// ─── Welcome screen ───────────────────────────────────────────────
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
        <div style={wStyles.logo}>
          <Bot size={32} color="#00c5ff" />
        </div>
        <h2 style={wStyles.title}>Welcome to MSX Smart Assistant</h2>
        <p style={wStyles.sub}>
          Your AI-powered guide to the Muscat Stock Exchange.<br/>
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
        <p style={wStyles.hint}>Muscat Stock Exchange · msx.om</p>
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
  const [userName, setUserName]   = useState(() => localStorage.getItem(USER_KEY) || '')
  const [messages, setMessages]   = useState([])
  const [input, setInput]         = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY) || null)
  const messagesEndRef            = useRef(null)
  const inputRef                  = useRef(null)

  // Load saved chat history on mount
  useEffect(() => {
    if (!userName) return
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Restore timestamps as Date objects
        const restored = parsed.map(m => ({ ...m, timestamp: new Date(m.timestamp) }))
        setMessages(restored)
        return
      } catch (e) {}
    }
    // No history — show welcome message
    setMessages([{
      role: 'assistant',
      content: `👋 Hello **${userName}**! I'm the MSX Smart Assistant.\n\nI can help you with:\n- Live stock prices and market data\n- Company information and news\n- Dividends and financial reports\n\nWhat would you like to know?`,
      timestamp: new Date(),
      source: 'system',
    }])
  }, [userName])

  // Save chat history whenever messages change
  useEffect(() => {
    if (messages.length === 0 || !userName) return
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages, userName])

  // Save session ID
  useEffect(() => {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId)
  }, [sessionId])

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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

  const handleSend = async (text) => {
    const message = (text || input).trim()
    if (!message || isLoading) return
    if (message.length > MAX_MESSAGE_LENGTH) return

    const userMsg = { role: 'user', content: message, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const history = messages
        .filter(m => m.role !== 'system')
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
    } catch (err) {
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
  }

  // Show welcome screen if no name
  if (!userName) {
    return <WelcomeScreen onSubmit={handleWelcome} />
  }

  const hasHistory = messages.length > 1

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}><Bot size={22} color="#00c5ff"/></div>
          <div>
            <div style={styles.headerTitle}>MSX Smart Assistant</div>
            <div style={styles.headerSub}>
              <span style={styles.dot}/> Hello, <strong>{userName}</strong>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {hasHistory && (
            <button onClick={handleClearChat} style={styles.clearBtn} title="Clear chat history">
              <Trash2 size={14}/> Clear
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.map((msg, i) => (
          <div key={i} style={{ ...styles.msgRow, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.role === 'assistant' && (
              <div style={styles.avatar}><Bot size={16} color="#00c5ff"/></div>
            )}
            <div style={{ maxWidth: '72%' }}>
              <div
                dir={hasArabic(msg.content) ? 'rtl' : 'ltr'}
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
                  <BookOpen size={11}/>
                  {msg.references.slice(0, 2).map((r, ri) => (
                    <span key={ri} style={styles.refItem}>{r}</span>
                  ))}
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div style={{ ...styles.avatar, background: 'var(--user-bubble)' }}>
                <User size={16} color="#93c5fd"/>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div style={{ ...styles.msgRow, justifyContent: 'flex-start' }}>
            <div style={styles.avatar}><Bot size={16} color="#00c5ff"/></div>
            <div style={{ ...styles.bubble, ...styles.bubbleAI, ...styles.typingBubble }}>
              <span style={styles.dot1}/>
              <span style={{ ...styles.dot1, animationDelay: '0.2s' }}/>
              <span style={{ ...styles.dot1, animationDelay: '0.4s' }}/>
            </div>
          </div>
        )}
        <div ref={messagesEndRef}/>
      </div>

      {/* Quick suggestions — only when 1 message (welcome) */}
      {messages.length === 1 && (
        <div style={styles.suggestions}>
          {[
            'What is OQEP stock price?',
            'Show me BKMB dividends',
            'Latest news for MTEL',
            'Top gainers today',
          ].map((s, i) => (
            <button key={i} style={styles.suggBtn} onClick={() => handleSend(s)}>
              <MessageSquare size={12}/> {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={styles.inputArea}>
        <div style={styles.inputWrapper}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value.slice(0, MAX_MESSAGE_LENGTH))}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            placeholder="Ask about any MSX-listed company..."
            rows={1}
            style={styles.textarea}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            style={{ ...styles.sendBtn, opacity: !input.trim() || isLoading ? 0.4 : 1 }}
          >
            {isLoading
              ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }}/>
              : <Send size={18}/>}
          </button>
        </div>
        <div style={styles.inputFooter}>
          <span style={styles.inputHint}>Enter to send · Shift+Enter for new line</span>
          {input.length > 0 && (
            <span style={{ ...styles.inputHint, color: input.length > MAX_MESSAGE_LENGTH * 0.9 ? 'var(--warning)' : 'var(--text-muted)' }}>
              {input.length}/{MAX_MESSAGE_LENGTH}
            </span>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes pulse { 0%,100%{opacity:0.3;transform:scale(0.8)} 50%{opacity:1;transform:scale(1)} }
        ul { padding-left: 18px; margin: 4px 0; }
        li { margin: 2px 0; }
        a  { color: var(--accent); }
      `}</style>
    </div>
  )
}

const styles = {
  page:        { display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)', maxWidth: 860, margin: '0 auto' },
  header:      { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-card)' },
  headerLeft:  { display: 'flex', alignItems: 'center', gap: 12 },
  logo:        { width: 40, height: 40, borderRadius: 10, background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 15 },
  headerSub:   { fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginTop: 1 },
  dot:         { width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 6px #10b981' },
  clearBtn:    { display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer' },
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
  inputFooter: { marginTop: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  inputHint:   { fontSize: 11, color: 'var(--text-muted)' },
}
