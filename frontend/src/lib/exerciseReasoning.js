/**
 * Exercise reasoning lookup.
 *
 * Maps common exercises to evidence-based reasoning: primary muscles,
 * movement pattern, skill level, and a short "why this" explanation.
 * Used for tooltips on the Plan page.
 *
 * Source references: NSCA Essentials of Strength Training & Conditioning (4th ed),
 * ACSM Guidelines for Exercise Testing (11th ed), Schoenfeld et al. hypertrophy
 * volume meta-analyses.
 */

// Core lookup — keys should be matched case-insensitively as substrings.
// Order matters: more specific keys first (e.g. "bulgarian split squat" before "squat").
const EXERCISE_DATA = [
  // ── Lower body compound ──
  { key: 'bulgarian split squat', category: 'lower compound', level: 'intermediate',
    primary: 'quads, glutes', pattern: 'unilateral squat',
    why: 'Unilateral loading corrects left-right strength imbalances and demands more stabilizer activation than bilateral squats. Excellent for hypertrophy with less spinal load.' },
  { key: 'goblet squat', category: 'lower compound', level: 'beginner',
    primary: 'quads, glutes, core', pattern: 'squat',
    why: 'Teaches the squat pattern with an anterior load — easier to maintain upright torso than back squat. Ideal entry-point compound movement.' },
  { key: 'barbell squat', category: 'lower compound', level: 'intermediate',
    primary: 'quads, glutes, core, lower back', pattern: 'squat',
    why: 'Gold-standard lower-body mass builder. Highest loadable compound movement for legs. Trains the full posterior chain.' },
  { key: 'front squat', category: 'lower compound', level: 'intermediate',
    primary: 'quads, core, upper back', pattern: 'squat',
    why: 'Anterior bar position enforces upright torso, emphasizing quad dominance and reducing lower-back shear compared to back squat.' },
  { key: 'squat', category: 'lower compound', level: 'beginner',
    primary: 'quads, glutes', pattern: 'squat',
    why: 'Foundational lower-body movement. Trains the largest muscle groups and elicits a robust systemic anabolic response.' },
  { key: 'deadlift', category: 'lower compound', level: 'intermediate',
    primary: 'hamstrings, glutes, back, core', pattern: 'hip hinge',
    why: 'Trains the entire posterior chain and grip strength. Highest neural demand of any lift — recovery-intensive but unmatched for total-body strength.' },
  { key: 'romanian deadlift', category: 'lower compound', level: 'beginner',
    primary: 'hamstrings, glutes, lower back', pattern: 'hip hinge',
    why: 'Isolates the hip hinge pattern with reduced lower-back stress vs conventional deadlift. Strong hamstring and glute hypertrophy stimulus.' },
  { key: 'glute bridge', category: 'lower accessory', level: 'beginner',
    primary: 'glutes, hamstrings', pattern: 'hip extension',
    why: 'Knee-friendly glute isolation. Improves hip extension strength without loading the spine — ideal for beginners and those with knee discomfort.' },
  { key: 'hip thrust', category: 'lower accessory', level: 'intermediate',
    primary: 'glutes', pattern: 'hip extension',
    why: 'Produces highest glute EMG activity of any exercise (Contreras et al., 2015). Knee-safe, spine-friendly, progressively loadable.' },
  { key: 'lunge', category: 'lower compound', level: 'beginner',
    primary: 'quads, glutes', pattern: 'unilateral squat',
    why: 'Unilateral movement develops balance and addresses side-to-side imbalances. Functional for daily movement.' },
  { key: 'calf raise', category: 'lower isolation', level: 'beginner',
    primary: 'gastrocnemius, soleus', pattern: 'plantar flexion',
    why: 'Direct calf stimulus — other lower-body exercises rarely fully load the calves through their range of motion.' },

  // ── Upper push ──
  { key: 'bench press', category: 'upper push', level: 'intermediate',
    primary: 'chest, triceps, front delts', pattern: 'horizontal push',
    why: 'Most loadable upper-body pressing movement. Trains the chest through a full stretch-shortening cycle with heavy mechanical tension.' },
  { key: 'overhead press', category: 'upper push', level: 'intermediate',
    primary: 'shoulders, triceps, core', pattern: 'vertical push',
    why: 'Develops shoulder strength and stability. Requires full-body tension — trains core isometrically as a side benefit.' },
  { key: 'push-up', category: 'upper push', level: 'beginner',
    primary: 'chest, triceps, core', pattern: 'horizontal push',
    why: 'Closed-chain movement — engages more stabilizers than bench press. Scalable from wall to one-arm variations.' },
  { key: 'pushup', category: 'upper push', level: 'beginner',
    primary: 'chest, triceps, core', pattern: 'horizontal push',
    why: 'Closed-chain movement — engages more stabilizers than bench press. Scalable from wall to one-arm variations.' },
  { key: 'wall push', category: 'upper push', level: 'beginner',
    primary: 'chest, triceps', pattern: 'horizontal push',
    why: 'Modified push-up reducing wrist and shoulder load. Suitable for users with wrist discomfort or rebuilding upper-body strength.' },
  { key: 'dip', category: 'upper push', level: 'intermediate',
    primary: 'chest, triceps, front delts', pattern: 'vertical push',
    why: 'High-load bodyweight movement targeting chest and triceps. Effective mass builder when pull-ups are paired for balance.' },
  { key: 'dumbbell press', category: 'upper push', level: 'beginner',
    primary: 'chest, triceps', pattern: 'horizontal push',
    why: 'Independent arms allow greater range of motion and correct left-right asymmetries. Safer than barbell for solo training.' },
  { key: 'incline press', category: 'upper push', level: 'intermediate',
    primary: 'upper chest, front delts', pattern: 'horizontal push',
    why: 'Shifts emphasis to the clavicular head of pectoralis major. Addresses the commonly-undertrained upper chest.' },

  // ── Upper pull ──
  { key: 'pull-up', category: 'upper pull', level: 'intermediate',
    primary: 'lats, biceps, upper back', pattern: 'vertical pull',
    why: 'Highest-intensity bodyweight pulling movement. Builds lats and grip strength. Best measurable indicator of relative upper-body strength.' },
  { key: 'pullup', category: 'upper pull', level: 'intermediate',
    primary: 'lats, biceps, upper back', pattern: 'vertical pull',
    why: 'Highest-intensity bodyweight pulling movement. Builds lats and grip strength. Best measurable indicator of relative upper-body strength.' },
  { key: 'chin-up', category: 'upper pull', level: 'intermediate',
    primary: 'biceps, lats', pattern: 'vertical pull',
    why: 'Supinated grip variation of pull-up — higher biceps activation. Often easier than pull-up due to improved biomechanical advantage.' },
  { key: 'row', category: 'upper pull', level: 'beginner',
    primary: 'lats, rhomboids, rear delts', pattern: 'horizontal pull',
    why: 'Balances pressing volume — crucial for shoulder health. Strengthens the rhomboids and rear delts that stabilize the shoulder blade.' },
  { key: 'band row', category: 'upper pull', level: 'beginner',
    primary: 'upper back, rear delts', pattern: 'horizontal pull',
    why: 'Accessible horizontal pull without equipment. Particularly good for posture correction and counteracting forward-head position from desk work.' },
  { key: 'lat pulldown', category: 'upper pull', level: 'beginner',
    primary: 'lats, biceps', pattern: 'vertical pull',
    why: 'Machine alternative to pull-ups — infinitely scalable load. Ideal for building toward a first bodyweight pull-up.' },
  { key: 'face pull', category: 'upper pull', level: 'beginner',
    primary: 'rear delts, rhomboids', pattern: 'horizontal pull',
    why: 'Corrective movement for shoulder health. Directly trains the often-weak external rotators, preventing impingement.' },

  // ── Arms / isolation ──
  { key: 'bicep curl', category: 'arm isolation', level: 'beginner',
    primary: 'biceps', pattern: 'elbow flexion',
    why: 'Direct biceps isolation — compound pulls give baseline stimulus, but curls add targeted hypertrophy volume.' },
  { key: 'tricep extension', category: 'arm isolation', level: 'beginner',
    primary: 'triceps', pattern: 'elbow extension',
    why: 'Direct triceps work. Triceps are 2/3 of upper-arm mass — compound presses train them partially; isolation maximizes development.' },
  { key: 'lateral raise', category: 'arm isolation', level: 'beginner',
    primary: 'side delts', pattern: 'shoulder abduction',
    why: 'Side deltoid isolation — the only exercise that effectively targets lateral deltoid head for that wide-shouldered look.' },

  // ── Core ──
  { key: 'plank', category: 'core', level: 'beginner',
    primary: 'core, obliques', pattern: 'anti-extension',
    why: 'Anti-extension isometric — trains core to resist spinal extension. Safer than sit-ups; transfers directly to heavy compound lifts.' },
  { key: 'dead bug', category: 'core', level: 'beginner',
    primary: 'deep core', pattern: 'anti-extension',
    why: 'Teaches core bracing with limb movement. Excellent for lower-back rehabilitation and beginner core strength.' },
  { key: 'bird dog', category: 'core', level: 'beginner',
    primary: 'core, glutes, back', pattern: 'anti-rotation',
    why: 'Trains spinal stability with contralateral limb movement. Recommended by McGill for lower-back health.' },
  { key: 'pallof press', category: 'core', level: 'intermediate',
    primary: 'obliques, core', pattern: 'anti-rotation',
    why: 'Anti-rotation core work — often neglected but critical for athletic performance and back health.' },

  // ── Cardio ──
  { key: 'walk', category: 'cardio', level: 'beginner',
    primary: 'cardiovascular', pattern: 'steady-state',
    why: 'Low-impact cardiovascular stimulus. Burns calories without interfering with strength training recovery.' },
  { key: 'jog', category: 'cardio', level: 'beginner',
    primary: 'cardiovascular', pattern: 'steady-state',
    why: 'Builds aerobic base. Requires healthy knees and ankles; alternate with low-impact options if joint issues present.' },
  { key: 'cycling', category: 'cardio', level: 'beginner',
    primary: 'cardiovascular, quads', pattern: 'steady-state',
    why: 'Zero-impact cardio — ideal for users with knee or ankle issues. Cadence-based intensity control.' },
  { key: 'swimming', category: 'cardio', level: 'beginner',
    primary: 'cardiovascular, full body', pattern: 'steady-state',
    why: 'Non-weight-bearing full-body cardio. Best option for users with joint problems or excess weight.' },
  { key: 'hiit', category: 'cardio', level: 'intermediate',
    primary: 'cardiovascular, fat oxidation', pattern: 'interval',
    why: 'Time-efficient — comparable VO₂max improvements to steady-state cardio in ~⅓ the time (Gibala et al., 2006).' },
]

/**
 * Look up reasoning for an exercise name.
 * Returns null if no match found.
 */
export function getExerciseReasoning(exerciseName) {
  if (!exerciseName) return null
  const lower = exerciseName.toLowerCase()
  for (const entry of EXERCISE_DATA) {
    if (lower.includes(entry.key)) {
      return {
        category: entry.category,
        level:    entry.level,
        primary:  entry.primary,
        pattern:  entry.pattern,
        why:      entry.why,
      }
    }
  }
  return null
}
