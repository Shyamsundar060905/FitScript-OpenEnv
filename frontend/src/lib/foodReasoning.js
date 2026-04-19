/**
 * Food reasoning lookup.
 *
 * Evidence-based rationale for common Indian foods. Used for tooltips on
 * the Plan page nutrition accordions.
 *
 * Sources: IFCT 2017 (Indian Food Composition Tables), USDA FoodData Central,
 * ICMR-NIN Dietary Guidelines for Indians (2020).
 */

const FOOD_REASONING = [
  // ── Grains ──
  { key: 'oats',        category: 'whole grain',
    primary: 'β-glucan fibre, complex carbs, 12g protein/100g',
    why: 'β-glucan soluble fibre lowers LDL cholesterol and blunts post-meal glucose spikes. One of the lowest-GI breakfast grains (GI ~55).' },
  { key: 'ragi',        category: 'millet',
    primary: 'calcium (344mg/100g), iron, complex carbs',
    why: 'Highest calcium content of any staple grain — 3× more than rice. Excellent for bone health in a low-dairy diet. Low GI (~55).' },
  { key: 'brown rice',  category: 'whole grain',
    primary: 'complex carbs, fibre, magnesium',
    why: 'Bran layer retains fibre and minerals lost in white rice. GI ~68 vs 73 for white rice — meaningful over daily intake.' },
  { key: 'white rice',  category: 'refined grain',
    primary: 'quick-digesting carbs, folate (enriched)',
    why: 'Highly palatable and easy to digest — useful post-workout. But high GI (~73); pair with protein, fat, or vegetables to slow absorption.' },
  { key: 'basmati',     category: 'long-grain rice',
    primary: 'carbs, lower GI than regular rice',
    why: 'Higher amylose content gives basmati a lower GI (~58) than other white rices. Preferable choice when rice is desired.' },
  { key: 'roti',        category: 'whole wheat flatbread',
    primary: 'complex carbs, 3g protein per 40g roti',
    why: 'Whole wheat atta retains fibre and B vitamins. GI ~62 — acceptable when portion-controlled and paired with dal or vegetables.' },
  { key: 'chapati',     category: 'whole wheat flatbread',
    primary: 'complex carbs, 3g protein per roti',
    why: 'Whole wheat atta retains fibre and B vitamins. GI ~62 — acceptable when portion-controlled and paired with dal or vegetables.' },
  { key: 'poha',        category: 'flattened rice',
    primary: 'iron (fortified), quick carbs',
    why: 'Traditional Indian fortified iron source. Moderate GI — improved significantly when cooked with peanuts and vegetables.' },
  { key: 'quinoa',      category: 'pseudo-grain',
    primary: 'complete protein, all 9 essential amino acids',
    why: 'One of very few plant sources with complete amino acid profile. Gluten-free alternative to wheat.' },

  // ── Legumes / pulses ──
  { key: 'moong dal',   category: 'legume',
    primary: '24g protein/100g dry, low GI',
    why: 'Easiest legume to digest — ideal for those new to high-legume diets. Complements rice/roti for complete protein.' },
  { key: 'toor dal',    category: 'legume',
    primary: '22g protein/100g dry, complex carbs',
    why: 'Staple Indian pulse. Complementary protein to rice — classic dal-chawal is a nutritionally complete meal.' },
  { key: 'masoor dal',  category: 'legume',
    primary: '25g protein/100g dry, iron, folate',
    why: 'Highest iron among common dals — crucial for vegetarian diets. Very low GI (~32).' },
  { key: 'rajma',       category: 'legume',
    primary: '24g protein/100g dry, fibre, potassium',
    why: 'High fibre content lowers cholesterol and improves satiety. Very low GI (~29) — excellent for diabetics.' },
  { key: 'chana',       category: 'legume',
    primary: '19g protein/100g, complex carbs, fibre',
    why: 'Most satiating legume per calorie. Roasted chana is an excellent snack — high protein, low GI (~28), shelf-stable.' },
  { key: 'chole',       category: 'legume',
    primary: '19g protein/100g, fibre',
    why: 'Cooked chickpeas — satisfying, versatile. Fibre content helps with cholesterol management.' },
  { key: 'dal',         category: 'legume',
    primary: 'plant protein, complex carbs, fibre',
    why: 'Foundational Indian protein source. Combined with rice or roti, provides complete amino acid profile at low cost.' },
  { key: 'soya',        category: 'complete plant protein',
    primary: 'complete protein, 36g/100g dry',
    why: 'One of few plant sources with all 9 essential amino acids. Highest protein density per gram among common plant foods.' },

  // ── Dairy ──
  { key: 'milk',        category: 'dairy',
    primary: '8g protein per 240ml, calcium, B12',
    why: 'Complete protein source for vegetarians. Casein is slow-digesting — useful before sleep for overnight muscle protein synthesis.' },
  { key: 'curd',        category: 'dairy (fermented)',
    primary: 'probiotics, 3g protein per 100g',
    why: 'Live cultures improve gut health and lactose tolerance. Low GI (~14). Essential component of traditional Indian diet.' },
  { key: 'yogurt',      category: 'dairy (fermented)',
    primary: 'probiotics, protein',
    why: 'Live cultures improve gut health. Greek/hung variety has 2-3× the protein of regular yogurt.' },
  { key: 'hung curd',   category: 'strained dairy',
    primary: '10g protein per 100g, low lactose',
    why: 'Straining doubles protein density vs regular curd while reducing lactose — gentler for lactose-sensitive users.' },
  { key: 'paneer',      category: 'fresh cheese',
    primary: '18g protein/100g, calcium',
    why: 'Highest protein density among common Indian vegetarian foods. Minimal carb content — excellent for low-glycemic meals.' },

  // ── Animal protein ──
  { key: 'egg',         category: 'animal protein',
    primary: '6g protein per egg, complete amino acids',
    why: 'Highest biological value protein of any whole food (BV 100). Yolks contain choline (crucial for liver function) and fat-soluble vitamins.' },
  { key: 'chicken',     category: 'animal protein',
    primary: '31g protein per 100g breast',
    why: 'Lean complete protein — minimal fat if skin removed. Consistent amino acid profile supports muscle protein synthesis.' },
  { key: 'fish',        category: 'animal protein',
    primary: 'complete protein + omega-3 fatty acids',
    why: 'Fatty fish (salmon, mackerel, sardines) provide EPA/DHA omega-3s — anti-inflammatory, cardioprotective. Aim for 2 servings/week.' },
  { key: 'whey',        category: 'protein supplement',
    primary: 'fast-digesting complete protein, high leucine',
    why: 'Highest leucine content of any protein — leucine is the primary trigger for muscle protein synthesis. Convenient post-workout.' },

  // ── Vegetables / fruits ──
  { key: 'spinach',     category: 'leafy green',
    primary: 'iron, folate, nitrates',
    why: 'Iron absorption improved 2-3× when paired with lemon/vitamin C. Nitrates modestly improve exercise performance.' },
  { key: 'palak',       category: 'leafy green',
    primary: 'iron, folate, nitrates',
    why: 'Iron absorption improved 2-3× when paired with lemon/vitamin C. Nitrates modestly improve exercise performance.' },
  { key: 'banana',      category: 'fruit',
    primary: 'potassium, quick carbs',
    why: 'Excellent pre- or intra-workout carb source. Potassium helps regulate blood pressure — useful for hypertensive users.' },
  { key: 'apple',       category: 'fruit',
    primary: 'fibre, polyphenols, moderate GI',
    why: 'Soluble fibre (pectin) aids satiety and cholesterol management. Whole fruit is superior to juice — fibre slows sugar absorption.' },
  { key: 'tomato',      category: 'vegetable',
    primary: 'lycopene, vitamin C',
    why: 'Lycopene absorption increases 3-4× when cooked with fat (traditional Indian tadka method inadvertently optimizes this).' },

  // ── Nuts / fats ──
  { key: 'almond',      category: 'nut',
    primary: 'healthy fats, 21g protein/100g, vitamin E',
    why: 'Soaked almonds (traditional Indian practice) improve nutrient bioavailability. 6-8 per day is a sensible portion.' },
  { key: 'peanut butter', category: 'nut butter',
    primary: '25g protein/100g, healthy fats',
    why: 'Most cost-effective plant protein + healthy fat combination. Pair with fruit to slow glucose absorption.' },
  { key: 'ghee',        category: 'fat',
    primary: 'fat-soluble vitamin carrier, medium-chain fats',
    why: 'Traditional Indian fat with high smoke point. Small amounts (1 tsp/meal) aid fat-soluble vitamin absorption from vegetables.' },
  { key: 'coconut',     category: 'fat',
    primary: 'medium-chain triglycerides',
    why: 'MCTs are metabolized differently from long-chain fats — used quickly for energy rather than stored. Traditional South Indian staple.' },
  { key: 'flax',        category: 'seed',
    primary: 'ALA omega-3, fibre, lignans',
    why: 'Plant-based omega-3 source. Must be ground for absorption — whole seeds pass through undigested.' },
  { key: 'chia',        category: 'seed',
    primary: 'ALA omega-3, fibre, protein',
    why: 'Highest fibre density of any common food. Absorbs 10× its weight in water — aids satiety and hydration.' },
]

export function getFoodReasoning(foodString) {
  if (!foodString) return null
  const lower = foodString.toLowerCase()
  for (const entry of FOOD_REASONING) {
    if (lower.includes(entry.key)) return entry
  }
  return null
}
