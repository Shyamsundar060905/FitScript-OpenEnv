"""
Nutrition Agent v2.

Changes from v1:
  - Uses proper food resolver (no substring bugs).
  - Reports `coverage` — fraction of foods verified against IFCT/USDA.
  - Verified macros override LLM estimates only when coverage is high.
  - Sanitizes adaptation_context.
  - Observability metrics include coverage, sources cited.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from llm.router import llm_call, parse_json_response
from memory.long_term import load_profile
from memory.episodic import save_nutrition_plan
from memory.semantic import retrieve_for_agent
from schemas import (
    UserProfile, NutritionPlan, DailyNutritionPlan, Meal, AgentMessage,
)
from utils.observability import agent_span
from utils.sanitize import sanitize_user_text
from data.knowledge_base.nutrition_db import verify_meal_macros


SYSTEM_PROMPT = """You are the Nutrition Agent in a multi-agent AI system.
You are a registered dietitian specialized in Indian vegetarian and sports
nutrition following ICMR-NIN dietary guidelines. Respond with valid JSON only.
All numeric values must be plain numbers.
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
        "fats_g": fats_g,
    }


def generate_nutrition_plan(
    profile: UserProfile,
    week_number: int = 1,
    calorie_adjustment: float = 0.0,
    adaptation_context: str = "",
) -> tuple[NutritionPlan, list, dict]:
    """
    Generate a 3-day nutrition plan.
    Returns (NutritionPlan, knowledge_chunks_used, verification_summary).
    """
    macros = calculate_macro_targets(profile)
    macros["calories"] = round(macros["calories"] + calorie_adjustment)
    restrictions = ', '.join(profile.dietary_restrictions) if profile.dietary_restrictions else 'none'
    safe_context = sanitize_user_text(adaptation_context, max_length=600)
    adaptation_note = f"\nAdaptation context: {safe_context}" if safe_context else ""

    knowledge, chunks_used = retrieve_for_agent(
        "nutrition",
        profile.to_summary(),
        goal=profile.goal,
        fitness_level=profile.fitness_level,
    )

    prompt = f"""Create a 3-day meal plan:

{profile.to_summary()}

Daily macro targets:
- Calories: {macros['calories']} kcal
- Protein: {macros['protein_g']}g
- Carbs: {macros['carbs_g']}g
- Fats: {macros['fats_g']}g
- Dietary restrictions: {restrictions}
{adaptation_note}

{knowledge}

Return ONLY a JSON object:
{{
  "user_id": "{profile.user_id}",
  "week_number": {week_number},
  "target_calories": {macros['calories']},
  "target_protein_g": {macros['protein_g']},
  "notes": "brief strategy",
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
- Use specific quantities: "100g paneer" or "1 cup milk" not just "paneer"
- Use these food names when possible: rajma, chana, chole, moong dal,
  masoor dal, toor dal, paneer, curd, milk, soya chunks, tofu,
  brown rice, white rice, oats, roti, spinach, banana, peanut butter,
  almonds, eggs, hung curd — they map to verified macros.
- Strictly respect dietary restrictions: {restrictions}
- Align all food choices with goal: {profile.goal}
"""

    response = llm_call(SYSTEM_PROMPT, prompt, json_mode=True)
    data = parse_json_response(response)

    # ── Verification pass ────────────────────────────────────────────────────
    # Track aggregate coverage across all meals for observability.
    total_verified = 0
    total_items = 0
    all_sources: set[str] = set()

    for day_data in data.get("daily_plans", []):
        day_total_cal = 0
        day_total_pro = 0
        day_total_carb = 0
        day_total_fat = 0

        for meal in day_data.get("meals", []):
            foods = meal.get("foods", [])
            verified = verify_meal_macros(foods, allow_fuzzy=True)
            total_items += len(foods)
            total_verified += len(verified["verified_items"])
            all_sources.update(verified["sources"])

            # If verification covered at least 60% of items, trust the
            # verified numbers. Otherwise keep LLM estimate (some exotic
            # foods might not be in the DB and LLM's guess is our fallback).
            if verified["coverage"] >= 0.6:
                meal["calories"]  = verified["calories"]
                meal["protein_g"] = verified["protein_g"]
                meal["carbs_g"]   = verified["carbs_g"]
                meal["fats_g"]    = verified["fats_g"]
                meal["_verified"] = True
                meal["_verification_coverage"] = verified["coverage"]
                meal["_verification_sources"] = verified["sources"]
            else:
                meal["_verified"] = False
                meal["_verification_coverage"] = verified["coverage"]

            day_total_cal  += meal.get("calories", 0)
            day_total_pro  += meal.get("protein_g", 0)
            day_total_carb += meal.get("carbs_g", 0)
            day_total_fat  += meal.get("fats_g", 0)

        day_data["total_calories"]  = round(day_total_cal, 1)
        day_data["total_protein_g"] = round(day_total_pro, 1)
        day_data["total_carbs_g"]   = round(day_total_carb, 1)
        day_data["total_fats_g"]    = round(day_total_fat, 1)

    verification_summary = {
        "total_food_items": total_items,
        "verified_items": total_verified,
        "overall_coverage": round(total_verified / total_items, 2) if total_items else 0,
        "sources_cited": sorted(all_sources),
    }

    # ── Build schema objects ─────────────────────────────────────────────────
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
                fats_g=float(m.get("fats_g", 0)),
            ))
        daily_plans.append(DailyNutritionPlan(
            day_name=day_data.get("day_name", ""),
            meals=meals,
            total_calories=float(day_data.get("total_calories", 0)),
            total_protein_g=float(day_data.get("total_protein_g", 0)),
            total_carbs_g=float(day_data.get("total_carbs_g", 0)),
            total_fats_g=float(day_data.get("total_fats_g", 0)),
        ))

    plan = NutritionPlan(
        user_id=profile.user_id,
        week_number=week_number,
        daily_plans=daily_plans,
        target_calories=macros["calories"],
        target_protein_g=macros["protein_g"],
        notes=data.get("notes", ""),
    )
    save_nutrition_plan(profile.user_id, week_number, data)
    return plan, chunks_used, verification_summary


def run(user_id: str, week_number: int = 1,
        calorie_adjustment: float = 0.0,
        adaptation_context: str = "") -> AgentMessage:
    profile = load_profile(user_id)
    if not profile:
        return AgentMessage(
            from_agent="nutrition", to_agent="orchestrator",
            message_type="conflict", payload={}, confidence=0.0,
            reasoning=f"No profile found for {user_id}",
        )

    with agent_span("nutrition", user_id, metadata={"week": week_number}) as span:
        plan, chunks_used, verification = generate_nutrition_plan(
            profile, week_number=week_number,
            calorie_adjustment=calorie_adjustment,
            adaptation_context=adaptation_context,
        )
        span["metrics"]["target_calories"] = plan.target_calories
        span["metrics"]["target_protein_g"] = plan.target_protein_g
        span["metrics"]["verification_coverage"] = verification["overall_coverage"]
        span["metrics"]["verified_items"] = verification["verified_items"]
        span["metrics"]["total_items"] = verification["total_food_items"]
        span["metrics"]["sources_cited"] = verification["sources_cited"]

    conflicts = []
    if plan.target_calories < profile.weight_kg * 28 and profile.goal == "muscle_gain":
        conflicts.append("fitness")

    return AgentMessage(
        from_agent="nutrition", to_agent="orchestrator",
        message_type="plan",
        payload={
            **plan.model_dump(),
            "knowledge_chunks": len(chunks_used),
            "knowledge_chunks_data": chunks_used,
            "verification": verification,
        },
        confidence=min(0.7 + 0.3 * verification["overall_coverage"], 0.95),
        conflicts_with=conflicts,
        reasoning=(
            f"Generated {len(plan.daily_plans)}-day plan. "
            f"Target: {plan.target_calories} kcal, {plan.target_protein_g}g protein. "
            f"Verification coverage: {verification['overall_coverage']*100:.0f}% "
            f"({verification['verified_items']}/{verification['total_food_items']} items) "
            f"cited from {verification['sources_cited']}."
        ),
    )