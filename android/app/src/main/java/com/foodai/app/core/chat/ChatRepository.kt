package com.foodai.app.core.chat

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.ChatApi
import com.foodai.app.core.network.ChatMessageCreateRequest
import com.foodai.app.core.network.ChatMessageResponseDto
import com.foodai.app.core.network.ConversationCreateRequest
import com.foodai.app.core.network.ConversationDto
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatRepository @Inject constructor(
    private val chatApi: ChatApi,
) {
    suspend fun start(recipeId: String? = null, planId: String? = null): ConversationDto =
        wrap {
            chatApi.createConversation(
                ConversationCreateRequest(
                    title = "FoodAI chat",
                    contextRecipeId = recipeId,
                    contextPlanId = planId,
                ),
            )
        }

    suspend fun get(conversationId: String): ConversationDto =
        wrap { chatApi.getConversation(conversationId) }

    suspend fun send(conversationId: String, content: String): ChatMessageResponseDto =
        wrap {
            chatApi.postMessage(conversationId, ChatMessageCreateRequest(content = content))
        }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
