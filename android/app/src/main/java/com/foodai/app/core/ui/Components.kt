package com.foodai.app.core.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import com.foodai.app.core.ui.components.FoodAILoading
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun LoadingPane(
    message: String = "Загрузка…",
    modifier: Modifier = Modifier,
) {
    FoodAILoading(message = message, modifier = modifier)
}

@Composable
fun FoodAiPrimaryButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    FoodAIPrimaryButton(
        label = label,
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        showArrow = false,
    )
}

@Composable
fun ErrorPane(
    message: String,
    onRetry: (() -> Unit)? = null,
    retryLabel: String = "Повторить",
    onSecondary: (() -> Unit)? = null,
    secondaryLabel: String = "Создать план",
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .padding(FoodAIDimens.Space24),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = message,
                style = FoodAITypography.bodyLarge,
                color = FoodAIColors.Error,
                textAlign = TextAlign.Center,
            )
            if (onSecondary != null) {
                FoodAIPrimaryButton(label = secondaryLabel, onClick = onSecondary, showArrow = false)
            }
            if (onRetry != null) {
                FoodAIPrimaryButton(label = retryLabel, onClick = onRetry, showArrow = false)
            }
        }
    }
}
