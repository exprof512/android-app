"""Deterministic food-photography prompts from validated recipes."""

from __future__ import annotations

import hashlib

from app.recipes.models import Recipe

TEMPLATE_VERSION = "food-photo-v1"
DEFAULT_STYLE = "modern_professional_food_photography"

COOKING_METHOD_PHRASE = {
    "boil": "boiled",
    "fry": "pan-fried",
    "bake": "oven-baked",
    "stew": "gently stewed",
    "grill": "grilled",
    "steam": "steamed",
    "raw": "freshly prepared raw",
    "mixed": "carefully prepared",
}


def build_image_prompt(recipe: Recipe) -> str:
    ingredients = ", ".join(
        f"{item.display_name} ({item.quantity_g:g} g)"
        for item in recipe.ingredients[:8]
    )
    method = COOKING_METHOD_PHRASE.get(recipe.cooking_method, "prepared")
    return (
        f'Modern professional food photography of the finished dish: "{recipe.name}". '
        f"Show the actual finished meal with these key ingredients: {ingredients}. "
        f"{method}, plated as a realistic home meal for {recipe.servings} serving(s). "
        "Appetizing but truthful portion, clean thoughtful plating and suitable neutral dishware. "
        "Natural soft light, neutral uncluttered background, clean composition, high detail, "
        "realistic food texture, editorial food photography. "
        "No text, labels, logos, people, hands, brand packaging, watermarks, cartoon style, "
        "or unrelated ingredients."
    )


def prompt_hash(*, recipe_fingerprint: str, model: str, output_format: str) -> str:
    raw = "|".join(
        [TEMPLATE_VERSION, recipe_fingerprint, DEFAULT_STYLE, model, output_format]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
