import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import {
  Save, CheckCircle2, FlaskConical, Trash2, BarChart2, User, Target,
  Package, Wrench, ChevronDown
} from 'lucide-react'
import clsx from 'clsx'

const GOALS = ['muscle_gain', 'weight_loss', 'endurance', 'maintenance']
const LEVELS = ['beginner', 'intermediate', 'advanced']
const DIETS = ['vegetarian', 'eggetarian', 'non_vegetarian', 'vegan', 'gluten_free', 'dairy_free']
const EQUIPMENT = [
  'bodyweight', 'dumbbells', 'barbell', 'pull_up_bar',
  'resistance_bands', 'kettlebell', 'gym_machines', 'bench',
]

function Toggle({ active, onClick, children }) {
  return (
    <button type="button" onClick={onClick}
      className={clsx('toggle', active ? 'toggle-on' : 'toggle-off')}>
      {children}
    </button>
  )
}

function SectionCard({ title, icon: Icon, description, children }) {
  return (
    <section className="card p-6">
      <div className="flex items-start gap-3 mb-5">
        <Icon size={15} className="text-ink-400 mt-0.5" strokeWidth={1.75} />
        <div>
          <h2 className="font-display text-[16px] font-semibold text-ink-900 tracking-tight">{title}</h2>
          {description && <p className="text-[12px] text-ink-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

export default function SettingsPage() {
  const { profile, setProfile } = useAuth()

  const [form, setForm] = useState({
    weight_kg:            profile?.weight_kg ?? 70,
    age:                  profile?.age ?? 22,
    sessions_per_week:    profile?.sessions_per_week ?? 4,
    goal:                 profile?.goal ?? 'muscle_gain',
    fitness_level:        profile?.fitness_level ?? 'intermediate',
    dietary_restrictions: profile?.dietary_restrictions ?? [],
    available_equipment:  profile?.available_equipment ?? ['bodyweight'],
  })

  const [saved,     setSaved]     = useState(false)
  const [saving,    setSaving]    = useState(false)
  const [seeding,   setSeeding]   = useState(false)
  const [clearing,  setClearing]  = useState(false)
  const [usage,     setUsage]     = useState(null)
  const [showUsage, setShowUsage] = useState(false)
  const [allergies, setAllergies] = useState('')

  // Fetch existing constraints to pre-fill the allergy box
  useEffect(() => {
    api.getConstraints().then(d => {
      const allergyConstraint = d.constraints.find(c => c.startsWith('SEVERE FOOD ALLERGY:'))
      if (allergyConstraint) {
        // Extract just the food names from the constraint string
        const match = allergyConstraint.match(/SEVERE FOOD ALLERGY: (.*) — STRICTLY/)
        if (match) setAllergies(match[1])
      }
    }).catch(() => {})
  }, [])

  function num(k) { return e => setForm(f => ({ ...f, [k]: Number(e.target.value) })) }

  function toggleList(k, v) {
    setForm(f => ({ ...f, [k]: f[k].includes(v) ? f[k].filter(x => x !== v) : [...f[k], v] }))
  }

  async function handleSave() {
    setSaving(true)
    try {
      // 1. Save standard profile data
      const updated = await api.updateProfile({
        ...form,
        available_equipment: form.available_equipment.length ? form.available_equipment : ['bodyweight'],
      })
      setProfile(updated)

      // 2. Handle the Allergy Constraint
      const existing = await api.getConstraints()
      // Keep everything EXCEPT the old allergy
      const filteredConstraints = existing.constraints.filter(c => !c.startsWith('SEVERE FOOD ALLERGY:'))
      
      // If they typed a new allergy, add it to the list
      if (allergies.trim()) {
        filteredConstraints.push(`SEVERE FOOD ALLERGY: ${allergies.trim()} — STRICTLY AVOID IN ALL MEALS`)
      }
      // Save constraints
      await api.updateConstraints(filteredConstraints)

      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (ex) { 
      alert(ex.detail ?? 'Failed to save') 
    } finally { 
      setSaving(true) 
      setSaving(false) // Reset saving state
    }
  }
  async function handleSeed() {
    setSeeding(true)
    try { await api.seedData(3); alert('✓ 3 weeks of test data seeded') }
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

  const bmi = profile ? (profile.weight_kg / ((profile.height_cm / 100) ** 2)).toFixed(1) : '—'

  return (
    <Container size="md">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Update your profile, preferences, and review system usage."
      />

      {saved && (
        <div className="flex items-center gap-2 bg-sage-50 text-sage-700 rounded-lg px-4 py-3 mb-5"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(107, 151, 55, 0.3)' }}>
          <CheckCircle2 size={15} strokeWidth={2} />
          <span className="text-[13px] font-medium">Profile updated</span>
        </div>
      )}

      <div className="flex flex-col gap-5">
        <SectionCard title="Basic info" icon={User}>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Weight · kg</label>
              <input type="number" step={0.5} className="input tnum" value={form.weight_kg} onChange={num('weight_kg')} />
            </div>
            <div>
              <label className="label">Age</label>
              <input type="number" min={16} max={80} className="input tnum" value={form.age} onChange={num('age')} />
            </div>
            <div>
              <label className="label">Sessions/wk</label>
              <input type="number" min={2} max={7} className="input tnum" value={form.sessions_per_week} onChange={num('sessions_per_week')} />
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Goal & level" icon={Target}>
          <div className="mb-5">
            <label className="label">Primary goal</label>
            <div className="flex flex-wrap gap-2">
              {GOALS.map(g => (
                <Toggle key={g} active={form.goal === g} onClick={() => setForm(f => ({ ...f, goal: g }))}>
                  {g.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </Toggle>
              ))}
            </div>
          </div>
          <div>
            <label className="label">Fitness level</label>
            <div className="flex gap-2">
              {LEVELS.map(l => (
                <Toggle key={l} active={form.fitness_level === l} onClick={() => setForm(f => ({ ...f, fitness_level: l }))}>
                  {l.charAt(0).toUpperCase() + l.slice(1)}
                </Toggle>
              ))}
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Equipment & diet" icon={Package}>
          <div className="mb-5">
            <label className="label">Available equipment</label>
            <div className="flex flex-wrap gap-2">
              {EQUIPMENT.map(e => (
                <Toggle key={e} active={form.available_equipment.includes(e)} onClick={() => toggleList('available_equipment', e)}>
                  {e.replace(/_/g, ' ')}
                </Toggle>
              ))}
            </div>
          </div>
          <div>
            <label className="label">Dietary restrictions</label>
            <div className="flex flex-wrap gap-2">
              {DIETS.map(d => (
                <Toggle key={d} active={form.dietary_restrictions.includes(d)} onClick={() => toggleList('dietary_restrictions', d)}>
                  {d.replace(/_/g, ' ')}
                </Toggle>
              ))}
            </div>
          </div>
          <div className="pt-4 hair-t">
            <label className="label">Food Allergies</label>
            <input 
              className="input" 
              placeholder="e.g. peanuts, shellfish, soy" 
              value={allergies} 
              onChange={e => setAllergies(e.target.value)} 
            />
            <p className="text-[11px] text-ink-400 mt-1.5 italic">
              Any foods listed here will be strictly excluded by the Nutrition Agent.
            </p>
          </div>
        </SectionCard>

        <button onClick={handleSave} disabled={saving} className="btn-primary w-full py-3.5 text-[14px]">
          <Save size={14} />
          {saving ? 'Saving…' : 'Save changes'}
        </button>

        {/* Computed info */}
        <div className="card p-6 bg-paper-100">
          <p className="eyebrow mb-3">Computed</p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2.5 text-[12.5px]">
            <div className="flex justify-between"><dt className="text-ink-500">Name</dt><dd className="font-medium text-ink-800">{profile?.name}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-500">Height</dt><dd className="font-medium text-ink-800 tnum">{profile?.height_cm} cm</dd></div>
            <div className="flex justify-between"><dt className="text-ink-500">BMI</dt><dd className="font-medium text-ink-800 tnum">{bmi}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-500">TDEE target</dt><dd className="font-medium text-ink-800 tnum">{profile?.tdee_estimate?.toFixed(0)} kcal/day</dd></div>
          </dl>
        </div>

        {/* Developer tools */}
        <SectionCard title="Developer tools" icon={Wrench}
                     description="For testing the multi-agent pipeline. Not part of the regular user flow.">
          <div className="grid sm:grid-cols-2 gap-3 mb-4">
            <button onClick={handleSeed} disabled={seeding} className="btn-secondary text-[13px]">
              <FlaskConical size={14} />
              {seeding ? 'Seeding…' : 'Seed 3 weeks of data'}
            </button>
            <button onClick={handleClear} disabled={clearing} className="btn-danger text-[13px]">
              <Trash2 size={14} />
              {clearing ? 'Clearing…' : 'Clear all my data'}
            </button>
          </div>

          <button onClick={handleUsage} className="btn-ghost text-[12.5px]">
            <BarChart2 size={13} />
            {showUsage ? 'Hide' : 'Show'} usage & diagnostics
            <ChevronDown size={13} className={clsx('transition-transform', showUsage && 'rotate-180')} />
          </button>

          {showUsage && usage && (
            <div className="mt-3 bg-ink-800 text-paper-100 rounded-lg p-4 text-[11.5px] font-mono tnum">
              <div className="flex justify-between hair-b pb-2 mb-2" style={{ borderColor: 'rgba(250, 247, 238, 0.1)' }}>
                <span className="text-paper-300">Plans today</span>
                <span>{usage.rate_limit?.used_today} / {usage.rate_limit?.daily_limit}</span>
              </div>
              <div className="flex justify-between pb-2">
                <span className="text-paper-300">Last hour</span>
                <span>{usage.rate_limit?.used_this_hour}</span>
              </div>
              {usage.runs?.successful_runs > 0 && (
                <>
                  <div className="hair-t pt-2 mt-2 flex justify-between" style={{ borderColor: 'rgba(250, 247, 238, 0.1)' }}>
                    <span className="text-paper-300">Agent runs (total)</span>
                    <span>{usage.runs.successful_runs}</span>
                  </div>
                  {Object.entries(usage.runs.by_agent ?? {}).map(([agent, s]) => (
                    <div key={agent} className="flex justify-between pl-2 mt-1">
                      <span className="text-paper-300">→ {agent}</span>
                      <span>{s.count} runs · {s.avg_ms}ms avg</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </SectionCard>
      </div>
    </Container>
  )
}
