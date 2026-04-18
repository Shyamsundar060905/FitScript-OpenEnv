import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Plus, Save, CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'

const DISCOMFORTS = [
  { label: '🦵 Knee pain',       value: 'knee pain — avoid squats, lunges, leg press' },
  { label: '🔙 Lower back pain', value: 'lower back pain — avoid deadlifts, heavy squats' },
  { label: '💪 Shoulder pain',   value: 'shoulder injury — avoid overhead press, dips' },
  { label: '🤝 Wrist pain',      value: 'wrist pain — avoid push-ups on palms, barbell curls' },
  { label: '🦶 Ankle pain',      value: 'ankle injury — avoid jumping, running' },
  { label: '😴 General fatigue', value: 'general fatigue — reduce intensity by 30%' },
]

function DiscomfortToggle({ label, active, onClick }) {
  return (
    <button
      type="button" onClick={onClick}
      className={clsx(
        'text-sm font-medium px-3 py-2 rounded-xl border transition-all duration-150 text-left',
        active
          ? 'bg-amber-50 border-amber-300 text-amber-800'
          : 'bg-white border-cream-400 text-ink-600 hover:border-amber-300'
      )}
    >
      {label}
    </button>
  )
}

export default function CheckinPage() {
  const { profile, refreshProfile } = useAuth()
  const today = new Date().toISOString().slice(0, 10)

  const [form, setForm] = useState({
    date: today,
    weight_kg: profile?.weight_kg ?? 70,
    calories_eaten: profile?.tdee_estimate ?? 2000,
    workout_completed: false,
    workout_rating: null,
    notes: '',
  })
  const [discomforts, setDiscomforts] = useState([])
  const [exercises,   setExercises]   = useState([{ name: '', sets: 3, reps: '', weight: 0 }])
  const [saving,      setSaving]      = useState(false)
  const [saved,       setSaved]       = useState(false)

  function num(k) { return e => setForm(f => ({ ...f, [k]: Number(e.target.value) })) }
  function txt(k) { return e => setForm(f => ({ ...f, [k]: e.target.value })) }

  function toggleDiscomfort(val) {
    setDiscomforts(prev =>
      prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val]
    )
  }

  function updateEx(i, k, v) {
    setExercises(prev => prev.map((e, idx) => idx === i ? { ...e, [k]: v } : e))
  }

  function addEx() {
    setExercises(prev => [...prev, { name: '', sets: 3, reps: '', weight: 0 }])
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.saveCheckin({
        date:               form.date,
        weight_kg:          form.weight_kg,
        calories_eaten:     form.calories_eaten,
        workout_completed:  form.workout_completed,
        workout_rating:     form.workout_rating,
        notes:              form.notes,
        discomforts,
        exercises: exercises.filter(e => e.name && e.reps),
      })
      await refreshProfile()
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      setExercises([{ name: '', sets: 3, reps: '', weight: 0 }])
    } catch (ex) {
      alert(ex.detail ?? 'Failed to save check-in')
    } finally { setSaving(false) }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">Daily Check-in</h1>
        <p className="text-sm text-ink-400 mt-1">Log your data — this is what the Progress Agent uses to detect trends.</p>
      </div>

      {saved && (
        <div className="flex items-center gap-2 bg-sage-500/10 border border-sage-500/20 text-sage-700 rounded-xl px-4 py-3 mb-5">
          <CheckCircle2 size={16} />
          <span className="text-sm font-medium">Check-in saved! Your agents will use this data.</span>
        </div>
      )}

      <div className="flex flex-col gap-5">
        {/* Body & Nutrition */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-4">Body & Nutrition</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Date</label>
              <input type="date" className="input" value={form.date} onChange={txt('date')} />
            </div>
            <div>
              <label className="label">Weight today (kg)</label>
              <input type="number" step={0.1} className="input" value={form.weight_kg} onChange={num('weight_kg')} />
            </div>
            <div className="col-span-2">
              <label className="label">Calories eaten</label>
              <input type="number" className="input" value={form.calories_eaten} onChange={num('calories_eaten')} />
            </div>
          </div>
        </div>

        {/* Workout */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-4">Workout</h2>
          <div className="flex items-center gap-3 mb-4">
            <button
              type="button"
              onClick={() => setForm(f => ({ ...f, workout_completed: !f.workout_completed }))}
              className={clsx(
                'flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all duration-150',
                form.workout_completed
                  ? 'bg-sage-500 text-white border-sage-500'
                  : 'bg-white text-ink-600 border-cream-400 hover:border-sage-500'
              )}
            >
              {form.workout_completed ? '✅ Completed' : '☐ Mark as completed'}
            </button>
          </div>

          {form.workout_completed && (
            <div>
              <label className="label">How hard was today's workout?</label>
              <div className="flex gap-2">
                {[1,2,3,4,5].map(r => (
                  <button
                    key={r} type="button"
                    onClick={() => setForm(f => ({ ...f, workout_rating: r }))}
                    className={clsx(
                      'w-10 h-10 rounded-xl border text-sm font-semibold transition-all duration-150',
                      form.workout_rating === r
                        ? 'bg-sage-500 text-white border-sage-500'
                        : 'bg-white text-ink-500 border-cream-400 hover:border-sage-500'
                    )}
                  >
                    {r}
                  </button>
                ))}
                <span className="text-xs text-ink-400 self-center ml-1">1 = very easy · 5 = very hard</span>
              </div>
            </div>
          )}

          <div className="mt-4">
            <label className="label">Notes (optional)</label>
            <textarea
              className="input resize-none"
              rows={3}
              placeholder="e.g. Felt great, slightly sore knees, hit a new PR…"
              value={form.notes}
              onChange={txt('notes')}
            />
          </div>
        </div>

        {/* Discomforts */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-1">Physical Discomfort Today?</h2>
          <p className="text-xs text-ink-400 mb-4">
            Selecting these updates your constraints — the Fitness Agent will avoid related exercises next time.
          </p>
          <div className="grid grid-cols-2 gap-2">
            {DISCOMFORTS.map(d => (
              <DiscomfortToggle
                key={d.value}
                label={d.label}
                active={discomforts.includes(d.value)}
                onClick={() => toggleDiscomfort(d.value)}
              />
            ))}
          </div>
          {discomforts.length === 0 && (
            <p className="text-xs text-ink-400 mt-3">No active constraints — your plan will include all exercises.</p>
          )}
        </div>

        {/* Exercise log */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-1">Log Today's Exercises</h2>
          <p className="text-xs text-ink-400 mb-4">
            Track weights and reps for progressive overload. The Fitness Agent will use this next week.
          </p>

          <div className="flex flex-col gap-3">
            {exercises.map((ex, i) => (
              <div key={i} className="grid grid-cols-[3fr_1fr_1fr_1fr] gap-2">
                <div>
                  {i === 0 && <label className="label">Exercise</label>}
                  <input className="input" placeholder="e.g. Push-ups" value={ex.name} onChange={e => updateEx(i, 'name', e.target.value)} />
                </div>
                <div>
                  {i === 0 && <label className="label">Sets</label>}
                  <input type="number" min={1} max={20} className="input" value={ex.sets} onChange={e => updateEx(i, 'sets', Number(e.target.value))} />
                </div>
                <div>
                  {i === 0 && <label className="label">Reps</label>}
                  <input className="input" placeholder="8-12" value={ex.reps} onChange={e => updateEx(i, 'reps', e.target.value)} />
                </div>
                <div>
                  {i === 0 && <label className="label">kg</label>}
                  <input type="number" step={0.5} min={0} className="input" value={ex.weight} onChange={e => updateEx(i, 'weight', Number(e.target.value))} />
                </div>
              </div>
            ))}
          </div>

          <button type="button" onClick={addEx} className="btn-ghost mt-3 text-sm flex items-center gap-2">
            <Plus size={15} /> Add another exercise
          </button>
        </div>

        <button onClick={handleSave} disabled={saving} className="btn-primary w-full py-3 flex items-center justify-center gap-2">
          <Save size={16} />
          {saving ? 'Saving…' : 'Save Check-in'}
        </button>
      </div>
    </div>
  )
}
