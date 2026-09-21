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
        val message = buildMessage(parsed?.message ?: parsed?.detail, details)
            ?: defaultMessage(code)
        val apiCode = parsed?.code
        return when (code) {
            401 -> ApiException.Unauthorized(message, apiCode)
            403 -> ApiException.Forbidden(message, apiCode)
            409 -> ApiException.Conflict(message, apiCode)
            422 -> ApiException.Validation(message, apiCode, details)
            else -> ApiException.Unexpected(message, code, apiCode)
        }
    }

    fun fromThrowable(error: Throwable): ApiException = when (error) {
        is ApiException -> error
        is HttpException -> fromHttp(error.code(), error.response()?.errorBody())
        is IOException -> ApiException.Network(error.message ?: "Нет соединения с сервером")
        else -> ApiException.Unexpected(error.message ?: "Неизвестная ошибка")
    }

    private fun buildMessage(base: String?, details: List<ApiErrorDetail>): String? {
        if (details.isEmpty()) return base
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
        422 -> "Проверьте введённые данные"
        else -> "Ошибка сервера ($code)"
    }
}
