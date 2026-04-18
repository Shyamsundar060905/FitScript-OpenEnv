import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { Zap, CheckCircle2, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

// No navigate() needed — Router in main.jsx reacts to user/profile state automatically

const FEATURES = [
  { title: 'Statistical plateau detection',      desc: '7-day rolling regression on body weight'    },
  { title: 'Verified Indian nutrition',           desc: 'Macros sourced from IFCT 2017 & USDA'      },
  { title: 'Deterministic progressive overload',  desc: 'Coaching rules, not LLM guesswork'          },
]

export default function AuthPage() {
  const { login, signup } = useAuth()
  const [tab, setTab]   = useState('login')
  const [form, setForm] = useState({ username: '', password: '', confirm: '' })
  const [err, setErr]   = useState('')
  const [loading, setLoading] = useState(false)

  function set(k) { return e => setForm(f => ({ ...f, [k]: e.target.value })) }

  async function handleLogin(e) {
    e.preventDefault()
    setErr(''); setLoading(true)
    try {
      await login(form.username, form.password)
      // Router automatically navigates when user+profile state updates
    } catch (ex) {
      setErr(ex.detail ?? 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  async function handleSignup(e) {
    e.preventDefault()
    if (form.password !== form.confirm) { setErr("Passwords don't match"); return }
    setErr(''); setLoading(true)
    try {
      await signup(form.username, form.password)
      // Router automatically navigates to /onboard when user is set, profile is null
    } catch (ex) {
      setErr(ex.detail ?? 'Could not create account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-[1.1fr_1fr] gap-6">

        {/* Hero panel */}
        <div className="card bg-cream-200 p-8 flex flex-col justify-between min-h-[520px]">
          <div>
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 rounded-xl bg-sage-500 flex items-center justify-center shadow-card">
                <Zap size={20} className="text-white" strokeWidth={2.5} />
              </div>
              <span className="font-display text-xl font-bold text-ink-900 tracking-tight">FitAgent</span>
            </div>

            <h1 className="font-display text-3xl font-bold text-ink-900 leading-tight mb-3">
              Personalized fitness,<br />grounded in evidence.
            </h1>
            <p className="text-sm text-ink-500 leading-relaxed mb-8">
              A multi-agent AI system that adapts your training and nutrition to your goals,
              your equipment, and your progress — every recommendation backed by peer-reviewed sports science.
            </p>

            <div className="flex flex-col gap-4">
              {FEATURES.map(f => (
                <div key={f.title} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-sage-500 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <CheckCircle2 size={11} className="text-white" strokeWidth={3} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink-800">{f.title}</p>
                    <p className="text-xs text-ink-400 mt-0.5">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-ink-300 mt-6 pt-5 border-t border-cream-400">
            Final-year B.Tech research project · Multi-agent systems · 2026
          </p>
        </div>

        {/* Auth form */}
        <div className="card p-8 flex flex-col">
          <div className="mb-6">
            <h2 className="font-display text-2xl font-bold text-ink-900 mb-1">
              {tab === 'login' ? 'Welcome back' : 'Create account'}
            </h2>
            <p className="text-sm text-ink-400">
              {tab === 'login'
                ? 'Sign in to continue your training plan'
                : 'Start your personalized fitness journey'}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex bg-cream-100 rounded-xl p-1 mb-6">
            {['login', 'signup'].map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setErr('') }}
                className={clsx(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150',
                  tab === t
                    ? 'bg-white text-ink-900 shadow-card'
                    : 'text-ink-400 hover:text-ink-700'
                )}
              >
                {t === 'login' ? 'Sign in' : 'Sign up'}
              </button>
            ))}
          </div>

          {err && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2.5 rounded-xl mb-4">
              <AlertCircle size={15} />
              <span>{err}</span>
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div>
                <label className="label">Username</label>
                <input
                  className="input" placeholder="your username"
                  value={form.username} onChange={set('username')}
                  autoFocus autoComplete="username"
                />
              </div>
              <div>
                <label className="label">Password</label>
                <input
                  className="input" type="password" placeholder="your password"
                  value={form.password} onChange={set('password')}
                  autoComplete="current-password"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="flex flex-col gap-4">
              <div>
                <label className="label">Username</label>
                <input
                  className="input" placeholder="choose a username"
                  value={form.username} onChange={set('username')}
                  autoFocus autoComplete="username"
                />
              </div>
              <div>
                <label className="label">Password</label>
                <input
                  className="input" type="password" placeholder="min 8 characters"
                  value={form.password} onChange={set('password')}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="label">Confirm Password</label>
                <input
                  className="input" type="password" placeholder="re-enter password"
                  value={form.confirm} onChange={set('confirm')}
                  autoComplete="new-password"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Creating account…' : 'Create account'}
              </button>
            </form>
          )}

          <p className="text-xs text-ink-300 text-center mt-6">
            By signing in you agree to use this research prototype responsibly. Not medical advice.
          </p>
        </div>
      </div>
    </div>
  )
}