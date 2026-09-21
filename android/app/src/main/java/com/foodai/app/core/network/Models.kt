package com.foodai.app.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ApiErrorBody(
    val code: String? = null,
    val message: String? = null,
    val detail: String? = null,
)

sealed class ApiException(
    message: String,
    val code: String? = null,
    val httpStatus: Int? = null,
) : Exception(message) {
    class Unauthorized(
        message: String = "Требуется вход",
        code: String? = "invalid_token",
    ) : ApiException(message, code, 401)

    class Forbidden(
        message: String,
        code: String? = null,
    ) : ApiException(message, code, 403)

    class Conflict(
        message: String,
        code: String? = null,
    ) : ApiException(message, code, 409)

    class Validation(
        message: String,
        code: String? = "validation_error",
    ) : ApiException(message, code, 422)

    class Network(
        message: String = "Нет соединения с сервером",
    ) : ApiException(message)

    class Unexpected(
        message: String,
        httpStatus: Int? = null,
        code: String? = null,
    ) : ApiException(message, code, httpStatus)
}

@Serializable
data class TokenPairResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Int,
    val user: UserSummaryDto,
)

@Serializable
data class UserSummaryDto(
    val id: String,
    val email: String,
    val tier: String = "free",
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
)

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    val locale: String = "ru-RU",
    @SerialName("accepted_terms_at") val acceptedTermsAt: String? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequest(
    @SerialName("refresh_token") val refreshToken: String,
)
