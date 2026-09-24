package com.foodai.app.core.ai

import com.foodai.app.core.network.ActionExecuteDto
import com.foodai.app.core.network.AdaptDayDto
import com.foodai.app.core.network.AiAdaptDayRequest
import com.foodai.app.core.network.AiApi
import com.foodai.app.core.network.AiApplyRequest
import com.foodai.app.core.network.AiExecuteRequest
import com.foodai.app.core.network.AiRecommendRequest
import com.foodai.app.core.network.AiSubstitutionRequest
import com.foodai.app.core.network.AiVariantRequest
import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.EntitlementStatusDto
import com.foodai.app.core.network.EntitlementsApi
import com.foodai.app.core.network.RecommendationsDto
import com.foodai.app.core.network.SubstitutionDto
import com.foodai.app.core.network.VariantDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import java.time.LocalDate
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AiRecommendationRepository @Inject constructor(
    private val aiApi: AiApi,
    private val entitlementsApi: EntitlementsApi,
    private val bus: AppStateBus,
) {
    suspend fun recommend(
        intent: String? = null,
        mealType: String? = null,
        date: LocalDate? = null,
    ): RecommendationsDto = wrap {
        aiApi.recommendations(
            AiRecommendRequest(
                intent = intent,
                mealType = mealType,
                date = date?.toString(),
            ),
        )
    }

    suspend fun adaptDay(date: LocalDate? = null): AdaptDayDto = wrap {
        aiApi.adaptDay(AiAdaptDayRequest(date = date?.toString()))
    }

    suspend fun ingredientSubstitution(
        recipeId: String,
        ingredientName: String,
    ): SubstitutionDto = wrap {
        aiApi.ingredientSubstitution(
            AiSubstitutionRequest(recipeId = recipeId, ingredientName = ingredientName),
        )
    }

    suspend fun recipeVariant(recipeId: String, variant: String): VariantDto = wrap {
        aiApi.recipeVariant(AiVariantRequest(recipeId = recipeId, variant = variant))
    }

    suspend fun apply(
        recommendationId: String,
        actionType: String,
        payload: Map<String, JsonElement> = emptyMap(),
        idempotencyKey: String? = UUID.randomUUID().toString(),
    ): ActionExecuteDto {
        val result = wrap {
            aiApi.apply(
                recommendationId = recommendationId,
                body = AiApplyRequest(actionType = actionType, payload = payload),
                idempotencyKey = idempotencyKey,
            )
        }
        emitAfterApply(actionType)
        return result
    }

    suspend fun execute(
        actionType: String,
        payload: Map<String, JsonElement> = emptyMap(),
        recommendationId: String? = null,
        idempotencyKey: String? = UUID.randomUUID().toString(),
    ): ActionExecuteDto {
        val result = wrap {
            aiApi.execute(
                AiExecuteRequest(
                    actionType = actionType,
                    payload = payload,
                    recommendationId = recommendationId,
                ),
                idempotencyKey = idempotencyKey,
            )
        }
        emitAfterApply(actionType)
        return result
    }

    suspend fun entitlements(): EntitlementStatusDto = wrap {
        entitlementsApi.me()
    }

    private fun emitAfterApply(actionType: String) {
        when (actionType) {
            "replace_meal_item" -> {
                bus.emit(DomainEvent.PlanChanged("ai_apply"))
                bus.emit(DomainEvent.ShoppingChanged())
            }
            "create_nutrition_log" -> {
                bus.emit(DomainEvent.NutritionLogChanged())
                bus.emit(DomainEvent.PlanChanged("ai_nutrition_log"))
            }
            "remember_dislike" -> bus.emit(DomainEvent.ProfileChanged("ai_dislike"))
            else -> Unit
        }
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}

fun aiPayload(vararg pairs: Pair<String, Any?>): Map<String, JsonElement> =
    pairs.mapNotNull { (key, value) ->
        when (value) {
            null -> null
            is String -> key to JsonPrimitive(value)
            is Number -> key to JsonPrimitive(value)
            is Boolean -> key to JsonPrimitive(value)
            else -> key to JsonPrimitive(value.toString())
        }
    }.toMap()
