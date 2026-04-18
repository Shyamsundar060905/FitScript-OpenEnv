import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../lib/api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(() => {
    try { return JSON.parse(localStorage.getItem('fa_user')) } catch { return null }
  })
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount: verify token still valid by fetching profile
  useEffect(() => {
    if (!user) { setLoading(false); return }
    api.getProfile()
      .then(p => setProfile(p))
      .catch(() => {
        setUser(null)
        localStorage.removeItem('fa_token')
        localStorage.removeItem('fa_user')
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(username, password) {
    const data = await api.login(username, password)
    localStorage.setItem('fa_token', data.token)
    localStorage.setItem('fa_user', JSON.stringify({ username: data.username, user_id: data.user_id }))
    // Load profile before setting user so Router sees both at once
    let p = null
    try { p = await api.getProfile() } catch { /* new user, no profile yet */ }
    // Set both in one batch — React 18 auto-batches these in async contexts
    setProfile(p)
    setUser({ username: data.username, user_id: data.user_id })
    return { ...data, hasProfile: !!p }
  }

  async function signup(username, password) {
    const data = await api.signup(username, password)
    localStorage.setItem('fa_token', data.token)
    localStorage.setItem('fa_user', JSON.stringify({ username: data.username, user_id: data.user_id }))
    setProfile(null)
    setUser({ username: data.username, user_id: data.user_id })
    return { ...data, hasProfile: false }
  }

  async function logout() {
    await api.logout().catch(() => {})
    localStorage.removeItem('fa_token')
    localStorage.removeItem('fa_user')
    setUser(null)
    setProfile(null)
  }

  function refreshProfile() {
    return api.getProfile().then(p => { setProfile(p); return p })
  }

  return (
    <AuthCtx.Provider value={{ user, profile, setProfile, loading, login, signup, logout, refreshProfile }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)