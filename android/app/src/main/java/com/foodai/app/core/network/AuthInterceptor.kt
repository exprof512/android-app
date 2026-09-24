package com.foodai.app.core.network

import com.foodai.app.core.auth.TokenStore
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenStore: TokenStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val access = tokenStore.accessToken()
        val request = if (access.isNullOrBlank()) {
            chain.request()
        } else {
            chain.request().newBuilder()
                .header("Authorization", "Bearer $access")
                .build()
        }
        return chain.proceed(request)
    }
}

/**
 * Single-flight refresh: Android must not refresh in parallel (token family revoke).
 */
@Singleton
class TokenAuthenticator @Inject constructor(
    private val tokenStore: TokenStore,
    private val refreshCoordinator: RefreshCoordinator,
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) return null
        val currentAccess = tokenStore.accessToken()
        val requestAccess = response.request.header("Authorization")?.removePrefix("Bearer ")?.trim()
        if (!currentAccess.isNullOrBlank() && currentAccess != requestAccess) {
            return response.request.newBuilder()
                .header("Authorization", "Bearer $currentAccess")
                .build()
        }
        val refreshed = runBlocking { refreshCoordinator.refresh() } ?: return null
        return response.request.newBuilder()
            .header("Authorization", "Bearer ${refreshed.accessToken}")
            .build()
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count += 1
            prior = prior.priorResponse
        }
        return count
    }
}

@Singleton
class RefreshCoordinator @Inject constructor(
    private val tokenStore: TokenStore,
    private val authApiProvider: AuthApiProvider,
) {
    private val mutex = Mutex()
    @Volatile private var sessionEpoch: Long = 0L

    /** Call under logout so an in-flight refresh cannot resurrect the session. */
    fun bumpSessionEpoch() {
        sessionEpoch += 1L
    }

    suspend fun refresh(): TokenPairResponse? = mutex.withLock {
        val epochAtStart = sessionEpoch
        val refresh = tokenStore.refreshToken() ?: return null
        return try {
            val pair = authApiProvider.authApi.refresh(RefreshRequest(refresh))
            if (epochAtStart != sessionEpoch) {
                return null
            }
            tokenStore.saveSession(pair)
            pair
        } catch (error: Exception) {
            // Only wipe session on auth rejection; keep tokens on transient IO.
            val status = (error as? retrofit2.HttpException)?.code()
            if (status == 401 || status == 403) {
                if (epochAtStart == sessionEpoch) {
                    tokenStore.clear()
                }
            }
            null
        }
    }
}

/** Lazy provider avoids circular DI between OkHttp authenticator and Retrofit. */
@Singleton
class AuthApiProvider @Inject constructor() {
    lateinit var authApi: AuthApi
}
