import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Mark } from '../components/AppShell'
import {
  AlertCircle, ArrowRight, User, Target, Package, HeartPulse,
  Stethoscope, Moon
} from 'lucide-react'
import clsx from 'clsx'

const GOALS = [
  { value: 'muscle_gain',  label: 'Muscle Gain',  sub: 'Build mass & strength',    emoji: '🏋️' },
  { value: 'weight_loss',  label: 'Weight Loss',  sub: 'Reduce body fat',          emoji: '🔥' },
  { value: 'endurance',    label: 'Endurance',    sub: 'Improve cardio capacity',  emoji: '🏃' },
  { value: 'maintenance',  label: 'Maintenance',  sub: 'Stay at current level',    emoji: '⚖️' },
]
const LEVELS = ['beginner', 'intermediate', 'advanced']
const ACTIVITY_LEVELS = [
  { value: 'sedentary',     label: 'Sedentary',          sub: 'Desk job, little walking' },
  { value: 'light',         label: 'Lightly active',     sub: 'Some daily walking' },
  { value: 'moderate',      label: 'Moderately active',  sub: 'On feet most of day' },
  { value: 'very_active',   label: 'Very active',        sub: 'Physical labour / sport' },
]
const DIETS  = ['vegetarian', 'vegan', 'gluten_free', 'dairy_free', 'halal']
const EQUIPMENT = [
  'bodyweight', 'dumbbells', 'barbell', 'pull_up_bar',
  'resistance_bands', 'kettlebell', 'gym_machines', 'bench',
]

// Health conditions — encoded as constraint strings so the Nutrition & Fitness
// agents pick them up via the existing /constraints endpoint. Zero backend changes.
const HEALTH_CONDITIONS = [
  {
    label: 'Type 2 Diabetes',
    value: 'type 2 diabetes — prioritize low-GI foods (ragi, oats, moong dal); limit white rice, refined sugar, fruit juices; emphasize protein and fibre at every meal to blunt glucose spikes',
    note:  '~77M Indians affected',
  },
  {
    label: 'Pre-diabetes / Insulin resistance',
    value: 'pre-diabetic — favour low-GI carbs; combine carbs with protein or healthy fat; avoid sugary drinks and refined flour',
    note:  'Early intervention matters',
  },
  {
    label: 'Hypertension (high BP)',
    value: 'hypertension — reduce sodium (pickles, papad, namkeen, processed foods); emphasize potassium-rich foods (banana, spinach, coconut water); avoid Valsalva holds in strength training',
    note:  '~220M Indians affected',
  },
  {
    label: 'High cholesterol',
    value: 'high cholesterol — favour soluble fibre (oats, legumes, psyllium); limit fried foods and vanaspati/ghee excess; include omega-3 sources (flax, chia, walnut)',
    note:  'Diet response is strong',
  },
  {
    label: 'PCOS / PCOD',
    value: 'PCOS — low glycemic load diet, adequate protein, resistance training preferred over excessive cardio; anti-inflammatory foods (turmeric, berries, nuts)',
    note:  'Common in Indian women',
  },
  {
    label: 'Hypothyroidism',
    value: 'hypothyroid — ensure iodine (iodized salt) and selenium (brazil nuts, eggs); avoid excessive raw cruciferous vegetables (cabbage, cauliflower) around levothyroxine',
    note:  'Affects metabolism',
  },
]

const INJURIES = [
  { label: 'Knee issues',    value: 'knee pain — avoid squats, lunges, leg press' },
  { label: 'Lower back',     value: 'lower back pain — avoid deadlifts, heavy squats' },
  { label: 'Shoulder',       value: 'shoulder injury — avoid overhead press, dips' },
  { label: 'Wrist',          value: 'wrist pain — avoid push-ups on palms, barbell curls' },
  { label: 'Ankle',          value: 'ankle injury — avoid jumping, running' },
  { label: 'Hip',            value: 'hip pain — avoid hip hinge movements' },
]

function Toggle({ active, onClick, children }) {
  return (
    <button type="button" onClick={onClick}
      className={clsx('toggle', active ? 'toggle-on' : 'toggle-off')}>
      {children}
    </button>
  )
}

function SectionCard({ num, title, icon: Icon, description, children }) {
  return (
    <section className="card p-7">
      <div className="flex items-start gap-3 mb-5">
        <span className="font-mono text-[11px] text-clay-500 tnum pt-0.5" style={{ letterSpacing: '0.12em' }}>
          {num}
        </span>
        <span className="w-6 h-px bg-ink-200 mt-2.5" />
        <Icon size={15} className="text-ink-400 mt-0.5" strokeWidth={1.75} />
        <div className="flex-1">
          <h2 className="font-display text-[17px] font-semibold text-ink-900 tracking-tight">{title}</h2>
          {description && <p className="text-[12px] text-ink-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

export default function OnboardPage() {
  const { setProfile } = useAuth()
  const [err, setErr]   = useState('')
  const [loading, setLoading] = useState(false)

  const [form, setForm] = useState({
    name: '', age: 22, sex: 'male',
    weight_kg: 70, height_cm: 170, sessions_per_week: 4,
    goal: 'muscle_gain', fitness_level: 'intermediate',
    activity_level: 'moderate',
    sleep_hours: 7,
    water_litres: 2,
    dietary_restrictions: [], available_equipment: ['bodyweight'],
    injuries: [],
    health_conditions: [],
  })

  function num(k) { return e => setForm(f => ({ ...f, [k]: Number(e.target.value) })) }
  function txt(k) { return e => setForm(f => ({ ...f, [k]: e.target.value })) }

  function toggleList(k, v) {
    setForm(f => ({
      ...f,
      [k]: f[k].includes(v) ? f[k].filter(x => x !== v) : [...f[k], v],
    }))
  }

  // TDEE using Mifflin-St Jeor + activity multiplier
  // BMR = 10w + 6.25h − 5a + s    where s = +5 for male, −161 for female
  const activity_mult = {
    sedentary: 1.2, light: 1.375, moderate: 1.55, very_active: 1.725,
  }[form.activity_level] ?? 1.55
  const sex_offset = form.sex === 'male' ? 5 : -161
  const bmr = 10 * form.weight_kg + 6.25 * form.height_cm - 5 * form.age + sex_offset
  const tdee_preview = Math.round(bmr * activity_mult)
  const bmi = form.height_cm ? (form.weight_kg / ((form.height_cm / 100) ** 2)).toFixed(1) : '—'

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setErr('Please enter your name'); return }
    if (!form.available_equipment.length) { setErr('Select at least one piece of equipment'); return }
    setErr(''); setLoading(true)

    const tdee_map = {
      weight_loss: tdee_preview - 400,
      muscle_gain: tdee_preview + 250,
      endurance:   tdee_preview + 100,
      maintenance: tdee_preview,
    }
    const tdee_estimate = Math.round(tdee_map[form.goal])

    try {
      const p = await api.createProfile({
        name: form.name.trim(),
        age: form.age, sex: form.sex,
        weight_kg: form.weight_kg, height_cm: form.height_cm,
        goal: form.goal, fitness_level: form.fitness_level,
        dietary_restrictions: form.dietary_restrictions,
        available_equipment: form.available_equipment,
        sessions_per_week: form.sessions_per_week,
        tdee_estimate,
      })

      // Merge everything into the constraints list — zero backend changes
      const combined = [...form.injuries, ...form.health_conditions]
      if (form.sleep_hours < 6) {
        combined.push(`low sleep (${form.sleep_hours}h) — prioritize recovery, reduce training volume 15%`)
      }
      if (form.water_litres < 1.5) {
        combined.push(`low hydration (${form.water_litres}L/day) — recommend increasing to 2.5-3L especially on training days`)
      }
      if (combined.length) await api.updateConstraints(combined)

      setProfile(p)
    } catch (ex) {
      setErr(ex.detail ?? 'Could not save profile')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <Mark size={32} />
          <span className="font-mono text-[10px] text-ink-400 tnum" style={{ letterSpacing: '0.18em' }}>
            Step · Onboarding
          </span>
        </div>

        <div className="mb-9">
          <p className="eyebrow text-clay-500 mb-2 flex items-center gap-2">
            <span className="w-1 h-1 bg-clay-500 rounded-full" />
            Profile setup
          </p>
          <h1 className="font-display text-display-lg text-ink-900 mb-3">
            Tell your agents about you.
          </h1>
          <p className="text-[14px] text-ink-500 max-w-lg leading-relaxed">
            The more context you give, the better your plan. We ask about health conditions because
            they fundamentally change which foods and exercises are safe — unlike generic fitness apps,
            your agents adapt accordingly.
          </p>
        </div>

        {err && (
          <div className="flex items-start gap-2 bg-clay-50 text-clay-600 text-[13px] px-3 py-2.5 rounded-lg mb-5"
               style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.35)' }}>
            <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
            <span>{err}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* 01 — basics */}
          <SectionCard num="01" title="About you" icon={User}>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="label">Name</label>
                <input className="input" placeholder="e.g. Arjun Sharma" value={form.name} onChange={txt('name')} />
              </div>
              <div>
                <label className="label">Age</label>
                <input className="input" type="number" min={16} max={80} value={form.age} onChange={num('age')} />
              </div>
              <div>
                <label className="label">Biological sex</label>
                <div className="flex gap-2">
                  {[
                    { v: 'male',   l: 'Male'   },
                    { v: 'female', l: 'Female' },
                  ].map(opt => (
                    <button key={opt.v} type="button"
                      onClick={() => setForm(f => ({ ...f, sex: opt.v }))}
                      className={clsx(
                        'flex-1 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150',
                        form.sex === opt.v
                          ? 'bg-ink-800 text-paper-50'
                          : 'bg-white text-ink-600 hover:bg-paper-100'
                      )}
                      style={form.sex === opt.v ? {} : { boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}>
                      {opt.l}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="label">Weight · kg</label>
                <input className="input" type="number" step={0.5} value={form.weight_kg} onChange={num('weight_kg')} />
              </div>
              <div>
                <label className="label">Height · cm</label>
                <input className="input" type="number" step={0.5} value={form.height_cm} onChange={num('height_cm')} />
              </div>
              <div className="col-span-2">
                <label className="label">Sessions per week</label>
                <input className="input" type="number" min={2} max={7} value={form.sessions_per_week} onChange={num('sessions_per_week')} />
                <p className="text-[10.5px] text-ink-400 mt-1">Biological sex used only for BMR calculation (Mifflin-St Jeor equation).</p>
              </div>
              <div className="col-span-2 flex items-center gap-2 mt-1 text-[12px] text-ink-500 flex-wrap">
                <span className="chip-paper">BMI <span className="ml-1 serif-num font-semibold text-ink-800">{bmi}</span></span>
                <span className="chip-paper">Est. TDEE <span className="ml-1 serif-num font-semibold text-ink-800">{tdee_preview}</span><span className="ml-0.5">kcal</span></span>
                <span className="text-ink-300 text-[11px]">computed live</span>
              </div>
            </div>
          </SectionCard>

          {/* 02 — goal */}
          <SectionCard num="02" title="Primary goal" icon={Target}>
            <div className="grid grid-cols-2 gap-2 mb-5">
              {GOALS.map(g => (
                <button key={g.value} type="button"
                  onClick={() => setForm(f => ({ ...f, goal: g.value }))}
                  className={clsx(
                    'flex items-center gap-3 p-3.5 rounded-lg text-left transition-all duration-150',
                    form.goal === g.value
                      ? 'bg-sage-50 text-ink-900'
                      : 'bg-white hover:bg-paper-100 text-ink-700'
                  )}
                  style={{
                    boxShadow: form.goal === g.value
                      ? 'inset 0 0 0 1.5px rgba(107, 151, 55, 0.8), 0 0 0 3px rgba(107, 151, 55, 0.1)'
                      : 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)',
                  }}>
                  <span className="text-xl">{g.emoji}</span>
                  <div>
                    <p className="text-[13.5px] font-semibold">{g.label}</p>
                    <p className="text-[11px] text-ink-400">{g.sub}</p>
                  </div>
                </button>
              ))}
            </div>
            <div>
              <label className="label">Fitness level</label>
              <div className="flex gap-2">
                {LEVELS.map(l => (
                  <Toggle key={l} active={form.fitness_level === l}
                    onClick={() => setForm(f => ({ ...f, fitness_level: l }))}>
                    {l.charAt(0).toUpperCase() + l.slice(1)}
                  </Toggle>
                ))}
              </div>
            </div>
          </SectionCard>

          {/* 03 — lifestyle */}
          <SectionCard num="03" title="Lifestyle" icon={Moon}
                       description="These help compute accurate calorie targets and detect recovery issues.">
            <div className="mb-5">
              <label className="label">Activity level (outside workouts)</label>
              <div className="grid grid-cols-2 gap-2">
                {ACTIVITY_LEVELS.map(a => (
                  <button key={a.value} type="button"
                    onClick={() => setForm(f => ({ ...f, activity_level: a.value }))}
                    className={clsx(
                      'p-3 rounded-lg text-left transition-all duration-150',
                      form.activity_level === a.value
                        ? 'bg-sage-50 text-ink-900'
                        : 'bg-white hover:bg-paper-100 text-ink-700'
                    )}
                    style={{
                      boxShadow: form.activity_level === a.value
                        ? 'inset 0 0 0 1.5px rgba(107, 151, 55, 0.8), 0 0 0 3px rgba(107, 151, 55, 0.1)'
                        : 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)',
                    }}>
                    <p className="text-[13px] font-semibold">{a.label}</p>
                    <p className="text-[11px] text-ink-400 mt-0.5">{a.sub}</p>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Sleep · hours/night</label>
                <input type="number" step={0.5} min={3} max={12} className="input tnum"
                       value={form.sleep_hours} onChange={num('sleep_hours')} />
                {form.sleep_hours < 6 && (
                  <p className="text-[10.5px] text-clay-600 mt-1">Low sleep → recovery-first programming</p>
                )}
              </div>
              <div>
                <label className="label">Water · litres/day</label>
                <input type="number" step={0.25} min={0.5} max={6} className="input tnum"
                       value={form.water_litres} onChange={num('water_litres')} />
              </div>
            </div>
          </SectionCard>

          {/* 04 — HEALTH CONDITIONS (new) */}
          <SectionCard num="04" title="Health conditions" icon={Stethoscope}
                       description="Many Indians are unaware that conditions like diabetes or hypertension require specific dietary adaptations. Your Nutrition Agent adjusts food choices accordingly.">
            <div className="grid grid-cols-1 gap-2">
              {HEALTH_CONDITIONS.map(hc => (
                <button key={hc.value} type="button"
                  onClick={() => toggleList('health_conditions', hc.value)}
                  className={clsx(
                    'flex items-center justify-between gap-3 p-3 rounded-lg text-left transition-all duration-150',
                    form.health_conditions.includes(hc.value)
                      ? 'bg-clay-50 text-clay-700'
                      : 'bg-white hover:bg-paper-100 text-ink-700'
                  )}
                  style={{
                    boxShadow: form.health_conditions.includes(hc.value)
                      ? 'inset 0 0 0 1px rgba(216, 100, 58, 0.5)'
                      : 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)',
                  }}>
                  <span className="text-[13px] font-medium">{hc.label}</span>
                  <span className="text-[10.5px] text-ink-400 italic">{hc.note}</span>
                </button>
              ))}
            </div>
            {form.health_conditions.length === 0 && (
              <p className="text-[11.5px] text-ink-400 mt-3 italic">
                None selected — skip this section if you have no diagnosed conditions.
              </p>
            )}
            <p className="text-[10.5px] text-ink-400 mt-4 italic">
              Educational content only. Always consult your doctor before changing diet or exercise.
            </p>
          </SectionCard>

          {/* 05 — equipment & diet */}
          <SectionCard num="05" title="Equipment & diet" icon={Package}>
            <div className="mb-5">
              <label className="label">Available equipment</label>
              <div className="flex flex-wrap gap-2">
                {EQUIPMENT.map(e => (
                  <Toggle key={e} active={form.available_equipment.includes(e)}
                    onClick={() => toggleList('available_equipment', e)}>
                    {e.replace(/_/g, ' ')}
                  </Toggle>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Dietary preferences <span className="normal-case tracking-normal text-ink-400 font-normal ml-1">— optional</span></label>
              <div className="flex flex-wrap gap-2">
                {DIETS.map(d => (
                  <Toggle key={d} active={form.dietary_restrictions.includes(d)}
                    onClick={() => toggleList('dietary_restrictions', d)}>
                    {d.replace(/_/g, ' ')}
                  </Toggle>
                ))}
              </div>
            </div>
          </SectionCard>

          {/* 06 — injuries */}
          <SectionCard num="06" title="Physical constraints" icon={HeartPulse}
                       description="The Fitness Agent will avoid exercises that could aggravate these.">
            <div className="grid grid-cols-2 gap-2">
              {INJURIES.map(inj => (
                <Toggle key={inj.value} active={form.injuries.includes(inj.value)}
                  onClick={() => toggleList('injuries', inj.value)}>
                  {inj.label}
                </Toggle>
              ))}
            </div>
          </SectionCard>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3.5 text-[14px] mt-3">
            {loading ? 'Creating profile…' : 'Create profile & start'}
            {!loading && <ArrowRight size={14} />}
          </button>
        </form>
      </div>
    </div>
  )
}
