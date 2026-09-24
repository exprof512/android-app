package com.foodai.app.core.network

import com.google.common.truth.Truth.assertThat
import kotlinx.serialization.json.Json
import org.junit.Test

class Phase19ModelsTest {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
    }

    @Test
    fun mealPlanParsesDayProgressAndWeekSummary() {
        val raw = """
            {
              "id": "11111111-1111-1111-1111-111111111111",
              "start_date": "2026-09-22",
              "end_date": "2026-09-28",
              "status": "ready",
              "daily_targets": {
                "calories_kcal": 1800,
                "protein_g": 120,
                "fat_g": 60,
                "carbohydrate_g": 180
              },
              "items": [],
              "day_progress": {
                "consumed_kcal": 400,
                "target_kcal": 1800,
                "remaining_kcal": 1400,
                "over_target_kcal": 0,
                "planned_remaining_kcal": 900,
                "from_plan_kcal": 400,
                "from_diary_kcal": 0,
                "protein": {"consumed_g": 20, "target_g": 120, "remaining_g": 100},
                "fat": {"consumed_g": 10, "target_g": 60, "remaining_g": 50},
                "carbs": {"consumed_g": 40, "target_g": 180, "remaining_g": 140},
                "completed_meals": 1,
                "planned_meals": 3,
                "skipped_meals": 0,
                "next_meal_item_id": "22222222-2222-2222-2222-222222222222",
                "next_meal_type": "lunch",
                "suggestions": ["Добавь белок"],
                "daily_estimated_cost_amount": 450.5
              },
              "week_summary": {
                "days": [
                  {
                    "date": "2026-09-22",
                    "status": "planned",
                    "calories_kcal": 1700,
                    "protein_g": 110,
                    "completed_meals": 1,
                    "planned_meals": 3,
                    "estimated_cost_amount": 400
                  }
                ]
              }
            }
        """.trimIndent()

        val plan = json.decodeFromString(MealPlanDto.serializer(), raw)
        assertThat(plan.dayProgress).isNotNull()
        assertThat(plan.dayProgress!!.remainingKcal).isEqualTo(1400)
        assertThat(plan.dayProgress!!.overTargetKcal).isEqualTo(0)
        assertThat(plan.dayProgress!!.plannedRemainingKcal).isEqualTo(900)
        assertThat(plan.dayProgress!!.fromPlanKcal).isEqualTo(400)
        assertThat(plan.dayProgress!!.protein.remainingG).isEqualTo(100.0)
        assertThat(plan.dayProgress!!.suggestions).containsExactly("Добавь белок")
        assertThat(plan.dayProgress!!.dailyEstimatedCostAmount).isEqualTo(450.5)
        assertThat(plan.weekSummary!!.days).hasSize(1)
        assertThat(plan.weekSummary!!.days.first().status).isEqualTo("planned")
    }

    @Test
    fun shoppingListParsesStaleAndCategory() {
        val raw = """
            {
              "id": "33333333-3333-3333-3333-333333333333",
              "meal_plan_id": "11111111-1111-1111-1111-111111111111",
              "from_date": "2026-09-22",
              "to_date": "2026-09-28",
              "status": "ready",
              "estimated_total_amount": 1200,
              "currency": "RUB",
              "stale": true,
              "plan_fingerprint": "abc",
              "items": [
                {
                  "id": "44444444-4444-4444-4444-444444444444",
                  "display_name": "Молоко",
                  "quantity_value": 1,
                  "unit": "l",
                  "is_completed": false,
                  "source_recipe_count": 1,
                  "category": "dairy"
                }
              ]
            }
        """.trimIndent()
        val list = json.decodeFromString(ShoppingListDto.serializer(), raw)
        assertThat(list.stale).isTrue()
        assertThat(list.estimatedTotalAmount).isEqualTo(1200.0)
        assertThat(list.items.first().category).isEqualTo("dairy")
    }

    @Test
    fun progressSummaryParsesSeriesAndPeriod() {
        val raw = """
            {
              "current_weight_kg": 70,
              "series": [
                {"date": "2026-09-20", "consumed_kcal": 1500, "protein_g": 90, "completed_meals": 2, "weight_kg": 70.2},
                {"date": "2026-09-21", "consumed_kcal": 1600, "protein_g": 95, "completed_meals": 3, "weight_kg": 70.0}
              ],
              "period_days": 7,
              "disclaimer": "test"
            }
        """.trimIndent()
        val summary = json.decodeFromString(ProgressSummaryDto.serializer(), raw)
        assertThat(summary.periodDays).isEqualTo(7)
        assertThat(summary.series).hasSize(2)
        assertThat(summary.series.first().consumedKcal).isEqualTo(1500)
    }

    @Test
    fun replaceRequestSerializesReason() {
        val encoded = json.encodeToString(
            MealPlanReplaceRequest.serializer(),
            MealPlanReplaceRequest(replaceReason = "more_protein"),
        )
        assertThat(encoded).contains("more_protein")
        assertThat(encoded).contains("replace_reason")
    }
}
