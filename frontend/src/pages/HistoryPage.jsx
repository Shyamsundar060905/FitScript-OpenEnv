import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts'
import { format, parseISO } from 'date-fns'

const CustomTooltip = ({ active, payload, label, unit }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-ink-800 text-paper-50 px-3 py-1.5 rounded-md text-[11px] tnum">
      <span className="text-paper-300">{label}</span>
      <span className="ml-2 font-semibold">{payload[0].value}{unit}</span>
    </div>
  )
}

export default function HistoryPage() {
  const [days, setDays]           = useState(30)
  const [logs, setLogs]           = useState([])
  const [weights, setWeights]     = useState([])
  const [exercises, setExercises] = useState([])
  const [selEx, setSelEx]         = useState('')
  const [exHistory, setExHistory] = useState([])

  useEffect(() => {
    api.getLogs(days).then(setLogs).catch(() => {})
    api.getWeights(days).then(setWeights).catch(() => {})
    api.getExercises(60).then(ex => { setExercises(ex); if (ex.length && !selEx) setSelEx(ex[0]) }).catch(() => {})
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
    <Container size="lg">
      <PageHeader
        eyebrow="Progress"
        title="History"
        description="Everything your agents analyze — body measurements, adherence, and exercise progression."
        actions={
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-ink-400">Range</span>
            <select value={days} onChange={e => setDays(Number(e.target.value))}
                    className="input w-auto text-[12px] py-1.5 tnum">
              {[7,14,30,60,90].map(d => <option key={d} value={d}>{d} days</option>)}
            </select>
          </div>
        }
      />

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-5 mb-5">
        <div className="card p-6">
          <p className="eyebrow mb-1">Body weight</p>
          <h2 className="section-title mb-5">Daily measurements</h2>
          {weightChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={weightChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="wGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"  stopColor="#6B9737" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="#6B9737" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#857E6C' }} axisLine={false} tickLine={false} />
                <YAxis domain={['dataMin - 1', 'dataMax + 1']}
                       tick={{ fontSize: 10, fill: '#857E6C' }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<CustomTooltip unit=" kg" />} cursor={{ stroke: '#D8D3C4', strokeDasharray: '2 4' }} />
                <Area type="monotone" dataKey="kg" stroke="#6B9737" strokeWidth={2} fill="url(#wGrad)"
                      dot={{ r: 2.5, fill: '#6B9737', strokeWidth: 0 }}
                      activeDot={{ r: 5, fill: '#6B9737', stroke: '#FAF7EE', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-[12.5px] text-ink-400">No weight data yet</div>
          )}
        </div>

        <div className="card p-6">
          <p className="eyebrow mb-1">Nutrition</p>
          <h2 className="section-title mb-5">Daily calories</h2>
          {calChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={calChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#857E6C' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#857E6C' }} axisLine={false} tickLine={false} width={40} />
                <Tooltip content={<CustomTooltip unit=" kcal" />} cursor={{ fill: 'rgba(28, 26, 20, 0.04)' }} />
                <Bar dataKey="kcal" fill="#B94A1E" radius={[3, 3, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-[12.5px] text-ink-400">No calorie data yet</div>
          )}
        </div>
      </div>

      {/* Full log table */}
      {logs.length > 0 && (
        <div className="card p-6 mb-5">
          <p className="eyebrow mb-1">Log</p>
          <h2 className="section-title mb-5">Full entries</h2>
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
                {[...logs].reverse().map((l, i) => (
                  <tr key={i} className="hair-b last:border-0">
                    <td className="py-3 pr-4 text-ink-700 whitespace-nowrap tnum">{format(parseISO(l.date), 'MMM d, yyyy')}</td>
                    <td className="py-3 pr-4">
                      {l.workout_completed
                        ? <span className="chip-sage">Done</span>
                        : <span className="text-ink-300">—</span>}
                    </td>
                    <td className="py-3 pr-4 text-ink-600 tnum">{l.workout_rating ? `${l.workout_rating}/5` : '—'}</td>
                    <td className="py-3 pr-4 text-ink-800 tnum">{l.weight_kg ? `${l.weight_kg} kg` : '—'}</td>
                    <td className="py-3 pr-4 text-ink-800 tnum">{l.calories_eaten ? `${Math.round(l.calories_eaten)}` : '—'}</td>
                    <td className="py-3 text-ink-500 text-[12.5px] max-w-[180px] truncate">{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Exercise history */}
      {exercises.length > 0 && (
        <div className="card p-6">
          <div className="flex items-start justify-between mb-5 gap-4 flex-wrap">
            <div>
              <p className="eyebrow mb-1">Progressive overload</p>
              <h2 className="section-title">Exercise progression</h2>
            </div>
            <select value={selEx} onChange={e => setSelEx(e.target.value)}
                    className="input w-auto text-[13px] py-1.5">
              {exercises.map(ex => <option key={ex} value={ex}>{ex}</option>)}
            </select>
          </div>
          {exHistory.length > 0 ? (
            <div className="overflow-x-auto -mx-6 px-6">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="hair-b">
                    {['Date','Performance','Notes'].map(h => (
                      <th key={h} className="pb-2.5 pr-4 eyebrow text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {exHistory.map((r, i) => (
                    <tr key={i} className="hair-b last:border-0">
                      <td className="py-3 pr-4 text-ink-700 whitespace-nowrap tnum">{format(parseISO(r.date), 'MMM d')}</td>
                      <td className="py-3 pr-4 font-mono text-[12px] text-ink-800 tnum">
                        {r.sets_completed} × {r.reps_completed}
                        {r.weight_kg > 0 ? ` @ ${r.weight_kg}kg` : ' (BW)'}
                      </td>
                      <td className="py-3 text-ink-500 text-[12.5px]">{r.notes || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-[13px] text-ink-400">No history for {selEx} yet.</p>
          )}
        </div>
      )}

      {logs.length === 0 && (
        <div className="card p-10 text-center">
          <p className="text-[13.5px] text-ink-400">
            No history yet. Log your first check-in to start tracking.
          </p>
        </div>
      )}
    </Container>
  )
}
