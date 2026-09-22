package com.foodai.app.core.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.foodai.app.core.network.TokenPairResponse
import com.foodai.app.core.network.UserSummaryDto
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

interface TokenStore {
    fun accessToken(): String?
    fun refreshToken(): String?
    fun user(): UserSummaryDto?
    fun hasSession(): Boolean
    fun pendingOnboarding(): Boolean
    fun setPendingOnboarding(value: Boolean)
    fun saveSession(pair: TokenPairResponse)
    fun clear()
}

@Singleton
class SecureTokenStore @Inject constructor(
    @ApplicationContext context: Context,
) : TokenStore {
    private val prefs: SharedPreferences = createPrefs(context)

    override fun accessToken(): String? = prefs.getString(KEY_ACCESS, null)

    override fun refreshToken(): String? = prefs.getString(KEY_REFRESH, null)

    override fun user(): UserSummaryDto? {
        val id = prefs.getString(KEY_USER_ID, null) ?: return null
        val email = prefs.getString(KEY_USER_EMAIL, null) ?: return null
        val tier = prefs.getString(KEY_USER_TIER, "free") ?: "free"
        return UserSummaryDto(id = id, email = email, tier = tier)
    }

    override fun hasSession(): Boolean =
        !accessToken().isNullOrBlank() && !refreshToken().isNullOrBlank()

    override fun pendingOnboarding(): Boolean = prefs.getBoolean(KEY_PENDING_ONBOARDING, false)

    override fun setPendingOnboarding(value: Boolean) {
        prefs.edit().putBoolean(KEY_PENDING_ONBOARDING, value).apply()
    }

    override fun saveSession(pair: TokenPairResponse) {
        prefs.edit()
            .putString(KEY_ACCESS, pair.accessToken)
            .putString(KEY_REFRESH, pair.refreshToken)
            .putString(KEY_USER_ID, pair.user.id)
            .putString(KEY_USER_EMAIL, pair.user.email)
            .putString(KEY_USER_TIER, pair.user.tier)
            .apply()
    }

    override fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val PREFS_NAME = "foodai_secure_session"
        private const val KEY_ACCESS = "access_token"
        private const val KEY_REFRESH = "refresh_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_USER_TIER = "user_tier"
        private const val KEY_PENDING_ONBOARDING = "pending_onboarding"

        fun createPrefs(context: Context): SharedPreferences {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            return EncryptedSharedPreferences.create(
                context,
                PREFS_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        }
    }
}

/** In-memory store for JVM unit tests without Android Keystore. */
class InMemoryTokenStore : TokenStore {
    private var access: String? = null
    private var refresh: String? = null
    private var summary: UserSummaryDto? = null
    private var pendingOnboarding: Boolean = false

    override fun accessToken(): String? = access
    override fun refreshToken(): String? = refresh
    override fun user(): UserSummaryDto? = summary
    override fun hasSession(): Boolean = !access.isNullOrBlank() && !refresh.isNullOrBlank()
    override fun pendingOnboarding(): Boolean = pendingOnboarding
    override fun setPendingOnboarding(value: Boolean) {
        pendingOnboarding = value
    }

    override fun saveSession(pair: TokenPairResponse) {
        access = pair.accessToken
        refresh = pair.refreshToken
        summary = pair.user
    }

    override fun clear() {
        access = null
        refresh = null
        summary = null
        pendingOnboarding = false
    }
}
