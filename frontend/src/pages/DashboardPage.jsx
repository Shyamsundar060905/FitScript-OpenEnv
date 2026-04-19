import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts'
import {
  Dumbbell, ClipboardCheck, AlertTriangle, ArrowRight, TrendingUp, TrendingDown,
  Activity, Minus
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

const GOAL_LABEL = {
  muscle_gain: 'Muscle gain',
  weight_loss: 'Fat loss',
  endurance:   'Endurance',
  maintenance: 'Maintenance',
}

function Metric({ label, value, unit, trend, trendLabel, tone = 'ink' }) {
  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus
  const trendColor =
    tone === 'inverse'
      ? trend < 0 ? 'text-sage-400' : trend > 0 ? 'text-clay-200' : 'text-paper-300'
      : trend > 0 ? 'text-sage-600' : trend < 0 ? 'text-clay-500' : 'text-ink-400'

  return (
    <div className={clsx(
      'metric',
      tone === 'inverse' && 'bg-ink-800 text-paper-50'
    )}>
      <p className={clsx('metric-label', tone === 'inverse' && 'text-paper-300')}>
        {label}
      </p>
      <div className="flex items-end gap-1.5 mt-2">
        <span className={clsx(
          'font-display text-[30px] font-bold leading-none tracking-tight tnum',
          tone === 'inverse' ? 'text-paper-50' : 'text-ink-900'
        )}>
          {value}
        </span>
        {unit && (
          <span className={clsx(
            'text-[13px] mb-1',
            tone === 'inverse' ? 'text-paper-300' : 'text-ink-400'
          )}>
            {unit}
          </span>
        )}
      </div>
      {trend !== undefined && (
        <div className={clsx('flex items-center gap-1 mt-2 text-[11px] font-medium tnum', trendColor)}>
          <TrendIcon size={11} strokeWidth={2.5} />
          <span>{trend > 0 ? '+' : ''}{trend}</span>
          {trendLabel && <span className="opacity-60">{trendLabel}</span>}
        </div>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-ink-800 text-paper-50 px-3 py-1.5 rounded-md text-[11px] tnum">
      <span className="text-paper-300">{label}</span>
      <span className="ml-2 font-semibold">{payload[0].value} kg</span>
    </div>
  )
}

export default function DashboardPage() {
  const { profile } = useAuth()
  const navigate = useNavigate()
  const [logs,    setLogs]    = useState([])
  const [weights, setWeights] = useState([])
  const [constraints, setConstraints] = useState([])

  useEffect(() => {
    api.getLogs(30).then(setLogs).catch(() => {})
    api.getWeights(30).then(setWeights).catch(() => {})
    api.getConstraints().then(d => setConstraints(d.constraints)).catch(() => {})
  }, [])

  const completed  = logs.filter(l => l.workout_completed).length
  const adherence  = logs.length ? Math.round(completed / logs.length * 100) : 0
  const weightChg  = weights.length >= 2
    ? +(weights[weights.length - 1].weight_kg - weights[0].weight_kg).toFixed(1)
    : 0
  const latestWeight = weights.length ? weights[weights.length - 1].weight_kg : profile?.weight_kg
  const bmi = profile?.height_cm ? (profile.weight_kg / ((profile.height_cm / 100) ** 2)).toFixed(1) : '—'

  const chartData = weights.map(w => ({
    date: format(parseISO(w.date), 'MMM d'),
    kg:   w.weight_kg,
  }))

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const today = format(new Date(), 'EEEE, MMMM d')

  const firstName = profile?.name?.split(' ')[0] ?? 'friend'

  return (
    <Container size="lg">
      {/* Greeting + date */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-1 h-1 bg-clay-500 rounded-full" />
          <span className="eyebrow text-clay-500">{today}</span>
        </div>
        <h1 className="font-display text-display-md text-ink-900">
          {greeting}, {firstName}.
        </h1>
        <p className="text-[13.5px] text-ink-500 mt-1.5">
          Here's where you stand and what's next.
        </p>
      </div>

      {/* Constraints banner */}
      {constraints.length > 0 && (
        <div className="flex items-start gap-3 bg-clay-50 rounded-xl px-4 py-3 mb-6"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.25)' }}>
          <AlertTriangle size={15} className="text-clay-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-clay-600">Active constraints</p>
            <p className="text-[12px] text-clay-500 mt-0.5">
              {constraints.map(c => c.split(' — ')[0]).join(' · ')}
              <span className="text-ink-400"> — Fitness Agent will avoid related exercises</span>
            </p>
          </div>
        </div>
      )}

      {/* Metric row — inverted "today" card + 3 paper tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <Metric label="Current weight" value={latestWeight} unit="kg"
                trend={weightChg} trendLabel="last 30d" tone="inverse" />
        <Metric label="BMI" value={bmi} />
        <Metric label="30-day adherence" value={`${adherence}`} unit="%" />
        <Metric label="Workouts done" value={completed} unit="sessions" />
      </div>

      {/* Primary row: weight chart + goal panel */}
      <div className="grid lg:grid-cols-[1.7fr_1fr] gap-6 mb-6">
        {/* Weight chart */}
        <div className="card p-6">
          <div className="flex items-start justify-between mb-1">
            <div>
              <p className="eyebrow mb-1">Weight trend</p>
              <h2 className="section-title">Last 30 days</h2>
            </div>
            {weightChg !== 0 && (
              <div className={clsx(
                'chip',
                weightChg > 0 ? 'chip-sage' : 'chip-clay'
              )}>
                {weightChg > 0 ? '+' : ''}{weightChg} kg
              </div>
            )}
          </div>
          <div className="mt-4 -mx-2">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"  stopColor="#6B9737" stopOpacity={0.22} />
                      <stop offset="100%" stopColor="#6B9737" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#857E6C' }} axisLine={false} tickLine={false} />
                  <YAxis domain={['dataMin - 1', 'dataMax + 1']}
                         tick={{ fontSize: 10, fill: '#857E6C' }}
                         axisLine={false} tickLine={false} width={32} />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#D8D3C4', strokeWidth: 1, strokeDasharray: '2 4' }} />
                  <Area type="monotone" dataKey="kg" stroke="#6B9737" strokeWidth={2}
                        fill="url(#weightGrad)"
                        dot={{ r: 2.5, fill: '#6B9737', strokeWidth: 0 }}
                        activeDot={{ r: 5, fill: '#6B9737', stroke: '#FAF7EE', strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex flex-col items-center justify-center text-center gap-2">
                <Activity size={20} className="text-ink-300" />
                <p className="text-[13px] text-ink-400">No weight data yet</p>
                <p className="text-[11.5px] text-ink-400">Log your first check-in to populate the chart.</p>
              </div>
            )}
          </div>
        </div>

        {/* Goal panel */}
        <div className="card p-6 flex flex-col">
          <p className="eyebrow mb-1">Your goal</p>
          <h2 className="section-title">{GOAL_LABEL[profile?.goal] ?? '—'}</h2>

          <div className="my-5 flex items-baseline gap-2">
            <span className="font-display text-[48px] font-bold text-ink-900 leading-none tracking-tighter tnum">
              {profile?.tdee_estimate?.toFixed(0)}
            </span>
            <span className="text-[12px] text-ink-400">kcal/day target</span>
          </div>

          <div className="ornament">
            <span className="ornament-dot" />
          </div>

          <dl className="flex flex-col gap-2.5 text-[12.5px]">
            <div className="flex justify-between">
              <dt className="text-ink-500">Fitness level</dt>
              <dd className="font-medium text-ink-800 capitalize">{profile?.fitness_level}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-ink-500">Sessions / week</dt>
              <dd className="font-medium text-ink-800 tnum">{profile?.sessions_per_week}</dd>
            </div>
            {profile?.dietary_restrictions?.length > 0 && (
              <div className="flex justify-between gap-2">
                <dt className="text-ink-500 flex-shrink-0">Diet</dt>
                <dd className="font-medium text-ink-800 text-right capitalize">
                  {profile.dietary_restrictions.join(', ').replace(/_/g, ' ')}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Quick actions — just 2 real actions, developer tools live in Settings now */}
      <div className="grid sm:grid-cols-2 gap-3 mb-6">
        <button onClick={() => navigate('/plan')}
                className="group card p-5 text-left hover:shadow-lift transition-all duration-200 flex items-center gap-4">
          <div className="w-11 h-11 rounded-lg bg-sage-50 flex items-center justify-center flex-shrink-0">
            <Dumbbell size={18} className="text-sage-600" strokeWidth={2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13.5px] font-semibold text-ink-900">Generate this week's plan</p>
            <p className="text-[11.5px] text-ink-500 mt-0.5">Run the full 6-agent pipeline</p>
          </div>
          <ArrowRight size={14} className="text-ink-300 group-hover:text-ink-700 group-hover:translate-x-0.5 transition-all" />
        </button>

        <button onClick={() => navigate('/checkin')}
                className="group card p-5 text-left hover:shadow-lift transition-all duration-200 flex items-center gap-4">
          <div className="w-11 h-11 rounded-lg bg-clay-50 flex items-center justify-center flex-shrink-0">
            <ClipboardCheck size={18} className="text-clay-500" strokeWidth={2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13.5px] font-semibold text-ink-900">Log today's check-in</p>
            <p className="text-[11.5px] text-ink-500 mt-0.5">Weight, meals, and workout rating</p>
          </div>
          <ArrowRight size={14} className="text-ink-300 group-hover:text-ink-700 group-hover:translate-x-0.5 transition-all" />
        </button>
      </div>

      {/* Recent activity */}
      {logs.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="eyebrow mb-1">Recent activity</p>
              <h2 className="section-title">Last 7 entries</h2>
            </div>
            <button onClick={() => navigate('/history')} className="btn-ghost text-[12px]">
              View all <ArrowRight size={12} />
            </button>
          </div>
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="hair-b">
                  {['Date','Workout','Difficulty','Weight','Calories','Notes'].map(h => (
                    <th key={h} className="pb-2.5 pr-4 eyebrow text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.slice(-7).reverse().map((l, i) => (
                  <tr key={i} className="hair-b last:border-0">
                    <td className="py-3 pr-4 text-ink-700 whitespace-nowrap tnum">
                      {format(parseISO(l.date), 'MMM d')}
                    </td>
                    <td className="py-3 pr-4">
                      {l.workout_completed
                        ? <span className="chip-sage">Completed</span>
                        : <span className="text-ink-300">—</span>}
                    </td>
                    <td className="py-3 pr-4 text-ink-600 tnum">{l.workout_rating ? `${l.workout_rating} / 5` : '—'}</td>
                    <td className="py-3 pr-4 text-ink-800 tnum">{l.weight_kg ? `${l.weight_kg} kg` : '—'}</td>
                    <td className="py-3 pr-4 text-ink-800 tnum">{l.calories_eaten ? `${Math.round(l.calories_eaten)}` : '—'}</td>
                    <td className="py-3 text-ink-500 text-[12.5px] max-w-[200px] truncate">{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {logs.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-[13.5px] text-ink-400">
            No activity logged yet. Start with a check-in or generate your first plan.
          </p>
        </div>
      )}
    </Container>
  )
}
