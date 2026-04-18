"""
Food Resolver — canonical name resolution with word-boundary matching.

Fixes the substring matching bug where "chana" matched "chole" and "milk"
matched "milkshake". Uses:
  - Canonical names with explicit aliases
  - Word-boundary regex (won't match inside other words)
  - Longest-match-wins priority (so "coconut milk" beats "milk")
  - Optional fuzzy fallback for typos

Any new food added to NUTRITION_DB should also be added here with its aliases.
"""

import re
from typing import Optional
from difflib import get_close_matches


# Canonical food definitions with aliases.
# Key = canonical name used in nutrition_db.
# Aliases = other terms users or LLM outputs might write.
FOOD_ALIASES: dict[str, list[str]] = {
    # Legumes
    "rajma":          ["rajma", "kidney beans", "red kidney beans"],
    "chana":          ["chana", "chickpeas cooked", "kabuli chana", "boiled chana"],
    "chole":          ["chole", "chickpeas curry", "chana masala"],
    "moong dal":      ["moong dal", "mung dal", "green gram dal", "yellow moong"],
    "masoor dal":     ["masoor dal", "red lentils", "red lentil"],
    "toor dal":       ["toor dal", "arhar dal", "pigeon pea", "tuvar dal"],
    "urad dal":       ["urad dal", "black gram dal", "split urad"],

    # Dairy — order matters for conflicts
    "paneer":         ["paneer", "cottage cheese indian"],
    "greek yogurt":   ["greek yogurt", "greek yoghurt"],
    "hung curd":      ["hung curd", "strained curd", "chakka"],
    "curd":           ["curd", "dahi", "yogurt", "yoghurt", "plain yogurt"],
    "milk":           ["milk", "cow milk", "whole milk", "toned milk", "full fat milk"],
    "skim milk":      ["skim milk", "skimmed milk", "double toned milk"],
    "coconut milk":   ["coconut milk", "nariyal doodh"],
    "almond milk":    ["almond milk"],
    "soy milk":       ["soy milk", "soya milk"],

    # Soy
    "soya chunks":    ["soya chunks", "soy chunks", "nutrela", "soya nuggets", "meal maker"],
    "tofu":           ["tofu", "bean curd", "soy paneer"],
    "tempeh":         ["tempeh"],

    # Grains
    "brown rice":     ["brown rice", "whole grain rice"],
    "white rice":     ["white rice", "steamed rice", "basmati rice", "jasmine rice"],
    "oats":           ["oats", "rolled oats", "oatmeal"],
    "quinoa":         ["quinoa"],
    "roti":           ["roti", "chapati", "phulka", "wheat roti"],
    "upma":           ["upma", "rava upma", "semolina upma"],
    "poha":           ["poha", "flattened rice", "beaten rice"],
    "ragi":           ["ragi", "finger millet", "nachni"],
    "bajra":          ["bajra", "pearl millet"],

    # Vegetables
    "spinach":        ["spinach", "palak"],
    "broccoli":       ["broccoli"],
    "mixed vegetables": ["mixed vegetables", "mixed veg", "vegetable curry"],
    "potato":         ["potato", "aloo"],
    "cauliflower":    ["cauliflower", "gobi", "phool gobi"],

    # Fruits
    "banana":         ["banana", "kela"],
    "apple":          ["apple", "seb"],
    "orange":         ["orange", "santra"],
    "fruits":         ["fruits", "mixed fruits", "fruit salad"],

    # Nuts & fats
    "peanut butter":  ["peanut butter", "pb"],
    "almonds":        ["almonds", "badam"],
    "walnuts":        ["walnuts", "akhrot"],
    "olive oil":      ["olive oil", "extra virgin olive oil"],
    "ghee":           ["ghee", "clarified butter"],

    # Protein
    "eggs":           ["eggs", "egg", "boiled egg", "scrambled egg"],
    "chicken breast": ["chicken breast", "grilled chicken", "chicken"],
    "fish":           ["fish", "rohu", "salmon", "tilapia"],
    "whey protein":   ["whey protein", "whey", "protein shake", "protein powder"],
}


# Unit conversions — how many grams one "piece" weighs.
UNIT_WEIGHTS_G = {
    "egg": 60,
    "banana": 120,
    "apple": 182,
    "orange": 130,
    "roti": 40,
    "chapati": 40,
    "phulka": 30,
    "glass milk": 240,   # 1 glass ~ 240ml ~ 240g
    "cup": 240,
    "bowl dal": 200,
    "slice bread": 30,
    "tbsp": 15,
    "tsp": 5,
}


# Precompile regex patterns for each canonical name.
# Longer aliases are matched first so "coconut milk" wins over "milk".
_COMPILED_PATTERNS: list[tuple[str, re.Pattern]] = []


def _compile_patterns():
    """Build regex patterns sorted by length descending so longest match wins."""
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS:
        return

    entries = []
    for canonical, aliases in FOOD_ALIASES.items():
        for alias in aliases:
            # \b word boundary prevents "chana" matching inside "chana masala"
            # except when the full alias "chana masala" is listed separately.
            pattern = re.compile(
                r'\b' + re.escape(alias.lower()) + r'\b',
                re.IGNORECASE
            )
            entries.append((canonical, alias, pattern))

    # Sort by alias length descending — longer matches win.
    entries.sort(key=lambda x: -len(x[1]))
    _COMPILED_PATTERNS = [(canonical, pattern) for canonical, _, pattern in entries]


def resolve_food(text: str) -> Optional[str]:
    """
    Resolve a food description to its canonical name.

    Returns canonical name or None if no match.

    Examples:
        resolve_food("chana masala")  -> "chole"  (matches longer alias first)
        resolve_food("100g rajma")    -> "rajma"
        resolve_food("milkshake")     -> None     (word boundary prevents match)
        resolve_food("coconut milk")  -> None     (no entry, won't match "milk")
    """
    if not text:
        return None

    _compile_patterns()
    text_lower = text.lower().strip()

    # Try exact pattern match
    for canonical, pattern in _COMPILED_PATTERNS:
        if pattern.search(text_lower):
            return canonical

    return None


def fuzzy_resolve_food(text: str, cutoff: float = 0.8) -> Optional[str]:
    """
    Fuzzy fallback for typos. Returns closest canonical name or None.
    Only used if exact resolve_food returns None.
    """
    if not text:
        return None

    text_clean = re.sub(r'\d+\s*(?:g|ml|gm|kg)?\s*', '', text.lower()).strip()
    all_aliases = [a for aliases in FOOD_ALIASES.values() for a in aliases]
    matches = get_close_matches(text_clean, all_aliases, n=1, cutoff=cutoff)
    if not matches:
        return None

    matched_alias = matches[0]
    for canonical, aliases in FOOD_ALIASES.items():
        if matched_alias in aliases:
            return canonical
    return None


def _strip_plural(text: str) -> str:
    """Basic plural stripping: 'rotis' -> 'roti', 'eggs' -> 'egg'."""
    # Don't strip if it would leave <3 chars
    words = text.split()
    cleaned = []
    for w in words:
        if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
            cleaned.append(w[:-1])
        else:
            cleaned.append(w)
    return ' '.join(cleaned)


def parse_quantity(text: str) -> tuple[Optional[float], str]:
    """
    Extract a weight in grams from text. Handles prefix and suffix forms.

    Returns (grams_or_None, remaining_food_text).

    Examples:
        parse_quantity("100g rajma")      -> (100.0, "rajma")
        parse_quantity("rajma 100g")      -> (100.0, "rajma")
        parse_quantity("2 eggs")          -> (120.0, "egg")
        parse_quantity("1 cup rice")      -> (240.0, "rice")
        parse_quantity("rajma curry")     -> (None, "rajma curry")
    """
    text = text.strip()

    # PREFIX pattern: "100g rajma", "200 ml milk", "1.5kg chicken"
    m = re.match(
        r'^([\d.]+)\s*(g|gm|grams?|ml|kg)\s+(.+)$',
        text, re.IGNORECASE
    )
    if m:
        qty = float(m.group(1))
        unit = m.group(2).lower()
        if unit == "kg":
            qty *= 1000
        food = _strip_plural(m.group(3).strip())
        return qty, food

    # SUFFIX pattern: "rajma 100g", "milk 250ml", "chicken 200g"
    m = re.match(
        r'^(.+?)\s+([\d.]+)\s*(g|gm|grams?|ml|kg)$',
        text, re.IGNORECASE
    )
    if m:
        food = _strip_plural(m.group(1).strip())
        qty = float(m.group(2))
        unit = m.group(3).lower()
        if unit == "kg":
            qty *= 1000
        return qty, food

    # COUNT pattern: "2 eggs", "1 banana", "3 rotis"
    m = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', text)
    if m:
        count = float(m.group(1))
        food = _strip_plural(m.group(2).strip().lower())

        # Check unit weights
        for unit_key, weight_g in UNIT_WEIGHTS_G.items():
            if unit_key in food:
                return count * weight_g, food

        # Default 100g per piece if countable but unknown
        return count * 100, food

    # No quantity found — return text unchanged
    return None, text


# Self-test
if __name__ == "__main__":
    print("── Food Resolver Tests ──\n")

    test_cases = [
        ("100g rajma",           "rajma",           100.0),
        ("200g chana masala",    "chole",           200.0),   # longer match wins
        ("1 cup milk",           "milk",            240.0),
        ("coconut milk 50ml",    "coconut milk",    50.0),    # own entry wins over milk
        ("milkshake 200ml",      None,              200.0),   # word boundary — no food match
        ("2 eggs",               "eggs",            120.0),
        ("3 rotis",              "roti",            120.0),
        ("1 glass milk",         "milk",            240.0),
        ("yogurt 150g",          "curd",            150.0),
        ("greek yogurt 100g",    "greek yogurt",    100.0),   # longer wins
        ("palak 100g",           "spinach",         100.0),
        ("50g almods",           None,              50.0),    # typo — None without fuzzy
    ]

    for inp, expected_food, expected_qty in test_cases:
        qty, food_text = parse_quantity(inp)
        resolved = resolve_food(food_text)
        ok_food = resolved == expected_food
        ok_qty = (qty is None and expected_qty is None) or \
                 (qty is not None and expected_qty is not None and abs(qty - expected_qty) < 0.1)
        mark = "✓" if (ok_food and ok_qty) else "✗"
        print(f"  {mark} '{inp}' -> food={resolved}, qty={qty}  "
              f"(expected {expected_food}, {expected_qty})")

    # Fuzzy test
    print("\n── Fuzzy matching ──")
    for typo in ["rajama", "palakk", "almods"]:
        print(f"  '{typo}' -> {fuzzy_resolve_food(typo)}")