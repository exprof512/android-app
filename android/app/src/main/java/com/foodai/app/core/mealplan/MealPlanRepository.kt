package com.foodai.app.core.mealplan

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.DishCardDto
import com.foodai.app.core.network.MealPlanApi
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.MealPlanGenerateRequest
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.network.MealPlanReplaceRequest
import com.foodai.app.core.network.RecipeApi
import com.foodai.app.core.network.RecipeImageDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class PlanSnapshot(
    val plan: MealPlanDto? = null,
    val loading: Boolean = false,
    val generating: Boolean = false,
    val error: String? = null,
    val missing: Boolean = false,
    val lastUpdatedEpochMs: Long = 0L,
)

/**
 * Authoritative Android meal-plan store: backend → this repository → ViewModels.
 * Today and Week both read [weekPlan] / fetch covering the selected date.
 */
@Singleton
class MealPlanRepository @Inject constructor(
    private val mealPlanApi: MealPlanApi,
    private val recipeApi: RecipeApi,
    private val bus: AppStateBus,
) {
    private val _weekPlan = MutableStateFlow(PlanSnapshot())
    val weekPlan: StateFlow<PlanSnapshot> = _weekPlan.asStateFlow()

    private val _todayPlan = MutableStateFlow(PlanSnapshot())
    val todayPlan: StateFlow<PlanSnapshot> = _todayPlan.asStateFlow()

    suspend fun refreshToday(date: LocalDate = LocalDate.now()): MealPlanDto {
        _todayPlan.value = _todayPlan.value.copy(loading = true, error = null, missing = false)
        return try {
            val plan = wrap { mealPlanApi.today(date.toString()) }
            _todayPlan.value = PlanSnapshot(
                plan = plan,
                lastUpdatedEpochMs = System.currentTimeMillis(),
            )
            plan
        } catch (error: Throwable) {
            val parsed = ApiErrorParser.fromThrowable(error)
            val missing = parsed.code == "meal_plan_not_found" || parsed.httpStatus == 404
            // Keep cached plan on network failure for offline UX.
            val cached = _todayPlan.value.plan
            _todayPlan.value = PlanSnapshot(
                plan = if (!missing) cached else null,
                missing = missing,
                error = parsed.message,
                lastUpdatedEpochMs = System.currentTimeMillis(),
            )
            throw parsed
        }
    }

    suspend fun refreshWeek(anchor: LocalDate = LocalDate.now()): MealPlanDto {
        _weekPlan.value = _weekPlan.value.copy(loading = true, error = null, missing = false)
        return try {
            val plan = wrap { mealPlanApi.week(anchor.toString()) }
            _weekPlan.value = PlanSnapshot(
                plan = plan,
                lastUpdatedEpochMs = System.currentTimeMillis(),
            )
            plan
        } catch (error: Throwable) {
            val parsed = ApiErrorParser.fromThrowable(error)
            val missing = parsed.code == "meal_plan_not_found" || parsed.httpStatus == 404
            val cached = _weekPlan.value.plan
            _weekPlan.value = PlanSnapshot(
                plan = if (!missing) cached else null,
                missing = missing,
                error = parsed.message,
                lastUpdatedEpochMs = System.currentTimeMillis(),
            )
            throw parsed
        }
    }

    /** Load both today slice and full week from the same covering plan when possible. */
    suspend fun refreshAll(anchor: LocalDate = LocalDate.now()) {
        runCatching { refreshWeek(anchor) }
        runCatching { refreshToday(anchor) }
    }

    suspend fun today(date: LocalDate = LocalDate.now()): MealPlanDto = refreshToday(date)

    suspend fun week(start: LocalDate = LocalDate.now()): MealPlanDto = refreshWeek(start)

    suspend fun generate(days: Int = 7, force: Boolean = false): MealPlanDto {
        _todayPlan.value = _todayPlan.value.copy(generating = true, error = null)
        _weekPlan.value = _weekPlan.value.copy(generating = true, error = null)
        return try {
            val plan = wrap {
                mealPlanApi.generate(
                    MealPlanGenerateRequest(
                        startDate = LocalDate.now().toString(),
                        days = days,
                        force = force,
                    ),
                )
            }
            _weekPlan.value = PlanSnapshot(plan = plan, lastUpdatedEpochMs = System.currentTimeMillis())
            runCatching { refreshToday(LocalDate.now()) }
            bus.emit(DomainEvent.PlanChanged("generate"))
            bus.emit(DomainEvent.ShoppingChanged(plan.id))
            plan
        } catch (error: Throwable) {
            val parsed = ApiErrorParser.fromThrowable(error)
            _todayPlan.value = _todayPlan.value.copy(generating = false, error = parsed.message)
            _weekPlan.value = _weekPlan.value.copy(generating = false, error = parsed.message)
            throw parsed
        }
    }

    suspend fun regenerate(days: Int = 7): MealPlanDto = generate(days = days, force = true)

    suspend fun replaceItem(itemId: String, reason: String = "user_requested"): MealPlanDto {
        // Stable per action so double-tap / retry hits server idempotency cache.
        val idempotencyKey = "replace:$itemId:$reason"
        val plan = wrap {
            mealPlanApi.replaceItem(
                itemId = itemId,
                body = MealPlanReplaceRequest(replaceReason = reason),
                idempotencyKey = idempotencyKey,
            )
        }
        _weekPlan.value = PlanSnapshot(plan = plan, lastUpdatedEpochMs = System.currentTimeMillis())
        runCatching { refreshToday(LocalDate.now()) }
        bus.emit(DomainEvent.PlanChanged("replace"))
        bus.emit(DomainEvent.ShoppingChanged(plan.id))
        return plan
    }

    suspend fun completeItem(itemId: String, completed: Boolean = true): MealPlanItemDto {
        val item = wrap { mealPlanApi.completeItem(itemId, completed) }
        runCatching { refreshAll(LocalDate.now()) }
        bus.emit(DomainEvent.PlanChanged("complete"))
        bus.emit(DomainEvent.NutritionLogChanged())
        return item
    }

    suspend fun skipItem(itemId: String, skipped: Boolean = true): MealPlanItemDto {
        val item = wrap { mealPlanApi.skipItem(itemId, skipped) }
        runCatching { refreshAll(LocalDate.now()) }
        bus.emit(DomainEvent.PlanChanged("skip"))
        return item
    }

    suspend fun recipe(recipeId: String): DishCardDto =
        wrap { recipeApi.getRecipe(recipeId) }

    suspend fun recipeImage(recipeId: String): RecipeImageDto =
        wrap { recipeApi.getImage(recipeId) }

    suspend fun setFavorite(recipeId: String, favorite: Boolean) {
        wrap {
            if (favorite) recipeApi.addFavorite(recipeId) else recipeApi.removeFavorite(recipeId)
        }
    }

    suspend fun listFavorites(): List<DishCardDto> =
        wrap { recipeApi.listFavorites() }

    suspend fun searchRecipes(query: String): List<DishCardDto> =
        wrap { recipeApi.search(query = query.ifBlank { null }) }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
