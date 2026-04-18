import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp, TrendingDown, Minus, Dumbbell, ClipboardCheck, FlaskConical, AlertTriangle } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

const GOAL_EMOJI = { muscle_gain: '🏋️', weight_loss: '🔥', endurance: '🏃', maintenance: '⚖️' }

function MetricCard({ value, unit, label, trend }) {
  return (
    <div className="metric-card">
      <div className="flex items-end gap-1 justify-center">
        <span className="text-2xl font-display font-bold text-ink-900">{value}</span>
        {unit && <span className="text-sm text-ink-400 mb-0.5">{unit}</span>}
      </div>
      <span className="text-[10px] font-semibold text-ink-400 uppercase tracking-wider">{label}</span>
      {trend !== undefined && (
        <span className={clsx('text-xs font-medium mt-0.5', trend > 0 ? 'text-sage-600' : trend < 0 ? 'text-red-500' : 'text-ink-400')}>
          {trend > 0 ? '↑' : trend < 0 ? '↓' : '–'} {Math.abs(trend)}
        </span>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-xs">
      <p className="text-ink-400">{label}</p>
      <p className="font-semibold text-ink-800">{payload[0].value} kg</p>
    </div>
  )
}

export default function DashboardPage() {
  const { profile } = useAuth()
  const navigate = useNavigate()
  const [logs,    setLogs]    = useState([])
  const [weights, setWeights] = useState([])
  const [constraints, setConstraints] = useState([])
  const [seeding, setSeeding] = useState(false)

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

  const chartData = weights.map(w => ({
    date: format(parseISO(w.date), 'MMM d'),
    kg:   w.weight_kg,
  }))

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'

  async function handleSeed() {
    setSeeding(true)
    try { await api.seedData(3); window.location.reload() }
    catch { } finally { setSeeding(false) }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">
          Good {greeting}, {profile?.name?.split(' ')[0]}!
        </h1>
        <p className="text-sm text-ink-400 mt-1">Here's your fitness overview</p>
      </div>

      {/* Constraints warning */}
      {constraints.length > 0 && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 mb-5">
          <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">Active constraints</p>
            <p className="text-xs text-amber-600 mt-0.5">
              {constraints.map(c => c.split(' — ')[0]).join(' · ')} — will be passed to the Fitness Agent
            </p>
          </div>
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <MetricCard value={profile?.weight_kg}  unit="kg" label="Current Weight" />
        <MetricCard value={profile ? ((profile.weight_kg / ((profile.height_cm/100)**2)).toFixed(1)) : '—'} label="BMI" />
        <MetricCard value={`${adherence}%`}  label="30-day Adherence" />
        <MetricCard value={completed}         label="Workouts Done" />
        <MetricCard
          value={`${weightChg > 0 ? '+' : ''}${weightChg}`}
          unit="kg"
          label="Weight Change"
          trend={weightChg}
        />
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-[2fr_1fr] gap-4 mb-6">
        {/* Weight chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Weight Trend — last 30 days</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8E3D5" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#9CA3AF' }}
                  axisLine={false} tickLine={false} width={36}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone" dataKey="kg"
                  stroke="#7CB342" strokeWidth={2.5}
                  dot={{ r: 3, fill: '#7CB342', strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: '#7CB342' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-ink-400">
              No weight data yet — log your first check-in
            </div>
          )}
        </div>

        {/* Goal card */}
        <div className="card p-5 flex flex-col justify-between">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Your Goal</h2>
          <div className="flex flex-col items-center text-center gap-2 flex-1 justify-center">
            <span className="text-4xl">{GOAL_EMOJI[profile?.goal] ?? '🎯'}</span>
            <p className="font-display font-bold text-lg text-ink-900 capitalize">
              {profile?.goal?.replace('_', ' ')}
            </p>
            <p className="text-xs text-ink-400">
              {profile?.fitness_level} · {profile?.sessions_per_week}x/week
            </p>
            <p className="text-xs text-ink-400">
              Target: {profile?.tdee_estimate?.toFixed(0)} kcal/day
            </p>
            {profile?.dietary_restrictions?.length > 0 && (
              <p className="text-xs text-amber-600 font-medium">
                ⚠️ {profile.dietary_restrictions.join(' · ')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card p-5 mb-6">
        <h2 className="text-sm font-semibold text-ink-700 mb-4">Quick Actions</h2>
        <div className="grid sm:grid-cols-3 gap-3">
          <button onClick={() => navigate('/plan')} className="btn-primary flex items-center justify-center gap-2">
            <Dumbbell size={16} />
            Generate This Week's Plan
          </button>
          <button onClick={() => navigate('/checkin')} className="btn-secondary flex items-center justify-center gap-2">
            <ClipboardCheck size={16} />
            Log Today's Check-in
          </button>
          <button onClick={handleSeed} disabled={seeding} className="btn-secondary flex items-center justify-center gap-2 text-ink-500">
            <FlaskConical size={16} />
            {seeding ? 'Seeding…' : 'Seed 3 Weeks Test Data'}
          </button>
        </div>
      </div>

      {/* Recent activity */}
      {logs.length > 0 && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Recent Activity</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-cream-400">
                  {['Date','Workout','Difficulty','Weight','Calories','Notes'].map(h => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold text-ink-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.slice(-7).reverse().map((l, i) => (
                  <tr key={i} className="border-b border-cream-100 last:border-0">
                    <td className="py-2.5 pr-4 text-ink-600 whitespace-nowrap">
                      {format(parseISO(l.date), 'MMM d')}
                    </td>
                    <td className="py-2.5 pr-4">{l.workout_completed ? '✅' : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-500">{l.workout_rating ? `${l.workout_rating}/5` : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-600">{l.weight_kg ? `${l.weight_kg} kg` : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-600">{l.calories_eaten ? `${Math.round(l.calories_eaten)}` : '—'}</td>
                    <td className="py-2.5 text-ink-400 text-xs max-w-[180px] truncate">{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
