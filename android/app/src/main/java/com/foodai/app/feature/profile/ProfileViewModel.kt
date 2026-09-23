package com.foodai.app.feature.profile

import android.net.Uri
import androidx.lifecycle.ViewModel
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.profile.LocalUserProfile
import com.foodai.app.core.profile.UserProfileStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val auth: AuthRepository,
    private val userProfileStore: UserProfileStore,
) : ViewModel() {
    val localProfile: StateFlow<LocalUserProfile> = userProfileStore.profile

    init {
        reload()
    }

    fun reload() {
        userProfileStore.load(userId())
    }

    fun setDisplayName(name: String) {
        userProfileStore.setDisplayName(userId(), name)
    }

    fun setBio(bio: String) {
        userProfileStore.setBio(userId(), bio)
    }

    fun setAvatar(uri: Uri): Boolean = userProfileStore.setAvatarFromUri(userId(), uri)

    fun clearAvatar() {
        userProfileStore.clearAvatar(userId())
    }

    fun displayNameOrFallback(email: String): String {
        val local = userProfileStore.profile.value.displayName
        if (local.isNotBlank()) return local
        return email.substringBefore("@").replaceFirstChar { it.uppercase() }
    }

    private fun userId(): String = auth.currentUser()?.id ?: "anon"
}
