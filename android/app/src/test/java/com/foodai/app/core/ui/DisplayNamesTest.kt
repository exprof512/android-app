package com.foodai.app.core.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class DisplayNamesTest {
    @Test
    fun stripsTrailingDateSuffix() {
        assertEquals(
            "Овсянка с яблоком",
            displayRecipeName("Овсянка с яблоком (2026-09-24)"),
        )
    }

    @Test
    fun leavesNormalNamesAlone() {
        assertEquals("Курица с рисом", displayRecipeName("Курица с рисом"))
    }
}
