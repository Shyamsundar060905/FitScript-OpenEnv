import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { Mark } from './components/AppShell'
import './index.css'

import AuthPage      from './pages/AuthPage'
import OnboardPage   from './pages/OnboardPage'
import DashboardPage from './pages/DashboardPage'
import PlanPage      from './pages/PlanPage'
import CheckinPage   from './pages/CheckinPage'
import HistoryPage   from './pages/HistoryPage'
import PhotosPage    from './pages/PhotosPage'
import SettingsPage  from './pages/SettingsPage'
import LearnPage     from './pages/LearnPage'
import AppShell      from './components/AppShell'

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <Mark size={36} />
          <div className="absolute inset-0 rounded-[9px] animate-pulse-soft bg-sage-500/20" />
        </div>
        <p className="font-mono text-[10px] text-ink-400 uppercase tnum" style={{ letterSpacing: '0.2em' }}>
          Loading
        </p>
      </div>
    </div>
  )
}

function Router() {
  const { user, profile, loading } = useAuth()

  if (loading) return <LoadingScreen />

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="*"      element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  if (!profile) {
    return (
      <Routes>
        <Route path="/onboard" element={<OnboardPage />} />
        <Route path="*"        element={<Navigate to="/onboard" replace />} />
      </Routes>
    )
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/"         element={<DashboardPage />} />
        <Route path="/plan"     element={<PlanPage />} />
        <Route path="/checkin"  element={<CheckinPage />} />
        <Route path="/history"  element={<HistoryPage />} />
        <Route path="/photos"   element={<PhotosPage />} />
        <Route path="/learn"    element={<LearnPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/login"    element={<Navigate to="/" replace />} />
        <Route path="/onboard"  element={<Navigate to="/" replace />} />
        <Route path="*"         element={<Navigate to="/" replace />} />
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
