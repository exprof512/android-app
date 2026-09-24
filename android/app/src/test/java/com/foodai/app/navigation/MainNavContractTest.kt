package com.foodai.app.navigation

import com.google.common.truth.Truth.assertThat
import org.junit.Test

/**
 * Bottom bar contract for Phase 24A: four destinations plus a separate AI action.
 * Diary and Add Food are not navigation tabs.
 */
class MainNavContractTest {
    @Test
    fun bottomTabsAreShortAndExcludeDiary() {
        val labels = listOf("Сегодня", "План", "Прогресс", "Профиль")
        labels.forEach { label ->
            assertThat(label.length).isAtMost(8)
            assertThat(label).doesNotContain("Дневник")
            assertThat(label).doesNotContain("+")
            assertThat(label).doesNotContain("\n")
        }
        assertThat(labels).containsExactly("Сегодня", "План", "Прогресс", "Профиль").inOrder()
        assertThat(labels).doesNotContain("AI")
    }
}
