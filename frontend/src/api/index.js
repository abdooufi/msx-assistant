import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('msx_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('msx_token')
      window.location.href = '/admin/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────────
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

// ─── Chat ─────────────────────────────────────────────────────────
export const sendMessage = (message, sessionId, history) =>
  api.post('/chat', { message, session_id: sessionId, history })

export const getChatHealth = () => api.get('/chat/health')

// ─── Knowledge Base ───────────────────────────────────────────────
export const listKnowledge = (params) => api.get('/knowledge', { params })
export const createKnowledge = (data) => api.post('/knowledge', data)
export const updateKnowledge = (id, data) => api.put(`/knowledge/${id}`, data)
export const deleteKnowledge = (id) => api.delete(`/knowledge/${id}`)

// ─── FAQ ──────────────────────────────────────────────────────────
export const listFAQs = (params) => api.get('/faq', { params })
export const listPublicFAQs = () => api.get('/faq/public')
export const createFAQ = (data) => api.post('/faq', data)
export const updateFAQ = (id, data) => api.put(`/faq/${id}`, data)
export const deleteFAQ = (id) => api.delete(`/faq/${id}`)

// ─── Admin ────────────────────────────────────────────────────────
export const getStats = () => api.get('/admin/stats')

// ─── Unanswered ───────────────────────────────────────────────────
export const listUnanswered = (params) => api.get('/unanswered', { params })
export const updateUnanswered = (id, data) => api.put(`/unanswered/${id}`, data)
export const deleteUnanswered = (id) => api.delete(`/unanswered/${id}`)

// ─── Companies (public) ───────────────────────────────────────────
export const getCompanyChart = (symbol, period = '1m') =>
  api.get(`/companies/chart/${symbol}`, { params: { period } })

export const searchCompaniesPublic = (q) =>
  api.get('/companies/public-search', { params: { q } })

export default api
