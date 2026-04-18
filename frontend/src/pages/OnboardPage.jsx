import { useState } from 'react'

import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Zap, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

const GOALS = [
  { value: 'muscle_gain',  label: 'Muscle Gain',  emoji: '🏋️' },
  { value: 'weight_loss',  label: 'Weight Loss',  emoji: '🔥' },
  { value: 'endurance',    label: 'Endurance',    emoji: '🏃' },
  { value: 'maintenance',  label: 'Maintenance',  emoji: '⚖️' },
]
const LEVELS = ['beginner', 'intermediate', 'advanced']
const DIETS  = ['vegetarian', 'vegan', 'gluten_free', 'dairy_free', 'halal']
const EQUIPMENT = [
  'bodyweight', 'dumbbells', 'barbell', 'pull_up_bar',
  'resistance_bands', 'kettlebell', 'gym_machines', 'bench',
]
const INJURIES = [
  { label: '🦵 Knee issues',    value: 'knee pain — avoid squats, lunges, leg press' },
  { label: '🔙 Lower back',     value: 'lower back pain — avoid deadlifts, heavy squats' },
  { label: '💪 Shoulder',       value: 'shoulder injury — avoid overhead press, dips' },
  { label: '🤝 Wrist',          value: 'wrist pain — avoid push-ups on palms, barbell curls' },
  { label: '🦶 Ankle',          value: 'ankle injury — avoid jumping, running' },
  { label: '🏃 Hip',            value: 'hip pain — avoid hip hinge movements' },
]

function Toggle({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'px-3 py-1.5 rounded-xl text-sm font-medium border transition-all duration-150',
        active
          ? 'bg-sage-500 text-white border-sage-500 shadow-card'
          : 'bg-white text-ink-600 border-cream-400 hover:border-sage-500 hover:text-sage-600'
      )}
    >
      {children}
    </button>
  )
}

export default function OnboardPage() {
  const { setProfile } = useAuth()

  const [err, setErr]   = useState('')
  const [loading, setLoading] = useState(false)

  const [form, setForm] = useState({
    name: '', age: 22, weight_kg: 70, height_cm: 170, sessions_per_week: 4,
    goal: 'muscle_gain', fitness_level: 'intermediate',
    dietary_restrictions: [], available_equipment: ['bodyweight'], injuries: [],
  })

  function num(k) { return e => setForm(f => ({ ...f, [k]: Number(e.target.value) })) }
  function txt(k) { return e => setForm(f => ({ ...f, [k]: e.target.value })) }

  function toggleList(k, v) {
    setForm(f => ({
      ...f,
      [k]: f[k].includes(v) ? f[k].filter(x => x !== v) : [...f[k], v],
    }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setErr('Please enter your name'); return }
    if (!form.available_equipment.length) { setErr('Select at least one equipment'); return }
    setErr(''); setLoading(true)

    const af = { beginner: 1.4, intermediate: 1.6, advanced: 1.8 }[form.fitness_level]
    const tdee_base = form.weight_kg * 22 * af
    const tdee_map  = { weight_loss: tdee_base - 400, muscle_gain: tdee_base + 300, endurance: tdee_base + 100, maintenance: tdee_base }
    const tdee_estimate = Math.round(tdee_map[form.goal])

    try {
      const p = await api.createProfile({
        name: form.name.trim(),
        age: form.age, weight_kg: form.weight_kg, height_cm: form.height_cm,
        goal: form.goal, fitness_level: form.fitness_level,
        dietary_restrictions: form.dietary_restrictions,
        available_equipment: form.available_equipment,
        sessions_per_week: form.sessions_per_week,
        tdee_estimate,
      })
      if (form.injuries.length) {
        await api.updateConstraints(form.injuries)
      }
      setProfile(p)

    } catch (ex) {
      setErr(ex.detail ?? 'Could not save profile')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center p-4 py-10">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl bg-sage-500 flex items-center justify-center">
            <Zap size={18} className="text-white" strokeWidth={2.5} />
          </div>
          <h1 className="font-display text-2xl font-bold text-ink-900">Set up your profile</h1>
        </div>
        <p className="text-sm text-ink-400 mb-8">Takes 2 minutes — helps our agents personalise everything for you.</p>

        {err && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2.5 rounded-xl mb-5">
            <AlertCircle size={15} /><span>{err}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {/* Basic */}
          <div className="card p-6">
            <h2 className="font-display font-bold text-ink-800 mb-4">Basic Info</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="label">Your name</label>
                <input className="input" placeholder="e.g. Arjun" value={form.name} onChange={txt('name')} />
              </div>
              <div>
                <label className="label">Age</label>
                <input className="input" type="number" min={16} max={80} value={form.age} onChange={num('age')} />
              </div>
              <div>
                <label className="label">Sessions / week</label>
                <input className="input" type="number" min={2} max={7} value={form.sessions_per_week} onChange={num('sessions_per_week')} />
              </div>
              <div>
                <label className="label">Weight (kg)</label>
                <input className="input" type="number" step={0.5} value={form.weight_kg} onChange={num('weight_kg')} />
              </div>
              <div>
                <label className="label">Height (cm)</label>
                <input className="input" type="number" step={0.5} value={form.height_cm} onChange={num('height_cm')} />
              </div>
            </div>
          </div>

          {/* Goal */}
          <div className="card p-6">
            <h2 className="font-display font-bold text-ink-800 mb-4">Primary Goal</h2>
            <div className="grid grid-cols-2 gap-3">
              {GOALS.map(g => (
                <button
                  key={g.value} type="button"
                  onClick={() => setForm(f => ({ ...f, goal: g.value }))}
                  className={clsx(
                    'flex items-center gap-3 p-4 rounded-xl border text-left transition-all duration-150',
                    form.goal === g.value
                      ? 'border-sage-500 bg-sage-500/8 shadow-card'
                      : 'border-cream-400 bg-white hover:border-sage-500/50'
                  )}
                >
                  <span className="text-2xl">{g.emoji}</span>
                  <span className="font-medium text-sm text-ink-800">{g.label}</span>
                </button>
              ))}
            </div>

            <div className="mt-4">
              <label className="label">Fitness Level</label>
              <div className="flex gap-2">
                {LEVELS.map(l => (
                  <Toggle key={l} active={form.fitness_level === l} onClick={() => setForm(f => ({ ...f, fitness_level: l }))}>
                    {l.charAt(0).toUpperCase() + l.slice(1)}
                  </Toggle>
                ))}
              </div>
            </div>
          </div>

          {/* Equipment & Diet */}
          <div className="card p-6">
            <h2 className="font-display font-bold text-ink-800 mb-4">Equipment & Diet</h2>
            <div className="mb-4">
              <label className="label">Available Equipment</label>
              <div className="flex flex-wrap gap-2">
                {EQUIPMENT.map(e => (
                  <Toggle key={e} active={form.available_equipment.includes(e)} onClick={() => toggleList('available_equipment', e)}>
                    {e.replace('_', ' ')}
                  </Toggle>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Dietary Restrictions (optional)</label>
              <div className="flex flex-wrap gap-2">
                {DIETS.map(d => (
                  <Toggle key={d} active={form.dietary_restrictions.includes(d)} onClick={() => toggleList('dietary_restrictions', d)}>
                    {d.replace('_', ' ')}
                  </Toggle>
                ))}
              </div>
            </div>
          </div>

          {/* Injuries */}
          <div className="card p-6">
            <h2 className="font-display font-bold text-ink-800 mb-1">Existing Injuries</h2>
            <p className="text-xs text-ink-400 mb-4">The Fitness Agent will skip exercises that aggravate these.</p>
            <div className="grid grid-cols-2 gap-2">
              {INJURIES.map(inj => (
                <Toggle key={inj.value} active={form.injuries.includes(inj.value)} onClick={() => toggleList('injuries', inj.value)}>
                  {inj.label}
                </Toggle>
              ))}
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3 text-base">
            {loading ? 'Creating profile…' : '🚀 Create My Profile'}
          </button>
        </form>
      </div>
    </div>
  )
}