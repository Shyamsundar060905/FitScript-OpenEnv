import { Info, Wheat, Drumstick, Leaf, HeartPulse } from 'lucide-react'

/**
 * NutritionLiteracy
 *
 * Educational panel explaining WHY the Nutrition Agent chose specific foods.
 * Entirely deterministic — generated from profile + plan data, no LLM calls.
 * This panel exists to address a core problem: Indians often lack fitness/nutrition
 * literacy, leading to well-intentioned but harmful diet choices (e.g., "dal-roti
 * is healthy" while ignoring glycemic load for diabetics).
 */

// Surface-level GI lookup for common Indian ingredients.
// Values from standard GI tables — not medical advice, but enough for education.
const GI_DATA = {
  'white rice':       { gi: 73, load: 'high',   note: 'High GI — spikes blood glucose rapidly' },
  'brown rice':       { gi: 68, load: 'medium', note: 'Medium GI — slower glucose release due to fibre' },
  'roti':             { gi: 62, load: 'medium', note: 'Medium GI — whole wheat slows absorption' },
  'wheat roti':       { gi: 62, load: 'medium', note: 'Medium GI — whole wheat slows absorption' },
  'ragi':             { gi: 55, load: 'low',    note: 'Low GI — excellent for blood sugar control' },
  'oats':             { gi: 55, load: 'low',    note: 'Low GI — β-glucan fibre blunts glucose spikes' },
  'moong dal':        { gi: 38, load: 'low',    note: 'Low GI — high protein + fibre combination' },
  'dal':              { gi: 38, load: 'low',    note: 'Low GI — lentils are naturally blood-sugar friendly' },
  'tofu':             { gi: 15, load: 'low',    note: 'Very low GI — near-zero glycemic impact' },
  'paneer':           { gi: 27, load: 'low',    note: 'Low GI — high protein, minimal glucose response' },
  'banana':           { gi: 51, load: 'medium', note: 'Medium GI — natural sugars + fibre' },
  'curd':             { gi: 14, load: 'low',    note: 'Very low GI — probiotic benefits' },
  'milk':             { gi: 39, load: 'low',    note: 'Low GI — lactose releases glucose slowly' },
  'poha':             { gi: 65, load: 'medium', note: 'Medium GI — pair with peanuts/veg to lower impact' },
}

// Map a food string to its GI entry if we recognise it.
function lookupGI(foodStr) {
  const lower = foodStr.toLowerCase()
  for (const [key, data] of Object.entries(GI_DATA)) {
    if (lower.includes(key)) return { food: key, ...data }
  }
  return null
}

// Identify protein completeness strategy (Indian-specific RAG insight).
function detectProteinStrategy(mealFoods) {
  const text = mealFoods.join(' ').toLowerCase()
  const hasLegume = /dal|moong|chana|rajma|chickpea|lentil|bean/.test(text)
  const hasGrain  = /rice|roti|wheat|bread|oats/.test(text)
  const hasDairy  = /milk|curd|paneer|yogurt|cheese/.test(text)
  const hasAnimal = /chicken|fish|egg|meat|whey/.test(text)

  if (hasAnimal) return null // complete on its own
  if (hasLegume && hasGrain) return {
    type: 'complementary',
    detail: 'Legumes + grains = complete amino acid profile (traditional Indian combination)',
  }
  if (hasDairy && hasGrain) return {
    type: 'complementary',
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

  // Extract all unique foods across all meals
  const allFoods = new Set()
  rx.nutrition_plan.daily_plans.forEach(day =>
    day.meals.forEach(meal =>
      meal.foods.forEach(f => allFoods.add(f))
    )
  )

  // Classify foods by GI
  const giBreakdown = { low: [], medium: [], high: [] }
  const unmatchedFoods = []
  for (const food of allFoods) {
    const gi = lookupGI(food)
    if (gi) giBreakdown[gi.load].push({ food, ...gi })
    else unmatchedFoods.push(food)
  }

  // Check first day's breakfast for protein completeness example
  const firstBreakfast = rx.nutrition_plan.daily_plans[0]?.meals?.find(m =>
    m.meal_name?.toLowerCase().includes('breakfast')
  )
  const proteinStrategy = firstBreakfast
    ? detectProteinStrategy(firstBreakfast.foods)
    : null

  // Health-aware messaging based on dietary restrictions
  const isVeg = profile?.dietary_restrictions?.includes('vegetarian')
                || profile?.dietary_restrictions?.includes('vegan')

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

      {/* Glycemic breakdown */}
      {hasAnyGiData && (
        <div className="mb-5">
          <div className="flex items-center gap-2 mb-3">
            <HeartPulse size={13} className="text-ink-500" strokeWidth={2} />
            <p className="smallcaps">Glycemic index — blood sugar impact</p>
          </div>

          <div className="grid grid-cols-3 gap-2 mb-3">
            {['low', 'medium', 'high'].map(load => (
              <div key={load} className={`rounded-lg px-3 py-2.5 ${LOAD_COLORS[load]}`}
                   style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.06)' }}>
                <p className="text-[10px] font-semibold uppercase tnum" style={{ letterSpacing: '0.14em' }}>
                  {load} GI
                </p>
                <p className="font-display text-[22px] font-bold mt-1 tnum">
                  {giBreakdown[load].length}
                </p>
                <p className="text-[11px] opacity-80 mt-0.5">
                  {load === 'low' && 'ideal for diabetics & weight loss'}
                  {load === 'medium' && 'pair with protein/fibre'}
                  {load === 'high' && 'limit; spike blood glucose'}
                </p>
              </div>
            ))}
          </div>

          <details className="group">
            <summary className="text-[11.5px] text-ink-500 cursor-pointer hover:text-ink-700 inline-flex items-center gap-1">
              See individual foods
              <span className="group-open:rotate-180 transition-transform">▾</span>
            </summary>
            <div className="mt-3 flex flex-col gap-1.5">
              {['low', 'medium', 'high'].map(load =>
                giBreakdown[load].map((item, i) => (
                  <div key={`${load}-${i}`} className="flex items-baseline gap-3 text-[12px] py-1.5 hair-b">
                    <span className={`chip ${LOAD_COLORS[load]}`} style={{ boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.08)' }}>
                      GI {item.gi}
                    </span>
                    <span className="font-medium text-ink-800 capitalize min-w-[90px]">{item.food}</span>
                    <span className="text-ink-500 flex-1">{item.note}</span>
                  </div>
                ))
              )}
            </div>
          </details>
        </div>
      )}

      {/* Protein strategy — vegetarian-specific insight */}
      {proteinStrategy && (
        <div className="rounded-lg bg-paper-100 p-4"
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
                plant proteins lack one or more essential amino acids —
                combining them restores the complete profile that animal proteins provide naturally.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Attribution */}
      <p className="text-[10.5px] text-ink-400 mt-4 italic">
        GI values from ICMR/NIN tables. Protein complementarity sourced from IFCT 2017.
        This is educational content, not medical advice.
      </p>
    </div>
  )
}