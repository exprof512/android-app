package com.foodai.app.core.network

import com.google.common.truth.Truth.assertThat
import kotlinx.serialization.json.Json
import org.junit.Test

class Phase20AiModelsTest {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
    }

    @Test
    fun recommendationsDtoParsesCandidates() {
        val raw = """
            {
              "recommendation_id": "11111111-1111-1111-1111-111111111111",
              "operation": "food_suggestion",
              "candidates": [
                {
                  "name": "Куриный салат",
                  "reason": "Белок и мало калорий",
                  "tags": ["high_protein"],
                  "cook_time_minutes": 20,
                  "servings": 1,
                  "calories_kcal": 420,
                  "protein_g": 35.5,
                  "fat_g": 12,
                  "carbohydrate_g": 30,
                  "estimated_cost_amount": 180.5,
                  "currency": "RUB",
                  "recipe_id": "22222222-2222-2222-2222-222222222222",
                  "warnings": []
                }
              ],
              "warnings": ["soft_budget"],
              "rejected_error_codes": []
            }
        """.trimIndent()

        val dto = json.decodeFromString(RecommendationsDto.serializer(), raw)
        assertThat(dto.recommendationId).isEqualTo("11111111-1111-1111-1111-111111111111")
        assertThat(dto.candidates).hasSize(1)
        assertThat(dto.candidates.first().name).isEqualTo("Куриный салат")
        assertThat(dto.candidates.first().caloriesKcal).isEqualTo(420)
        assertThat(dto.candidates.first().proteinG).isEqualTo(35.5)
        assertThat(dto.candidates.first().estimatedCostAmount).isEqualTo(180.5)
        assertThat(dto.warnings).containsExactly("soft_budget")
    }

    @Test
    fun adaptDayParsesReplacements() {
        val raw = """
            {
              "recommendation_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              "on_date": "2026-09-24",
              "replacements": [
                {
                  "meal_type": "dinner",
                  "reason": "Осталось мало калорий",
                  "candidate": {
                    "name": "Рыба на пару",
                    "cook_time_minutes": 25,
                    "servings": 1,
                    "calories_kcal": 350,
                    "protein_g": 40,
                    "fat_g": 10,
                    "carbohydrate_g": 15,
                    "recipe_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
                  }
                }
              ],
              "warnings": [],
              "rationale": "Подобрали лёгкий ужин",
              "note": "Предложения не применены."
            }
        """.trimIndent()

        val dto = json.decodeFromString(AdaptDayDto.serializer(), raw)
        assertThat(dto.onDate).isEqualTo("2026-09-24")
        assertThat(dto.replacements).hasSize(1)
        assertThat(dto.replacements.first().mealType).isEqualTo("dinner")
        assertThat(dto.replacements.first().candidate?.name).isEqualTo("Рыба на пару")
        assertThat(dto.rationale).contains("лёгкий")
    }

    @Test
    fun entitlementsParsesAiRecommendationRemaining() {
        val raw = """
            {
              "tier": "free",
              "features": [
                {
                  "feature": "ai_recommendation",
                  "limit_value": 15,
                  "used_value": 3,
                  "remaining": 12
                }
              ],
              "premium_only": ["image_regenerate"]
            }
        """.trimIndent()
        val dto = json.decodeFromString(EntitlementStatusDto.serializer(), raw)
        assertThat(dto.aiRecommendationRemaining()).isEqualTo(12)
        assertThat(dto.tier).isEqualTo("free")
    }

    @Test
    fun applyRequestSerializesActionType() {
        val encoded = json.encodeToString(
            AiApplyRequest.serializer(),
            AiApplyRequest(
                actionType = "create_nutrition_log",
                payload = mapOf(
                    "recipe_id" to kotlinx.serialization.json.JsonPrimitive("rid"),
                    "meal_type" to kotlinx.serialization.json.JsonPrimitive("lunch"),
                ),
            ),
        )
        assertThat(encoded).contains("create_nutrition_log")
        assertThat(encoded).contains("action_type")
        assertThat(encoded).contains("recipe_id")
    }
}
