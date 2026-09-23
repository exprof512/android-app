package com.foodai.app.core.shopping

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.ShoppingApi
import com.foodai.app.core.network.ShoppingGenerateRequest
import com.foodai.app.core.network.ShoppingListDto
import com.foodai.app.core.network.ShoppingListItemDto
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ShoppingRepository @Inject constructor(
    private val shoppingApi: ShoppingApi,
) {
    suspend fun current(mealPlanId: String? = null): ShoppingListDto =
        wrap { shoppingApi.current(mealPlanId) }

    suspend fun generate(
        mealPlanId: String,
        excludeAvailableProducts: Boolean = true,
    ): ShoppingListDto =
        wrap {
            shoppingApi.generate(
                ShoppingGenerateRequest(
                    mealPlanId = mealPlanId,
                    excludeAvailableProducts = excludeAvailableProducts,
                ),
            )
        }

    suspend fun completeItem(itemId: String, completed: Boolean = true): ShoppingListItemDto =
        wrap { shoppingApi.completeItem(itemId, completed) }

    suspend fun clearCompleted(listId: String? = null): ShoppingListDto =
        wrap { shoppingApi.clearCompleted(listId) }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
