package com.foodai.app.core.profile

import android.content.Context
import android.content.SharedPreferences
import android.net.Uri
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

data class LocalUserProfile(
    val displayName: String = "",
    val avatarPath: String? = null,
    val bio: String = "Стремлюсь к здоровью, энергии и большим целям",
)

/**
 * Display name + avatar stored on device, keyed by user id.
 * Avatar bytes are copied into app files (survives content URI expiry).
 */
@Singleton
class UserProfileStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val _profile = MutableStateFlow(LocalUserProfile())
    val profile: StateFlow<LocalUserProfile> = _profile.asStateFlow()

    fun load(userId: String) {
        _profile.value = LocalUserProfile(
            displayName = prefs.getString(key(userId, "name"), "").orEmpty(),
            avatarPath = prefs.getString(key(userId, "avatar"), null),
            bio = prefs.getString(key(userId, "bio"), null)
                ?: "Стремлюсь к здоровью, энергии и большим целям",
        )
    }

    fun setDisplayName(userId: String, name: String) {
        val cleaned = name.trim().take(40)
        prefs.edit().putString(key(userId, "name"), cleaned).apply()
        _profile.value = _profile.value.copy(displayName = cleaned)
    }

    fun setBio(userId: String, bio: String) {
        val cleaned = bio.trim().take(120)
        prefs.edit().putString(key(userId, "bio"), cleaned).apply()
        _profile.value = _profile.value.copy(bio = cleaned)
    }

    fun setAvatarFromUri(userId: String, uri: Uri): Boolean {
        return runCatching {
            val dir = File(context.filesDir, "avatars").also { it.mkdirs() }
            val dest = File(dir, "$userId.jpg")
            context.contentResolver.openInputStream(uri)?.use { input ->
                dest.outputStream().use { output -> input.copyTo(output) }
            } ?: return false
            prefs.edit().putString(key(userId, "avatar"), dest.absolutePath).apply()
            _profile.value = _profile.value.copy(avatarPath = dest.absolutePath)
            true
        }.getOrDefault(false)
    }

    fun clearAvatar(userId: String) {
        val path = prefs.getString(key(userId, "avatar"), null)
        if (path != null) File(path).delete()
        prefs.edit().remove(key(userId, "avatar")).apply()
        _profile.value = _profile.value.copy(avatarPath = null)
    }

    fun clearUser(userId: String) {
        clearAvatar(userId)
        prefs.edit()
            .remove(key(userId, "name"))
            .remove(key(userId, "bio"))
            .apply()
        if (_profile.value.displayName.isNotEmpty() || _profile.value.avatarPath != null) {
            _profile.value = LocalUserProfile()
        }
    }

    fun clearAll() {
        File(context.filesDir, "avatars").listFiles()?.forEach { it.delete() }
        prefs.edit().clear().apply()
        _profile.value = LocalUserProfile()
    }

    private fun key(userId: String, field: String) = "$userId:$field"

    companion object {
        private const val PREFS = "foodai_user_profile"
    }
}
