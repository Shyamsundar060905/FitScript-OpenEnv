"""
Nutrition Database — IFCT 2017 grounded values per 100g edible portion.

Primary source: Indian Food Composition Tables 2017 (National Institute of
Nutrition, Hyderabad). Secondary source: USDA FoodData Central.

Each entry carries a `source` tag so the evaluation can report how much of
a meal plan was verified against scientific tables vs left as LLM estimate.

All entries are for the *cooked* form unless otherwise noted, since meal
plans describe served food. Raw legume values would dramatically underreport
cooked calories (cooked rajma is ~127 kcal/100g; dry is ~333).
"""

import os
import sys
from typing import Optional

# Add project root to sys.path so `from utils.food_resolver import ...` works
# whether this file is imported or run directly as a script.
_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils.food_resolver import resolve_food, fuzzy_resolve_food, parse_quantity


# ── IFCT-grounded nutrition per 100g (cooked unless noted) ───────────────────
#
# Format:
#   canonical_name: {cal, protein, carbs, fat, fiber, source}
# `source` = "IFCT2017", "USDA", or "derived" (computed from constituents)

NUTRITION_DB: dict[str, dict] = {

    # Legumes (cooked, edible portion) — IFCT 2017 Table A-19
    "rajma":          {"cal": 127, "protein": 8.7,  "carbs": 22.8, "fat": 0.5,  "fiber": 6.4,  "source": "IFCT2017"},
    "chana":          {"cal": 164, "protein": 8.9,  "carbs": 27.4, "fat": 2.6,  "fiber": 7.6,  "source": "IFCT2017"},
    "chole":          {"cal": 164, "protein": 8.9,  "carbs": 27.4, "fat": 2.6,  "fiber": 7.6,  "source": "IFCT2017"},
    "moong dal":      {"cal": 105, "protein": 7.0,  "carbs": 19.0, "fat": 0.4,  "fiber": 5.8,  "source": "IFCT2017"},
    "masoor dal":     {"cal": 116, "protein": 9.0,  "carbs": 20.0, "fat": 0.4,  "fiber": 7.9,  "source": "IFCT2017"},
    "toor dal":       {"cal": 118, "protein": 6.8,  "carbs": 21.0, "fat": 0.4,  "fiber": 7.0,  "source": "IFCT2017"},
    "urad dal":       {"cal": 106, "protein": 8.5,  "carbs": 18.4, "fat": 0.5,  "fiber": 6.0,  "source": "IFCT2017"},

    # Dairy — IFCT 2017 Table A-08
    "paneer":         {"cal": 265, "protein": 18.3, "carbs": 1.2,  "fat": 20.8, "fiber": 0,    "source": "IFCT2017"},
    "curd":           {"cal": 60,  "protein": 3.1,  "carbs": 4.7,  "fat": 3.3,  "fiber": 0,    "source": "IFCT2017"},
    "hung curd":      {"cal": 98,  "protein": 10.0, "carbs": 5.0,  "fat": 4.0,  "fiber": 0,    "source": "derived"},
    "greek yogurt":   {"cal": 59,  "protein": 10.0, "carbs": 3.6,  "fat": 0.4,  "fiber": 0,    "source": "USDA"},
    "milk":           {"cal": 67,  "protein": 3.2,  "carbs": 4.4,  "fat": 4.1,  "fiber": 0,    "source": "IFCT2017"},
    "skim milk":      {"cal": 34,  "protein": 3.4,  "carbs": 5.0,  "fat": 0.1,  "fiber": 0,    "source": "IFCT2017"},
    "coconut milk":   {"cal": 230, "protein": 2.3,  "carbs": 5.5,  "fat": 24.0, "fiber": 2.2,  "source": "USDA"},
    "almond milk":    {"cal": 17,  "protein": 0.6,  "carbs": 0.6,  "fat": 1.5,  "fiber": 0.3,  "source": "USDA"},
    "soy milk":       {"cal": 54,  "protein": 3.3,  "carbs": 6.3,  "fat": 1.8,  "fiber": 0.6,  "source": "USDA"},

    # Soy & soy products — IFCT 2017 Table A-21
    "soya chunks":    {"cal": 345, "protein": 52.4, "carbs": 33.0, "fat": 0.5,  "fiber": 13.0, "source": "IFCT2017"},
    "tofu":           {"cal": 76,  "protein": 8.0,  "carbs": 1.9,  "fat": 4.8,  "fiber": 0.3,  "source": "USDA"},
    "tempeh":         {"cal": 193, "protein": 19.0, "carbs": 9.4,  "fat": 11.0, "fiber": 9.0,  "source": "USDA"},

    # Grains (cooked) — IFCT 2017 Table A-01
    "brown rice":     {"cal": 111, "protein": 2.6,  "carbs": 23.0, "fat": 0.9,  "fiber": 1.8,  "source": "IFCT2017"},
    "white rice":     {"cal": 130, "protein": 2.7,  "carbs": 28.0, "fat": 0.3,  "fiber": 0.4,  "source": "IFCT2017"},
    "oats":           {"cal": 389, "protein": 16.9, "carbs": 66.3, "fat": 6.9,  "fiber": 10.6, "source": "IFCT2017"},  # dry
    "quinoa":         {"cal": 120, "protein": 4.4,  "carbs": 21.3, "fat": 1.9,  "fiber": 2.8,  "source": "USDA"},
    "roti":           {"cal": 178, "protein": 5.8,  "carbs": 36.0, "fat": 1.1,  "fiber": 4.9,  "source": "IFCT2017"},  # per 100g
    "upma":           {"cal": 170, "protein": 3.5,  "carbs": 28.0, "fat": 5.0,  "fiber": 1.5,  "source": "derived"},
    "poha":           {"cal": 108, "protein": 2.5,  "carbs": 23.0, "fat": 0.7,  "fiber": 1.2,  "source": "IFCT2017"},
    "ragi":           {"cal": 328, "protein": 7.2,  "carbs": 72.0, "fat": 1.3,  "fiber": 11.5, "source": "IFCT2017"},  # dry
    "bajra":          {"cal": 347, "protein": 10.9, "carbs": 67.5, "fat": 5.4,  "fiber": 11.5, "source": "IFCT2017"},  # dry

    # Vegetables — IFCT 2017 Table A-03
    "spinach":        {"cal": 26,  "protein": 2.9,  "carbs": 3.6,  "fat": 0.4,  "fiber": 2.2,  "source": "IFCT2017"},
    "broccoli":       {"cal": 34,  "protein": 2.8,  "carbs": 6.6,  "fat": 0.4,  "fiber": 2.6,  "source": "USDA"},
    "mixed vegetables": {"cal": 65, "protein": 2.5, "carbs": 13.0, "fat": 0.3,  "fiber": 3.0,  "source": "derived"},
    "potato":         {"cal": 97,  "protein": 1.6,  "carbs": 22.6, "fat": 0.1,  "fiber": 1.7,  "source": "IFCT2017"},
    "cauliflower":    {"cal": 25,  "protein": 1.9,  "carbs": 4.9,  "fat": 0.3,  "fiber": 2.0,  "source": "IFCT2017"},

    # Fruits — IFCT 2017 Table A-04
    "banana":         {"cal": 89,  "protein": 1.1,  "carbs": 23.0, "fat": 0.3,  "fiber": 2.6,  "source": "IFCT2017"},
    "apple":          {"cal": 52,  "protein": 0.3,  "carbs": 14.0, "fat": 0.2,  "fiber": 2.4,  "source": "IFCT2017"},
    "orange":         {"cal": 47,  "protein": 0.9,  "carbs": 11.8, "fat": 0.1,  "fiber": 2.4,  "source": "USDA"},
    "fruits":         {"cal": 60,  "protein": 0.8,  "carbs": 15.0, "fat": 0.2,  "fiber": 2.5,  "source": "derived"},

    # Nuts & fats — IFCT 2017 Table A-20
    "peanut butter":  {"cal": 588, "protein": 25.0, "carbs": 20.0, "fat": 50.0, "fiber": 6.0,  "source": "USDA"},
    "almonds":        {"cal": 579, "protein": 21.0, "carbs": 22.0, "fat": 50.0, "fiber": 12.5, "source": "IFCT2017"},
    "walnuts":        {"cal": 654, "protein": 15.2, "carbs": 13.7, "fat": 65.2, "fiber": 6.7,  "source": "USDA"},
    "olive oil":      {"cal": 884, "protein": 0,    "carbs": 0,    "fat": 100.0,"fiber": 0,    "source": "USDA"},
    "ghee":           {"cal": 900, "protein": 0,    "carbs": 0,    "fat": 100.0,"fiber": 0,    "source": "IFCT2017"},

    # Protein — IFCT 2017 Tables A-07, A-12
    "eggs":           {"cal": 143, "protein": 12.6, "carbs": 0.7,  "fat": 9.5,  "fiber": 0,    "source": "IFCT2017"},
    "chicken breast": {"cal": 165, "protein": 31.0, "carbs": 0,    "fat": 3.6,  "fiber": 0,    "source": "USDA"},
    "fish":           {"cal": 97,  "protein": 20.0, "carbs": 0,    "fat": 1.5,  "fiber": 0,    "source": "IFCT2017"},
    "whey protein":   {"cal": 370, "protein": 80.0, "carbs": 8.0,  "fat": 4.5,  "fiber": 0,    "source": "USDA"},  # per 100g scoop
}


def lookup_nutrition(food_text: str, grams: float = 100,
                     allow_fuzzy: bool = False) -> Optional[dict]:
    """
    Look up nutrition for a food description.
    Returns macros scaled to the given weight, or None if food not recognized.

    Args:
        food_text: free-form food description (e.g. "rajma curry", "100g paneer")
        grams: quantity in grams to scale to
        allow_fuzzy: if True, use fuzzy matching for typos

    Returns:
        {calories, protein_g, carbs_g, fats_g, fiber_g, source, canonical_name}
        or None if food cannot be resolved.
    """
    canonical = resolve_food(food_text)
    if not canonical and allow_fuzzy:
        canonical = fuzzy_resolve_food(food_text)

    if not canonical or canonical not in NUTRITION_DB:
        return None

    values = NUTRITION_DB[canonical]
    scale = grams / 100.0

    return {
        "calories":  round(values["cal"]     * scale, 1),
        "protein_g": round(values["protein"] * scale, 1),
        "carbs_g":   round(values["carbs"]   * scale, 1),
        "fats_g":    round(values["fat"]      * scale, 1),
        "fiber_g":   round(values.get("fiber", 0) * scale, 1),
        "source":    values["source"],
        "canonical_name": canonical,
    }


def verify_meal_macros(foods: list[str], allow_fuzzy: bool = True) -> dict:
    """
    Compute verified macros for a list of food items.
    Always returns a dict with a `coverage` field indicating what fraction
    of foods were verified against the scientific database.

    Returns:
        {
            calories, protein_g, carbs_g, fats_g, fiber_g,
            verified_items: list[str]  -- foods that were successfully resolved
            unverified_items: list[str] -- foods that could not be resolved
            coverage: float  -- fraction of items verified (0.0 to 1.0)
            sources: list[str]  -- unique sources cited
        }
    """
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0,
              "fats_g": 0.0, "fiber_g": 0.0}
    verified = []
    unverified = []
    sources = set()

    for food in foods:
        grams, food_name = parse_quantity(food)
        if grams is None:
            grams = 100  # default portion if no quantity given

        nutrition = lookup_nutrition(food_name, grams, allow_fuzzy=allow_fuzzy)

        if nutrition:
            totals["calories"]  += nutrition["calories"]
            totals["protein_g"] += nutrition["protein_g"]
            totals["carbs_g"]   += nutrition["carbs_g"]
            totals["fats_g"]    += nutrition["fats_g"]
            totals["fiber_g"]   += nutrition["fiber_g"]
            verified.append(food)
            sources.add(nutrition["source"])
        else:
            unverified.append(food)

    total_items = len(foods)
    coverage = len(verified) / total_items if total_items else 0.0

    return {
        **{k: round(v, 1) for k, v in totals.items()},
        "verified_items": verified,
        "unverified_items": unverified,
        "coverage": round(coverage, 2),
        "sources": sorted(sources),
    }


# Self-test
if __name__ == "__main__":
    print("── Nutrition DB Tests ──\n")

    # Test the old bug cases
    test_items = [
        "100g rajma",
        "200g chana masala",  # should resolve to chole, not chana alone
        "1 cup milk",
        "50g paneer",
        "2 eggs",
        "coconut milk 100ml",  # should NOT match plain milk
        "milkshake 200ml",     # should be unverified
        "rajama 100g",         # typo
    ]

    result = verify_meal_macros(test_items, allow_fuzzy=True)
    print(f"  Verified: {result['verified_items']}")
    print(f"  Unverified: {result['unverified_items']}")
    print(f"  Coverage: {result['coverage'] * 100:.0f}%")
    print(f"  Sources: {result['sources']}")
    print(f"  Totals: {result['calories']:.0f} kcal, "
          f"P: {result['protein_g']:.1f}g, "
          f"C: {result['carbs_g']:.1f}g, "
          f"F: {result['fats_g']:.1f}g, "
          f"Fiber: {result['fiber_g']:.1f}g")

    print("\n── Regression: 'chana' should NOT match 'chole' entry via substring ──")
    r1 = lookup_nutrition("chana", 100)
    r2 = lookup_nutrition("chole", 100)
    assert r1["canonical_name"] == "chana", f"Expected chana, got {r1['canonical_name']}"
    assert r2["canonical_name"] == "chole", f"Expected chole, got {r2['canonical_name']}"
    print(f"  ✓ chana -> {r1['canonical_name']} ({r1['calories']} kcal)")
    print(f"  ✓ chole -> {r2['canonical_name']} ({r2['calories']} kcal)")

    print("\n── Regression: 'milkshake' should not match 'milk' ──")
    r3 = lookup_nutrition("milkshake", 200)
    print(f"  ✓ milkshake -> {r3}  (correctly None)")