import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import { Plus, Save, CheckCircle2, Scale, Dumbbell, Activity, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

const DISCOMFORTS = [
  { label: 'Knee pain',       value: 'knee pain — avoid squats, lunges, leg press' },
  { label: 'Lower back pain', value: 'lower back pain — avoid deadlifts, heavy squats' },
  { label: 'Shoulder pain',   value: 'shoulder injury — avoid overhead press, dips' },
  { label: 'Wrist pain',      value: 'wrist pain — avoid push-ups on palms, barbell curls' },
  { label: 'Ankle pain',      value: 'ankle injury — avoid jumping, running' },
  { label: 'General fatigue', value: 'general fatigue — reduce intensity by 30%' },
]

function SectionCard({ num, title, icon: Icon, description, children }) {
  return (
    <section className="card p-6">
      <div className="flex items-start gap-3 mb-5">
        <span className="font-mono text-[11px] text-clay-500 tnum pt-0.5" style={{ letterSpacing: '0.12em' }}>
          {num}
        </span>
        <span className="w-6 h-px bg-ink-200 mt-2.5" />
        <Icon size={15} className="text-ink-400 mt-0.5" strokeWidth={1.75} />
        <div className="flex-1 min-w-0">
          <h2 className="font-display text-[16px] font-semibold text-ink-900 tracking-tight">{title}</h2>
          {description && <p className="text-[12px] text-ink-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </section>
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

  function removeEx(i) {
    setExercises(prev => prev.filter((_, idx) => idx !== i))
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.saveCheckin({
        date:              form.date,
        weight_kg:         form.weight_kg,
        calories_eaten:    form.calories_eaten,
        workout_completed: form.workout_completed,
        workout_rating:    form.workout_rating,
        notes:             form.notes,
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
    <Container size="md">
      <PageHeader
        eyebrow="Daily log"
        title="Check-in"
        description="Log today's data. This is what the Progress Agent uses to detect trends and recommend adaptations."
      />

      {saved && (
        <div className="flex items-center gap-2 bg-sage-50 text-sage-700 rounded-lg px-4 py-3 mb-5"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(107, 151, 55, 0.3)' }}>
          <CheckCircle2 size={15} strokeWidth={2} />
          <span className="text-[13px] font-medium">Check-in saved. Agents will use this data in your next plan.</span>
        </div>
      )}

      <div className="flex flex-col gap-5">
        <SectionCard num="01" title="Body & nutrition" icon={Scale}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Date</label>
              <input type="date" className="input tnum" value={form.date} onChange={txt('date')} />
            </div>
            <div>
              <label className="label">Weight · kg</label>
              <input type="number" step={0.1} className="input tnum" value={form.weight_kg} onChange={num('weight_kg')} />
            </div>
            <div className="col-span-2">
              <label className="label">Calories eaten</label>
              <input type="number" className="input tnum" value={form.calories_eaten} onChange={num('calories_eaten')} />
            </div>
          </div>
        </SectionCard>

        <SectionCard num="02" title="Workout" icon={Dumbbell}>
          <button type="button"
            onClick={() => setForm(f => ({ ...f, workout_completed: !f.workout_completed }))}
            className={clsx(
              'w-full flex items-center justify-between gap-2 px-4 py-3 rounded-lg text-[13px] font-medium transition-all duration-150',
              form.workout_completed ? 'bg-sage-500 text-white' : 'bg-paper-100 text-ink-600 hover:bg-paper-200'
            )}
            style={!form.workout_completed ? { boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' } : {}}
          >
            <span className="flex items-center gap-2">
              {form.workout_completed
                ? <CheckCircle2 size={15} strokeWidth={2} />
                : <span className="w-3.5 h-3.5 rounded-full border border-ink-300" />}
              {form.workout_completed ? 'Workout completed' : 'Mark workout as completed'}
            </span>
          </button>

          {form.workout_completed && (
            <div className="mt-4">
              <label className="label">Difficulty rating</label>
              <div className="flex items-center gap-1.5">
                {[1,2,3,4,5].map(r => (
                  <button key={r} type="button"
                    onClick={() => setForm(f => ({ ...f, workout_rating: r }))}
                    className={clsx(
                      'flex-1 py-2 rounded-lg text-[13px] font-semibold tnum transition-all duration-150',
                      form.workout_rating === r
                        ? 'bg-ink-800 text-paper-50'
                        : 'bg-paper-100 text-ink-500 hover:bg-paper-200'
                    )}
                    style={form.workout_rating === r ? {} : { boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}
                  >
                    {r}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-ink-400 mt-2 flex justify-between">
                <span>1 — very easy</span><span>5 — very hard</span>
              </p>
            </div>
          )}

          <div className="mt-4">
            <label className="label">Notes — optional</label>
            <textarea className="input resize-none" rows={3}
              placeholder="e.g. Felt great, slightly sore knees, hit a new PR…"
              value={form.notes} onChange={txt('notes')} />
          </div>
        </SectionCard>

        <SectionCard num="03" title="Physical discomfort today?"
                     icon={AlertTriangle}
                     description="Selecting these updates your constraints — the Fitness Agent will avoid related exercises next week.">
          <div className="grid grid-cols-2 gap-2">
            {DISCOMFORTS.map(d => (
              <button key={d.value} type="button"
                onClick={() => toggleDiscomfort(d.value)}
                className={clsx(
                  'px-3 py-2.5 rounded-lg text-[13px] font-medium text-left transition-all duration-150',
                  discomforts.includes(d.value)
                    ? 'bg-clay-50 text-clay-600'
                    : 'bg-white text-ink-600 hover:bg-paper-100'
                )}
                style={{
                  boxShadow: discomforts.includes(d.value)
                    ? 'inset 0 0 0 1px rgba(216, 100, 58, 0.5)'
                    : 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)'
                }}>
                {d.label}
              </button>
            ))}
          </div>
          {discomforts.length === 0 && (
            <p className="text-[12px] text-ink-400 mt-3 italic">
              No constraints selected. Plans will include all exercises.
            </p>
          )}
        </SectionCard>

        <SectionCard num="04" title="Log exercises" icon={Activity}
                     description="Track weights and reps for progressive overload. The Fitness Agent will use this next week.">
          <div className="flex flex-col gap-2">
            {exercises.map((ex, i) => (
              <div key={i} className="grid grid-cols-[3fr_1fr_1fr_1fr_auto] gap-2 items-end">
                <div>
                  {i === 0 && <label className="label">Exercise</label>}
                  <input className="input" placeholder="e.g. Push-ups" value={ex.name}
                    onChange={e => updateEx(i, 'name', e.target.value)} />
                </div>
                <div>
                  {i === 0 && <label className="label">Sets</label>}
                  <input type="number" min={1} max={20} className="input tnum" value={ex.sets}
                    onChange={e => updateEx(i, 'sets', Number(e.target.value))} />
                </div>
                <div>
                  {i === 0 && <label className="label">Reps</label>}
                  <input className="input tnum" placeholder="8-12" value={ex.reps}
                    onChange={e => updateEx(i, 'reps', e.target.value)} />
                </div>
                <div>
                  {i === 0 && <label className="label">kg</label>}
                  <input type="number" step={0.5} min={0} className="input tnum" value={ex.weight}
                    onChange={e => updateEx(i, 'weight', Number(e.target.value))} />
                </div>
                <div>
                  {i === 0 && <div className="h-[26px]" />}
                  {exercises.length > 1 ? (
                    <button type="button" onClick={() => removeEx(i)}
                      className="w-10 h-[42px] text-ink-400 hover:text-clay-500 hover:bg-clay-50 rounded-lg transition-colors flex items-center justify-center">
                      ×
                    </button>
                  ) : <div className="w-10" />}
                </div>
              </div>
            ))}
          </div>

          <button type="button" onClick={addEx} className="btn-ghost mt-3 text-[13px]">
            <Plus size={14} /> Add exercise
          </button>
        </SectionCard>

        <button onClick={handleSave} disabled={saving}
                className="btn-primary w-full py-3.5 text-[14px]">
          <Save size={14} />
          {saving ? 'Saving…' : 'Save check-in'}
        </button>
      </div>
    </Container>
  )
}
