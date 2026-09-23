"""BMR, TDEE, calorie target and macro calculation with safety guardrails.

AI may propose a dish, but every calorie and gram that FoodAI stores or shows
comes from this module.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, get_args

from app.nutrition.errors import NutritionValidationError

DISCLAIMER = "Расчёты приблизительны и не заменяют врача или диетолога."

Sex = Literal["female", "male", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "high", "very_high"]
GoalType = Literal["lose_weight", "maintain_weight", "gain_weight"]
CalorieMode = Literal["auto", "deficit", "surplus", "target"]

SEXES: tuple[str, ...] = get_args(Sex)
ACTIVITY_LEVELS: tuple[str, ...] = get_args(ActivityLevel)
GOAL_TYPES: tuple[str, ...] = get_args(GoalType)
CALORIE_MODES: tuple[str, ...] = get_args(CalorieMode)

DEFAULT_ACTIVITY_FACTORS: dict[str, Decimal] = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "high": Decimal("1.725"),
    "very_high": Decimal("1.9"),
}

# Mifflin–St Jeor sex constants; "other" uses their midpoint.
_BMR_SEX_CONSTANT: dict[str, Decimal] = {
    "male": Decimal("5"),
    "female": Decimal("-161"),
    "other": Decimal("-78"),
}

KCAL_PER_KG_BODY_MASS = Decimal("7700")
DEFAULT_MAX_WEEKLY_WEIGHT_CHANGE_KG = Decimal("2.0")
MIN_SAFE_BMI = Decimal("18.5")

PROTEIN_G_PER_KG = Decimal("1.6")
PROTEIN_KCAL_PER_G = Decimal("4")
FAT_KCAL_PER_G = Decimal("9")
CARBOHYDRATE_KCAL_PER_G = Decimal("4")
FAT_SHARE_OF_CALORIES = Decimal("0.30")
MIN_FAT_G_PER_KG = Decimal("0.6")
# Keeping protein and fat inside these shares leaves carbohydrates non-negative.
MIN_PROTEIN_SHARE = Decimal("0.10")
MAX_PROTEIN_SHARE = Decimal("0.35")
MIN_FAT_SHARE = Decimal("0.20")
MAX_FAT_SHARE = Decimal("0.35")


@dataclass(frozen=True)
class GoalRequest:
    """Anthropometrics and goal, already validated for type and range."""

    sex: str
    age_years: int
    height_cm: Decimal
    current_weight_kg: Decimal
    activity_level: str
    goal_type: str
    target_weight_kg: Decimal | None = None
    desired_weekly_change_kg: Decimal | None = None
    daily_calorie_mode: str = "auto"
    daily_calorie_value: int | None = None


@dataclass(frozen=True)
class NutrientPortion:
    """One canonical ingredient amount inside a dish."""

    grams: Decimal
    calories_per_100g: Decimal
    protein_per_100g: Decimal
    fat_per_100g: Decimal
    carbohydrate_per_100g: Decimal


@dataclass(frozen=True)
class RecipeNutrition:
    calories_kcal: int
    protein_g: Decimal
    fat_g: Decimal
    carbohydrate_g: Decimal


@dataclass(frozen=True)
class MacroTargets:
    protein_g: int
    fat_g: int
    carbohydrate_g: int


@dataclass(frozen=True)
class NutritionTargets:
    bmr_kcal: int
    tdee_kcal: int
    recommended_calorie_target_kcal: int
    applied_safety_floor_kcal: int
    macro_targets_g: MacroTargets
    warnings: list[str] = field(default_factory=list)
    policy_version: str = "v1"


def _round_int(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _round_grams(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class NutritionEngine:
    """Deterministic calculator; it never calls AI and never reads the database."""

    def __init__(
        self,
        *,
        activity_factors: dict[str, Decimal],
        min_daily_calories_female: int,
        min_daily_calories_male: int,
        max_weekly_weight_change_kg: Decimal,
        policy_version: str = "v1",
    ) -> None:
        self._activity_factors = activity_factors
        self._min_daily_calories_female = min_daily_calories_female
        self._min_daily_calories_male = min_daily_calories_male
        self._max_weekly_weight_change_kg = max_weekly_weight_change_kg
        self.policy_version = policy_version

    @classmethod
    def from_settings(cls, settings: object) -> "NutritionEngine":
        raw_factors = getattr(settings, "nutrition_activity_factors_json", "")
        max_change = getattr(settings, "nutrition_max_weekly_weight_change_kg", None)
        return cls(
            activity_factors=parse_activity_factors(raw_factors),
            min_daily_calories_female=getattr(
                settings, "nutrition_min_daily_calories_female"
            ),
            min_daily_calories_male=getattr(
                settings, "nutrition_min_daily_calories_male"
            ),
            max_weekly_weight_change_kg=(
                DEFAULT_MAX_WEEKLY_WEIGHT_CHANGE_KG
                if max_change is None
                else Decimal(str(max_change))
            ),
            policy_version=str(getattr(settings, "nutrition_policy_version", "v1")),
        )

    @property
    def max_weekly_weight_change_kg(self) -> Decimal:
        return self._max_weekly_weight_change_kg

    def safety_floor_kcal(self, sex: str) -> int:
        """Unknown or other sex uses the higher floor until a clinical review."""
        if sex == "female":
            return self._min_daily_calories_female
        if sex == "male":
            return self._min_daily_calories_male
        return max(self._min_daily_calories_female, self._min_daily_calories_male)

    def basal_metabolic_rate_kcal(self, request: GoalRequest) -> Decimal:
        return (
            Decimal("10") * request.current_weight_kg
            + Decimal("6.25") * request.height_cm
            - Decimal("5") * Decimal(request.age_years)
            + _BMR_SEX_CONSTANT[request.sex]
        )

    def calculate(self, request: GoalRequest) -> NutritionTargets:
        self._validate(request)

        bmr = self.basal_metabolic_rate_kcal(request)
        tdee = bmr * self._activity_factors[request.activity_level]
        raw_target = self._raw_target_kcal(request, tdee)

        warnings = [DISCLAIMER]
        floor = self.safety_floor_kcal(request.sex)
        target = raw_target
        if target < Decimal(floor):
            target = Decimal(floor)
            warnings.append(
                f"Целевая калорийность поднята до безопасного минимума {floor} ккал в день."
            )

        target_kcal = _round_int(target)
        return NutritionTargets(
            bmr_kcal=_round_int(bmr),
            tdee_kcal=_round_int(tdee),
            recommended_calorie_target_kcal=target_kcal,
            applied_safety_floor_kcal=floor,
            macro_targets_g=self.macro_targets(
                calories_kcal=target_kcal, weight_kg=request.current_weight_kg
            ),
            warnings=warnings,
            policy_version=self.policy_version,
        )

    def recipe_nutrition(
        self, portions: Sequence[NutrientPortion], *, servings: int = 1
    ) -> RecipeNutrition:
        """Sum canonical ingredient values; AI numbers never reach this path."""
        if servings < 1:
            raise ValueError("servings must be at least 1.")

        totals = {"calories": Decimal("0"), "protein": Decimal("0"), "fat": Decimal("0"), "carbohydrate": Decimal("0")}
        for portion in portions:
            share = portion.grams / Decimal("100")
            totals["calories"] += portion.calories_per_100g * share
            totals["protein"] += portion.protein_per_100g * share
            totals["fat"] += portion.fat_per_100g * share
            totals["carbohydrate"] += portion.carbohydrate_per_100g * share

        divisor = Decimal(servings)
        return RecipeNutrition(
            calories_kcal=_round_int(totals["calories"] / divisor),
            protein_g=_round_grams(totals["protein"] / divisor),
            fat_g=_round_grams(totals["fat"] / divisor),
            carbohydrate_g=_round_grams(totals["carbohydrate"] / divisor),
        )

    def macro_targets(self, *, calories_kcal: int, weight_kg: Decimal) -> MacroTargets:
        calories = Decimal(calories_kcal)

        protein_g = self._clamp(
            PROTEIN_G_PER_KG * weight_kg,
            minimum=calories * MIN_PROTEIN_SHARE / PROTEIN_KCAL_PER_G,
            maximum=calories * MAX_PROTEIN_SHARE / PROTEIN_KCAL_PER_G,
        )
        fat_g = self._clamp(
            max(
                calories * FAT_SHARE_OF_CALORIES / FAT_KCAL_PER_G,
                MIN_FAT_G_PER_KG * weight_kg,
            ),
            minimum=calories * MIN_FAT_SHARE / FAT_KCAL_PER_G,
            maximum=calories * MAX_FAT_SHARE / FAT_KCAL_PER_G,
        )
        remaining = (
            calories - protein_g * PROTEIN_KCAL_PER_G - fat_g * FAT_KCAL_PER_G
        )
        carbohydrate_g = max(remaining, Decimal("0")) / CARBOHYDRATE_KCAL_PER_G

        return MacroTargets(
            protein_g=_round_int(protein_g),
            fat_g=_round_int(fat_g),
            carbohydrate_g=_round_int(carbohydrate_g),
        )

    def _raw_target_kcal(self, request: GoalRequest, tdee: Decimal) -> Decimal:
        value = Decimal(request.daily_calorie_value or 0)
        if request.daily_calorie_mode == "target":
            return value
        if request.daily_calorie_mode == "deficit":
            return tdee - value
        if request.daily_calorie_mode == "surplus":
            return tdee + value
        weekly_change = request.desired_weekly_change_kg or Decimal("0")
        daily_delta = weekly_change * KCAL_PER_KG_BODY_MASS / Decimal("7")
        if request.goal_type == "lose_weight":
            return tdee - daily_delta
        if request.goal_type == "gain_weight":
            return tdee + daily_delta
        return tdee

    def _validate(self, request: GoalRequest) -> None:
        details: list[dict[str, str]] = []

        if request.sex not in SEXES:
            details.append({"field": "sex", "reason": "unsupported_value"})
        if request.activity_level not in self._activity_factors:
            details.append({"field": "activity_level", "reason": "unsupported_value"})
        if request.goal_type not in GOAL_TYPES:
            details.append({"field": "goal_type", "reason": "unsupported_value"})
        if request.daily_calorie_mode not in CALORIE_MODES:
            details.append({"field": "daily_calorie_mode", "reason": "unsupported_value"})
        if details:
            raise NutritionValidationError(details)

        details.extend(self._validate_rate(request))
        details.extend(self._validate_target_weight(request))
        details.extend(self._validate_calorie_mode(request))
        if details:
            raise NutritionValidationError(details)

    def _validate_rate(self, request: GoalRequest) -> list[dict[str, str]]:
        weekly_change = request.desired_weekly_change_kg
        if weekly_change is None:
            if request.goal_type != "maintain_weight" and request.daily_calorie_mode == "auto":
                return [{"field": "desired_weekly_change_kg", "reason": "required"}]
            return []
        if weekly_change < 0:
            return [{"field": "desired_weekly_change_kg", "reason": "must_not_be_negative"}]
        if weekly_change > self._max_weekly_weight_change_kg:
            return [
                {
                    "field": "desired_weekly_change_kg",
                    "reason": "exceeds_safe_weekly_change",
                }
            ]
        if request.goal_type == "maintain_weight" and weekly_change > 0:
            return [
                {
                    "field": "desired_weekly_change_kg",
                    "reason": "must_be_zero_for_maintain_weight",
                }
            ]
        return []

    def _validate_target_weight(self, request: GoalRequest) -> list[dict[str, str]]:
        target_weight = request.target_weight_kg
        if target_weight is None:
            return []
        if request.goal_type == "lose_weight" and target_weight >= request.current_weight_kg:
            return [{"field": "target_weight_kg", "reason": "must_be_below_current_weight"}]
        if request.goal_type == "gain_weight" and target_weight <= request.current_weight_kg:
            return [{"field": "target_weight_kg", "reason": "must_be_above_current_weight"}]

        height_m = request.height_cm / Decimal("100")
        if target_weight / (height_m * height_m) < MIN_SAFE_BMI:
            return [{"field": "target_weight_kg", "reason": "below_safe_bmi"}]
        return []

    def _validate_calorie_mode(self, request: GoalRequest) -> list[dict[str, str]]:
        mode = request.daily_calorie_mode
        value = request.daily_calorie_value
        if mode == "auto":
            return []
        if value is None or value <= 0:
            return [{"field": "daily_calorie_value", "reason": "required"}]
        if mode == "deficit" and request.goal_type == "gain_weight":
            return [{"field": "daily_calorie_mode", "reason": "inconsistent_with_goal_type"}]
        if mode == "surplus" and request.goal_type == "lose_weight":
            return [{"field": "daily_calorie_mode", "reason": "inconsistent_with_goal_type"}]
        if mode in {"deficit", "surplus"} and request.goal_type == "maintain_weight":
            return [{"field": "daily_calorie_mode", "reason": "inconsistent_with_goal_type"}]
        return []

    @staticmethod
    def _clamp(value: Decimal, *, minimum: Decimal, maximum: Decimal) -> Decimal:
        return max(minimum, min(value, maximum))


def parse_activity_factors(raw: str) -> dict[str, Decimal]:
    """Merge NUTRITION_ACTIVITY_FACTORS_JSON over the defaults, failing fast."""
    factors = dict(DEFAULT_ACTIVITY_FACTORS)
    if not raw.strip():
        return factors
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("NUTRITION_ACTIVITY_FACTORS_JSON is not valid JSON.") from error
    if not isinstance(overrides, dict):
        raise RuntimeError("NUTRITION_ACTIVITY_FACTORS_JSON must be a JSON object.")

    unknown = sorted(set(overrides) - set(factors))
    if unknown:
        raise RuntimeError(
            f"NUTRITION_ACTIVITY_FACTORS_JSON has unknown activity levels: {', '.join(unknown)}"
        )
    for level, value in overrides.items():
        try:
            factor = Decimal(str(value))
        except ArithmeticError as error:
            raise RuntimeError(
                f"NUTRITION_ACTIVITY_FACTORS_JSON has a non-numeric factor for {level}."
            ) from error
        if factor <= 0:
            raise RuntimeError(
                f"NUTRITION_ACTIVITY_FACTORS_JSON must use positive factors; {level} is not."
            )
        factors[level] = factor
    return factors
