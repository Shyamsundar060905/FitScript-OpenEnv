// Central API client
// Uses VITE_API_URL env var for prod (Render URL), falls back to /api proxy for local dev
// NOTE: uses || not ?? because .env sets VITE_API_URL="" (empty string, not undefined)

const BASE = import.meta.env.VITE_API_URL || '/api'

function getToken() {
  return localStorage.getItem('fa_token')
}

async function req(method, path, body = null) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  })

  if (res.status === 401) {
    localStorage.removeItem('fa_token')
    localStorage.removeItem('fa_user')
    window.location.href = '/login'
    return
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, detail: data.detail ?? 'Request failed' }
  return data
}

export const api = {
  // Auth
  login:  (username, password) => req('POST', '/auth/login',  { username, password }),
  signup: (username, password) => req('POST', '/auth/signup', { username, password }),
  logout: ()                   => req('POST', '/auth/logout'),

  // Profile
  getProfile:    ()       => req('GET',   '/profile'),
  createProfile: (body)   => req('POST',  '/profile', body),
  updateProfile: (body)   => req('PATCH', '/profile', body),

  // Constraints
  getConstraints:    ()      => req('GET',  '/constraints'),
  updateConstraints: (list)  => req('POST', '/constraints', { constraints: list }),

  // Plan
  runPlan:       (week_number) => req('POST', '/plan/run', { week_number }),
  getLatestPlan: ()            => req('GET',  '/plan/latest'),

  // Export — returns full URL string; token appended by caller for browser download
  exportPdf: (week) => `${BASE}/plan/export/pdf/${week}`,
  exportIcs: (week) => `${BASE}/plan/export/ics/${week}`,

  // Check-in
  saveCheckin: (body) => req('POST', '/checkin', body),

  // History
  getLogs:           (days = 30)       => req('GET', `/history/logs?days=${days}`),
  getWeights:        (days = 30)       => req('GET', `/history/weights?days=${days}`),
  getExercises:      (days = 60)       => req('GET', `/history/exercises?days=${days}`),
  getExerciseDetail: (name, days = 60) => req('GET', `/history/exercise/${encodeURIComponent(name)}?days=${days}`),

  // Usage
  getUsage: () => req('GET', '/usage'),

  // Dev tools
  seedData:  (weeks = 3) => req('POST',   `/dev/seed?weeks=${weeks}`),
  clearData: ()          => req('DELETE',  '/dev/clear'),

  health: () => req('GET', '/health'),
}