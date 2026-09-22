package com.foodai.app.core.auth

import com.foodai.app.core.network.AuthApi
import com.foodai.app.core.network.LoginRequest
import com.foodai.app.core.network.LogoutRequest
import com.foodai.app.core.network.RefreshRequest
import com.foodai.app.core.network.RegisterRequest
import com.foodai.app.core.network.TokenPairResponse
import com.foodai.app.core.network.UserSummaryDto
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import org.junit.Test

private class FakeAuthApi(
    private var pair: TokenPairResponse,
) : AuthApi {
    var loginCalls = 0
    var logoutCalls = 0

    override suspend fun register(body: RegisterRequest): TokenPairResponse = pair
    override suspend fun login(body: LoginRequest): TokenPairResponse {
        loginCalls += 1
        return pair.copy(
            user = pair.user.copy(email = body.email.lowercase()),
        )
    }

    override suspend fun refresh(body: RefreshRequest): TokenPairResponse = pair
    override suspend fun logout(body: LogoutRequest) {
        logoutCalls += 1
    }

    override suspend fun me(): UserSummaryDto = pair.user
}

class AuthRepositoryTest {
    @Test
    fun loginPersistsSession() = runTest {
        val store = InMemoryTokenStore()
        val api = FakeAuthApi(
            TokenPairResponse(
                accessToken = "access-1",
                refreshToken = "refresh-1",
                expiresIn = 900,
                user = UserSummaryDto("u1", "anna@example.com", "free"),
            ),
        )
        val repo = AuthRepository(api, api, store, NoOpLocalSessionCleaner)

        val pair = repo.login("Anna@Example.com", "password123")

        assertThat(pair.accessToken).isEqualTo("access-1")
        assertThat(store.hasSession()).isTrue()
        assertThat(store.accessToken()).isEqualTo("access-1")
        assertThat(store.user()?.email).isEqualTo("anna@example.com")
        assertThat(api.loginCalls).isEqualTo(1)
    }

    @Test
    fun logoutClearsLocalSessionEvenIfRemoteFails() = runTest {
        val store = InMemoryTokenStore()
        store.saveSession(
            TokenPairResponse(
                accessToken = "a",
                refreshToken = "r",
                expiresIn = 900,
                user = UserSummaryDto("u1", "a@b.c"),
            ),
        )
        val failing = object : AuthApi by FakeAuthApi(
            TokenPairResponse("a", "r", expiresIn = 1, user = UserSummaryDto("u1", "a@b.c")),
        ) {
            override suspend fun logout(body: LogoutRequest) {
                error("boom")
            }
        }
        val repo = AuthRepository(failing, failing, store, NoOpLocalSessionCleaner)
        repo.logout()
        assertThat(store.hasSession()).isFalse()
    }
}

private object NoOpLocalSessionCleaner : LocalSessionCleaner {
    override fun clearBeforeNewSession() = Unit
    override fun clearOnLogout(userId: String?) = Unit
}
