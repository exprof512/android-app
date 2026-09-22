package com.foodai.app.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens

/**
 * Shared chrome for all onboarding steps: safe areas, progress, header, scroll body, CTA.
 */
@Composable
fun OnboardingScaffold(
    step: Int,
    total: Int,
    title: String,
    subtitle: String,
    onBack: (() -> Unit)?,
    primaryLabel: String,
    onPrimary: () -> Unit,
    modifier: Modifier = Modifier,
    primaryEnabled: Boolean = true,
    showPrimary: Boolean = true,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = FoodAIDimens.ScreenPadding)
            .padding(top = FoodAIDimens.Space16, bottom = FoodAIDimens.Space20),
    ) {
        FoodAIOnboardingTopBar(
            step = step,
            total = total,
            onBack = onBack,
        )
        Spacer(Modifier.height(FoodAIDimens.Space24))
        FoodAIHeader(title = title, subtitle = subtitle)
        Spacer(Modifier.height(FoodAIDimens.Space20))
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
            content = content,
        )
        if (showPrimary) {
            Spacer(Modifier.height(FoodAIDimens.Space16))
            FoodAIPrimaryButton(
                label = primaryLabel,
                onClick = onPrimary,
                enabled = primaryEnabled,
                showArrow = true,
            )
        }
    }
}
