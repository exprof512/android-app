package com.foodai.app.core.auth

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.AuthApi
import com.foodai.app.core.network.LoginRequest
import com.foodai.app.core.network.LogoutRequest
import com.foodai.app.core.network.RegisterRequest
import com.foodai.app.core.network.RefreshCoordinator
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
    private val localSessionCleaner: LocalSessionCleaner,
    private val refreshCoordinator: RefreshCoordinator,
) {
    fun hasSession(): Boolean = tokenStore.hasSession()

    fun currentUser(): UserSummaryDto? = tokenStore.user()

    fun pendingOnboarding(): Boolean = tokenStore.pendingOnboarding()

    fun setPendingOnboarding(value: Boolean) = tokenStore.setPendingOnboarding(value)

    suspend fun login(email: String, password: String): TokenPairResponse =
        wrap {
            localSessionCleaner.clearBeforeNewSession()
            val pair = bareAuthApi.login(LoginRequest(email.trim(), password))
            tokenStore.saveSession(pair)
            // Existing account: Boot decides by profile completeness.
            tokenStore.setPendingOnboarding(false)
            pair
        }

    suspend fun register(email: String, password: String): TokenPairResponse =
        wrap {
            localSessionCleaner.clearBeforeNewSession()
            val pair = bareAuthApi.register(
                RegisterRequest(
                    email = email.trim(),
                    password = password,
                    acceptedTermsAt = Instant.now().toString(),
                ),
            )
            tokenStore.saveSession(pair)
            tokenStore.setPendingOnboarding(true)
            pair
        }

    suspend fun refreshMe(): UserSummaryDto =
        wrap {
            val me = authedAuthApi.me()
            val summary = UserSummaryDto(id = me.id, email = me.email, tier = me.tier)
            val access = tokenStore.accessToken()
            val refresh = tokenStore.refreshToken()
            if (!access.isNullOrBlank() && !refresh.isNullOrBlank()) {
                tokenStore.saveSession(
                    TokenPairResponse(
                        accessToken = access,
                        refreshToken = refresh,
                        expiresIn = 0,
                        user = summary,
                    ),
                )
            }
            summary
        }

    suspend fun currentAccount(): com.foodai.app.core.network.CurrentUserDto =
        wrap { authedAuthApi.me() }

    suspend fun forgotPassword(email: String) =
        wrap { bareAuthApi.forgotPassword(com.foodai.app.core.network.EmailOnlyRequest(email.trim())) }

    suspend fun resetPassword(token: String, newPassword: String) =
        wrap {
            bareAuthApi.resetPassword(
                com.foodai.app.core.network.ResetPasswordRequest(token, newPassword),
            )
        }

    suspend fun resendVerification(email: String) =
        wrap {
            bareAuthApi.resendVerification(com.foodai.app.core.network.EmailOnlyRequest(email.trim()))
        }

    suspend fun listSessions() = wrap { authedAuthApi.listSessions() }

    suspend fun revokeSession(id: String) = wrap { authedAuthApi.revokeSession(id) }

    suspend fun revokeAllSessions() = wrap { authedAuthApi.revokeAllSessions() }

    suspend fun exportData(): kotlinx.serialization.json.JsonObject =
        wrap {
            val payload = authedAuthApi.exportData()
            if (!payload.containsKey("exported_at")) {
                throw com.foodai.app.core.network.ApiException.Unexpected(
                    "Экспорт пуст или повреждён",
                    httpStatus = 500,
                )
            }
            payload
        }

    suspend fun deleteAccount(): Boolean =
        wrap {
            val response = authedAuthApi.deleteAccount(
                com.foodai.app.core.network.DeleteAccountRequest("DELETE"),
            )
            // Drain/close body — 204 has no JSON payload.
            response.body()?.close()
            if (!response.isSuccessful) {
                throw com.foodai.app.core.network.ApiException.Unexpected(
                    "Не удалось удалить аккаунт",
                    httpStatus = response.code(),
                )
            }
            localSessionCleaner.clearOnLogout(tokenStore.user()?.id)
            refreshCoordinator.bumpSessionEpoch()
            tokenStore.clear()
            true
        }

    suspend fun logout() {
        val previousUserId = tokenStore.user()?.id
        val refresh = tokenStore.refreshToken()
        try {
            if (!refresh.isNullOrBlank()) {
                authedAuthApi.logout(LogoutRequest(refresh))
            }
        } catch (_: Exception) {
            // Local clear always wins — logout is idempotent server-side.
        } finally {
            refreshCoordinator.bumpSessionEpoch()
            localSessionCleaner.clearOnLogout(previousUserId)
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
