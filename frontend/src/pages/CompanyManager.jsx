import { useEffect, useState } from 'react'
import axios from 'axios'
import { Search, ExternalLink, Loader2, RefreshCw, BarChart2, TrendingUp, TrendingDown, Newspaper, DollarSign, Users, PieChart } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const api = axios.create({ baseURL: 'http://localhost:8001/api' })
api.interceptors.request.use(c => {
  const t = localStorage.getItem('msx_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

const PERIODS = [
  { value: '1w', label: '1W' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
  { value: '6m', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '5y', label: '5Y' },
]

const TABS = [
  { id: 'overview',  label: 'Overview',   icon: PieChart },
  { id: 'chart',     label: 'Chart',      icon: BarChart2 },
  { id: 'news',      label: 'News',       icon: Newspaper },
  { id: 'dividends', label: 'Dividends',  icon: DollarSign },
  { id: 'financial', label: 'Financial',  icon: TrendingUp },
  { id: 'board',     label: 'Board',      icon: Users },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: '#00c5ff', fontWeight: 600 }}>{p.name}: {Number(p.value).toFixed(3)}</div>
      ))}
    </div>
  )
}

function DataBlock({ data, maxItems = 30 }) {
  if (!data) return <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>No data available</div>

  const flatten = (obj, prefix = '', depth = 0) => {
    const lines = []
    if (depth > 3) return lines
    if (Array.isArray(obj)) {
      obj.slice(0, 10).forEach((item, i) => lines.push(...flatten(item, `${prefix}[${i+1}]`, depth + 1)))
    } else if (obj && typeof obj === 'object') {
      Object.entries(obj).forEach(([k, v]) => lines.push(...flatten(v, prefix ? `${prefix} › ${k}` : k, depth + 1)))
    } else if (obj !== null && obj !== undefined) {
      const s = String(obj).trim()
      if (s && s !== '0' && s !== 'null' && !s.includes('${')) {
        lines.push({ key: prefix, value: s })
      }
    }
    return lines
  }

  const lines = flatten(data).slice(0, maxItems)
  if (lines.length === 0) return <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>No data found</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {lines.map((line, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
          <span style={{ color: 'var(--text-muted)', minWidth: 180, flexShrink: 0, fontSize: 12 }}>{line.key}</span>
          <span style={{ color: 'var(--text)', wordBreak: 'break-word' }}>{line.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function CompanyManager() {
  const [companies, setCompanies]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [searching, setSearching]   = useState(false)
  const [selected, setSelected]     = useState(null)
  const [activeTab, setActiveTab]   = useState('overview')
  const [period, setPeriod]         = useState('1m')
  const [tabData, setTabData]       = useState({})
  const [loadingTab, setLoadingTab] = useState(false)
  const [chartData, setChartData]   = useState([])
  const [mssqlOk, setMssqlOk]       = useState(null)

  useEffect(() => {
    api.get('/companies/health').then(r => setMssqlOk(r.data.mssql === 'connected')).catch(() => setMssqlOk(false))
    fetchCompanies()
  }, [])

  const fetchCompanies = async () => {
    setLoading(true)
    try { const r = await api.get('/companies'); setCompanies(r.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleSearch = async () => {
    if (!search.trim()) return fetchCompanies()
    setSearching(true)
    try { const r = await api.get(`/companies/search?q=${encodeURIComponent(search)}`); setCompanies(r.data) }
    catch (e) { console.error(e) }
    finally { setSearching(false) }
  }

  const loadTab = async (tab, sym, per) => {
    const key = tab === 'chart' ? `${tab}_${per}` : tab
    if (tabData[key]) return
    setLoadingTab(true)
    try {
      let r
      const s = sym || selected?.Symbol
      if (tab === 'overview') r = await api.get(`/companies/lookup/${s}`)
      else if (tab === 'chart') { r = await api.get(`/companies/chart/${s}?period=${per}`); buildChart(r.data.chart) }
      else if (tab === 'news') r = await api.get(`/companies/news/${s}`)
      else if (tab === 'dividends') r = await api.get(`/companies/dividends/${s}`)
      else if (tab === 'financial') r = await api.get(`/companies/financial/${s}`)
      else if (tab === 'board') r = await api.get(`/companies/board/${s}`)
      if (r) setTabData(prev => ({ ...prev, [key]: r.data }))
    } catch (e) { console.error(e) }
    finally { setLoadingTab(false) }
  }

  const buildChart = (raw) => {
    if (!raw) return
    const arr = Array.isArray(raw) ? raw : (raw.d ? JSON.parse(raw.d) : [])
    if (!arr.length) return
    const cols = Object.keys(arr[0])
    const dateCol  = cols.find(c => /date|dt|time|period/i.test(c)) || cols[0]
    const priceCol = cols.find(c => /close|price|last|value/i.test(c)) || cols[1]
    setChartData(arr.map(row => ({
      date: String(row[dateCol] || '').split('T')[0],
      price: parseFloat(row[priceCol]) || null,
    })).filter(r => r.price))
  }

  const handleSelectCompany = (c) => {
    setSelected(c)
    setTabData({})
    setChartData([])
    setActiveTab('overview')
    loadTab('overview', c.Symbol)
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    loadTab(tab, null, period)
  }

  const handlePeriodChange = (per) => {
    setPeriod(per)
    const key = `chart_${per}`
    if (!tabData[key]) loadTab('chart', null, per)
    else buildChart(tabData[key]?.chart)
  }

  const trend = chartData.length > 1 ? (() => {
    const first = chartData[0]?.price, last = chartData[chartData.length-1]?.price
    if (!first || !last) return null
    return { pct: ((last-first)/first*100).toFixed(2), up: last >= first }
  })() : null

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700 }}>Companies</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>{companies.length} securities · MSM_GEO_Live + MSX.om</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 12, padding: '5px 12px', borderRadius: 8, border: '1px solid var(--border)', background: mssqlOk ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', color: mssqlOk ? 'var(--success)' : 'var(--danger)' }}>
            ● MSSQL {mssqlOk ? 'Connected' : 'Failed'}
          </span>
          <button className="btn btn-ghost" onClick={fetchCompanies}><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* Search */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="Search by symbol, English or Arabic name..." value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} style={{ flex: 1, maxWidth: 420 }} />
        <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
          {searching ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={14} />} Search
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '300px 1fr' : '1fr', gap: 20 }}>

        {/* List */}
        <div style={{ maxHeight: '82vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}><Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} /><div style={{ marginTop: 8 }}>Loading...</div></div>
          ) : companies.map((c, i) => (
            <div key={i} className="card" onClick={() => handleSelectCompany(c)} style={{ cursor: 'pointer', padding: '10px 14px', border: selected?.Symbol === c.Symbol ? '1px solid var(--accent)' : '1px solid var(--border)', background: selected?.Symbol === c.Symbol ? 'var(--accent-dim)' : 'var(--bg-card)', transition: 'all 0.15s' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--accent)', fontSize: 14 }}>{c.Symbol}</span>
                    {c.isSharia && <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 10, background: 'rgba(16,185,129,0.15)', color: 'var(--success)' }}>Sharia</span>}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 1 }}>{c.LongNameEn || c.ShortNameEn}</div>
                  {c.LongNameAr && <div style={{ fontSize: 11, color: 'var(--text-muted)', direction: 'rtl' }}>{c.LongNameAr}</div>}
                </div>
                <a href={`https://www.msx.om/snapshot.aspx?s=${c.Symbol}`} target="_blank" rel="noopener" onClick={e => e.stopPropagation()} style={{ fontSize: 10, color: 'var(--accent)' }}><ExternalLink size={10} /></a>
              </div>
            </div>
          ))}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
            {/* Company header */}
            <div className="card" style={{ border: '1px solid var(--accent-glow)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--accent)' }}>{selected.Symbol}</span>
                    {trend && (
                      <span style={{ fontSize: 13, fontWeight: 600, color: trend.up ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center', gap: 4 }}>
                        {trend.up ? <TrendingUp size={14}/> : <TrendingDown size={14}/>} {trend.up ? '+' : ''}{trend.pct}%
                      </span>
                    )}
                  </div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 13 }}>{selected.LongNameEn || selected.ShortNameEn}</div>
                  {selected.LongNameAr && <div style={{ color: 'var(--text-muted)', fontSize: 12, direction: 'rtl' }}>{selected.LongNameAr}</div>}
                </div>
                <a href={`https://www.msx.om/snapshot.aspx?s=${selected.Symbol}`} target="_blank" rel="noopener" className="btn btn-ghost" style={{ fontSize: 12 }}>
                  <ExternalLink size={13}/> MSX.om
                </a>
              </div>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 2, background: 'var(--bg-card)', padding: 4, borderRadius: 10, border: '1px solid var(--border)', flexWrap: 'wrap' }}>
              {TABS.map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => handleTabChange(id)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 14px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, background: activeTab === id ? 'var(--accent)' : 'transparent', color: activeTab === id ? '#000' : 'var(--text-muted)', fontWeight: activeTab === id ? 700 : 400, transition: 'all 0.15s' }}>
                  <Icon size={12}/> {label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="card" style={{ flex: 1, overflowY: 'auto', maxHeight: '55vh' }}>
              {loadingTab ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
                  <div style={{ marginTop: 8 }}>Loading from MSX.om...</div>
                </div>
              ) : (
                <>
                  {/* Chart tab */}
                  {activeTab === 'chart' && (
                    <div>
                      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
                        {PERIODS.map(p => (
                          <button key={p.value} onClick={() => handlePeriodChange(p.value)} style={{ padding: '4px 14px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, background: period === p.value ? 'var(--accent)' : 'var(--bg-hover)', color: period === p.value ? '#000' : 'var(--text-muted)', fontWeight: period === p.value ? 700 : 400 }}>
                            {p.label}
                          </button>
                        ))}
                      </div>
                      {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                          <AreaChart data={chartData}>
                            <defs>
                              <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#00c5ff" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#00c5ff" stopOpacity={0}/>
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
                            <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} interval="preserveStartEnd"/>
                            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} domain={['auto','auto']} width={55}/>
                            <Tooltip content={<CustomTooltip/>}/>
                            <Area type="monotone" dataKey="price" name="Price" stroke="#00c5ff" strokeWidth={2} fill="url(#pg)" dot={false} activeDot={{ r: 4 }}/>
                          </AreaChart>
                        </ResponsiveContainer>
                      ) : (
                        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No chart data available</div>
                      )}
                    </div>
                  )}

                  {/* Overview tab */}
                  {activeTab === 'overview' && <DataBlock data={tabData['overview']} />}

                  {/* News tab */}
                  {activeTab === 'news' && <DataBlock data={tabData['news']} />}

                  {/* Dividends tab */}
                  {activeTab === 'dividends' && <DataBlock data={tabData['dividends']} />}

                  {/* Financial tab */}
                  {activeTab === 'financial' && <DataBlock data={tabData['financial']} />}

                  {/* Board tab */}
                  {activeTab === 'board' && <DataBlock data={tabData['board']} />}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
