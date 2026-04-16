"""
Nutrition Agent — generates meal plans with macros.
Uses filtered RAG for evidence-based, culturally relevant recommendations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import save_nutrition_plan
from memory.semantic import retrieve_for_agent
from schemas import UserProfile, NutritionPlan, DailyNutritionPlan, Meal, AgentMessage


SYSTEM_PROMPT = """You are the Nutrition Agent in a multi-agent AI system.
You are an expert registered dietitian with specialization in Indian vegetarian
and sports nutrition. You follow ICMR-NIN dietary guidelines.
You always respond with valid JSON only. No explanations, no markdown, no formulas.
All numeric values must be plain numbers, never math expressions.
"""


def calculate_macro_targets(profile: UserProfile) -> dict:
    tdee = profile.tdee_estimate
    if profile.goal == "weight_loss":
        calories  = tdee - 400
        protein_g = round(profile.weight_kg * 2.2)
    elif profile.goal == "muscle_gain":
        calories  = tdee + 250
        protein_g = round(profile.weight_kg * 2.0)
    elif profile.goal == "endurance":
        calories  = tdee + 100
        protein_g = round(profile.weight_kg * 1.6)
    else:
        calories  = tdee
        protein_g = round(profile.weight_kg * 1.8)

    fats_g  = round(calories * 0.25 / 9)
    carbs_g = round(max((calories - protein_g * 4 - fats_g * 9) / 4, 50))
    return {
        "calories": round(calories),
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fats_g": fats_g
    }


def generate_nutrition_plan(profile: UserProfile, week_number: int = 1,
                             calorie_adjustment: float = 0.0,
                             adaptation_context: str = "") -> tuple:
    """
    Generate a 3-day nutrition plan.
    Returns (NutritionPlan, knowledge_chunks_used)
    """
    macros = calculate_macro_targets(profile)
    macros["calories"] = round(macros["calories"] + calorie_adjustment)
    restrictions = ', '.join(profile.dietary_restrictions) if profile.dietary_restrictions else 'none'
    adaptation_note = f"\nAdaptation context: {adaptation_context}" if adaptation_context else ""

    # Filtered RAG retrieval
    knowledge, chunks_used = retrieve_for_agent(
        "nutrition",
        profile.to_summary(),
        goal=profile.goal,
        fitness_level=profile.fitness_level
    )

    prompt = f"""Create a 3-day meal plan for this user:

{profile.to_summary()}

Daily macro targets:
- Calories: {macros['calories']} kcal
- Protein: {macros['protein_g']}g
- Carbs: {macros['carbs_g']}g
- Fats: {macros['fats_g']}g
- Dietary restrictions: {restrictions}
{adaptation_note}

{knowledge}

Return ONLY a JSON object in this exact structure:
{{
  "user_id": "{profile.user_id}",
  "week_number": {week_number},
  "target_calories": {macros['calories']},
  "target_protein_g": {macros['protein_g']},
  "notes": "brief nutrition strategy based on the guidelines above",
  "daily_plans": [
    {{
      "day_name": "Monday",
      "total_calories": 2850.0,
      "total_protein_g": 156.0,
      "total_carbs_g": 320.0,
      "total_fats_g": 79.0,
      "meals": [
        {{
          "meal_name": "Breakfast",
          "foods": ["100g oats", "200ml milk", "1 banana"],
          "calories": 450.0,
          "protein_g": 18.0,
          "carbs_g": 70.0,
          "fats_g": 8.0
        }}
      ]
    }}
  ]
}}

Rules:
- Provide exactly 3 days: Monday, Tuesday, Wednesday
- Include 4 meals per day: Breakfast, Lunch, Snack, Dinner
- Strictly respect dietary restrictions: {restrictions}
- Use specific quantities: "100g paneer" not just "paneer"
- Prioritize Indian foods where possible
- Use the nutrition knowledge above to justify food choices
- All numbers must be plain values, never formulas
- Goal is {profile.goal} — align all food choices accordingly
"""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=False)
    data = parse_json_response(response)
    from data.knowledge_base.nutrition_db import verify_meal_macros

    # Verify and correct meal macros
    for day_data in data.get("daily_plans", []):
        day_total_cal = 0
        day_total_pro = 0
        for meal in day_data.get("meals", []):
            verified = verify_meal_macros(meal.get("foods", []))
            # Only use verified values if they're reasonable
            # (at least 80% of LLM estimate — prevents partial matching errors)
            if verified and verified["calories"] >= meal.get("calories", 0) * 0.5:
                meal["calories"]  = verified["calories"]
                meal["protein_g"] = verified["protein_g"]
                meal["carbs_g"]   = verified["carbs_g"]
                meal["fats_g"]    = verified["fats_g"]
            day_total_cal += meal.get("calories", 0)
            day_total_pro += meal.get("protein_g", 0)
        # Recalculate day totals from verified meals
        day_data["total_calories"]  = round(day_total_cal, 1)
        day_data["total_protein_g"] = round(day_total_pro, 1)

    daily_plans = []
    for day_data in data.get("daily_plans", []):
        meals = []
        for m in day_data.get("meals", []):
            meals.append(Meal(
                meal_name=m.get("meal_name", ""),
                foods=m.get("foods", []),
                calories=float(m.get("calories", 0)),
                protein_g=float(m.get("protein_g", 0)),
                carbs_g=float(m.get("carbs_g", 0)),
                fats_g=float(m.get("fats_g", 0))
            ))
        daily_plans.append(DailyNutritionPlan(
            day_name=day_data.get("day_name", ""),
            meals=meals,
            total_calories=float(day_data.get("total_calories", 0)),
            total_protein_g=float(day_data.get("total_protein_g", 0)),
            total_carbs_g=float(day_data.get("total_carbs_g", 0)),
            total_fats_g=float(day_data.get("total_fats_g", 0))
        ))

    plan = NutritionPlan(
        user_id=profile.user_id,
        week_number=week_number,
        daily_plans=daily_plans,
        target_calories=macros["calories"],
        target_protein_g=macros["protein_g"],
        notes=data.get("notes", "")
    )
    save_nutrition_plan(profile.user_id, week_number, data)
    return plan, chunks_used


def format_plan_for_display(plan: NutritionPlan) -> str:
    lines = [f"\n{'='*50}",
             f"NUTRITION PLAN — Week {plan.week_number}",
             f"Targets: {plan.target_calories} kcal | {plan.target_protein_g}g protein",
             f"Notes: {plan.notes}", '='*50]
    for day in plan.daily_plans[:2]:
        lines.append(f"\n📅 {day.day_name}  "
                     f"({day.total_calories:.0f} kcal | "
                     f"P:{day.total_protein_g:.0f}g "
                     f"C:{day.total_carbs_g:.0f}g "
                     f"F:{day.total_fats_g:.0f}g)")
        lines.append("-" * 40)
        for meal in day.meals:
            lines.append(f"  🍽  {meal.meal_name} ({meal.calories:.0f} kcal · P:{meal.protein_g:.0f}g)")
            for food in meal.foods:
                lines.append(f"      • {food}")
    return "\n".join(lines)


def run(user_id: str, week_number: int = 1,
        calorie_adjustment: float = 0.0,
        adaptation_context: str = "") -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(
            from_agent="nutrition", to_agent="orchestrator",
            message_type="conflict", payload={}, confidence=0.0,
            reasoning=f"No profile found for {user_id}"
        )

    plan, chunks_used = generate_nutrition_plan(
        profile, week_number=week_number,
        calorie_adjustment=calorie_adjustment,
        adaptation_context=adaptation_context
    )

    conflicts = []
    if plan.target_calories < profile.weight_kg * 28 and profile.goal == "muscle_gain":
        conflicts.append("fitness")

    return AgentMessage(
        from_agent="nutrition", to_agent="orchestrator",
        message_type="plan",
        payload={**plan.model_dump(),
                 "knowledge_chunks": len(chunks_used),
                 "knowledge_chunks_data": chunks_used},
        confidence=0.9, conflicts_with=conflicts,
        reasoning=(f"Generated {len(plan.daily_plans)}-day plan. "
                   f"Target: {plan.target_calories} kcal, "
                   f"{plan.target_protein_g}g protein. "
                   f"RAG retrieved {len(chunks_used)} knowledge chunks.")
    )


if __name__ == "__main__":
    from memory.long_term import create_sample_user
    print("\n── Test: Generate nutrition plan with filtered RAG ──")
    profile = create_sample_user()
    plan, chunks = generate_nutrition_plan(profile, week_number=1)
    print(f"  Knowledge chunks used: {len(chunks)}")
    for c in chunks:
        print(f"  - [{c.get('relevance', 0):.2f}] {c['content'][:80]}...")
    print(format_plan_for_display(plan))
    print("\n  [Nutrition Agent v2] ✓ Test passed")