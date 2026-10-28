package com.foodai.app.core.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class FormattingTest {
    @Test
    fun `kcal uses russian grouping`() {
        assertEquals("2 722", formatKcal(2722).replace('\u00A0', ' '))
        assertEquals("374", formatKcal(374))
    }

    @Test
    fun `day plural follows russian rules`() {
        assertEquals("день", daysWord(1))
        assertEquals("дня", daysWord(2))
        assertEquals("дня", daysWord(4))
        assertEquals("дней", daysWord(5))
        assertEquals("дней", daysWord(11))
        assertEquals("дней", daysWord(12))
        assertEquals("дней", daysWord(14))
        assertEquals("день", daysWord(21))
        assertEquals("дня", daysWord(22))
        assertEquals("дней", daysWord(25))
    }
}
