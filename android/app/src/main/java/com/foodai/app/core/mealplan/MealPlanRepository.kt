package com.foodai.app.core.mealplan

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.DishCardDto
import com.foodai.app.core.network.MealPlanApi
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.MealPlanGenerateRequest
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.network.RecipeApi
import com.foodai.app.core.network.RecipeImageDto
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MealPlanRepository @Inject constructor(
    private val mealPlanApi: MealPlanApi,
    private val recipeApi: RecipeApi,
) {
    suspend fun today(date: LocalDate = LocalDate.now()): MealPlanDto =
        wrap { mealPlanApi.today(date.toString()) }

    suspend fun week(start: LocalDate = LocalDate.now()): MealPlanDto =
        wrap { mealPlanApi.week(start.toString()) }

    suspend fun generate(days: Int = 7): MealPlanDto =
        wrap {
            mealPlanApi.generate(
                MealPlanGenerateRequest(
                    startDate = LocalDate.now().toString(),
                    days = days,
                ),
            )
        }

    suspend fun replaceItem(itemId: String): MealPlanDto =
        wrap { mealPlanApi.replaceItem(itemId) }

    suspend fun completeItem(itemId: String, completed: Boolean = true): MealPlanItemDto =
        wrap { mealPlanApi.completeItem(itemId, completed) }

    suspend fun recipe(recipeId: String): DishCardDto =
        wrap { recipeApi.getRecipe(recipeId) }

    suspend fun recipeImage(recipeId: String): RecipeImageDto =
        wrap { recipeApi.getImage(recipeId) }

    suspend fun setFavorite(recipeId: String, favorite: Boolean) {
        wrap {
            if (favorite) recipeApi.addFavorite(recipeId) else recipeApi.removeFavorite(recipeId)
        }
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
