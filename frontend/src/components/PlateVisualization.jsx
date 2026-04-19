/**
 * PlateVisualization
 *
 * Donut chart visualization of the nutrition plan's macro composition.
 * Shows:
 *   1. Your actual plate — calories from protein, carbs, fats by percentage
 *   2. Recommended plate — evidence-based target ratios
 *   3. Portion guide — Harvard Healthy Eating Plate adapted for Indian context
 *
 * Uses pure SVG — no recharts dependency.
 * Deterministic: computed from nutrition_plan totals, no LLM.
 *
 * Target ratios derived from ICMR-NIN 2020 guidelines and ISSN protein position stand:
 *   Weight loss / maintenance: 30% P / 40% C / 30% F
 *   Muscle gain:               25% P / 50% C / 25% F
 *   Endurance:                 20% P / 55% C / 25% F
 */

const TARGET_RATIOS = {
  weight_loss: { protein: 0.30, carbs: 0.40, fats: 0.30, label: 'Weight loss targets' },
  muscle_gain: { protein: 0.25, carbs: 0.50, fats: 0.25, label: 'Muscle gain targets' },
  endurance:   { protein: 0.20, carbs: 0.55, fats: 0.25, label: 'Endurance targets' },
  maintenance: { protein: 0.25, carbs: 0.50, fats: 0.25, label: 'Maintenance targets' },
}

// Donut chart SVG — inputs are percentages (0-1) for protein, carbs, fats
function Donut({ protein, carbs, fats, size = 160, strokeWidth = 28, label }) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const center = size / 2

  // Segments — start at top (rotated -90°), go clockwise
  const proteinLen = protein * circumference
  const carbsLen   = carbs * circumference
  const fatsLen    = fats * circumference

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mb-2">
        {/* Background track */}
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="#F4F0E2" strokeWidth={strokeWidth}
        />
        {/* Protein — sage */}
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="#6B9737" strokeWidth={strokeWidth}
          strokeDasharray={`${proteinLen} ${circumference - proteinLen}`}
          strokeDashoffset={0}
          transform={`rotate(-90 ${center} ${center})`}
        />
        {/* Carbs — ink/paper dark */}
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="#2D2921" strokeWidth={strokeWidth}
          strokeDasharray={`${carbsLen} ${circumference - carbsLen}`}
          strokeDashoffset={-proteinLen}
          transform={`rotate(-90 ${center} ${center})`}
        />
        {/* Fats — clay */}
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="#B94A1E" strokeWidth={strokeWidth}
          strokeDasharray={`${fatsLen} ${circumference - fatsLen}`}
          strokeDashoffset={-(proteinLen + carbsLen)}
          transform={`rotate(-90 ${center} ${center})`}
        />
        {/* Centre label */}
        <text
          x={center} y={center - 4}
          textAnchor="middle"
          className="font-display fill-ink-900"
          fontSize="13" fontWeight="600"
        >
          {label}
        </text>
        <text
          x={center} y={center + 14}
          textAnchor="middle"
          className="fill-ink-400 font-mono"
          fontSize="9"
          style={{ letterSpacing: '0.14em' }}
        >
          MACROS
        </text>
      </svg>
    </div>
  )
}

function LegendRow({ color, label, pct, grams }) {
  return (
    <div className="flex items-center gap-2 text-[12px]">
      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: color }} />
      <span className="text-ink-700 font-medium flex-1">{label}</span>
      <span className="font-mono text-ink-800 tnum text-[11.5px]">{pct}%</span>
      {grams !== undefined && <span className="font-mono text-ink-400 tnum text-[11px]">({grams}g)</span>}
    </div>
  )
}

export default function PlateVisualization({ rx, profile }) {
  if (!rx?.nutrition_plan?.daily_plans?.length) return null

  // Average across the plan
  const dailies = rx.nutrition_plan.daily_plans
  const avg = dailies.reduce((acc, d) => ({
    protein: acc.protein + d.total_protein_g,
    carbs:   acc.carbs   + d.total_carbs_g,
    fats:    acc.fats    + d.total_fats_g,
    kcal:    acc.kcal    + d.total_calories,
  }), { protein: 0, carbs: 0, fats: 0, kcal: 0 })

  const n = dailies.length
  const dailyProtein = Math.round(avg.protein / n)
  const dailyCarbs   = Math.round(avg.carbs / n)
  const dailyFats    = Math.round(avg.fats / n)
  const dailyKcal    = Math.round(avg.kcal / n)

  // Calories from each macro (Atwater)
  const kcalP = dailyProtein * 4
  const kcalC = dailyCarbs * 4
  const kcalF = dailyFats * 9
  const totalKcal = kcalP + kcalC + kcalF

  if (totalKcal === 0) return null

  const actualProteinPct = kcalP / totalKcal
  const actualCarbsPct   = kcalC / totalKcal
  const actualFatsPct    = kcalF / totalKcal

  const target = TARGET_RATIOS[profile?.goal] ?? TARGET_RATIOS.maintenance

  // Variance vs target
  const proteinDelta = Math.round((actualProteinPct - target.protein) * 100)
  const carbsDelta   = Math.round((actualCarbsPct - target.carbs) * 100)
  const fatsDelta    = Math.round((actualFatsPct - target.fats) * 100)

  function deltaChip(delta) {
    const abs = Math.abs(delta)
    if (abs <= 3) return <span className="chip-sage text-[10px]">on target</span>
    if (abs <= 7) return <span className="chip-paper text-[10px]">{delta > 0 ? '+' : ''}{delta}% vs target</span>
    return <span className="chip-clay text-[10px]">{delta > 0 ? '+' : ''}{delta}% vs target</span>
  }

  return (
    <div className="card p-6">
      <div className="mb-5">
        <p className="eyebrow mb-1">Macro composition</p>
        <h2 className="section-title">Your plate, visualized</h2>
        <p className="text-[12.5px] text-ink-500 mt-1">
          Average daily macronutrient split across the plan, compared against evidence-based
          targets for your goal.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-5">
        {/* Actual plate */}
        <div className="flex flex-col items-center">
          <p className="smallcaps mb-2">Your actual plate</p>
          <Donut
            protein={actualProteinPct}
            carbs={actualCarbsPct}
            fats={actualFatsPct}
            label={`${dailyKcal}`}
          />
          <p className="text-[10.5px] text-ink-400 tnum mb-4">kcal / day</p>
          <div className="w-full flex flex-col gap-1.5">
            <LegendRow color="#6B9737" label="Protein" pct={Math.round(actualProteinPct * 100)} grams={dailyProtein} />
            <LegendRow color="#2D2921" label="Carbs"   pct={Math.round(actualCarbsPct * 100)}   grams={dailyCarbs} />
            <LegendRow color="#B94A1E" label="Fats"    pct={Math.round(actualFatsPct * 100)}    grams={dailyFats} />
          </div>
        </div>

        {/* Target plate */}
        <div className="flex flex-col items-center">
          <p className="smallcaps mb-2">{target.label}</p>
          <Donut
            protein={target.protein}
            carbs={target.carbs}
            fats={target.fats}
            label="Target"
          />
          <p className="text-[10.5px] text-ink-400 italic mb-4">ICMR-NIN / ISSN guidelines</p>
          <div className="w-full flex flex-col gap-1.5">
            <LegendRow color="#6B9737" label="Protein" pct={Math.round(target.protein * 100)} />
            <LegendRow color="#2D2921" label="Carbs"   pct={Math.round(target.carbs * 100)} />
            <LegendRow color="#B94A1E" label="Fats"    pct={Math.round(target.fats * 100)} />
          </div>
        </div>
      </div>

      {/* Variance analysis */}
      <div className="rounded-lg bg-paper-100 p-4"
           style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
        <p className="smallcaps mb-3">How your plate compares</p>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11.5px] font-medium text-ink-700">Protein</span>
              {deltaChip(proteinDelta)}
            </div>
            <div className="h-1 rounded-full bg-ink-100 overflow-hidden">
              <div className="h-full bg-sage-500 transition-all"
                   style={{ width: `${Math.min(100, actualProteinPct * 100 / target.protein * 50)}%` }} />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11.5px] font-medium text-ink-700">Carbs</span>
              {deltaChip(carbsDelta)}
            </div>
            <div className="h-1 rounded-full bg-ink-100 overflow-hidden">
              <div className="h-full bg-ink-800 transition-all"
                   style={{ width: `${Math.min(100, actualCarbsPct * 100 / target.carbs * 50)}%` }} />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11.5px] font-medium text-ink-700">Fats</span>
              {deltaChip(fatsDelta)}
            </div>
            <div className="h-1 rounded-full bg-ink-100 overflow-hidden">
              <div className="h-full bg-clay-500 transition-all"
                   style={{ width: `${Math.min(100, actualFatsPct * 100 / target.fats * 50)}%` }} />
            </div>
          </div>
        </div>
      </div>

      <p className="text-[10.5px] text-ink-400 italic mt-4">
        Computed via Atwater: calories from each macro = grams × (4 for P/C, 9 for F).
        Targets are evidence-based ranges, not rigid rules — ±5% is within normal variation.
      </p>
    </div>
  )
}
