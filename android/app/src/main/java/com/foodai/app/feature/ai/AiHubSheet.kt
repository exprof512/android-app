package com.foodai.app.feature.ai

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.automirrored.outlined.Chat
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

/**
 * Existing AI and plan actions. Each row calls the current backend path;
 * the sheet does not answer locally.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiHubSheet(
    onDismiss: () -> Unit,
    onWhatToEat: () -> Unit,
    onAdaptDay: () -> Unit,
    onReplaceMeal: () -> Unit,
    onShopping: () -> Unit,
    onChat: () -> Unit,
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = FoodAIColors.Surface,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = FoodAIDimens.ScreenPadding)
                .padding(bottom = FoodAIDimens.Space24),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            Text("FoodAI", style = FoodAITypography.titleLarge)
            Text(
                "Что будем делать?",
                style = FoodAITypography.bodyMedium,
                color = FoodAIColors.TextSecondary,
            )
            Spacer(Modifier.height(FoodAIDimens.Space8))
            HubRow(Icons.Outlined.Restaurant, "Что съесть?", "Подбор с учётом остатка дня", onWhatToEat)
            HubRow(Icons.Outlined.AutoAwesome, "Адаптировать день", "Перестроить оставшиеся приёмы", onAdaptDay)
            HubRow(Icons.Outlined.SwapHoriz, "Заменить блюдо", "Следующий приём в плане", onReplaceMeal)
            HubRow(Icons.Outlined.ShoppingCart, "Что купить?", "Список по текущему плану", onShopping)
            HubRow(Icons.AutoMirrored.Outlined.Chat, "Спросить FoodAI", "Чат с ассистентом", onChat)
        }
    }
}

@Composable
private fun HubRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = FoodAIDimens.Space12),
    ) {
        androidx.compose.foundation.layout.Row(
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = FoodAIColors.Primary,
                modifier = Modifier.size(24.dp),
            )
            Column {
                Text(title, style = FoodAITypography.titleMedium, maxLines = 1)
                Text(
                    subtitle,
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                    maxLines = 1,
                )
            }
        }
    }
}
