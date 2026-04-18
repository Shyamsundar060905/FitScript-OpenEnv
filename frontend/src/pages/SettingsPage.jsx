import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Save, CheckCircle2, FlaskConical, Trash2, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

const GOALS = ['muscle_gain', 'weight_loss', 'endurance', 'maintenance']
const LEVELS = ['beginner', 'intermediate', 'advanced']
const DIETS  = ['vegetarian', 'vegan', 'gluten_free', 'dairy_free', 'halal']
const EQUIPMENT = [
  'bodyweight', 'dumbbells', 'barbell', 'pull_up_bar',
  'resistance_bands', 'kettlebell', 'gym_machines', 'bench',
]

function Toggle({ active, onClick, children }) {
  return (
    <button
      type="button" onClick={onClick}
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

export default function SettingsPage() {
  const { profile, setProfile, refreshProfile } = useAuth()

  const [form, setForm] = useState({
    weight_kg:            profile?.weight_kg ?? 70,
    age:                  profile?.age ?? 22,
    sessions_per_week:    profile?.sessions_per_week ?? 4,
    goal:                 profile?.goal ?? 'muscle_gain',
    fitness_level:        profile?.fitness_level ?? 'intermediate',
    dietary_restrictions: profile?.dietary_restrictions ?? [],
    available_equipment:  profile?.available_equipment ?? ['bodyweight'],
  })

  const [saved,    setSaved]    = useState(false)
  const [saving,   setSaving]   = useState(false)
  const [seeding,  setSeeding]  = useState(false)
  const [clearing, setClearing] = useState(false)
  const [usage,    setUsage]    = useState(null)
  const [showUsage, setShowUsage] = useState(false)

  function num(k) { return e => setForm(f => ({ ...f, [k]: Number(e.target.value) })) }

  function toggleList(k, v) {
    setForm(f => ({
      ...f,
      [k]: f[k].includes(v) ? f[k].filter(x => x !== v) : [...f[k], v],
    }))
  }

  async function handleSave() {
    setSaving(true)
    try {
      const updated = await api.updateProfile({
        ...form,
        available_equipment: form.available_equipment.length ? form.available_equipment : ['bodyweight'],
      })
      setProfile(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (ex) {
      alert(ex.detail ?? 'Failed to save')
    } finally { setSaving(false) }
  }

  async function handleSeed() {
    setSeeding(true)
    try { await api.seedData(3); alert('✓ 3 weeks of test data seeded!') }
    catch { alert('Failed to seed data') }
    finally { setSeeding(false) }
  }

  async function handleClear() {
    if (!confirm('Delete ALL your progress data? This cannot be undone.')) return
    setClearing(true)
    try { await api.clearData(); alert('✓ All data cleared') }
    catch { alert('Failed to clear data') }
    finally { setClearing(false) }
  }

  async function handleUsage() {
    if (showUsage) { setShowUsage(false); return }
    const data = await api.getUsage().catch(() => null)
    setUsage(data)
    setShowUsage(true)
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">Settings</h1>
        <p className="text-sm text-ink-400 mt-1">Update your profile and preferences.</p>
      </div>

      {saved && (
        <div className="flex items-center gap-2 bg-sage-500/10 border border-sage-500/20 text-sage-700 rounded-xl px-4 py-3 mb-5">
          <CheckCircle2 size={16} />
          <span className="text-sm font-medium">Profile updated!</span>
        </div>
      )}

      <div className="flex flex-col gap-5">
        {/* Basic info */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-4">Basic Info</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Weight (kg)</label>
              <input type="number" step={0.5} className="input" value={form.weight_kg} onChange={num('weight_kg')} />
            </div>
            <div>
              <label className="label">Age</label>
              <input type="number" min={16} max={80} className="input" value={form.age} onChange={num('age')} />
            </div>
            <div>
              <label className="label">Sessions / week</label>
              <input type="number" min={2} max={7} className="input" value={form.sessions_per_week} onChange={num('sessions_per_week')} />
            </div>
          </div>
        </div>

        {/* Goal */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-4">Goal & Level</h2>
          <div className="mb-4">
            <label className="label">Primary Goal</label>
            <div className="flex gap-2 flex-wrap">
              {GOALS.map(g => (
                <Toggle key={g} active={form.goal === g} onClick={() => setForm(f => ({ ...f, goal: g }))}>
                  {g.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </Toggle>
              ))}
            </div>
          </div>
          <div>
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
            <label className="label">Dietary Restrictions</label>
            <div className="flex flex-wrap gap-2">
              {DIETS.map(d => (
                <Toggle key={d} active={form.dietary_restrictions.includes(d)} onClick={() => toggleList('dietary_restrictions', d)}>
                  {d.replace('_', ' ')}
                </Toggle>
              ))}
            </div>
          </div>
        </div>

        <button onClick={handleSave} disabled={saving} className="btn-primary w-full py-3 flex items-center justify-center gap-2">
          <Save size={16} />
          {saving ? 'Saving…' : 'Save Changes'}
        </button>

        {/* Developer tools */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-1">Developer Tools</h2>
          <p className="text-xs text-ink-400 mb-4">For testing and diagnostics only.</p>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <button onClick={handleSeed} disabled={seeding} className="btn-secondary flex items-center justify-center gap-2 text-sm">
              <FlaskConical size={15} />
              {seeding ? 'Seeding…' : 'Seed 3 Weeks Data'}
            </button>
            <button onClick={handleClear} disabled={clearing} className="btn-secondary flex items-center justify-center gap-2 text-sm text-red-500 hover:bg-red-50 hover:border-red-200">
              <Trash2 size={15} />
              {clearing ? 'Clearing…' : 'Clear All My Data'}
            </button>
          </div>

          <button onClick={handleUsage} className="btn-ghost text-xs flex items-center gap-1.5">
            📊 {showUsage ? 'Hide' : 'Show'} Usage & Diagnostics
          </button>

          {showUsage && usage && (
            <div className="mt-3 bg-cream-100 rounded-xl p-4 text-xs font-mono text-ink-600 space-y-1">
              <p>Plans today: {usage.rate_limit?.used_today} / {usage.rate_limit?.daily_limit}</p>
              <p>Last hour: {usage.rate_limit?.used_this_hour}</p>
              {usage.runs?.successful_runs > 0 && (
                <>
                  <p className="mt-2">Total agent runs: {usage.runs.successful_runs}</p>
                  {Object.entries(usage.runs.by_agent ?? {}).map(([agent, s]) => (
                    <p key={agent}>  • {agent}: {s.count} runs, avg {s.avg_ms}ms</p>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        {/* Account info */}
        <div className="card p-6">
          <h2 className="font-display font-bold text-ink-800 mb-3">Profile Info</h2>
          <div className="text-sm text-ink-500 space-y-1 font-mono">
            <p>Name: {profile?.name}</p>
            <p>BMI: {profile ? (profile.weight_kg / ((profile.height_cm / 100) ** 2)).toFixed(1) : '—'}</p>
            <p>TDEE estimate: {profile?.tdee_estimate?.toFixed(0)} kcal/day</p>
            <p>Height: {profile?.height_cm} cm</p>
          </div>
        </div>
      </div>
    </div>
  )
}
