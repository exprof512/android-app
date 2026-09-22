package com.foodai.app.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens

@Composable
fun FoodAILinearProgress(
    progress: Float,
    modifier: Modifier = Modifier,
) {
    LinearProgressIndicator(
        progress = { progress.coerceIn(0f, 1f) },
        modifier = modifier
            .fillMaxWidth()
            .height(FoodAIDimens.StepBarHeight)
            .clip(RoundedCornerShape(percent = 50)),
        color = FoodAIColors.Primary,
        trackColor = FoodAIColors.Divider,
    )
}

@Composable
fun FoodAIStepIndicator(
    step: Int,
    total: Int,
    modifier: Modifier = Modifier,
) {
    val safeTotal = total.coerceAtLeast(1)
    val safeStep = step.coerceIn(1, safeTotal)
    Box(modifier = modifier.fillMaxWidth()) {
        FoodAILinearProgress(progress = safeStep / safeTotal.toFloat())
    }
}
