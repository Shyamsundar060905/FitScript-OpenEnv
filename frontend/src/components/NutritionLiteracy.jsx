import { Info, Leaf, HeartPulse } from 'lucide-react'

/**
 * NutritionLiteracy v2
 *
 * Educational panel explaining WHY the Nutrition Agent chose specific foods.
 * Purely deterministic — computed from profile + nutrition_plan, no LLM calls.
 *
 * v2 additions:
 *   - Daily Glycemic Load (GL = GI × carbs_g ÷ 100) per meal and per day
 *   - Portion-aware parsing (100g oats, 1 cup milk, 2 roti, etc.)
 *   - GL band classification: <80 low, 80-120 medium, >120 high
 */

// GI values + approximate carb content per 100g (for GL estimation).
// Sources: ICMR/NIN tables + standard GI reference databases.
const FOOD_DATA = {
  'white rice':   { gi: 73, carbs: 80, load: 'high',   note: 'High GI — spikes blood glucose rapidly' },
  'brown rice':   { gi: 68, carbs: 77, load: 'medium', note: 'Medium GI — slower glucose release due to fibre' },
  'basmati':      { gi: 58, carbs: 78, load: 'medium', note: 'Basmati has lower GI than regular rice (higher amylose)' },
  'roti':         { gi: 62, carbs: 51, load: 'medium', note: 'Medium GI — whole wheat slows absorption' },
  'chapati':      { gi: 62, carbs: 51, load: 'medium', note: 'Medium GI — whole wheat slows absorption' },
  'wheat':        { gi: 62, carbs: 71, load: 'medium', note: 'Medium GI — whole wheat slows absorption' },
  'ragi':         { gi: 55, carbs: 72, load: 'low',    note: 'Low GI — excellent for blood sugar control, high calcium' },
  'oats':         { gi: 55, carbs: 66, load: 'low',    note: 'Low GI — β-glucan fibre blunts glucose spikes' },
  'moong dal':    { gi: 38, carbs: 63, load: 'low',    note: 'Low GI — high protein + fibre combination' },
  'toor dal':     { gi: 42, carbs: 60, load: 'low',    note: 'Low GI — traditional pulse, good amino acid profile' },
  'masoor dal':   { gi: 32, carbs: 60, load: 'low',    note: 'Very low GI — excellent for diabetics' },
  'rajma':        { gi: 29, carbs: 60, load: 'low',    note: 'Very low GI — high fibre, slow glucose release' },
  'chana':        { gi: 28, carbs: 61, load: 'low',    note: 'Very low GI — high protein legume' },
  'dal':          { gi: 38, carbs: 63, load: 'low',    note: 'Low GI — lentils are naturally blood-sugar friendly' },
  'tofu':         { gi: 15, carbs: 2,  load: 'low',    note: 'Very low GI — near-zero glycemic impact' },
  'paneer':       { gi: 27, carbs: 4,  load: 'low',    note: 'Low GI — high protein, minimal glucose response' },
  'banana':       { gi: 51, carbs: 23, load: 'medium', note: 'Medium GI — natural sugars + fibre' },
  'curd':         { gi: 14, carbs: 5,  load: 'low',    note: 'Very low GI — probiotic benefits' },
  'yogurt':       { gi: 14, carbs: 5,  load: 'low',    note: 'Very low GI — probiotic benefits' },
  'milk':         { gi: 39, carbs: 5,  load: 'low',    note: 'Low GI — lactose releases glucose slowly' },
  'poha':         { gi: 65, carbs: 76, load: 'medium', note: 'Medium GI — pair with peanuts/veg to lower impact' },
  'soya':         { gi: 18, carbs: 30, load: 'low',    note: 'Very low GI — complete plant protein' },
  'egg':          { gi: 0,  carbs: 1,  load: 'low',    note: 'No GI impact — pure protein and fat' },
  'spinach':      { gi: 15, carbs: 4,  load: 'low',    note: 'Negligible GI — micronutrient dense' },
  'peanut butter':{ gi: 14, carbs: 20, load: 'low',    note: 'Low GI — healthy fats slow any glucose rise' },
  'almond':       { gi: 15, carbs: 22, load: 'low',    note: 'Low GI — healthy fats and fibre' },
}

// Parse portion size from food string → grams.
// "100g oats" → 100, "1 cup milk" → 240, "2 roti" → 80, "200ml milk" → 200
function parseGrams(foodStr) {
  const s = foodStr.toLowerCase()
  const gMatch = s.match(/(\d+(?:\.\d+)?)\s*g(?:rams?)?\b/)
  if (gMatch) return parseFloat(gMatch[1])
  const mlMatch = s.match(/(\d+(?:\.\d+)?)\s*ml\b/)
  if (mlMatch) return parseFloat(mlMatch[1])
  const cupMatch = s.match(/(\d+(?:\.\d+)?)\s*cup/)
  if (cupMatch) {
    const n = parseFloat(cupMatch[1])
    if (/milk|curd|yogurt|water/.test(s)) return n * 240
    return n * 180
  }
  const tbspMatch = s.match(/(\d+(?:\.\d+)?)\s*(?:tbsp|tablespoon)/)
  if (tbspMatch) return parseFloat(tbspMatch[1]) * 15
  const numMatch = s.match(/^(\d+(?:\.\d+)?)\s+/)
  if (numMatch) {
    const n = parseFloat(numMatch[1])
    if (/roti|chapati/.test(s)) return n * 40
    if (/banana/.test(s))       return n * 120
    if (/egg/.test(s))          return n * 50
    if (/apple|orange/.test(s)) return n * 150
  }
  return 100  // fallback
}

function lookupFood(foodStr) {
  const lower = foodStr.toLowerCase()
  for (const [key, data] of Object.entries(FOOD_DATA)) {
    if (lower.includes(key)) return { food: key, ...data }
  }
  return null
}

function computeGL(foodStr, foodData) {
  const grams = parseGrams(foodStr)
  const carbsInPortion = (foodData.carbs / 100) * grams
  const gl = (foodData.gi * carbsInPortion) / 100
  return { grams, carbsInPortion: Math.round(carbsInPortion), gl: Math.round(gl) }
}

function classifyDailyGL(totalGL) {
  if (totalGL < 80)  return { band: 'low',    label: 'Low daily load',    note: 'Excellent for blood-sugar stability' }
  if (totalGL < 120) return { band: 'medium', label: 'Medium daily load', note: 'Acceptable for most; diabetics should aim lower' }
  return                   { band: 'high',   label: 'High daily load',   note: 'Consider swapping white rice for ragi/oats' }
}

function detectProteinStrategy(mealFoods) {
  const text = mealFoods.join(' ').toLowerCase()
  const hasLegume = /dal|moong|chana|rajma|chickpea|lentil|bean/.test(text)
  const hasGrain  = /rice|roti|wheat|bread|oats/.test(text)
  const hasDairy  = /milk|curd|paneer|yogurt|cheese/.test(text)
  const hasAnimal = /chicken|fish|egg|meat|whey/.test(text)
  if (hasAnimal) return null
  if (hasLegume && hasGrain) return {
    detail: 'Legumes + grains = complete amino acid profile (traditional Indian combination)',
  }
  if (hasDairy && hasGrain) return {
    detail: 'Dairy + grains supply all 9 essential amino acids',
  }
  return null
}

const LOAD_COLORS = {
  low:    'text-sage-700 bg-sage-50',
  medium: 'text-amber-700 bg-amber-50',
  high:   'text-clay-600 bg-clay-50',
}

export default function NutritionLiteracy({ rx, profile }) {
  if (!rx?.nutrition_plan?.daily_plans?.length) return null

  const dayGLs = rx.nutrition_plan.daily_plans.map(day => {
    let dailyGL = 0
    const mealDetails = day.meals.map(meal => {
      let mealGL = 0
      const foodEntries = meal.foods.map(food => {
        const data = lookupFood(food)
        if (!data) return { food, matched: false }
        const gl = computeGL(food, data)
        mealGL += gl.gl
        return { food, matched: true, ...data, ...gl }
      })
      dailyGL += mealGL
      return { name: meal.meal_name, gl: Math.round(mealGL), foods: foodEntries }
    })
    return { day: day.day_name, gl: Math.round(dailyGL), meals: mealDetails }
  })

  const foodMap = new Map()
  dayGLs.forEach(d => d.meals.forEach(m => m.foods.forEach(f => {
    if (f.matched && !foodMap.has(f.food)) foodMap.set(f.food, f)
  })))
  const giBreakdown = { low: [], medium: [], high: [] }
  for (const f of foodMap.values()) giBreakdown[f.load].push(f)

  const avgDailyGL = Math.round(dayGLs.reduce((s, d) => s + d.gl, 0) / dayGLs.length)
  const glBand = classifyDailyGL(avgDailyGL)

  const firstBreakfast = rx.nutrition_plan.daily_plans[0]?.meals?.find(m =>
    m.meal_name?.toLowerCase().includes('breakfast')
  )
  const proteinStrategy = firstBreakfast ? detectProteinStrategy(firstBreakfast.foods) : null

  const hasAnyGiData = giBreakdown.low.length + giBreakdown.medium.length + giBreakdown.high.length > 0
  if (!hasAnyGiData && !proteinStrategy) return null

  return (
    <div className="card p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg bg-clay-50 flex items-center justify-center flex-shrink-0">
          <Info size={15} className="text-clay-500" strokeWidth={2} />
        </div>
        <div className="flex-1">
          <p className="eyebrow text-clay-500 mb-1">Nutrition literacy</p>
          <h2 className="section-title">Why these foods?</h2>
          <p className="text-[12.5px] text-ink-500 mt-1 leading-relaxed">
            Most Indians learn "dal-roti is healthy" without understanding glycemic impact or protein
            completeness. This panel shows the evidence behind today's food choices.
          </p>
        </div>
      </div>

      {/* Daily Glycemic Load — hero metric */}
      {hasAnyGiData && (
        <div className="mb-5">
          <div className="flex items-center gap-2 mb-3">
            <HeartPulse size={13} className="text-ink-500" strokeWidth={2} />
            <p className="smallcaps">Daily glycemic load — blood sugar impact</p>
          </div>

          <div className="rounded-xl p-5 mb-3"
               style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
            <div className="flex items-baseline gap-3 mb-2 flex-wrap">
              <span className={`font-display text-[42px] font-bold leading-none tnum
                ${glBand.band === 'low' ? 'text-sage-700' :
                  glBand.band === 'medium' ? 'text-amber-700' : 'text-clay-600'}`}>
                {avgDailyGL}
              </span>
              <span className="text-[12px] text-ink-400 tnum">GL / day avg</span>
              <span className={`chip ml-auto ${LOAD_COLORS[glBand.band]}`}
                    style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.1)' }}>
                {glBand.label}
              </span>
            </div>
            <p className="text-[12px] text-ink-500">{glBand.note}</p>

            {/* GL scale visualization */}
            <div className="mt-4 flex items-center gap-1 text-[10px] text-ink-400 tnum">
              <span className="w-6">0</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden flex">
                <div className="bg-sage-200 flex-[80]" />
                <div className="bg-amber-200 flex-[40]" />
                <div className="bg-clay-200 flex-[80]" />
              </div>
              <span className="w-8 text-right">200+</span>
            </div>
            <div className="flex justify-between text-[9.5px] text-ink-400 tnum mt-0.5 px-6">
              <span>low  ≤80</span>
              <span>med  81–120</span>
              <span>high  &gt;120</span>
            </div>
          </div>

          {/* Per-day breakdown */}
          <div className={`grid gap-2 mb-3 ${
            dayGLs.length === 3 ? 'grid-cols-3' :
            dayGLs.length >= 7 ? 'grid-cols-7' :
            'grid-cols-' + dayGLs.length}`}>
            {dayGLs.map((d, i) => {
              const band = classifyDailyGL(d.gl).band
              return (
                <div key={i} className={`rounded-lg p-2.5 ${LOAD_COLORS[band]}`}
                     style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.06)' }}>
                  <p className="text-[10px] font-semibold uppercase tnum" style={{ letterSpacing: '0.14em' }}>
                    {d.day.slice(0, 3)}
                  </p>
                  <p className="font-display text-[18px] font-bold mt-1 tnum">
                    {d.gl}
                  </p>
                  <p className="text-[10px] opacity-80">GL</p>
                </div>
              )
            })}
          </div>

          <details className="group">
            <summary className="text-[11.5px] text-ink-500 cursor-pointer hover:text-ink-700 inline-flex items-center gap-1">
              Per-meal breakdown
              <span className="group-open:rotate-180 transition-transform">▾</span>
            </summary>
            <div className="mt-3 flex flex-col gap-3">
              {dayGLs.map((d, i) => (
                <div key={i}>
                  <p className="text-[11.5px] font-semibold text-ink-700 mb-1">{d.day}</p>
                  <div className="grid grid-cols-1 gap-1">
                    {d.meals.map((m, j) => {
                      const mealBand = classifyDailyGL(m.gl * 3).band
                      return (
                        <div key={j} className="flex items-center gap-2 text-[11.5px] py-1">
                          <span className={`chip ${LOAD_COLORS[mealBand]}`}
                                style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.08)' }}>
                            GL {m.gl}
                          </span>
                          <span className="text-ink-700 min-w-[70px] font-medium">{m.name}</span>
                          <span className="text-ink-400 text-[11px] truncate">
                            {m.foods.filter(f => f.matched).map(f => f.food).join(', ') || '—'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* GI breakdown counts */}
      {hasAnyGiData && (
        <div className="mb-5">
          <p className="smallcaps mb-3">Individual food glycemic index</p>
          <div className="grid grid-cols-3 gap-2">
            {['low', 'medium', 'high'].map(load => (
              <div key={load} className={`rounded-lg px-3 py-2.5 ${LOAD_COLORS[load]}`}
                   style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.06)' }}>
                <p className="text-[10px] font-semibold uppercase tnum" style={{ letterSpacing: '0.14em' }}>
                  {load} GI
                </p>
                <p className="font-display text-[20px] font-bold mt-1 tnum">
                  {giBreakdown[load].length}
                </p>
                <p className="text-[10.5px] opacity-80 mt-0.5">
                  {load === 'low' && 'ideal for diabetics'}
                  {load === 'medium' && 'pair w/ protein/fibre'}
                  {load === 'high' && 'spikes blood glucose'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Protein strategy — vegetarian-specific insight */}
      {proteinStrategy && (
        <div className="rounded-lg bg-paper-100 p-4 mb-4"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}>
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-md bg-sage-50 flex items-center justify-center flex-shrink-0">
              <Leaf size={13} className="text-sage-600" strokeWidth={2} />
            </div>
            <div className="flex-1">
              <p className="text-[12.5px] font-semibold text-ink-800 mb-0.5">
                Complete protein strategy
              </p>
              <p className="text-[12px] text-ink-600 leading-relaxed">
                {proteinStrategy.detail}. This matters for vegetarians because individual
                plant proteins often lack one or more essential amino acids —
                combining them restores the complete profile that animal proteins provide naturally.
              </p>
            </div>
          </div>
        </div>
      )}

      <p className="text-[10.5px] text-ink-400 italic">
        GI values from ICMR/NIN tables. GL formula: (GI × carbs_g) ÷ 100 per serving.
        Protein complementarity sourced from IFCT 2017. Educational content, not medical advice.
      </p>
    </div>
  )
}
