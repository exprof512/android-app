package com.foodai.app.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun FoodAICard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = FoodAIShapes.CardLarge
    if (onClick != null) {
        Surface(
            onClick = onClick,
            modifier = modifier.fillMaxWidth(),
            shape = shape,
            color = FoodAIColors.Surface,
            shadowElevation = 1.dp,
            tonalElevation = 0.dp,
        ) {
            Column(modifier = Modifier.padding(FoodAIDimens.Space16), content = content)
        }
    } else {
        Surface(
            modifier = modifier.fillMaxWidth(),
            shape = shape,
            color = FoodAIColors.Surface,
            shadowElevation = 1.dp,
            tonalElevation = 0.dp,
        ) {
            Column(modifier = Modifier.padding(FoodAIDimens.Space16), content = content)
        }
    }
}

@Composable
fun FoodAIInfoCard(
    text: String,
    modifier: Modifier = Modifier,
    icon: ImageVector = Icons.Outlined.Lightbulb,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.PrimarySoft)
            .padding(FoodAIDimens.Space12),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = FoodAIColors.Primary,
            modifier = Modifier.size(20.dp),
        )
        Text(
            text = text,
            style = FoodAITypography.bodySmall,
            color = FoodAIColors.TextSecondary,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
fun FoodAIMetricCard(
    title: String,
    value: String,
    subtitle: String? = null,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.PrimarySoft)
            .padding(FoodAIDimens.Space16),
    ) {
        Text(title, style = FoodAITypography.labelMedium, color = FoodAIColors.TextSecondary)
        Spacer(Modifier.height(FoodAIDimens.Space4))
        Text(value, style = FoodAITypography.headlineSmall, color = FoodAIColors.TextPrimary)
        if (subtitle != null) {
            Spacer(Modifier.height(FoodAIDimens.Space4))
            Text(subtitle, style = FoodAITypography.bodySmall, color = FoodAIColors.TextSecondary)
        }
    }
}

@Composable
fun FoodAIProgressCard(
    title: String,
    progress: Float,
    caption: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .border(1.dp, FoodAIColors.Divider, FoodAIShapes.CardLarge)
            .padding(FoodAIDimens.Space16),
    ) {
        Text(title, style = FoodAITypography.titleMedium)
        Spacer(Modifier.height(FoodAIDimens.Space12))
        FoodAILinearProgress(progress = progress.coerceIn(0f, 1f))
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text(caption, style = FoodAITypography.bodySmall)
    }
}

enum class SelectableCardState { Default, Selected, Disabled }

@Composable
fun FoodAISelectableCard(
    title: String,
    subtitle: String? = null,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    leading: @Composable (() -> Unit)? = null,
    enabled: Boolean = true,
) {
    val state = when {
        !enabled -> SelectableCardState.Disabled
        selected -> SelectableCardState.Selected
        else -> SelectableCardState.Default
    }
    val bg = when (state) {
        SelectableCardState.Selected -> FoodAIColors.PrimarySoft
        SelectableCardState.Disabled -> FoodAIColors.SurfaceMuted
        SelectableCardState.Default -> FoodAIColors.Surface
    }
    val border = when (state) {
        SelectableCardState.Selected -> FoodAIColors.Primary
        else -> FoodAIColors.Divider
    }
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(bg)
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = border,
                shape = FoodAIShapes.CardLarge,
            )
            .clickable(enabled = enabled, role = Role.RadioButton, onClick = onClick)
            .padding(horizontal = FoodAIDimens.Space16, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (leading != null) {
            leading()
            Spacer(Modifier.width(FoodAIDimens.Space12))
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = FoodAITypography.titleMedium, color = FoodAIColors.TextPrimary)
            if (subtitle != null) {
                Spacer(Modifier.height(2.dp))
                Text(subtitle, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
            }
        }
        SelectionIndicator(selected = selected)
    }
}

@Composable
fun SelectionIndicator(selected: Boolean) {
    Box(
        modifier = Modifier
            .size(24.dp)
            .clip(CircleShape)
            .background(if (selected) FoodAIColors.Primary else Color.Transparent)
            .border(
                width = if (selected) 0.dp else 1.5.dp,
                color = if (selected) Color.Transparent else FoodAIColors.TextMuted,
                shape = CircleShape,
            ),
        contentAlignment = Alignment.Center,
    ) {
        if (selected) {
            Icon(
                imageVector = Icons.Filled.Check,
                contentDescription = "Выбрано",
                tint = FoodAIColors.TextOnPrimary,
                modifier = Modifier.size(14.dp),
            )
        }
    }
}

@Composable
fun FoodAIPrivacyBadge(
    text: String,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .clip(FoodAIShapes.Pill)
            .background(FoodAIColors.PrimarySoft)
            .padding(horizontal = FoodAIDimens.Space12, vertical = FoodAIDimens.Space8),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
    ) {
        Icon(
            imageVector = Icons.Outlined.Info,
            contentDescription = null,
            tint = FoodAIColors.Primary,
            modifier = Modifier.size(16.dp),
        )
        Text(text, style = FoodAITypography.bodySmall, color = FoodAIColors.PrimaryDark)
    }
}
