import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import {
  Beef, Wheat, Droplets, Flame, BookOpen, HeartPulse, Activity, Info,
} from 'lucide-react'

/**
 * LearnPage — standalone nutrition & fitness literacy content.
 *
 * Addresses the BTP's core thesis: many Indians lack foundational fitness
 * and nutrition literacy, leading to well-intentioned but harmful choices.
 * This page provides the baseline knowledge that other apps assume users
 * already have.
 *
 * Content sourced from: ICMR-NIN Dietary Guidelines for Indians (2020),
 * ISSN Position Stand on Protein (Jäger et al., 2017), ACSM Position
 * Stand on Weight Management, Schoenfeld's volume meta-analyses.
 */

function SectionHeader({ num, icon: Icon, title, blurb }) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <span className="font-mono text-[11px] text-clay-500 tnum pt-0.5"
            style={{ letterSpacing: '0.12em' }}>{num}</span>
      <span className="w-6 h-px bg-ink-200 mt-2.5" />
      <Icon size={15} className="text-ink-400 mt-0.5" strokeWidth={1.75} />
      <div className="flex-1 min-w-0">
        <h2 className="font-display text-[18px] font-semibold text-ink-900 tracking-tight">{title}</h2>
        {blurb && <p className="text-[12.5px] text-ink-500 mt-0.5 leading-relaxed">{blurb}</p>}
      </div>
    </div>
  )
}

function KeyValue({ label, value }) {
  return (
    <div className="flex justify-between gap-4 py-2 hair-b last:border-0">
      <dt className="text-[12.5px] text-ink-500">{label}</dt>
      <dd className="text-[12.5px] font-medium text-ink-800 text-right">{value}</dd>
    </div>
  )
}

function Myth({ myth, truth }) {
  return (
    <div className="rounded-lg bg-paper-100 p-4"
         style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
      <div className="flex items-start gap-2 mb-2">
        <span className="chip-clay text-[10px]">Myth</span>
        <p className="text-[12.5px] text-ink-700 flex-1 italic">"{myth}"</p>
      </div>
      <div className="flex items-start gap-2">
        <span className="chip-sage text-[10px]">Truth</span>
        <p className="text-[12.5px] text-ink-800 flex-1">{truth}</p>
      </div>
    </div>
  )
}

function FoodTable({ title, rows }) {
  return (
    <div className="mb-4">
      <p className="smallcaps mb-2">{title}</p>
      <div className="rounded-lg bg-paper-100 overflow-hidden"
           style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
        <table className="w-full text-[12px]">
          <thead>
            <tr className="hair-b">
              <th className="text-left py-2 px-3 eyebrow">Food</th>
              <th className="text-right py-2 px-3 eyebrow">Protein / 100g</th>
              <th className="text-right py-2 px-3 eyebrow">Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="hair-b last:border-0">
                <td className="py-2 px-3 font-medium text-ink-800 capitalize">{r.food}</td>
                <td className="py-2 px-3 text-right font-mono tnum text-ink-700">{r.protein}g</td>
                <td className="py-2 px-3 text-right text-[11.5px] text-ink-500">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function LearnPage() {
  return (
    <Container size="md">
      <PageHeader
        eyebrow="Foundations"
        title="Learn the basics"
        description="The fundamentals of fitness and nutrition that most apps assume you already know — but rarely teach. Written for an Indian context."
      />

      <div className="flex flex-col gap-8">

        {/* Macronutrients */}
        <section className="card p-6">
          <SectionHeader
            num="01" icon={Flame}
            title="The three macronutrients"
            blurb="Every calorie you eat comes from one of three macronutrients. Understanding what each does changes how you read food labels forever."
          />

          <div className="grid md:grid-cols-3 gap-3 mt-5">
            {/* Protein */}
            <div className="rounded-xl bg-sage-50 p-4"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(107,151,55,0.25)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Beef size={14} className="text-sage-700" strokeWidth={2} />
                <p className="font-display text-[14px] font-semibold text-sage-700">Protein</p>
              </div>
              <p className="font-mono text-[11px] text-sage-700 tnum mb-3">4 kcal / gram</p>
              <p className="text-[12px] text-ink-700 leading-relaxed mb-3">
                The building block of muscle, skin, enzymes, and hormones. Your body cannot store
                protein — you need daily intake.
              </p>
              <p className="text-[11.5px] text-ink-600">
                <span className="font-semibold">How much:</span> 1.6–2.2g per kg body weight for
                active adults. A 70kg person = 112–154g/day.
              </p>
            </div>

            {/* Carbs */}
            <div className="rounded-xl bg-paper-200 p-4"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Wheat size={14} className="text-ink-700" strokeWidth={2} />
                <p className="font-display text-[14px] font-semibold text-ink-800">Carbohydrates</p>
              </div>
              <p className="font-mono text-[11px] text-ink-700 tnum mb-3">4 kcal / gram</p>
              <p className="text-[12px] text-ink-700 leading-relaxed mb-3">
                Your body's preferred fuel, especially for the brain and high-intensity exercise.
                "Carbs" is not a bad word — quality and timing matter.
              </p>
              <p className="text-[11.5px] text-ink-600">
                <span className="font-semibold">How much:</span> 3–5g/kg for active adults.
                Prefer low-GI sources (ragi, oats, dal) over refined (white rice, sugar).
              </p>
            </div>

            {/* Fats */}
            <div className="rounded-xl bg-clay-50 p-4"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216,100,58,0.25)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Droplets size={14} className="text-clay-600" strokeWidth={2} />
                <p className="font-display text-[14px] font-semibold text-clay-600">Fats</p>
              </div>
              <p className="font-mono text-[11px] text-clay-600 tnum mb-3">9 kcal / gram</p>
              <p className="text-[12px] text-ink-700 leading-relaxed mb-3">
                Essential for hormones, cell membranes, and absorption of fat-soluble vitamins
                (A, D, E, K). Ghee and coconut oil have been staples in Indian diets for millennia.
              </p>
              <p className="text-[11.5px] text-ink-600">
                <span className="font-semibold">How much:</span> 20–30% of total calories.
                Prefer monounsaturated (ghee, olive oil, nuts) over industrial seed oils.
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-lg bg-ink-800 text-paper-100 p-4">
            <p className="text-[11px] text-paper-300 uppercase tnum mb-2" style={{ letterSpacing: '0.14em' }}>
              The equation
            </p>
            <p className="font-mono text-[13px] text-paper-100">
              Total kcal = (4 × protein_g) + (4 × carbs_g) + (9 × fats_g)
            </p>
            <p className="text-[11px] text-paper-300 mt-2 italic">
              Known as the Atwater system. Every calorie on every food label is computed this way.
            </p>
          </div>
        </section>

        {/* Glycemic Load */}
        <section className="card p-6">
          <SectionHeader
            num="02" icon={HeartPulse}
            title="Glycemic Index & Glycemic Load"
            blurb="Why 'dal is healthy, rice is bad' is an oversimplification — portion size matters more than the food itself."
          />

          <div className="mb-4">
            <p className="text-[13px] text-ink-700 leading-relaxed mb-3">
              <strong>Glycemic Index (GI)</strong> measures how quickly a food raises blood glucose,
              on a 0–100 scale. Pure glucose = 100.
            </p>
            <p className="text-[13px] text-ink-700 leading-relaxed">
              <strong>Glycemic Load (GL)</strong> accounts for portion size —
              the actual blood sugar impact of a meal depends on both the GI
              <em> and</em> how much carbohydrate you eat.
            </p>
          </div>

          <div className="rounded-lg bg-ink-800 text-paper-100 p-4 mb-4">
            <p className="font-mono text-[13px] text-paper-100 mb-1">
              GL = (GI × carbs in grams) ÷ 100
            </p>
            <p className="text-[11px] text-paper-300 italic">
              Example: 100g white rice has GI 73 and 80g of carbs → GL = (73 × 80) / 100 = 58
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="rounded-lg bg-sage-50 text-sage-700 p-3"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(107,151,55,0.25)' }}>
              <p className="eyebrow">Low GL</p>
              <p className="font-display text-[20px] font-bold tnum">&lt; 80</p>
              <p className="text-[11px] mt-1">per day — ideal for diabetics</p>
            </div>
            <div className="rounded-lg bg-amber-50 text-amber-700 p-3"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(180,120,30,0.25)' }}>
              <p className="eyebrow">Medium GL</p>
              <p className="font-display text-[20px] font-bold tnum">80–120</p>
              <p className="text-[11px] mt-1">per day — most people</p>
            </div>
            <div className="rounded-lg bg-clay-50 text-clay-600 p-3"
                 style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216,100,58,0.25)' }}>
              <p className="eyebrow">High GL</p>
              <p className="font-display text-[20px] font-bold tnum">&gt; 120</p>
              <p className="text-[11px] mt-1">per day — risk for insulin resistance</p>
            </div>
          </div>

          <Myth
            myth="I only eat rice and dal — that should be fine."
            truth="If that 'rice' is 300g of white rice (GL ~174), you're exceeding the daily high-GL threshold in one meal. Switch half the portion to ragi or brown rice and pair with vegetables to drop it to moderate levels."
          />
        </section>

        {/* Indian vegetarian protein */}
        <section className="card p-6">
          <SectionHeader
            num="03" icon={Beef}
            title="Protein on a vegetarian Indian diet"
            blurb="The biggest fitness gap for Indian users: under-eating protein by 30–50%. Here's how to hit your target without meat."
          />

          <FoodTable
            title="High-protein vegetarian Indian foods"
            rows={[
              { food: 'paneer',            protein: '18',  note: 'highest density per 100g' },
              { food: 'tofu',              protein: '8',   note: 'minimal carbs' },
              { food: 'soya chunks (dry)', protein: '52',  note: 'cooked weight doubles — divide by 2' },
              { food: 'moong dal (dry)',   protein: '24',  note: 'cooked weight triples — divide by 3' },
              { food: 'rajma (dry)',       protein: '24',  note: 'cooked weight triples' },
              { food: 'chana (dry)',       protein: '19',  note: 'roasted variant is shelf-stable snack' },
              { food: 'curd (hung)',       protein: '10',  note: 'double regular curd, half lactose' },
              { food: 'milk',              protein: '3.3', note: 'per 100ml — a cup = ~8g' },
              { food: 'egg (whole)',       protein: '13',  note: 'one egg = ~6g, complete protein' },
              { food: 'whey protein',      protein: '80',  note: 'supplement — 1 scoop = ~24g' },
            ]}
          />

          <div className="rounded-lg bg-sage-50 p-4 mb-4"
               style={{ boxShadow: 'inset 0 0 0 0.5px rgba(107,151,55,0.25)' }}>
            <p className="text-[12.5px] font-semibold text-sage-700 mb-1.5">The complete protein trick</p>
            <p className="text-[12px] text-ink-700 leading-relaxed">
              Individual plant proteins lack one or more of the 9 essential amino acids.
              Combining two types fixes this:
            </p>
            <ul className="text-[12px] text-ink-700 mt-2 space-y-0.5">
              <li>• <strong>Legumes + grains</strong> → dal + rice, rajma + roti, chole + chawal</li>
              <li>• <strong>Dairy + grains</strong> → milk + oats, paneer + roti</li>
              <li>• <strong>Nuts/seeds + grains</strong> → peanut butter on toast, til laddu</li>
            </ul>
            <p className="text-[11.5px] text-ink-600 mt-2 italic">
              Traditional Indian combinations got this right centuries ago. The science caught up in the 1970s.
            </p>
          </div>

          <Myth
            myth="You can't build muscle without eating chicken or whey protein."
            truth="Plenty of evidence shows vegetarians can match animal-protein results when total protein and leucine intake are matched. Soya, dairy, and legume-grain combinations hit complete amino acid profiles."
          />
        </section>

        {/* Progressive overload */}
        <section className="card p-6">
          <SectionHeader
            num="04" icon={Activity}
            title="Progressive overload — the one rule of strength training"
            blurb="If you do the same workout every week, your body has no reason to change. Here's the only training principle you really need to understand."
          />

          <p className="text-[13px] text-ink-700 leading-relaxed mb-4">
            Your muscles adapt to stress. If you lift 20kg for 10 reps this week, and the same
            next week, your body has already solved that problem — no adaptation happens. To keep
            growing, you must progressively increase demand over time.
          </p>

          <div className="rounded-lg bg-paper-100 p-4 mb-4"
               style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28,26,20,0.08)' }}>
            <p className="smallcaps mb-2">Four ways to progressively overload</p>
            <dl>
              <KeyValue label="Add weight"  value="+2.5kg compound / +1.25kg isolation when you hit rep ceiling" />
              <KeyValue label="Add reps"    value="same weight, more reps (bodyweight progression)" />
              <KeyValue label="Add sets"    value="more total volume over the week" />
              <KeyValue label="Better form" value="slower tempo, fuller range of motion" />
            </dl>
          </div>

          <div className="rounded-lg bg-ink-800 text-paper-100 p-4 mb-4">
            <p className="text-[11px] text-paper-300 uppercase tnum mb-2" style={{ letterSpacing: '0.14em' }}>
              FitAgent's rule (used by the Fitness Agent)
            </p>
            <p className="font-mono text-[11.5px] text-paper-100 leading-relaxed">
              If all sets hit the top rep target at the prescribed weight → add weight next session.<br />
              If any set missed reps → repeat same prescription next session.<br />
              If multiple sets missed reps → deload to 90% next session to rebuild.
            </p>
          </div>

          <Myth
            myth="I should 'muscle confusion' — do a different workout every session."
            truth="There's no scientific basis for 'muscle confusion.' Research consistently shows consistent, progressively overloaded programs produce better results than constantly-changing ones. Stick with a program for 8+ weeks before switching."
          />
        </section>

        {/* Hydration & lifestyle */}
        <section className="card p-6">
          <SectionHeader
            num="05" icon={Droplets}
            title="Water, sleep, and why they matter"
            blurb="The two free interventions most people ignore — despite their outsize effect on every other aspect of health."
          />

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="smallcaps mb-2">Water</p>
              <p className="text-[12.5px] text-ink-700 leading-relaxed mb-3">
                Aim for <strong>35ml per kg body weight</strong> per day. A 70kg person = ~2.5 litres.
                Add another 500ml for every hour of training.
              </p>
              <p className="text-[12px] text-ink-600 leading-relaxed">
                Dehydration of just 2% reduces strength output by ~5% and cognitive performance
                noticeably. Check urine colour — pale straw = adequate, dark yellow = inadequate.
              </p>
            </div>
            <div>
              <p className="smallcaps mb-2">Sleep</p>
              <p className="text-[12.5px] text-ink-700 leading-relaxed mb-3">
                <strong>7–9 hours per night</strong> for adults. Growth hormone peaks in deep sleep —
                this is literally when muscle repair happens.
              </p>
              <p className="text-[12px] text-ink-600 leading-relaxed">
                Sleeping &lt; 6 hours increases ghrelin (hunger hormone) and decreases leptin
                (satiety hormone). You'll eat more without realizing it.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-lg bg-clay-50 p-4"
               style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216,100,58,0.25)' }}>
            <p className="text-[12px] text-clay-700 leading-relaxed">
              <strong>FitAgent auto-adjustment:</strong> If you log less than 6 hours of sleep,
              the Fitness Agent automatically reduces your training volume by 15% for that cycle
              to prioritize recovery.
            </p>
          </div>
        </section>

        {/* Further reading */}
        <section className="card p-6">
          <SectionHeader
            num="06" icon={BookOpen}
            title="Further reading"
            blurb="Peer-reviewed sources that FitAgent's knowledge base draws from."
          />
          <ul className="flex flex-col gap-2.5 text-[12.5px] text-ink-700">
            <li className="flex gap-2">
              <span className="font-mono text-[10px] text-clay-500 tnum pt-1" style={{ letterSpacing: '0.1em' }}>R01</span>
              <span><strong>ICMR-NIN</strong>. Dietary Guidelines for Indians, 2020 — the authoritative reference for Indian nutritional needs.</span>
            </li>
            <li className="flex gap-2">
              <span className="font-mono text-[10px] text-clay-500 tnum pt-1" style={{ letterSpacing: '0.1em' }}>R02</span>
              <span><strong>IFCT 2017</strong> — Indian Food Composition Tables. Nutrient content of 528 Indian foods.</span>
            </li>
            <li className="flex gap-2">
              <span className="font-mono text-[10px] text-clay-500 tnum pt-1" style={{ letterSpacing: '0.1em' }}>R03</span>
              <span><strong>Jäger et al. 2017</strong>. ISSN Position Stand: Protein and Exercise. J Int Soc Sports Nutr.</span>
            </li>
            <li className="flex gap-2">
              <span className="font-mono text-[10px] text-clay-500 tnum pt-1" style={{ letterSpacing: '0.1em' }}>R04</span>
              <span><strong>Schoenfeld et al. 2017</strong>. Dose-response relationship between weekly resistance training volume and increases in muscle mass.</span>
            </li>
            <li className="flex gap-2">
              <span className="font-mono text-[10px] text-clay-500 tnum pt-1" style={{ letterSpacing: '0.1em' }}>R05</span>
              <span><strong>Mifflin &amp; St Jeor 1990</strong>. A new predictive equation for resting energy expenditure in healthy individuals. Am J Clin Nutr.</span>
            </li>
          </ul>
        </section>

        <p className="text-center text-[11px] text-ink-400 italic py-4">
          This is educational content. Always consult a qualified doctor or dietitian before
          making significant changes to your diet or exercise, especially if you have a medical condition.
        </p>
      </div>
    </Container>
  )
}
