"""Map common AI / colloquial ingredient names onto the seed catalog.

RecipeEngine matches AI strings to catalog keys. Models often invent close
variants (куриное филе, томаты, овсянка); aliases and soft token matching
keep meal-plan generation from failing with ``unknown_ingredient``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key

# alias canonical_key → catalog normalized_name
INGREDIENT_ALIASES: dict[str, str] = {
    "куриное филе": "куриная грудка",
    "филе курицы": "куриная грудка",
    "куриная грудь": "куриная грудка",
    "филе куриное": "куриная грудка",
    "курица": "куриная грудка",
    "грудка куриная": "куриная грудка",
    "индейка филе": "индейка",
    "филе индейки": "индейка",
    "томаты": "помидор",
    "томат": "помидор",
    "помидоры": "помидор",
    "томаты черри": "помидор",
    "черри": "помидор",
    "лук": "лук репчатый",
    "репчатый лук": "лук репчатый",
    "капуста": "капуста белокочанная",
    "овсянка": "овсяные хлопья",
    "овес": "овсяные хлопья",
    "хлопья овсяные": "овсяные хлопья",
    "овсяные хлопья геркулес": "овсяные хлопья",
    "геркулес": "овсяные хлопья",
    "йогурт": "греческий йогурт",
    "йогурт натуральный": "греческий йогурт",
    "натуральный йогурт": "греческий йогурт",
    "сыр": "сыр твердый",
    "твердый сыр": "сыр твердый",
    "масло оливковое": "оливковое масло",
    "масло подсолнечное": "подсолнечное масло",
    "масло сливочное": "сливочное масло",
    "перец": "болгарский перец",
    "перец болгарский": "болгарский перец",
    "сладкий перец": "болгарский перец",
    "вода питьевая": "вода",
    "хлеб": "хлеб цельнозерновой",
    "цельнозерновой хлеб": "хлеб цельнозерновой",
    "макароны твердых сортов": "макароны",
    "паста": "макароны",
    "рис белый": "рис",
    "рис длиннозерный": "рис",
    "грибы": "шампиньоны",
    "грибы шампиньоны": "шампиньоны",
    "цуккини": "кабачок",
    "цукини": "кабачок",
    "базилик свежий": "базилик",
    "зелень": "петрушка",
    "петрушка свежая": "петрушка",
    "укроп свежий": "укроп",
    "чеснок зубчик": "чеснок",
    "зубчик чеснока": "чеснок",
    "лимонный сок": "лимон",
    "сметана 15": "сметана",
    "сметана 20": "сметана",
    "томатная паста": "томатная паста",
    "киноа": "киноа",
    "кускус": "кускус",
    "авокадо": "авокадо",
    "соевый соус": "соевый соус",
    "нут": "нут",
    "булгур": "булгур",
    "батат": "батат",
    "сладкий картофель": "батат",
}

_STOP_TOKENS = frozenset({"и", "с", "из", "для", "на", "по", "или", "свежий", "свежие"})


def resolve_catalog_key(
    name: str, catalog: Mapping[str, Ingredient]
) -> str | None:
    """Return catalog ``normalized_name`` for an AI ingredient label, or None."""
    key = canonical_key(name)
    if not key:
        return None
    if key in catalog:
        return key

    alias = INGREDIENT_ALIASES.get(key)
    if alias is not None and alias in catalog:
        return alias

    # Partial key: alias map may use a shorter form contained in the AI string.
    for alias_key, target in INGREDIENT_ALIASES.items():
        if len(alias_key) < 4:
            continue
        if alias_key in key or key in alias_key:
            if target in catalog:
                return target

    return _fuzzy_catalog_key(key, catalog)


def _fuzzy_catalog_key(key: str, catalog: Mapping[str, Ingredient]) -> str | None:
    """Match when a catalog name is a whole-word substring of the AI name (or vice versa)."""
    candidates: list[tuple[int, str]] = []
    key_tokens = {t for t in key.split() if t not in _STOP_TOKENS and len(t) >= 3}

    for catalog_key in catalog:
        if len(catalog_key) < 3:
            continue
        if _whole_word_contains(key, catalog_key) or _whole_word_contains(
            catalog_key, key
        ):
            candidates.append((len(catalog_key), catalog_key))
            continue
        catalog_tokens = {
            t for t in catalog_key.split() if t not in _STOP_TOKENS and len(t) >= 4
        }
        shared = key_tokens & catalog_tokens
        if shared:
            candidates.append((max(len(t) for t in shared), catalog_key))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _whole_word_contains(haystack: str, needle: str) -> bool:
    if len(needle) < 4:
        return False
    return re.search(rf"(^|\s){re.escape(needle)}(\s|$)", haystack) is not None
