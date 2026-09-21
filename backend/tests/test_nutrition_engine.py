from __future__ import annotations

from decimal import Decimal

import pytest

from app.nutrition.engine import (
    DEFAULT_ACTIVITY_FACTORS,
    DISCLAIMER,
    GoalRequest,
    NutritionEngine,
    parse_activity_factors,
)
from app.nutrition.errors import NutritionValidationError


def build_engine(
    *,
    min_female: int = 1200,
    min_male: int = 1500,
    max_weekly_change: str = "1.0",
    activity_factors: dict[str, Decimal] | None = None,
) -> NutritionEngine:
    return NutritionEngine(
        activity_factors=activity_factors or dict(DEFAULT_ACTIVITY_FACTORS),
        min_daily_calories_female=min_female,
        min_daily_calories_male=min_male,
        max_weekly_weight_change_kg=Decimal(max_weekly_change),
    )


def build_request(**overrides) -> GoalRequest:
    values = {
        "sex": "female",
        "age_years": 31,
        "height_cm": Decimal("168"),
        "current_weight_kg": Decimal("72.4"),
        "activity_level": "moderate",
        "goal_type": "lose_weight",
        "target_weight_kg": Decimal("64"),
        "desired_weekly_change_kg": Decimal("0.4"),
        "daily_calorie_mode": "auto",
        "daily_calorie_value": None,
    }
    values.update(overrides)
    return GoalRequest(**values)


def reasons(error: NutritionValidationError) -> dict[str, str]:
    return {detail["field"]: detail["reason"] for detail in error.details or []}


def test_documented_example_matches_the_engine() -> None:
    targets = build_engine().calculate(build_request())

    assert targets.bmr_kcal == 1458
    assert targets.tdee_kcal == 2260
    assert targets.recommended_calorie_target_kcal == 1820
    assert targets.applied_safety_floor_kcal == 1200
    assert targets.macro_targets_g.protein_g == 116
    assert targets.macro_targets_g.fat_g == 61
    assert targets.macro_targets_g.carbohydrate_g == 203
    assert targets.warnings == [DISCLAIMER]


def test_mifflin_st_jeor_uses_the_sex_constant() -> None:
    engine = build_engine()
    common = {
        "age_years": 40,
        "height_cm": Decimal("180"),
        "current_weight_kg": Decimal("80"),
        "goal_type": "maintain_weight",
        "target_weight_kg": None,
        "desired_weekly_change_kg": None,
    }

    male = engine.basal_metabolic_rate_kcal(build_request(sex="male", **common))
    female = engine.basal_metabolic_rate_kcal(build_request(sex="female", **common))
    other = engine.basal_metabolic_rate_kcal(build_request(sex="other", **common))

    assert male == Decimal("1730")
    assert female == Decimal("1564")
    assert other == Decimal("1647")


@pytest.mark.parametrize(
    ("activity_level", "expected_tdee"),
    [
        ("sedentary", 1750),
        ("light", 2005),
        ("moderate", 2260),
        ("high", 2515),
        ("very_high", 2770),
    ],
)
def test_tdee_follows_the_activity_factor(activity_level: str, expected_tdee: int) -> None:
    targets = build_engine().calculate(build_request(activity_level=activity_level))

    assert targets.tdee_kcal == expected_tdee


def test_maintain_weight_keeps_the_tdee() -> None:
    targets = build_engine().calculate(
        build_request(
            goal_type="maintain_weight",
            target_weight_kg=None,
            desired_weekly_change_kg=None,
        )
    )

    assert targets.recommended_calorie_target_kcal == targets.tdee_kcal


def test_gain_weight_adds_a_surplus() -> None:
    targets = build_engine().calculate(
        build_request(
            goal_type="gain_weight",
            target_weight_kg=Decimal("78"),
            desired_weekly_change_kg=Decimal("0.35"),
        )
    )

    assert targets.recommended_calorie_target_kcal == 2645


def test_explicit_deficit_is_applied_to_the_tdee() -> None:
    targets = build_engine().calculate(
        build_request(daily_calorie_mode="deficit", daily_calorie_value=400)
    )

    assert targets.recommended_calorie_target_kcal == targets.tdee_kcal - 400


def test_explicit_surplus_is_applied_to_the_tdee() -> None:
    targets = build_engine().calculate(
        build_request(
            goal_type="gain_weight",
            target_weight_kg=Decimal("78"),
            desired_weekly_change_kg=Decimal("0.3"),
            daily_calorie_mode="surplus",
            daily_calorie_value=300,
        )
    )

    assert targets.recommended_calorie_target_kcal == targets.tdee_kcal + 300


def test_explicit_target_is_used_as_is() -> None:
    targets = build_engine().calculate(
        build_request(daily_calorie_mode="target", daily_calorie_value=1700)
    )

    assert targets.recommended_calorie_target_kcal == 1700
    assert targets.warnings == [DISCLAIMER]


@pytest.mark.parametrize(
    ("sex", "expected_floor"),
    [("female", 1200), ("male", 1500), ("other", 1500)],
)
def test_safety_floor_depends_on_sex(sex: str, expected_floor: int) -> None:
    engine = build_engine()

    targets = engine.calculate(
        build_request(sex=sex, daily_calorie_mode="target", daily_calorie_value=900)
    )

    assert engine.safety_floor_kcal(sex) == expected_floor
    assert targets.applied_safety_floor_kcal == expected_floor
    assert targets.recommended_calorie_target_kcal == expected_floor
    assert any(str(expected_floor) in warning for warning in targets.warnings)
    assert targets.warnings[0] == DISCLAIMER


def test_target_above_the_floor_produces_no_floor_warning() -> None:
    targets = build_engine().calculate(build_request())

    assert targets.recommended_calorie_target_kcal > targets.applied_safety_floor_kcal
    assert targets.warnings == [DISCLAIMER]


def test_an_aggressive_deficit_cannot_go_below_the_floor() -> None:
    targets = build_engine().calculate(
        build_request(daily_calorie_mode="deficit", daily_calorie_value=1800)
    )

    assert targets.recommended_calorie_target_kcal == 1200


def test_weekly_change_above_the_cap_is_rejected() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(
            build_request(desired_weekly_change_kg=Decimal("1.5"))
        )

    assert error.value.status_code == 422
    assert error.value.code == "nutrition_validation_error"
    assert reasons(error.value) == {
        "desired_weekly_change_kg": "exceeds_safe_weekly_change"
    }


def test_the_weekly_change_cap_is_configurable() -> None:
    targets = build_engine(max_weekly_change="1.5").calculate(
        build_request(desired_weekly_change_kg=Decimal("1.5"))
    )

    assert targets.recommended_calorie_target_kcal == 1200


def test_negative_weekly_change_is_rejected() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(
            build_request(desired_weekly_change_kg=Decimal("-0.2"))
        )

    assert reasons(error.value) == {
        "desired_weekly_change_kg": "must_not_be_negative"
    }


def test_maintain_weight_rejects_a_weekly_change() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(
            build_request(
                goal_type="maintain_weight",
                target_weight_kg=None,
                desired_weekly_change_kg=Decimal("0.3"),
            )
        )

    assert reasons(error.value) == {
        "desired_weekly_change_kg": "must_be_zero_for_maintain_weight"
    }


def test_auto_mode_requires_a_pace_for_a_weight_change_goal() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(build_request(desired_weekly_change_kg=None))

    assert reasons(error.value) == {"desired_weekly_change_kg": "required"}


def test_target_weight_must_match_the_goal_direction() -> None:
    engine = build_engine()

    with pytest.raises(NutritionValidationError) as losing:
        engine.calculate(build_request(target_weight_kg=Decimal("80")))
    with pytest.raises(NutritionValidationError) as gaining:
        engine.calculate(
            build_request(
                goal_type="gain_weight",
                target_weight_kg=Decimal("70"),
                desired_weekly_change_kg=Decimal("0.3"),
            )
        )

    assert reasons(losing.value) == {
        "target_weight_kg": "must_be_below_current_weight"
    }
    assert reasons(gaining.value) == {
        "target_weight_kg": "must_be_above_current_weight"
    }


def test_target_weight_below_a_safe_bmi_is_rejected() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(build_request(target_weight_kg=Decimal("48")))

    assert reasons(error.value) == {"target_weight_kg": "below_safe_bmi"}


def test_explicit_calorie_modes_require_a_value() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(build_request(daily_calorie_mode="deficit"))

    assert reasons(error.value) == {"daily_calorie_value": "required"}


@pytest.mark.parametrize(
    ("goal_type", "mode"),
    [
        ("lose_weight", "surplus"),
        ("gain_weight", "deficit"),
        ("maintain_weight", "deficit"),
    ],
)
def test_calorie_mode_must_match_the_goal(goal_type: str, mode: str) -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(
            build_request(
                goal_type=goal_type,
                target_weight_kg=None,
                desired_weekly_change_kg=None,
                daily_calorie_mode=mode,
                daily_calorie_value=300,
            )
        )

    assert reasons(error.value) == {
        "daily_calorie_mode": "inconsistent_with_goal_type"
    }


def test_unsupported_enumerations_are_reported_together() -> None:
    with pytest.raises(NutritionValidationError) as error:
        build_engine().calculate(
            build_request(sex="unknown", activity_level="extreme")
        )

    assert reasons(error.value) == {
        "sex": "unsupported_value",
        "activity_level": "unsupported_value",
    }


@pytest.mark.parametrize(
    ("calories", "weight"),
    [(1200, "120"), (1500, "45"), (2500, "80"), (4000, "60")],
)
def test_macro_targets_stay_within_the_calorie_budget(calories: int, weight: str) -> None:
    macros = build_engine().macro_targets(
        calories_kcal=calories, weight_kg=Decimal(weight)
    )

    macro_calories = (
        macros.protein_g * 4 + macros.fat_g * 9 + macros.carbohydrate_g * 4
    )
    assert macros.protein_g > 0
    assert macros.fat_g > 0
    assert macros.carbohydrate_g >= 0
    assert abs(macro_calories - calories) <= 20


def test_protein_is_capped_for_a_heavy_user_on_a_low_target() -> None:
    macros = build_engine().macro_targets(calories_kcal=1200, weight_kg=Decimal("120"))

    assert macros.protein_g == 105
    assert macros.carbohydrate_g >= 0


def test_activity_factors_default_when_unset() -> None:
    assert parse_activity_factors("") == DEFAULT_ACTIVITY_FACTORS
    assert parse_activity_factors("   ") == DEFAULT_ACTIVITY_FACTORS


def test_activity_factors_merge_over_the_defaults() -> None:
    factors = parse_activity_factors('{"moderate": 1.6}')

    assert factors["moderate"] == Decimal("1.6")
    assert factors["sedentary"] == DEFAULT_ACTIVITY_FACTORS["sedentary"]


def test_overridden_activity_factor_changes_the_tdee() -> None:
    engine = build_engine(activity_factors=parse_activity_factors('{"moderate": 2}'))

    targets = engine.calculate(build_request())

    assert targets.tdee_kcal == 2916


@pytest.mark.parametrize(
    "raw",
    ['{"moderate": 1.6', "[]", '{"unknown_level": 1.2}', '{"moderate": 0}', '{"moderate": "x"}'],
)
def test_invalid_activity_factors_fail_fast(raw: str) -> None:
    with pytest.raises(RuntimeError):
        parse_activity_factors(raw)
