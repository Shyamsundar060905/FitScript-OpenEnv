import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import './index.css'

import AuthPage      from './pages/AuthPage'
import OnboardPage   from './pages/OnboardPage'
import DashboardPage from './pages/DashboardPage'
import PlanPage      from './pages/PlanPage'
import CheckinPage   from './pages/CheckinPage'
import HistoryPage   from './pages/HistoryPage'
import PhotosPage    from './pages/PhotosPage'
import SettingsPage  from './pages/SettingsPage'
import AppShell      from './components/AppShell'

function Router() {
  const { user, profile, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-cream-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-sage-500 border-t-transparent animate-spin" />
          <p className="text-sm text-ink-400 font-medium">Loading…</p>
        </div>
      </div>
    )
  }

  // Not logged in → only /login accessible
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="*"      element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  // Logged in but no profile → only /onboard accessible
  if (!profile) {
    return (
      <Routes>
        <Route path="/onboard" element={<OnboardPage />} />
        <Route path="*"        element={<Navigate to="/onboard" replace />} />
      </Routes>
    )
  }

  // Fully authenticated → main app
  return (
    <AppShell>
      <Routes>
        <Route path="/"          element={<DashboardPage />} />
        <Route path="/plan"      element={<PlanPage />} />
        <Route path="/checkin"   element={<CheckinPage />} />
        <Route path="/history"   element={<HistoryPage />} />
        <Route path="/photos"    element={<PhotosPage />} />
        <Route path="/settings"  element={<SettingsPage />} />
        {/* Catch logged-in users hitting /login or /onboard */}
        <Route path="/login"     element={<Navigate to="/" replace />} />
        <Route path="/onboard"   element={<Navigate to="/" replace />} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <AuthProvider>
      <Router />
    </AuthProvider>
  </BrowserRouter>
)