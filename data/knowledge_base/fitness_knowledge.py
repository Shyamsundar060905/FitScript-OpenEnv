"""
Comprehensive fitness and nutrition knowledge base.
Each entry: (id, content, tags)
Tags are used for filtered retrieval — agents only get relevant documents.

Sources this is grounded in:
- NSCA Essentials of Strength Training and Conditioning
- ACSM Exercise Guidelines
- ICMR-NIN Dietary Guidelines for Indians (2020)
- WHO Nutrition Recommendations
- Current Sports Medicine literature on hypertrophy and periodization
"""

# ── EXERCISE SCIENCE ──────────────────────────────────────────────────────────

EXERCISE_SCIENCE = [

    # Progressive Overload
    ("ex_001",
     "Progressive overload is the foundational principle of strength training. "
     "To stimulate adaptation, training stress must increase over time. "
     "Methods: increase load (weight), increase volume (sets × reps), "
     "increase frequency, decrease rest periods, or improve technique. "
     "For beginners, add weight every session. Intermediates add weight weekly. "
     "Advanced lifters periodize over months. Without progressive overload, "
     "muscles fully adapt and growth stops within 4-6 weeks.",
     ["progressive_overload", "all_goals", "all_levels", "programming"]),

    ("ex_002",
     "Double progression method: progress reps first, then weight. "
     "Example: target 3 sets of 8-12 reps. Start at 8 reps. Each session, "
     "try to add 1-2 reps. Once you hit 12 reps on all sets, increase weight "
     "by 2.5-5kg and return to 8 reps. This is the most practical progression "
     "system for intermediate lifters with dumbbells or barbells.",
     ["progressive_overload", "muscle_gain", "intermediate", "programming"]),

    # Volume and Frequency
    ("ex_003",
     "Minimum Effective Volume (MEV) for muscle growth per muscle group per week: "
     "chest 10 sets, back 10 sets, shoulders 8 sets, biceps 6 sets, "
     "triceps 6 sets, quads 8 sets, hamstrings 6 sets, glutes 6 sets, "
     "calves 6 sets. Maximum Adaptive Volume (MAV) is roughly 1.5× MEV. "
     "Exceeding Maximum Recoverable Volume (MRV) causes overtraining. "
     "Start at MEV and increase by 2 sets per muscle group per mesocycle.",
     ["volume", "hypertrophy", "muscle_gain", "intermediate", "advanced", "programming"]),

    ("ex_004",
     "Training frequency: each muscle group should be trained 2× per week "
     "for optimal hypertrophy. Research shows 2× per week produces ~70% more "
     "muscle growth than 1× per week at the same total volume. "
     "Splits: Upper/Lower 4 days, Push/Pull/Legs 6 days, Full Body 3 days. "
     "For beginners: Full Body 3× per week is optimal. "
     "For intermediates: Upper/Lower or PPL. "
     "For advanced: PPL or specialization programs.",
     ["frequency", "hypertrophy", "muscle_gain", "all_levels", "programming"]),

    ("ex_005",
     "Rep ranges and their primary adaptations: "
     "1-5 reps at 85-100% 1RM = maximal strength, neural adaptations. "
     "6-12 reps at 67-85% 1RM = hypertrophy (muscle size), optimal for muscle gain. "
     "12-20 reps at 50-67% 1RM = muscular endurance, metabolic stress hypertrophy. "
     "All rep ranges build muscle, but 6-12 is most efficient for hypertrophy. "
     "For compound movements use lower rep ranges. For isolation, higher ranges.",
     ["rep_ranges", "hypertrophy", "strength", "muscle_gain", "all_levels"]),

    # Rest and Recovery
    ("ex_006",
     "Rest periods between sets significantly affect training outcomes. "
     "For strength (1-5 reps): rest 3-5 minutes to allow full ATP resynthesis. "
     "For hypertrophy (6-12 reps): rest 60-120 seconds. "
     "For endurance (15+ reps): rest 30-60 seconds. "
     "Shorter rest increases metabolic stress but reduces load capability. "
     "Longer rest allows heavier loads and more total volume. "
     "Recent research shows longer rest (2+ min) may be superior for hypertrophy.",
     ["rest", "recovery", "all_goals", "all_levels"]),

    ("ex_007",
     "Muscle protein synthesis (MPS) remains elevated for 24-48 hours after "
     "resistance training. This is why training the same muscle group again "
     "after 48 hours is optimal. Training a muscle only once per week means "
     "it is only in a growth state for 2 of every 7 days. Training twice per week "
     "doubles the anabolic stimulus. Each training session resets the MPS clock.",
     ["recovery", "frequency", "muscle_gain", "hypertrophy", "intermediate", "advanced"]),

    # Periodization
    ("ex_008",
     "Periodization is the systematic variation of training variables over time. "
     "Linear periodization: increase weight, decrease reps each week. "
     "Week 1: 3×12, Week 2: 3×10, Week 3: 3×8, Week 4: 3×6 (heavier). "
     "Undulating periodization: vary intensity within a week. "
     "Monday: heavy (5 reps), Wednesday: moderate (10 reps), Friday: light (15 reps). "
     "Daily undulating periodization (DUP) produces superior strength and size gains "
     "compared to linear periodization in intermediate and advanced lifters.",
     ["periodization", "programming", "muscle_gain", "strength", "intermediate", "advanced"]),

    ("ex_009",
     "Deload week: a planned reduction in training stress every 4-8 weeks. "
     "Reduce volume by 40-50% (keep same weight or reduce by 10-20%). "
     "Purpose: allow connective tissue to recover, clear accumulated fatigue, "
     "allow supercompensation. Signs you need a deload: persistent joint pain, "
     "decreasing strength over 2+ weeks, poor sleep, lack of motivation. "
     "Beginners may not need formal deloads for 3-4 months. "
     "Advanced lifters deload every 4-6 weeks.",
     ["deload", "recovery", "periodization", "all_levels", "programming"]),

    # Plateau Breaking
    ("ex_010",
     "Plateau in strength/size occurs when the body fully adapts to a stimulus. "
     "Solutions by type: "
     "Strength plateau: change rep range (5→3 rep work), add pause reps, "
     "tempo training, or test 1RM and reset percentages. "
     "Size plateau: increase weekly volume by 2-4 sets per muscle group, "
     "add a technique variation (incline vs flat bench), "
     "change exercise order. "
     "Weight loss plateau: recalculate TDEE (it decreases as you lose weight), "
     "add 1-2 cardio sessions, implement diet break at maintenance for 1-2 weeks.",
     ["plateau", "programming", "all_goals", "intermediate", "advanced"]),

    ("ex_011",
     "Overtraining syndrome (OTS) vs overreaching: "
     "Functional overreaching: short-term performance decrease, "
     "resolves in 1-2 weeks with rest. Normal and expected in hard training. "
     "Non-functional overreaching: performance decrease for weeks-months, "
     "mood disturbances, hormonal disruption. "
     "OTS: rare, requires months of recovery. "
     "Warning signs: resting HR elevated 5+ bpm above baseline, "
     "strength dropping over 2+ consecutive sessions, "
     "persistent muscle soreness, poor sleep quality, irritability. "
     "Solution: immediate deload or complete rest for 1-2 weeks.",
     ["overtraining", "recovery", "all_levels", "programming"]),

    # Beginner Programming
    ("ex_012",
     "Beginner program principles (0-12 months training): "
     "Full body training 3× per week is optimal. "
     "Focus on compound movements: squat, hinge, push, pull, carry. "
     "Linear progression works best — add weight every session. "
     "Keep volume low initially (2-3 sets per exercise, 3-4 exercises per session). "
     "Prioritize learning movement patterns over loading. "
     "Soreness is normal for first 2-4 weeks then decreases. "
     "Avoid advanced techniques (drop sets, supersets) until form is solid.",
     ["beginner", "programming", "all_goals", "muscle_gain", "weight_loss"]),

    ("ex_013",
     "Bodyweight training progression ladder: "
     "Push: wall push-ups → incline push-ups → knee push-ups → full push-ups "
     "→ diamond push-ups → archer push-ups → one-arm push-up negatives. "
     "Pull: dead hang → scapular pulls → negative pull-ups → band-assisted "
     "→ full pull-ups → weighted pull-ups → L-sit pull-ups. "
     "Squat: chair-assisted → goblet squat → bodyweight squat → pause squat "
     "→ Bulgarian split squat → pistol squat negatives → pistol squat. "
     "Always master current level before progressing. 3 sets of 10 clean reps = ready to progress.",
     ["bodyweight", "calisthenics", "beginner", "intermediate", "progressive_overload"]),

    # Equipment-Specific
    ("ex_014",
     "Dumbbell-only training: effective for all goals with correct programming. "
     "Key exercises: goblet squat, Romanian deadlift, dumbbell bench press, "
     "bent-over row, shoulder press, lunges, single-leg RDL, bicep curls, "
     "tricep extensions, lateral raises. "
     "Limitation: hard to load very heavy for compound movements. "
     "Solution: use higher rep ranges (10-20) and focus on time under tension. "
     "Tempo training (3 seconds down, 1 second pause, 1 second up) increases "
     "difficulty without heavier weights.",
     ["dumbbells", "equipment", "all_goals", "all_levels"]),

    ("ex_015",
     "Resistance band training: highly effective for muscle activation and "
     "assistance work. Bands provide accommodating resistance — load is lighter "
     "at the bottom of movement and heavier at top. "
     "Best uses: warm-up activation, assistance for pull-ups, "
     "lateral walks for glute activation, face pulls for shoulder health, "
     "banded push-ups for chest. "
     "Bands complement but do not fully replace free weights for hypertrophy "
     "due to lack of consistent peak tension.",
     ["resistance_bands", "equipment", "all_goals", "beginner", "intermediate"]),

    # Cardio and Conditioning
    ("ex_016",
     "Cardio for different goals: "
     "Weight loss: 150-300 min moderate cardio per week, "
     "or 75-150 min vigorous cardio. LISS (low intensity steady state) "
     "burns fat, easy to recover from. HIIT burns more calories per minute "
     "but requires more recovery. Do cardio after weights, not before. "
     "Muscle gain: limit cardio to 2-3 sessions of 20-30 min LISS per week. "
     "Excessive cardio interferes with muscle protein synthesis (interference effect). "
     "Endurance: periodized cardio with base building (zone 2), "
     "threshold work, and VO2max sessions.",
     ["cardio", "weight_loss", "endurance", "muscle_gain", "all_levels"]),

    # Injury Prevention
    ("ex_017",
     "Knee pain during exercise: "
     "Patellofemoral pain (front of knee): avoid deep squats, leg extensions, "
     "running downhill. Replace with: step-ups, leg press at partial range, "
     "swimming, cycling. Strengthen VMO (inner quad) with terminal knee extensions. "
     "IT band syndrome (outer knee): avoid running, cycling long distances. "
     "Strengthen glutes and hip abductors. Foam roll IT band. "
     "General knee advice: always warm up, avoid locking out knee under load, "
     "keep knee tracking over second toe.",
     ["knee_pain", "injury", "modification", "all_levels"]),

    ("ex_018",
     "Lower back pain during training: "
     "Acute lower back pain: stop deadlifts, squats, rowing movements. "
     "Replace with: leg press, hip thrust, lat pulldown, cable rows seated. "
     "Focus on core stability: dead bugs, bird dogs, plank variations. "
     "Chronic lower back: strengthen glutes and core, improve hip mobility. "
     "Romanian deadlifts with light weight and perfect form can rehabilitate "
     "lower back over time. Always brace core (360-degree pressure) before lifting. "
     "Avoid spinal flexion under load.",
     ["lower_back", "injury", "modification", "all_levels"]),

    ("ex_019",
     "Shoulder pain during training: "
     "Rotator cuff irritation: avoid overhead pressing, upright rows, "
     "behind-neck exercises. Replace overhead press with landmine press "
     "or incline press. Add: face pulls, band external rotations, "
     "Y-T-W raises for shoulder health. "
     "AC joint pain: avoid dips, decline press, wide-grip bench. "
     "Impingement: avoid internal rotation under load. "
     "General: maintain 2:1 ratio of pulling to pushing exercises. "
     "Warm up rotator cuff before heavy pressing.",
     ["shoulder_pain", "injury", "modification", "all_levels"]),

    ("ex_020",
     "Wrist pain during training: "
     "Common causes: poor wrist alignment in push-ups, incorrect bar grip. "
     "Modifications: push-ups on fists instead of palms, "
     "use push-up handles or parallettes, "
     "use neutral grip dumbbells instead of barbell for pressing. "
     "Strengthen: wrist curls, reverse curls, rice bucket exercises. "
     "Avoid: behind-neck exercises, extreme wrist extension under load. "
     "If acute: rest 1-2 weeks, ice, then gradually return with modifications.",
     ["wrist_pain", "injury", "modification", "all_levels"]),

    # Warm-up and Cool-down
    ("ex_021",
     "Effective warm-up protocol (10-15 minutes): "
     "Phase 1 — General warm-up: 5 min light cardio (jumping jacks, jump rope). "
     "Phase 2 — Dynamic mobility: leg swings, arm circles, hip circles, "
     "thoracic rotations, ankle circles (2 min). "
     "Phase 3 — Activation: glute bridges, band pull-aparts, face pulls (2 min). "
     "Phase 4 — Specific warm-up: 2-3 warm-up sets of first exercise "
     "at 50%, 70%, 90% of working weight. "
     "Never stretch cold muscles statically before lifting. "
     "Static stretching is for post-workout cool-down.",
     ["warmup", "injury_prevention", "all_goals", "all_levels"]),
]

# ── NUTRITION SCIENCE ─────────────────────────────────────────────────────────

NUTRITION_SCIENCE = [

    # Protein
    ("nut_001",
     "Protein requirements for different goals and activity levels: "
     "Sedentary adult (RDA): 0.8g per kg bodyweight. "
     "Recreational exerciser: 1.2-1.6g per kg. "
     "Muscle gain (resistance training): 1.6-2.2g per kg. "
     "Weight loss (preserve muscle): 2.2-3.1g per kg (higher protein prevents muscle loss). "
     "Endurance athlete: 1.2-1.6g per kg. "
     "Upper limit: beyond 2.5g/kg shows no additional benefit for most people. "
     "Distribute protein across 4+ meals, each containing 20-40g.",
     ["protein", "all_goals", "all_levels", "nutrition_fundamentals"]),

    ("nut_002",
     "Protein quality and completeness: "
     "Complete proteins (all 9 essential amino acids): "
     "Animal sources: chicken, fish, eggs, dairy, whey. "
     "Plant sources: soy (tofu, tempeh, edamame), quinoa, buckwheat, hemp seeds. "
     "Incomplete proteins: most legumes and grains are incomplete alone. "
     "Complementary proteins: combine legumes + grains for complete profile. "
     "Dal + rice = complete protein (traditional Indian combination is nutritionally optimal). "
     "Rajma + rice, chhole + roti, moong dal + wheat roti — all provide complete amino acids.",
     ["protein", "vegetarian", "indian", "nutrition_fundamentals", "all_goals"]),

    ("nut_003",
     "Leucine threshold and muscle protein synthesis: "
     "Leucine is the key amino acid that triggers muscle protein synthesis (MPS). "
     "Threshold: approximately 2-3g leucine per meal needed to maximally stimulate MPS. "
     "Leucine content per 100g protein: whey 10g, eggs 8.5g, chicken 7.5g, "
     "tofu 6.5g, lentils 6g, chickpeas 6g. "
     "Practical implication: vegetarians need slightly more total protein "
     "to hit the leucine threshold. Aim for 30-40g protein per meal from plant sources.",
     ["protein", "vegetarian", "muscle_gain", "nutrition_science"]),

    ("nut_004",
     "Carbohydrates for performance and body composition: "
     "Primary fuel for high-intensity exercise (>65% VO2max). "
     "Stored as glycogen in muscles (400-600g) and liver (100g). "
     "Depleted glycogen = reduced performance, increased muscle breakdown. "
     "For muscle gain: high carb intake (4-7g/kg) fuels training and prevents catabolism. "
     "For weight loss: moderate carbs (2-4g/kg), prioritize around workout. "
     "Best sources: oats, brown rice, sweet potato, quinoa, fruits, whole wheat roti. "
     "Timing: largest carb intake pre- and post-workout.",
     ["carbohydrates", "all_goals", "all_levels", "nutrition_fundamentals"]),

    ("nut_005",
     "Caloric deficit principles for fat loss: "
     "1kg of fat = approximately 7700 kcal. "
     "Moderate deficit of 300-500 kcal/day = 0.3-0.5kg fat loss per week. "
     "Aggressive deficit (500-750 kcal/day) = faster loss but risks muscle loss. "
     "Never below 1200 kcal (women) or 1500 kcal (men) — metabolic adaptation risk. "
     "As you lose weight, TDEE decreases — recalculate every 4-6 weeks. "
     "Diet breaks: 1-2 weeks at maintenance every 8-12 weeks "
     "resets metabolic adaptation and improves adherence.",
     ["weight_loss", "caloric_deficit", "nutrition_fundamentals", "all_levels"]),

    ("nut_006",
     "Caloric surplus for muscle gain — lean bulk strategy: "
     "Optimal surplus: 200-300 kcal above TDEE. "
     "Smaller surplus = slower gains but less fat gain. "
     "Larger surplus (500+) = faster weight gain but disproportionate fat gain. "
     "Expected rate of gain: beginners 1-1.5kg/month, intermediates 0.5-1kg/month, "
     "advanced 0.25-0.5kg/month. "
     "If gaining faster than expected, reduce surplus by 100 kcal. "
     "If not gaining after 2 weeks, increase by 100-200 kcal.",
     ["muscle_gain", "caloric_surplus", "nutrition_fundamentals", "all_levels"]),

    ("nut_007",
     "Meal timing for performance and body composition: "
     "Pre-workout (2-3 hours before): complex carbs + moderate protein + low fat. "
     "Example: oats with milk, roti with dal, banana with peanut butter. "
     "Avoid high fat or high fiber immediately pre-workout (slows digestion). "
     "Post-workout (within 2 hours): protein + fast carbs for recovery. "
     "Example: protein shake + banana, curd with rice, paneer with roti. "
     "The anabolic window is wider than previously thought — "
     "total daily intake matters more than precise timing.",
     ["meal_timing", "all_goals", "all_levels", "nutrition_fundamentals"]),

    ("nut_008",
     "Fats in athlete nutrition: "
     "Minimum fat intake: 20-35% of total calories (0.5-1.5g/kg bodyweight). "
     "Below 20% fat impairs hormone production (testosterone, estrogen). "
     "Prioritize: unsaturated fats (olive oil, nuts, avocado, fatty fish). "
     "Limit: saturated fats (ghee, butter, coconut oil) to 10% of calories. "
     "Avoid: trans fats (vanaspati, processed foods). "
     "Omega-3 fatty acids (flaxseeds, walnuts, fish) reduce inflammation, "
     "improve recovery, and may enhance muscle protein synthesis.",
     ["fats", "nutrition_fundamentals", "all_goals", "all_levels"]),

    # Micronutrients for Athletes
    ("nut_009",
     "Iron for athletes (critical for vegetarians and women): "
     "Function: oxygen transport in red blood cells. "
     "Deficiency causes: fatigue, reduced endurance, poor recovery. "
     "RDA: men 8mg/day, women 18mg/day, vegetarians need 1.8× more "
     "(plant iron is less bioavailable). "
     "Best vegetarian sources: spinach, lentils, rajma, chana, tofu, "
     "pumpkin seeds, fortified cereals. "
     "Absorption tip: consume with vitamin C (lemon juice on dal, "
     "tomatoes with spinach). Avoid coffee/tea within 1 hour of iron-rich meals.",
     ["micronutrients", "iron", "vegetarian", "all_goals", "all_levels"]),

    ("nut_010",
     "Vitamin D and calcium for athletes: "
     "Vitamin D functions: calcium absorption, muscle function, immune health, "
     "testosterone production. "
     "Deficiency very common in India due to indoor lifestyles and darker skin. "
     "RDA: 600-800 IU, athletes may need 2000-4000 IU. "
     "Sources: sunlight (best), fortified milk, egg yolk, fatty fish. "
     "Calcium RDA: 1000mg/day for adults. "
     "Vegetarian sources: milk (300mg/cup), curd (200mg/cup), "
     "paneer (200mg/100g), ragi (350mg/100g), sesame seeds (1000mg/100g).",
     ["micronutrients", "vitamin_d", "calcium", "vegetarian", "indian", "all_goals"]),

    ("nut_011",
     "Vitamin B12 for vegetarians and vegans: "
     "Critical for nerve function, red blood cell formation, energy metabolism. "
     "B12 is found almost exclusively in animal products. "
     "Vegetarians at risk — dairy and eggs provide some but often insufficient. "
     "Vegans must supplement: 250-500 mcg cyanocobalamin daily or "
     "2000 mcg weekly. "
     "Signs of deficiency: fatigue, weakness, numbness, poor memory. "
     "Vegetarian Indian sources: milk (0.4 mcg/cup), curd (0.6 mcg/cup), "
     "paneer (0.3 mcg/100g), eggs (0.6 mcg each).",
     ["micronutrients", "b12", "vegetarian", "vegan", "indian", "all_goals"]),

    ("nut_012",
     "Hydration for athletes: "
     "Dehydration of just 2% bodyweight reduces strength by 5-8% "
     "and aerobic capacity by 10-20%. "
     "Daily water intake: 35-45ml per kg bodyweight as baseline. "
     "Add 500-750ml per hour of moderate exercise. "
     "Add 1-1.5L per hour of intense exercise in heat. "
     "Electrolytes lost in sweat: sodium, potassium, magnesium. "
     "For sessions under 60 min: water is sufficient. "
     "For sessions over 60 min or heavy sweating: electrolyte drink or "
     "add pinch of salt + lemon to water (Indian ORS-style drink).",
     ["hydration", "all_goals", "all_levels", "nutrition_fundamentals"]),

    # Indian Food Specific
    ("nut_013",
     "High-protein Indian vegetarian foods and their protein content: "
     "Soy chunks/granules (dry): 52g protein per 100g — best plant protein source. "
     "Paneer: 18-20g protein per 100g, also high in calcium. "
     "Chana dal (Bengal gram): 22g protein per 100g dry. "
     "Rajma (kidney beans): 24g protein per 100g dry, 9g cooked. "
     "Moong dal: 24g protein per 100g dry, 7g cooked. "
     "Masoor dal (red lentils): 26g protein per 100g dry. "
     "Greek yogurt/hung curd: 10g protein per 100g. "
     "Curd (dahi): 3.5g protein per 100g. "
     "Cottage cheese is similar to paneer. "
     "Eggs: 6g protein each (for those who eat them).",
     ["protein", "vegetarian", "indian", "nutrition_database", "muscle_gain"]),

    ("nut_014",
     "Indian grains and their nutritional profile: "
     "Roti (whole wheat, 1 medium): 70 kcal, 3g protein, 15g carbs, 1g fat. "
     "Brown rice (cooked, 100g): 111 kcal, 2.6g protein, 23g carbs, 0.9g fat. "
     "White rice (cooked, 100g): 130 kcal, 2.7g protein, 28g carbs, 0.3g fat. "
     "Oats (dry, 100g): 389 kcal, 17g protein, 66g carbs, 7g fat — excellent. "
     "Quinoa (cooked, 100g): 120 kcal, 4.4g protein, 22g carbs, 1.9g fat, complete protein. "
     "Poha (flattened rice, 100g): 76 kcal, 1.5g protein, 17g carbs. "
     "Ragi (finger millet, 100g): 328 kcal, 7g protein, 72g carbs — high in calcium.",
     ["carbohydrates", "indian", "nutrition_database", "all_goals"]),

    ("nut_015",
     "Indian vegetables and legumes calorie and nutrition guide: "
     "Dal (cooked, 100g): average 100-120 kcal, 7-9g protein, 18g carbs. "
     "Chole (chickpeas, cooked, 100g): 164 kcal, 9g protein, 27g carbs, 2.6g fat. "
     "Palak (spinach, 100g): 23 kcal, 2.9g protein, 3.6g carbs — high iron. "
     "Aloo (potato, 100g): 77 kcal, 2g protein, 17g carbs — nutrient dense. "
     "Broccoli (100g): 34 kcal, 2.8g protein, 7g carbs — high vitamin C. "
     "Banana (1 medium): 89 kcal, 1g protein, 23g carbs — excellent pre-workout. "
     "Apple (1 medium): 95 kcal, 0.5g protein, 25g carbs — good fiber source.",
     ["indian", "nutrition_database", "all_goals", "all_levels"]),

    ("nut_016",
     "Practical high-protein Indian meal ideas for muscle gain: "
     "Breakfast: soya chunks upma (30g protein), "
     "moong dal chilla with paneer filling (25g protein), "
     "oats with milk and nuts (20g protein). "
     "Lunch: rajma chawal with curd (35g protein), "
     "paneer bhurji with 3 rotis (30g protein), "
     "chole with brown rice (28g protein). "
     "Dinner: tofu stir fry with quinoa (30g protein), "
     "dal makhani with roti (20g protein) + glass of milk. "
     "Snacks: hung curd with fruits (15g), "
     "roasted chana (10g per handful), "
     "peanut butter with banana (12g).",
     ["indian", "vegetarian", "muscle_gain", "meal_ideas", "practical"]),

    ("nut_017",
     "Indian weight loss meal strategy: "
     "Use volumetrics — eat foods with high volume but low calories. "
     "Best choices: vegetables (dal with lots of vegetables), "
     "salads before meals reduce overall intake. "
     "Swap: white rice → brown rice (saves 20 kcal/100g, more fiber). "
     "Maida → atta (whole wheat, more fiber and protein). "
     "Frying → baking, air frying, steaming (saves 100-200 kcal per meal). "
     "Reduce oil: most Indian cooking uses 2-4 tbsp oil per dish (240-480 kcal). "
     "Use non-stick pans, measure oil. "
     "Chapati count: 2-3 medium rotis per meal, not 4-5.",
     ["weight_loss", "indian", "practical", "meal_ideas", "all_levels"]),

    # Special Nutrition Topics
    ("nut_018",
     "Creatine supplementation — most researched supplement in sports science: "
     "Benefits: increases phosphocreatine stores, improves high-intensity performance "
     "by 5-15%, enhances muscle recovery, may increase lean mass. "
     "Dosage: 3-5g creatine monohydrate daily (no loading needed). "
     "Timing: any time of day with food. "
     "Safety: extensively studied, safe for healthy adults. "
     "Note: creatine is naturally found only in meat — vegetarians have "
     "lower baseline stores and respond better to supplementation. "
     "Form: monohydrate is cheapest and most effective.",
     ["supplements", "creatine", "vegetarian", "muscle_gain", "performance"]),

    ("nut_019",
     "Pre and post workout nutrition simplified: "
     "Pre-workout goal: fuel the session and prevent muscle breakdown. "
     "2-3 hours before: full meal (carbs + protein + small fat). "
     "30-60 min before: easily digestible carb + small protein. "
     "Examples: banana + 2 tbsp peanut butter, small bowl of oats with milk. "
     "Post-workout goal: replenish glycogen, stimulate muscle protein synthesis. "
     "Within 2 hours: 20-40g protein + carbohydrates. "
     "Examples: curd rice with dal, paneer paratha, milk with banana. "
     "The post-workout window is real but not as narrow as once thought.",
     ["meal_timing", "pre_workout", "post_workout", "all_goals", "practical"]),

    ("nut_020",
     "Managing hunger on a caloric deficit: "
     "High-satiety strategies: prioritize protein (most satiating macronutrient), "
     "eat high-fiber foods (vegetables, legumes, whole grains), "
     "drink water before meals (reduces intake by ~13%), "
     "eat slowly (takes 20 min for satiety signals to reach brain). "
     "Indian deficit-friendly foods: dal (filling, high protein, low calorie), "
     "sprouts (low calorie, high nutrition), "
     "raita (low calorie, high protein). "
     "Avoid liquid calories (juice, chai with sugar, cold drinks). "
     "Strategic meal timing: larger meals before workouts, "
     "lighter dinner improves sleep and reduces overnight fat storage.",
     ["weight_loss", "hunger", "practical", "indian", "all_levels"]),
]

# ── PERSONALIZATION AND ADAPTATION RULES ─────────────────────────────────────

ADAPTATION_RULES = [

    ("adapt_001",
     "Plateau detection criteria and response protocols: "
     "Weight loss plateau: body weight unchanged (±0.5kg) for 14+ days "
     "despite consistent caloric deficit. "
     "Response: recalculate TDEE (weight loss reduces it), "
     "add 1-2 cardio sessions, implement refeed day at maintenance 1× per week, "
     "check for calorie creep (measure portions accurately). "
     "Strength plateau: same weight lifted for 3+ consecutive sessions. "
     "Response: deload, change rep range, add accessory work, "
     "improve sleep and nutrition.",
     ["plateau", "adaptation", "programming", "all_goals"]),

    ("adapt_002",
     "How to adapt training for different fitness levels: "
     "Beginner (0-1 year): linear progression, 3 full body sessions, "
     "2-3 sets per exercise, focus on form, avoid failure. "
     "Intermediate (1-3 years): split routines, 3-4 sets, "
     "periodized programming, occasional training to failure. "
     "Advanced (3+ years): advanced techniques (rest-pause, drop sets, "
     "supersets), detailed periodization, high frequency specialization, "
     "regular deloads mandatory. "
     "Transitioning between levels: when progress stalls consistently "
     "despite proper form and nutrition.",
     ["adaptation", "all_levels", "programming", "all_goals"]),

    ("adapt_003",
     "Adapting plans for time constraints: "
     "30 minutes: full body circuit, 3-4 compound exercises, "
     "minimal rest (30-45 sec), supersets. "
     "45 minutes: upper/lower or push/pull focus, 4-5 exercises, "
     "moderate rest (60 sec). "
     "60 minutes: standard session with warm-up, 5-6 exercises. "
     "90 minutes: full session with accessories and mobility work. "
     "If short on time: prioritize compound movements, cut isolation work. "
     "3 × 10 min sessions can be as effective as 1 × 30 min for beginners.",
     ["adaptation", "time_constraints", "all_goals", "all_levels"]),

    ("adapt_004",
     "Adherence-based plan modification: "
     "If adherence below 70%: reduce session frequency by 1 day per week. "
     "Simpler is better for adherence than optimal but complex. "
     "Identify barrier: time, motivation, equipment, soreness, enjoyment. "
     "Solutions by barrier: "
     "Time → shorter sessions, home workouts. "
     "Motivation → training partner, different music, new exercises. "
     "Soreness → reduce volume, improve warm-up, check sleep/nutrition. "
     "Enjoyment → include 1-2 exercises the user enjoys even if suboptimal.",
     ["adherence", "adaptation", "all_goals", "all_levels"]),

    ("adapt_005",
     "Progressive overload for home/dumbbell training: "
     "When you max out on weight available: "
     "1. Increase reps (double progression). "
     "2. Add pauses: 2-second pause at bottom of movement. "
     "3. Slow eccentric: 3-4 seconds lowering phase. "
     "4. Reduce rest periods. "
     "5. Add unilateral work (single-arm, single-leg = double challenge). "
     "6. Increase range of motion (deficit push-ups, deep squat). "
     "7. Add instability (single-leg Romanian deadlift vs bilateral). "
     "These techniques add intensity without needing more weight.",
     ["progressive_overload", "dumbbells", "bodyweight", "adaptation",
      "intermediate", "advanced"]),

    ("adapt_006",
     "Goal transition adaptation: "
     "Switching from weight loss to muscle gain: "
     "Reverse diet — increase calories by 50-100 kcal per week for 4-8 weeks "
     "until at maintenance, then add surplus. "
     "Change training: reduce cardio, increase weights and volume. "
     "Switching from muscle gain to weight loss: "
     "Reduce calories by 200-300 kcal per week until deficit. "
     "Maintain lifting frequency and intensity to preserve muscle. "
     "Add 1-2 cardio sessions. "
     "Key: make changes gradually to avoid metabolic shock.",
     ["adaptation", "goal_change", "all_levels", "programming"]),

    ("adapt_007",
     "Sleep and recovery optimization: "
     "Sleep is the most anabolic activity available — "
     "80% of growth hormone is released during deep sleep. "
     "7-9 hours per night is optimal for athletes. "
     "Poor sleep (under 6 hours) increases cortisol by 37%, "
     "reduces testosterone by 15%, and impairs reaction time and strength. "
     "Sleep optimization: consistent bedtime, dark and cool room (18-20°C), "
     "no screens 30 min before bed, avoid caffeine after 2pm, "
     "magnesium glycinate 300-400mg before bed may improve sleep quality.",
     ["recovery", "sleep", "all_goals", "all_levels"]),

    ("adapt_008",
     "Stress and training: managing life stress with fitness: "
     "High psychological stress elevates cortisol — the same stress hormone "
     "elevated by training. When life stress is high: "
     "Reduce training volume by 30-40% (keep intensity). "
     "Prioritize sleep and nutrition over training frequency. "
     "Lower intensity training (yoga, walking) reduces cortisol and is "
     "better than high intensity when stressed. "
     "Signs of too much total stress: poor sleep, low motivation, "
     "constant fatigue, getting sick frequently.",
     ["recovery", "stress", "adaptation", "all_goals", "all_levels"]),
]

# ── Combine all knowledge ─────────────────────────────────────────────────────

ALL_KNOWLEDGE = EXERCISE_SCIENCE + NUTRITION_SCIENCE + ADAPTATION_RULES