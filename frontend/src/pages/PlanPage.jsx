import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import Container from '../components/Container'
import NutritionLiteracy from '../components/NutritionLiteracy'
import {
  ChevronDown, ChevronUp, BookOpen, AlertTriangle, Download, Calendar,
  User, BarChart3, Dumbbell, Apple, GitMerge, Brain, Check, X, Loader2, Sparkles
} from 'lucide-react'
import clsx from 'clsx'

const STEPS = [
  { key: 'profile',   label: 'Profile Agent',       icon: User,      desc: 'Loading user profile' },
  { key: 'progress',  label: 'Progress Agent',      icon: BarChart3, desc: 'Analyzing progress history' },
  { key: 'fitness',   label: 'Fitness Agent',       icon: Dumbbell,  desc: 'Generating workout plan' },
  { key: 'nutrition', label: 'Nutrition Agent',     icon: Apple,     desc: 'Building nutrition plan' },
  { key: 'conflicts', label: 'Conflict Resolver',   icon: GitMerge,  desc: 'Checking for conflicts' },
  { key: 'synthesis', label: 'Orchestrator',        icon: Brain,     desc: 'Synthesizing prescription' },
]

function AgentStep({ step, status, detail, index, total }) {
  const Icon = step.icon
  const isLast = index === total - 1

  return (
    <div className="relative">
      {/* Connecting line to next step */}
      {!isLast && (
        <div className={clsx(
          'absolute left-[19px] top-[38px] w-px h-[calc(100%+4px)] transition-colors duration-500',
          status === 'done' ? 'bg-sage-400' : 'bg-ink-200'
        )} />
      )}

      <div className={clsx(
        'flex items-start gap-3 p-3 rounded-lg transition-all duration-300',
        status === 'running' && 'bg-white shadow-lift',
        status === 'done'    && 'bg-sage-50/60',
        status === 'error'   && 'bg-clay-50',
      )}>
        {/* Icon bubble */}
        <div className={clsx(
          'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300',
          status === 'done'    && 'bg-sage-500 text-white',
          status === 'running' && 'bg-ink-900 text-paper-50',
          status === 'pending' && 'bg-paper-200 text-ink-300',
          status === 'error'   && 'bg-clay-500 text-white',
        )}>
          {status === 'done' && <Check size={16} strokeWidth={2.5} />}
          {status === 'running' && <Loader2 size={16} className="animate-spin" strokeWidth={2} />}
          {status === 'pending' && <Icon size={15} strokeWidth={1.75} />}
          {status === 'error' && <X size={16} strokeWidth={2.5} />}
        </div>

        {/* Label + detail */}
        <div className="flex-1 min-w-0 pt-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-ink-400 tnum" style={{ letterSpacing: '0.1em' }}>
              0{index + 1}
            </span>
            <span className={clsx(
              'text-[13px] font-semibold',
              status === 'done'    && 'text-sage-700',
              status === 'running' && 'text-ink-900',
              status === 'pending' && 'text-ink-400',
              status === 'error'   && 'text-clay-600',
            )}>
              {step.label}
            </span>
          </div>
          <p className={clsx(
            'text-[11.5px] mt-0.5 truncate',
            status === 'running' ? 'text-ink-700' : 'text-ink-400'
          )}>
            {detail || step.desc}
          </p>
        </div>

        {/* Status text */}
        {status === 'running' && (
          <span className="text-[10px] text-clay-500 font-mono uppercase tnum mt-2" style={{ letterSpacing: '0.14em' }}>
            Running
          </span>
        )}
        {status === 'done' && (
          <span className="text-[10px] text-sage-600 font-mono uppercase tnum mt-2" style={{ letterSpacing: '0.14em' }}>
            Done
          </span>
        )}
      </div>
    </div>
  )
}

function ExerciseDay({ day, index }) {
  const [open, setOpen] = useState(index === 0)
  return (
    <div className="rounded-lg overflow-hidden mb-2 bg-paper-100"
         style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-paper-200 transition-colors text-left">
        <div className="flex items-center gap-3 min-w-0">
          <span className="font-mono text-[10px] text-clay-500 tnum" style={{ letterSpacing: '0.1em' }}>
            D{index + 1}
          </span>
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-ink-800">{day.day_name}</span>
            <span className="text-[11px] text-ink-400 ml-2">· {day.focus} · ~{day.estimated_duration_minutes} min</span>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="text-ink-400" /> : <ChevronDown size={14} className="text-ink-400" />}
      </button>
      {open && (
        <div className="px-4 py-3 bg-white hair-t flex flex-col gap-2.5">
          {day.exercises.map((ex, i) => (
            <div key={i} className="flex items-start justify-between gap-4 text-[13px]">
              <div className="min-w-0">
                <span className="font-medium text-ink-800">{ex.name}</span>
                {ex.notes && <p className="text-[11.5px] text-ink-400 mt-0.5 leading-relaxed">↳ {ex.notes}</p>}
              </div>
              <span className="font-mono text-[11.5px] text-ink-600 tnum whitespace-nowrap flex-shrink-0">
                {ex.duration_minutes
                  ? `${ex.duration_minutes}m`
                  : `${ex.sets} × ${String(ex.reps).replace('-', '–')} · ${ex.rest_seconds}s`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function NutritionDay({ day, index }) {
  const [open, setOpen] = useState(index === 0)
  const cal  = day.meals.reduce((s, m) => s + m.calories, 0)
  const prot = day.meals.reduce((s, m) => s + m.protein_g, 0)
  const carb = day.meals.reduce((s, m) => s + m.carbs_g, 0)
  const fat  = day.meals.reduce((s, m) => s + m.fats_g, 0)

  return (
    <div className="rounded-lg overflow-hidden mb-2 bg-paper-100"
         style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-paper-200 transition-colors text-left">
        <div className="flex items-center gap-3 min-w-0">
          <span className="font-mono text-[10px] text-clay-500 tnum" style={{ letterSpacing: '0.1em' }}>
            D{index + 1}
          </span>
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-ink-800">{day.day_name}</span>
            <span className="text-[11px] text-ink-400 ml-2 tnum">
              · {Math.round(cal)} kcal · P {Math.round(prot)} · C {Math.round(carb)} · F {Math.round(fat)}
            </span>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="text-ink-400" /> : <ChevronDown size={14} className="text-ink-400" />}
      </button>
      {open && (
        <div className="px-4 py-3 bg-white hair-t flex flex-col gap-3">
          {day.meals.map((meal, i) => (
            <div key={i}>
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <p className="text-[13px] font-semibold text-ink-800">{meal.meal_name}</p>
                <span className="font-mono text-[11px] text-ink-500 tnum whitespace-nowrap">
                  {Math.round(meal.calories)} kcal · P {Math.round(meal.protein_g)}
                </span>
              </div>
              <ul className="flex flex-col gap-0.5 mt-1">
                {meal.foods.map((f, j) => (
                  <li key={j} className="text-[12px] text-ink-500 ml-1">— {f}</li>
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
  const [weekNum, setWeekNum] = useState(1)
  const [status,  setStatus]  = useState({})
  const [running, setRunning] = useState(false)
  const [rx,      setRx]      = useState(null)
  const [error,   setError]   = useState('')
  const [constraints, setConstraints] = useState([])

  useEffect(() => {
    api.health().catch(() => {})
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
      setStep('profile', 'running', 'Loading profile from long-term memory…')
      await new Promise(r => setTimeout(r, 250))
      setStep('profile', 'done', `${profile?.name} · ${profile?.goal?.replace('_', ' ')}`)
      setStep('progress', 'running', 'Querying episodic memory for trends…')

      const result = await api.runPlan(weekNum)

      const sigs = result.adaptation_signals ?? []
      setStep('progress',  'done',
        sigs.length
          ? sigs.map(s => `${s.signal_type} (${s.severity})`).join(' · ')
          : 'No adaptation signals detected')
      setStep('fitness',   'done', `${result.workout_plan?.weekly_volume_sets} sets/week planned`)
      setStep('nutrition', 'done', `${Math.round(result.nutrition_plan?.target_calories)} kcal/day target`)
      setStep('conflicts', 'done',
        result.conflicts_resolved?.length
          ? `${result.conflicts_resolved.length} conflict(s) resolved`
          : 'No conflicts detected')
      setStep('synthesis', 'done', 'Prescription ready')
      setRx(result)
    } catch (ex) {
      setStep('synthesis', 'error', 'Pipeline halted')
      if (ex.status === 429) {
        const d = ex.detail
        setError(d.reason === 'cooldown'
          ? `Please wait ${d.retry_after_seconds}s before generating another plan.`
          : `Daily plan limit reached. Resets in ${Math.round(d.retry_after_seconds / 60)} minutes.`)
      } else {
        setError(ex.detail ?? String(ex))
      }
    } finally { setRunning(false) }
  }

  const pdfUrl = rx ? api.exportPdf(rx.week_number) : null
  const icsUrl = rx ? api.exportIcs(rx.week_number) : null
  const token  = typeof window !== 'undefined' ? localStorage.getItem('fa_token') : ''

  return (
    <Container size="lg">
      {/* Header with run control */}
      <div className="flex items-start justify-between gap-6 mb-8 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-1 h-1 bg-clay-500 rounded-full" />
            <span className="eyebrow text-clay-500">Multi-agent pipeline</span>
          </div>
          <h1 className="font-display text-display-md text-ink-900">Your weekly plan</h1>
          <p className="text-[13.5px] text-ink-500 mt-1.5 max-w-xl">
            Run the six-agent pipeline to generate a personalized workout and nutrition prescription.
          </p>
        </div>

        <div className="flex items-end gap-3">
          <div>
            <label className="label">Week</label>
            <input type="number" min={1} max={52}
              value={weekNum} onChange={e => setWeekNum(Number(e.target.value))}
              className="input w-20 tnum text-center" />
          </div>
          <button onClick={runAgents} disabled={running} className="btn-accent">
            <Sparkles size={14} />
            {running ? 'Running…' : 'Run agents'}
          </button>
        </div>
      </div>

      {constraints.length > 0 && (
        <div className="flex items-start gap-3 bg-clay-50 rounded-xl px-4 py-3 mb-6"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.25)' }}>
          <AlertTriangle size={15} className="text-clay-500 flex-shrink-0 mt-0.5" />
          <p className="text-[12.5px] text-clay-600">
            <span className="font-semibold">Active constraints: </span>
            {constraints.map(c => c.split(' — ')[0]).join(' · ')}
            <span className="text-ink-500"> — Fitness Agent will avoid related exercises.</span>
          </p>
        </div>
      )}

      {error && (
        <div className="bg-clay-50 text-clay-600 text-[13px] rounded-xl px-4 py-3 mb-6"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.35)' }}>
          {error}
        </div>
      )}

      {/* Pipeline — always visible, shows pending state when idle */}
      {(Object.keys(status).length > 0 || running) && (
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="eyebrow mb-1">Pipeline status</p>
              <h2 className="section-title">
                {running ? 'Agents are working' : 'Pipeline complete'}
              </h2>
            </div>
            <span className="font-mono text-[10px] text-ink-400 tnum" style={{ letterSpacing: '0.18em' }}>
              6 AGENTS · SEQUENTIAL
            </span>
          </div>
          <div className="flex flex-col gap-1">
            {STEPS.map((s, i) => (
              <AgentStep
                key={s.key}
                step={s}
                index={i}
                total={STEPS.length}
                status={status[s.key]?.st ?? 'pending'}
                detail={status[s.key]?.detail}
              />
            ))}
          </div>
          {running && (
            <p className="text-[11px] text-ink-400 mt-4 italic">
              First run after inactivity may take 20–30 seconds while the backend wakes up.
            </p>
          )}
        </div>
      )}

      {/* Prescription */}
      {rx && (
        <div className="flex flex-col gap-6 animate-fade-in">
          {/* Orchestrator summary — hero card with clay accent stripe */}
          <div className="card relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-clay-500" />
            <div className="p-6">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <p className="eyebrow text-clay-500 mb-1">Orchestrator summary</p>
                  <h2 className="font-display text-[20px] font-semibold text-ink-900 tracking-tight">
                    Week {rx.week_number} prescription
                  </h2>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <a href={`${pdfUrl}?token=${token}`} target="_blank" rel="noopener noreferrer">
                    <button className="btn-secondary text-[12px] px-3 py-2">
                      <Download size={13} /> PDF
                    </button>
                  </a>
                  <a href={`${icsUrl}?token=${token}`} target="_blank" rel="noopener noreferrer">
                    <button className="btn-secondary text-[12px] px-3 py-2">
                      <Calendar size={13} /> Calendar
                    </button>
                  </a>
                </div>
              </div>
              <p className="text-[14px] text-ink-700 leading-relaxed">{rx.orchestrator_notes}</p>
            </div>
          </div>

          {/* Nutrition literacy — explains WHY specific foods were chosen */}
          <NutritionLiteracy rx={rx} profile={profile} />

          {/* Adaptation signals */}
          {rx.adaptation_signals?.length > 0 && (
            <div className="card p-6">
              <p className="eyebrow mb-1">Adaptation signals</p>
              <h2 className="section-title mb-4">What the Progress Agent noticed</h2>
              <div className="flex flex-col gap-3">
                {rx.adaptation_signals.map((s, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-paper-100">
                    <span className={clsx(
                      s.severity === 'high'   && 'badge-high',
                      s.severity === 'medium' && 'badge-medium',
                      s.severity === 'low'    && 'badge-low',
                    )}>
                      {s.severity}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium text-ink-800 capitalize">
                        {s.signal_type.replace(/_/g, ' ')}
                      </p>
                      <p className="text-[12.5px] text-ink-500 mt-0.5">{s.description}</p>
                      <p className="text-[12px] text-clay-600 mt-1.5">→ {s.recommended_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Conflicts */}
          {rx.conflicts_resolved?.length > 0 && (
            <div className="card p-6">
              <p className="eyebrow mb-1">Conflict resolution</p>
              <h2 className="section-title mb-4">Reconciled by the orchestrator</h2>
              <div className="flex flex-col gap-2">
                {rx.conflicts_resolved.map((c, i) => (
                  <p key={i} className="text-[13px] text-ink-700 bg-paper-100 rounded-lg px-3 py-2.5">
                    {c}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Workout + Nutrition */}
          <div className="grid lg:grid-cols-2 gap-5">
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="eyebrow mb-1">Fitness Agent</p>
                  <h2 className="section-title">Workout plan</h2>
                </div>
                <span className="chip-sage">
                  {rx.workout_plan?.weekly_volume_sets} sets/wk
                </span>
              </div>
              {rx.workout_plan?.notes && (
                <p className="text-[12px] text-ink-500 mb-4 italic">{rx.workout_plan.notes}</p>
              )}
              {rx.workout_plan?.days?.map((day, i) => <ExerciseDay key={i} day={day} index={i} />)}
            </div>

            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="eyebrow mb-1">Nutrition Agent</p>
                  <h2 className="section-title">Nutrition plan</h2>
                </div>
                <span className="chip-clay tnum">
                  {Math.round(rx.nutrition_plan?.target_calories)} kcal
                </span>
              </div>
              <p className="text-[12px] text-ink-500 mb-4">
                {Math.round(rx.nutrition_plan?.target_protein_g)}g protein · {rx.nutrition_plan?.daily_plans?.length} days
              </p>
              {rx.nutrition_plan?.daily_plans?.map((day, i) => <NutritionDay key={i} day={day} index={i} />)}
            </div>
          </div>

          {/* Agent log */}
          {rx.agent_log?.length > 0 && (
            <details className="card p-6 group">
              <summary className="cursor-pointer list-none">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="eyebrow mb-1">Audit trail</p>
                    <h2 className="section-title flex items-center gap-2">
                      Agent decision log
                      <span className="text-[11px] text-ink-400 font-normal normal-case tracking-normal">
                        — {rx.agent_log.length} entries
                      </span>
                    </h2>
                  </div>
                  <ChevronDown size={16} className="text-ink-400 group-open:rotate-180 transition-transform" />
                </div>
              </summary>
              <div className="mt-5 flex flex-col gap-3">
                {rx.agent_log.map((e, i) => (
                  <div key={i} className="hair-b pb-3 last:border-0 last:pb-0">
                    <div className="flex items-baseline gap-2">
                      <span className="text-[13px] font-semibold text-ink-800">{e.agent}</span>
                      <span className="text-[10px] text-ink-400 font-mono tnum ml-auto">{e.timestamp}</span>
                    </div>
                    <p className="text-[12.5px] text-ink-600 mt-0.5">→ {e.decision}</p>
                    {e.detail && (
                      <p className="text-[11px] text-ink-400 mt-1 font-mono bg-paper-100 rounded px-2 py-1.5 break-words">
                        {String(e.detail).slice(0, 240)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Knowledge used */}
          {rx.knowledge_used?.length > 0 && (
            <details className="card p-6 group">
              <summary className="cursor-pointer list-none">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="eyebrow mb-1">RAG grounding</p>
                    <h2 className="section-title flex items-center gap-2">
                      <BookOpen size={14} />
                      Knowledge base sources
                      <span className="text-[11px] text-ink-400 font-normal normal-case tracking-normal">
                        — {rx.knowledge_used.length} chunks retrieved
                      </span>
                    </h2>
                  </div>
                  <ChevronDown size={16} className="text-ink-400 group-open:rotate-180 transition-transform" />
                </div>
              </summary>
              <div className="mt-5 flex flex-col gap-5">
                {rx.knowledge_used.slice(0, 6).map((chunk, i) => {
                  const rel = chunk.relevance ?? 0
                  const pct = Math.round(rel * 100)
                  return (
                    <div key={i}>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-mono text-[10px] text-ink-400 tnum" style={{ letterSpacing: '0.1em' }}>
                          S{String(i + 1).padStart(2, '0')}
                        </span>
                        <div className="flex-1 h-1 bg-paper-200 rounded-full overflow-hidden">
                          <div className="h-full bg-sage-500 rounded-full transition-all"
                               style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-[11px] text-ink-500 font-mono tnum">{pct}%</span>
                      </div>
                      <p className="text-[12.5px] text-ink-700 bg-paper-100 rounded-lg px-3 py-2.5 leading-relaxed">
                        {chunk.content}
                      </p>
                      {chunk.tags?.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {chunk.tags.slice(0, 4).map(t => (
                            <span key={t} className="chip-paper">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </details>
          )}
        </div>
      )}

      {!rx && !running && Object.keys(status).length === 0 && (
        <div className="card p-10 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-paper-200 mb-3">
            <Sparkles size={18} className="text-ink-400" />
          </div>
          <p className="text-[14px] text-ink-700 font-medium">No plan generated yet</p>
          <p className="text-[12.5px] text-ink-400 mt-1">
            Click "Run agents" to generate your first weekly prescription.
          </p>
        </div>
      )}
    </Container>
  )
}