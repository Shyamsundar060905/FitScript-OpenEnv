import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { Mark } from '../components/AppShell'
import { AlertCircle, ArrowRight } from 'lucide-react'
import clsx from 'clsx'

const FEATURES = [
  {
    num: '01',
    title: 'Statistical plateau detection',
    desc:  '7-day rolling regression on body weight and training volume.',
  },
  {
    num: '02',
    title: 'Evidence-based nutrition',
    desc:  'Macros sourced from IFCT 2017 and USDA food databases.',
  },
  {
    num: '03',
    title: 'Deterministic progressive overload',
    desc:  'Coaching rules from sports science, not LLM improvisation.',
  },
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
    try { await login(form.username, form.password) }
    catch (ex) { setErr(ex.detail ?? 'Invalid username or password') }
    finally { setLoading(false) }
  }

  async function handleSignup(e) {
    e.preventDefault()
    if (form.password !== form.confirm) { setErr("Passwords don't match"); return }
    if (form.password.length < 8)       { setErr("Password must be at least 8 characters"); return }
    setErr(''); setLoading(true)
    try { await signup(form.username, form.password) }
    catch (ex) { setErr(ex.detail ?? 'Could not create account') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-stretch">
      {/* Left: editorial hero — hidden on mobile */}
      <div className="hidden lg:flex flex-1 flex-col justify-between p-12 relative overflow-hidden hair-r bg-paper-100">
        {/* Decorative grain */}
        <div className="absolute inset-0 bg-grain opacity-50 pointer-events-none" />
        {/* Corner ornament */}
        <div className="absolute top-6 right-6 flex items-center gap-2 text-ink-300 font-mono text-[10px] tnum" style={{ letterSpacing: '0.2em' }}>
          <span>v2.0</span>
          <span className="w-4 h-px bg-ink-200" />
          <span>MMXXVI</span>
        </div>

        <div className="relative z-10">
          <Mark size={36} />
        </div>

        <div className="relative z-10 max-w-lg">
          <p className="eyebrow text-clay-500 mb-4 flex items-center gap-2">
            <span className="w-1 h-1 bg-clay-500 rounded-full" />
            A multi-agent fitness system
          </p>
          <h1 className="font-display text-display-xl text-ink-900 mb-6">
            Training that{' '}
            <em className="not-italic relative inline-block">
              thinks
              <svg className="absolute -bottom-2 left-0 w-full" height="6" viewBox="0 0 200 6" preserveAspectRatio="none">
                <path d="M0,3 Q50,0 100,3 T200,3" stroke="#B94A1E" strokeWidth="2" fill="none" strokeLinecap="round" />
              </svg>
            </em>
            ,{' '}
            grounded in evidence.
          </h1>
          <p className="text-[15px] text-ink-500 leading-relaxed max-w-md">
            Five specialized agents analyze your progress, design your workouts,
            plan your nutrition, and adapt every week — each recommendation citing
            the sports-science source behind it.
          </p>
        </div>

        <div className="relative z-10">
          <div className="flex flex-col gap-5">
            {FEATURES.map(f => (
              <div key={f.num} className="flex items-start gap-4">
                <span className="font-mono text-[11px] text-clay-500 tnum pt-0.5" style={{ letterSpacing: '0.1em' }}>
                  {f.num}
                </span>
                <div className="flex-1">
                  <p className="text-[13.5px] font-semibold text-ink-800">{f.title}</p>
                  <p className="text-[12.5px] text-ink-500 mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: auth form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-paper">
        <div className="w-full max-w-[380px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex justify-center mb-6">
            <Mark size={32} />
          </div>

          <div className="mb-7">
            <p className="eyebrow text-clay-500 mb-2">
              {tab === 'login' ? 'Welcome back' : 'Get started'}
            </p>
            <h2 className="font-display text-display-md text-ink-900">
              {tab === 'login' ? 'Sign in to FitAgent' : 'Create your account'}
            </h2>
            <p className="text-[13.5px] text-ink-500 mt-2">
              {tab === 'login'
                ? 'Pick up where your agents left off.'
                : 'Set up in under two minutes.'}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex bg-paper-200 rounded-lg p-0.5 mb-5 text-[13px]">
            {[
              ['login',  'Sign in'],
              ['signup', 'Create account'],
            ].map(([t, label]) => (
              <button
                key={t}
                onClick={() => { setTab(t); setErr('') }}
                className={clsx(
                  'flex-1 py-2 font-medium rounded-md transition-all duration-200',
                  tab === t
                    ? 'bg-white text-ink-900 shadow-card'
                    : 'text-ink-500 hover:text-ink-800'
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {err && (
            <div className="flex items-start gap-2 bg-clay-50 text-clay-600 text-[13px] px-3 py-2.5 rounded-lg mb-4"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.35)' }}>
              <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
              <span>{err}</span>
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div>
                <label className="label">Username</label>
                <input className="input" placeholder="your username"
                       value={form.username} onChange={set('username')}
                       autoFocus autoComplete="username" />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" placeholder="••••••••"
                       value={form.password} onChange={set('password')}
                       autoComplete="current-password" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Signing in…' : 'Sign in'}
                {!loading && <ArrowRight size={14} />}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="flex flex-col gap-4">
              <div>
                <label className="label">Username</label>
                <input className="input" placeholder="choose a username"
                       value={form.username} onChange={set('username')}
                       autoFocus autoComplete="username" />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" placeholder="minimum 8 characters"
                       value={form.password} onChange={set('password')}
                       autoComplete="new-password" />
              </div>
              <div>
                <label className="label">Confirm password</label>
                <input className="input" type="password" placeholder="re-enter password"
                       value={form.confirm} onChange={set('confirm')}
                       autoComplete="new-password" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Creating account…' : 'Create account'}
                {!loading && <ArrowRight size={14} />}
              </button>
            </form>
          )}

          <p className="text-[11.5px] text-ink-400 text-center mt-6 leading-relaxed">
            FitAgent is a research prototype. Not a substitute for medical advice.
          </p>
        </div>
      </div>
    </div>
  )
}
