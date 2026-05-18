import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('msx_token'))
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const isAuthenticated = !!token

  const login = async (username, password) => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await apiLogin(username, password)
      const t = res.data.access_token
      localStorage.setItem('msx_token', t)
      setToken(t)
      return true
    } catch (e) {
      setError(e.response?.data?.detail || 'Login failed')
      return false
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('msx_token')
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, isLoading, error }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
