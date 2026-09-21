package com.foodai.app.core.auth

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.AuthApi
import com.foodai.app.core.network.LoginRequest
import com.foodai.app.core.network.LogoutRequest
import com.foodai.app.core.network.RegisterRequest
import com.foodai.app.core.network.TokenPairResponse
import com.foodai.app.core.network.UserSummaryDto
import java.time.Instant
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    @Named("bare") private val bareAuthApi: AuthApi,
    @Named("authed") private val authedAuthApi: AuthApi,
    private val tokenStore: TokenStore,
) {
    fun hasSession(): Boolean = tokenStore.hasSession()

    fun currentUser(): UserSummaryDto? = tokenStore.user()

    suspend fun login(email: String, password: String): TokenPairResponse =
        wrap {
            val pair = bareAuthApi.login(LoginRequest(email.trim(), password))
            tokenStore.saveSession(pair)
            pair
        }

    suspend fun register(email: String, password: String): TokenPairResponse =
        wrap {
            val pair = bareAuthApi.register(
                RegisterRequest(
                    email = email.trim(),
                    password = password,
                    acceptedTermsAt = Instant.now().toString(),
                ),
            )
            tokenStore.saveSession(pair)
            pair
        }

    suspend fun refreshMe(): UserSummaryDto =
        wrap {
            val me = authedAuthApi.me()
            val access = tokenStore.accessToken()
            val refresh = tokenStore.refreshToken()
            if (!access.isNullOrBlank() && !refresh.isNullOrBlank()) {
                tokenStore.saveSession(
                    TokenPairResponse(
                        accessToken = access,
                        refreshToken = refresh,
                        expiresIn = 0,
                        user = me,
                    ),
                )
            }
            me
        }

    suspend fun logout() {
        val refresh = tokenStore.refreshToken()
        try {
            if (!refresh.isNullOrBlank()) {
                authedAuthApi.logout(LogoutRequest(refresh))
            }
        } catch (_: Exception) {
            // Local clear always wins — logout is idempotent server-side.
        } finally {
            tokenStore.clear()
        }
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}

fun com.foodai.app.core.network.ApiException.toUiMessage(): String = message ?: "Ошибка"
