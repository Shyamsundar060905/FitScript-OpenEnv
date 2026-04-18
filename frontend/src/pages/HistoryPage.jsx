import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { format, parseISO } from 'date-fns'

const CustomTooltip = ({ active, payload, label, unit }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="card px-3 py-2 text-xs shadow-lift">
      <p className="text-ink-400">{label}</p>
      <p className="font-semibold text-ink-800">{payload[0].value}{unit}</p>
    </div>
  )
}

export default function HistoryPage() {
  const [days,      setDays]      = useState(30)
  const [logs,      setLogs]      = useState([])
  const [weights,   setWeights]   = useState([])
  const [exercises, setExercises] = useState([])
  const [selEx,     setSelEx]     = useState('')
  const [exHistory, setExHistory] = useState([])

  useEffect(() => {
    api.getLogs(days).then(setLogs).catch(() => {})
    api.getWeights(days).then(setWeights).catch(() => {})
    api.getExercises(60).then(ex => { setExercises(ex); if (ex.length) setSelEx(ex[0]) }).catch(() => {})
  }, [days])

  useEffect(() => {
    if (selEx) api.getExerciseDetail(selEx, 60).then(setExHistory).catch(() => {})
  }, [selEx])

  const weightChart = weights.map(w => ({ date: format(parseISO(w.date), 'MMM d'), kg: w.weight_kg }))
  const calChart    = logs.filter(l => l.calories_eaten).map(l => ({
    date: format(parseISO(l.date), 'MMM d'),
    kcal: Math.round(l.calories_eaten),
  }))

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">Progress History</h1>
        <div className="flex items-center gap-2">
          <label className="text-xs text-ink-400 font-medium">Show last</label>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="input w-auto text-xs"
          >
            {[7,14,30,60,90].map(d => <option key={d} value={d}>{d} days</option>)}
          </select>
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Weight Trend</h2>
          {weightChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={weightChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8E3D5" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <YAxis domain={['auto','auto']} tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} width={34} />
                <Tooltip content={<CustomTooltip unit=" kg" />} />
                <Line type="monotone" dataKey="kg" stroke="#7CB342" strokeWidth={2.5}
                  dot={{ r: 3, fill: '#7CB342', strokeWidth: 0 }}
                  activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-ink-400">No weight data yet</div>
          )}
        </div>

        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Daily Calories</h2>
          {calChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={calChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8E3D5" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} axisLine={false} tickLine={false} width={42} />
                <Tooltip content={<CustomTooltip unit=" kcal" />} />
                <Bar dataKey="kcal" fill="#7CB342" radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-ink-400">No calorie data yet</div>
          )}
        </div>
      </div>

      {/* Full log table */}
      {logs.length > 0 && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Full Log</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-cream-400 text-left">
                  {['Date','Workout','Difficulty','Weight','Calories','Notes'].map(h => (
                    <th key={h} className="pb-2 pr-4 text-xs font-semibold text-ink-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...logs].reverse().map((l, i) => (
                  <tr key={i} className="border-b border-cream-100 last:border-0">
                    <td className="py-2.5 pr-4 text-ink-600 whitespace-nowrap">{format(parseISO(l.date), 'MMM d, yyyy')}</td>
                    <td className="py-2.5 pr-4">{l.workout_completed ? '✅' : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-500">{l.workout_rating ? `${l.workout_rating}/5` : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-600">{l.weight_kg ? `${l.weight_kg} kg` : '—'}</td>
                    <td className="py-2.5 pr-4 text-ink-600">{l.calories_eaten ? `${Math.round(l.calories_eaten)}` : '—'}</td>
                    <td className="py-2.5 text-ink-400 text-xs max-w-[160px] truncate">{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Exercise history */}
      {exercises.length > 0 && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-ink-700 mb-4">Exercise Progression</h2>
          <div className="mb-4">
            <label className="label">Select exercise</label>
            <select value={selEx} onChange={e => setSelEx(e.target.value)} className="input w-auto">
              {exercises.map(ex => <option key={ex} value={ex}>{ex}</option>)}
            </select>
          </div>
          {exHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-cream-400 text-left">
                    {['Date','Performance','Notes'].map(h => (
                      <th key={h} className="pb-2 pr-4 text-xs font-semibold text-ink-400 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {exHistory.map((r, i) => (
                    <tr key={i} className="border-b border-cream-100 last:border-0">
                      <td className="py-2.5 pr-4 text-ink-600 whitespace-nowrap">{format(parseISO(r.date), 'MMM d')}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs text-ink-700">
                        {r.sets_completed}×{r.reps_completed}
                        {r.weight_kg > 0 ? ` @ ${r.weight_kg}kg` : ' (BW)'}
                      </td>
                      <td className="py-2.5 text-ink-400 text-xs">{r.notes || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-ink-400">No history for {selEx} yet.</p>
          )}
        </div>
      )}

      {logs.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-ink-400 text-sm">No history yet. Log your first check-in to start tracking!</p>
        </div>
      )}
    </div>
  )
}
