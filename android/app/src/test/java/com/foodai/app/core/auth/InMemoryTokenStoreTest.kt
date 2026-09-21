package com.foodai.app.core.auth

import com.foodai.app.core.network.TokenPairResponse
import com.foodai.app.core.network.UserSummaryDto
import com.google.common.truth.Truth.assertThat
import org.junit.Test

class InMemoryTokenStoreTest {
    @Test
    fun saveAndClearRoundTrip() {
        val store = InMemoryTokenStore()
        assertThat(store.hasSession()).isFalse()
        store.saveSession(
            TokenPairResponse(
                accessToken = "acc",
                refreshToken = "ref",
                expiresIn = 60,
                user = UserSummaryDto("id", "user@foodai.app", "free"),
            ),
        )
        assertThat(store.hasSession()).isTrue()
        assertThat(store.accessToken()).isEqualTo("acc")
        assertThat(store.refreshToken()).isEqualTo("ref")
        assertThat(store.user()?.email).isEqualTo("user@foodai.app")
        store.clear()
        assertThat(store.hasSession()).isFalse()
        assertThat(store.accessToken()).isNull()
    }
}
