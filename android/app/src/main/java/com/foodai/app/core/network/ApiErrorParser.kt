package com.foodai.app.core.network

import kotlinx.serialization.json.Json
import okhttp3.ResponseBody
import retrofit2.HttpException
import java.io.IOException

object ApiErrorParser {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    fun fromHttp(code: Int, errorBody: ResponseBody?): ApiException {
        val raw = runCatching { errorBody?.string() }.getOrNull().orEmpty()
        val envelope = runCatching { json.decodeFromString(ApiErrorEnvelope.serializer(), raw) }.getOrNull()
        val parsed = envelope?.error
            ?: runCatching { json.decodeFromString(ApiErrorBody.serializer(), raw) }.getOrNull()
        val details = parsed?.details.orEmpty()
        val message = humanize(parsed?.message ?: parsed?.detail, parsed?.code, details)
            ?: defaultMessage(code)
        val apiCode = parsed?.code
        return when (code) {
            401 -> ApiException.Unauthorized(message, apiCode)
            403 -> ApiException.Forbidden(message, apiCode)
            409 -> ApiException.Conflict(message, apiCode)
            422 -> ApiException.Validation(message, apiCode, details)
            429 -> ApiException.RateLimited(message, apiCode)
            else -> ApiException.Unexpected(message, code, apiCode)
        }
    }

    fun fromThrowable(error: Throwable): ApiException = when (error) {
        is ApiException -> error
        is HttpException -> fromHttp(error.code(), error.response()?.errorBody())
        is IOException -> ApiException.Network(error.message ?: "Нет соединения с сервером")
        else -> ApiException.Unexpected(error.message ?: "Неизвестная ошибка")
    }

    private fun humanize(
        base: String?,
        code: String?,
        details: List<ApiErrorDetail>,
    ): String? {
        if (code == "premium_required") {
            return base ?: "Эта функция доступна в Premium."
        }
        if (code == "usage_limit_exceeded") {
            return base ?: "Достигнут дневной лимит бесплатного тарифа."
        }
        val unknownIngredients = details.any { it.reason == "unknown_ingredient" }
        if (code == "recipe_validation_error" || unknownIngredients) {
            return "Не удалось собрать рецепт из справочника продуктов. Нажмите «Повторить» — " +
                "мы соберём план из каталога."
        }
        if (details.isEmpty()) return base
        // Keep technical field:reason only for non-recipe validation (forms).
        if (code == "recipe_validation_error") {
            return base ?: "Рецепт не прошёл проверку."
        }
        val detailText = details.joinToString("; ") { d ->
            listOfNotNull(d.field, d.reason).joinToString(": ")
        }
        return when {
            base.isNullOrBlank() -> detailText
            detailText.isBlank() -> base
            else -> "$base ($detailText)"
        }
    }

    private fun defaultMessage(code: Int): String = when (code) {
        401 -> "Неверный email или пароль"
        403 -> "Доступ запрещён"
        409 -> "Конфликт данных"
        413 -> "Фото слишком большое. Попробуйте другое фото или уменьшите размер."
        422 -> "Проверьте введённые данные"
        429 -> "Слишком много запросов. Попробуйте позже."
        else -> "Ошибка сервера ($code)"
    }
}
