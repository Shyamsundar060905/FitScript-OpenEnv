import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Zap, ChevronDown, ChevronUp, BookOpen, AlertTriangle, Download, Calendar } from 'lucide-react'
import clsx from 'clsx'

const STEPS = [
  { key: 'profile',   label: '👤 Profile Agent',     desc: 'Loading user profile' },
  { key: 'progress',  label: '📊 Progress Agent',     desc: 'Analysing progress history' },
  { key: 'fitness',   label: '💪 Fitness Agent',      desc: 'Generating workout plan' },
  { key: 'nutrition', label: '🥗 Nutrition Agent',    desc: 'Building nutrition plan' },
  { key: 'conflicts', label: '⚡ Conflict Resolver',  desc: 'Checking for conflicts' },
  { key: 'synthesis', label: '🧠 Orchestrator',       desc: 'Synthesising prescription' },
]

function AgentStep({ label, status, detail }) {
  return (
    <div className={clsx('agent-step', {
      'agent-done':    status === 'done',
      'agent-running': status === 'running',
      'agent-pending': status === 'pending',
      'agent-error':   status === 'error',
    })}>
      <span className="text-lg leading-none">
        {status === 'done' ? '✅' : status === 'running' ? '⟳' : status === 'error' ? '❌' : '⏳'}
      </span>
      <div className="min-w-0">
        <span className="font-medium">{label}</span>
        {detail && <span className="text-xs opacity-60 ml-2">{detail}</span>}
      </div>
    </div>
  )
}

function ExerciseDay({ day }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-cream-400 rounded-xl overflow-hidden mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-cream-100 transition-colors text-left"
      >
        <div>
          <span className="font-medium text-sm text-ink-800">{day.day_name}</span>
          <span className="text-xs text-ink-400 ml-2">· {day.focus} · ~{day.estimated_duration_minutes}min</span>
        </div>
        {open ? <ChevronUp size={16} className="text-ink-400" /> : <ChevronDown size={16} className="text-ink-400" />}
      </button>
      {open && (
        <div className="px-4 py-3 bg-cream-50 border-t border-cream-400 flex flex-col gap-3">
          {day.exercises.map((ex, i) => (
            <div key={i} className="text-sm">
              <span className="font-medium text-ink-800">{ex.name}</span>
              <span className="text-ink-500 ml-2">
                {ex.duration_minutes
                  ? `${ex.duration_minutes} min`
                  : `${ex.sets} × ${String(ex.reps).replace('-', '–')} reps | rest ${ex.rest_seconds}s`}
              </span>
              {ex.notes && <p className="text-xs text-ink-400 mt-0.5">↳ {ex.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function NutritionDay({ day }) {
  const [open, setOpen] = useState(false)
  const cal  = day.meals.reduce((s, m) => s + m.calories, 0)
  const prot = day.meals.reduce((s, m) => s + m.protein_g, 0)
  const carb = day.meals.reduce((s, m) => s + m.carbs_g, 0)
  const fat  = day.meals.reduce((s, m) => s + m.fats_g, 0)

  return (
    <div className="border border-cream-400 rounded-xl overflow-hidden mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-cream-100 transition-colors text-left"
      >
        <div>
          <span className="font-medium text-sm text-ink-800">{day.day_name}</span>
          <span className="text-xs text-ink-400 ml-2">
            · {Math.round(cal)} kcal · P:{Math.round(prot)}g C:{Math.round(carb)}g F:{Math.round(fat)}g
          </span>
        </div>
        {open ? <ChevronUp size={16} className="text-ink-400" /> : <ChevronDown size={16} className="text-ink-400" />}
      </button>
      {open && (
        <div className="px-4 py-3 bg-cream-50 border-t border-cream-400 flex flex-col gap-3">
          {day.meals.map((meal, i) => (
            <div key={i}>
              <p className="text-sm font-medium text-ink-800">
                {meal.meal_name}
                <span className="font-normal text-ink-400 ml-1">
                  ({Math.round(meal.calories)} kcal · P:{Math.round(meal.protein_g)}g)
                </span>
              </p>
              <ul className="mt-1 flex flex-col gap-0.5">
                {meal.foods.map((f, j) => (
                  <li key={j} className="text-xs text-ink-500 ml-2">• {f}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PlanPage() {
  const { profile } = useAuth()
  const [weekNum,  setWeekNum]  = useState(1)
  const [status,   setStatus]   = useState({})   // {stepKey: 'done'|'running'|'pending'|'error'}
  const [running,  setRunning]  = useState(false)
  const [rx,       setRx]       = useState(null)
  const [error,    setError]    = useState('')
  const [constraints, setConstraints] = useState([])

  useEffect(() => {
    // Load latest plan and constraints
    api.getLatestPlan().then(p => { if (p) setRx(p) }).catch(() => {})
    api.getConstraints().then(d => setConstraints(d.constraints)).catch(() => {})
  }, [])

  function setStep(key, st, detail = '') {
    setStatus(prev => ({ ...prev, [key]: { st, detail } }))
  }

  async function runAgents() {
    setRunning(true); setError('')
    const init = Object.fromEntries(STEPS.map(s => [s.key, { st: 'pending', detail: '' }]))
    setStatus(init)

    try {
      setStep('profile', 'running', 'Loading…')
      await new Promise(r => setTimeout(r, 200))
      setStep('profile', 'done', `${profile?.name} · ${profile?.goal?.replace('_', ' ')}`)
      setStep('progress', 'running', 'Querying memory…')

      const result = await api.runPlan(weekNum)

      const sigs = result.adaptation_signals ?? []
      setStep('progress',  'done', sigs.map(s => `${s.signal_type}(${s.severity})`).join(', ') || 'No issues')
      setStep('fitness',   'done', `${result.workout_plan?.weekly_volume_sets} sets/week`)
      setStep('nutrition', 'done', `${Math.round(result.nutrition_plan?.target_calories)} kcal/day`)
      setStep('conflicts', 'done', result.conflicts_resolved?.length ? `${result.conflicts_resolved.length} resolved` : 'No conflicts')
      setStep('synthesis', 'done', 'Prescription ready ✓')
      setRx(result)
    } catch (ex) {
      setStep('synthesis', 'error', '')
      if (ex.status === 429) {
        const d = ex.detail
        setError(d.reason === 'cooldown'
          ? `⏳ Please wait ${d.retry_after_seconds}s before generating another plan.`
          : `📅 Daily plan limit reached. Resets in ${Math.round(d.retry_after_seconds / 60)} minutes.`)
      } else {
        setError(ex.detail ?? String(ex))
      }
    } finally { setRunning(false) }
  }

  const pdfUrl = rx ? api.exportPdf(rx.week_number) : null
  const icsUrl = rx ? api.exportIcs(rx.week_number) : null

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="font-display text-2xl font-bold text-ink-900 mb-6">My Weekly Plan</h1>

      {constraints.length > 0 && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 mb-5">
          <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-700">
            <span className="font-medium">Active constraints: </span>
            {constraints.map(c => c.split(' — ')[0]).join(' · ')} — Fitness Agent will avoid related exercises.
          </p>
        </div>
      )}

      {/* Controls */}
      <div className="card p-5 mb-6 flex items-end gap-4">
        <div className="flex-1">
          <label className="label">Week number</label>
          <input
            type="number" min={1} max={52}
            value={weekNum}
            onChange={e => setWeekNum(Number(e.target.value))}
            className="input w-32"
          />
        </div>
        <button onClick={runAgents} disabled={running} className="btn-primary flex items-center gap-2 px-6">
          <Zap size={16} />
          {running ? 'Running agents…' : 'Run All Agents'}
        </button>
      </div>

      {error && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-xl px-4 py-3 mb-5">
          {error}
        </div>
      )}

      {/* Pipeline steps */}
      {Object.keys(status).length > 0 && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-semibold text-ink-600 mb-3 uppercase tracking-wider">Agent Pipeline</h2>
          <div className="flex flex-col gap-1.5">
            {STEPS.map(s => (
              <AgentStep
                key={s.key}
                label={s.label}
                status={status[s.key]?.st ?? 'pending'}
                detail={status[s.key]?.detail}
              />
            ))}
          </div>
        </div>
      )}

      {/* Prescription */}
      {rx && (
        <div className="flex flex-col gap-5 animate-fade-in">
          {/* Orchestrator notes */}
          <div className="card p-5 border-l-4 border-l-blue-400">
            <p className="text-xs font-semibold text-ink-400 uppercase tracking-wider mb-2">
              Orchestrator Summary — Week {rx.week_number}
            </p>
            <p className="text-sm text-ink-700 leading-relaxed">{rx.orchestrator_notes}</p>

            {/* Exports */}
            <div className="flex gap-3 mt-4">
              <a href={`${pdfUrl}?token=${localStorage.getItem('fa_token')}`} target="_blank" rel="noopener noreferrer">
                <button className="btn-secondary flex items-center gap-2 text-xs">
                  <Download size={14} /> Download PDF
                </button>
              </a>
              <a href={`${icsUrl}?token=${localStorage.getItem('fa_token')}`} target="_blank" rel="noopener noreferrer">
                <button className="btn-secondary flex items-center gap-2 text-xs">
                  <Calendar size={14} /> Export to Calendar
                </button>
              </a>
            </div>
          </div>

          {/* Adaptation signals */}
          {rx.adaptation_signals?.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-ink-700 mb-3">Adaptation Signals</h2>
              <div className="flex flex-col gap-3">
                {rx.adaptation_signals.map((s, i) => (
                  <div key={i}>
                    <span className={clsx('badge', {
                      'badge-high':   s.severity === 'high',
                      'badge-medium': s.severity === 'medium',
                      'badge-low':    s.severity === 'low',
                    })}>
                      {s.signal_type.replace('_', ' ')} · {s.severity}
                    </span>
                    <span className="text-sm text-ink-700 ml-2">{s.description}</span>
                    <p className="text-xs text-ink-400 mt-0.5 ml-1">→ {s.recommended_action}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Conflicts */}
          {rx.conflicts_resolved?.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-ink-700 mb-3">Conflicts Resolved</h2>
              {rx.conflicts_resolved.map((c, i) => (
                <p key={i} className="text-sm text-ink-600 bg-blue-50 border border-blue-200 rounded-xl px-3 py-2 mb-2">{c}</p>
              ))}
            </div>
          )}

          {/* Agent log */}
          {rx.agent_log?.length > 0 && (
            <details className="card p-5">
              <summary className="text-sm font-semibold text-ink-700 cursor-pointer">
                🔍 Agent Decision Log — see how each agent reasoned
              </summary>
              <div className="mt-4 flex flex-col gap-3">
                {rx.agent_log.map((e, i) => (
                  <div key={i} className="border-b border-cream-400 pb-3 last:border-0">
                    <p className="text-sm font-medium text-ink-800">{e.icon} {e.agent} <span className="text-ink-400 font-normal text-xs">{e.timestamp}</span></p>
                    <p className="text-xs text-ink-600 mt-0.5">✦ {e.decision}</p>
                    {e.detail && <p className="text-xs text-ink-400 mt-0.5 font-mono">{e.detail?.slice(0, 200)}</p>}
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Knowledge */}
          {rx.knowledge_used?.length > 0 && (
            <details className="card p-5">
              <summary className="text-sm font-semibold text-ink-700 cursor-pointer flex items-center gap-2">
                <BookOpen size={15} /> Knowledge Base Used — {rx.knowledge_used.length} sources
              </summary>
              <div className="mt-4 flex flex-col gap-4">
                {rx.knowledge_used.slice(0, 6).map((chunk, i) => {
                  const rel = chunk.relevance ?? 0
                  const bars = Math.round(rel * 10)
                  return (
                    <div key={i}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-semibold text-ink-500">Source {i+1}</span>
                        <span className="font-mono text-xs text-sage-600">{'█'.repeat(bars)}{'░'.repeat(10-bars)}</span>
                        <span className="text-xs text-ink-400">{(rel * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-xs text-ink-600 bg-cream-100 rounded-xl px-3 py-2 leading-relaxed">{chunk.content}</p>
                      {chunk.tags?.length > 0 && (
                        <div className="flex gap-1 mt-1.5 flex-wrap">
                          {chunk.tags.slice(0, 4).map(t => (
                            <span key={t} className="text-[10px] bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </details>
          )}

          {/* Workout + Nutrition plans */}
          <div className="grid lg:grid-cols-2 gap-5">
            <div className="card p-5">
              <h2 className="font-display font-bold text-ink-800 mb-1">Workout Plan</h2>
              <p className="text-xs text-ink-400 mb-4">
                {rx.workout_plan?.weekly_volume_sets} sets/week · {rx.workout_plan?.notes}
              </p>
              {rx.workout_plan?.days?.map((day, i) => <ExerciseDay key={i} day={day} />)}
            </div>

            <div className="card p-5">
              <h2 className="font-display font-bold text-ink-800 mb-1">Nutrition Plan</h2>
              <p className="text-xs text-ink-400 mb-4">
                {Math.round(rx.nutrition_plan?.target_calories)} kcal ·{' '}
                {Math.round(rx.nutrition_plan?.target_protein_g)}g protein/day
              </p>
              {rx.nutrition_plan?.daily_plans?.map((day, i) => <NutritionDay key={i} day={day} />)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
