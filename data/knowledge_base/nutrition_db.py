"""
Verified nutrition values per 100g from ICMR-NIN dietary guidelines.
Used to validate and correct LLM-generated macro estimates.
"""

NUTRITION_DB = {
    # Legumes (cooked)
    "rajma":          {"cal": 127, "protein": 8.7,  "carbs": 22.8, "fat": 0.5},
    "chana":          {"cal": 164, "protein": 8.9,  "carbs": 27.4, "fat": 2.6},
    "moong dal":      {"cal": 105, "protein": 7.0,  "carbs": 19.0, "fat": 0.4},
    "masoor dal":     {"cal": 116, "protein": 9.0,  "carbs": 20.0, "fat": 0.4},
    "toor dal":       {"cal": 118, "protein": 6.8,  "carbs": 21.0, "fat": 0.4},
    "chole":          {"cal": 164, "protein": 8.9,  "carbs": 27.4, "fat": 2.6},

    # Dairy
    "paneer":         {"cal": 265, "protein": 18.3, "carbs": 1.2,  "fat": 20.8},
    "curd":           {"cal": 60,  "protein": 3.1,  "carbs": 4.7,  "fat": 3.3},
    "milk":           {"cal": 67,  "protein": 3.2,  "carbs": 4.4,  "fat": 4.1},
    "hung curd":      {"cal": 98,  "protein": 10.0, "carbs": 5.0,  "fat": 4.0},
    "greek yogurt":   {"cal": 59,  "protein": 10.0, "carbs": 3.6,  "fat": 0.4},

    # Soy
    "soya chunks":    {"cal": 345, "protein": 52.4, "carbs": 33.0, "fat": 0.5},
    "tofu":           {"cal": 76,  "protein": 8.0,  "carbs": 1.9,  "fat": 4.8},
    "tempeh":         {"cal": 193, "protein": 19.0, "carbs": 9.4,  "fat": 11.0},

    # Grains
    "brown rice":     {"cal": 111, "protein": 2.6,  "carbs": 23.0, "fat": 0.9},
    "white rice":     {"cal": 130, "protein": 2.7,  "carbs": 28.0, "fat": 0.3},
    "oats":           {"cal": 389, "protein": 16.9, "carbs": 66.3, "fat": 6.9},
    "quinoa":         {"cal": 120, "protein": 4.4,  "carbs": 21.3, "fat": 1.9},
    "roti":           {"cal": 71,  "protein": 2.5,  "carbs": 15.3, "fat": 0.4},
    "upma":           {"cal": 170, "protein": 3.5,  "carbs": 28.0, "fat": 5.0},
    "poha":           {"cal": 76,  "protein": 1.5,  "carbs": 17.0, "fat": 0.4},

    # Vegetables
    "spinach":        {"cal": 23,  "protein": 2.9,  "carbs": 3.6,  "fat": 0.4},
    "broccoli":       {"cal": 34,  "protein": 2.8,  "carbs": 6.6,  "fat": 0.4},
    "mixed vegetables":{"cal": 65, "protein": 2.5,  "carbs": 13.0, "fat": 0.3},

    # Fruits
    "banana":         {"cal": 89,  "protein": 1.1,  "carbs": 23.0, "fat": 0.3},
    "apple":          {"cal": 52,  "protein": 0.3,  "carbs": 14.0, "fat": 0.2},
    "fruits":         {"cal": 60,  "protein": 0.8,  "carbs": 15.0, "fat": 0.2},

    # Nuts and fats
    "peanut butter":  {"cal": 588, "protein": 25.0, "carbs": 20.0, "fat": 50.0},
    "almonds":        {"cal": 579, "protein": 21.0, "carbs": 22.0, "fat": 50.0},
    "olive oil":      {"cal": 884, "protein": 0.0,  "carbs": 0.0,  "fat": 100.0},

    # Protein sources
    "eggs":           {"cal": 143, "protein": 12.6, "carbs": 0.7,  "fat": 9.5},
    "chicken breast": {"cal": 165, "protein": 31.0, "carbs": 0.0,  "fat": 3.6},
}


def lookup_nutrition(food_item: str, grams: float = 100) -> dict:
    """
    Look up nutrition for a food item.
    Returns macros scaled to the given weight.
    """
    food_lower = food_item.lower().strip()

    # Try exact match first
    for key, values in NUTRITION_DB.items():
        if key in food_lower:
            scale = grams / 100
            return {
                "calories":  round(values["cal"]     * scale, 1),
                "protein_g": round(values["protein"] * scale, 1),
                "carbs_g":   round(values["carbs"]   * scale, 1),
                "fats_g":    round(values["fat"]      * scale, 1),
                "source": "ICMR-NIN verified"
            }
    return None


def parse_food_item(food_str: str) -> tuple[float, str]:
    """
    Parse '100g rajma' into (100.0, 'rajma').
    Returns (None, food_str) if can't parse weight.
    """
    import re
    # Match patterns like "100g", "200ml", "2 rotis", "1 banana"
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:g|ml|gm)?\s+(.+)$',
                     food_str.strip(), re.IGNORECASE)
    if match:
        return float(match.group(1)), match.group(2).strip()

    # Count items like "2 eggs", "1 banana"
    match = re.match(r'^(\d+)\s+(.+)$', food_str.strip())
    if match:
        count = float(match.group(1))
        food  = match.group(2).strip()
        # Estimate weight per unit
        unit_weights = {
            "egg": 60, "banana": 120, "apple": 182,
            "roti": 40, "glass milk": 240, "cup": 240
        }
        for item, weight in unit_weights.items():
            if item in food.lower():
                return count * weight, food
        return count * 100, food  # default 100g per unit

    return None, food_str


def verify_meal_macros(foods: list) -> dict | None:
    """
    Calculate verified macros for a list of food items.
    Returns None if foods can't be parsed.
    """
    total = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fats_g": 0}
    verified_count = 0

    for food in foods:
        grams, food_name = parse_food_item(food)
        if grams is None:
            continue
        nutrition = lookup_nutrition(food_name, grams)
        if nutrition:
            total["calories"]  += nutrition["calories"]
            total["protein_g"] += nutrition["protein_g"]
            total["carbs_g"]   += nutrition["carbs_g"]
            total["fats_g"]    += nutrition["fats_g"]
            verified_count += 1

    if verified_count == 0:
        return None

    return {k: round(v, 1) for k, v in total.items()}