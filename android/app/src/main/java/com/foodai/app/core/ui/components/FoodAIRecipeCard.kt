package com.foodai.app.core.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.foodai.app.core.network.RecipeImageDto
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun FoodAILoading(
    message: String = "Загрузка…",
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = FoodAIColors.Primary)
            Spacer(Modifier.height(FoodAIDimens.Space16))
            Text(message, style = FoodAITypography.bodyLarge, color = FoodAIColors.TextSecondary)
        }
    }
}

@Composable
fun FoodAIEmptyState(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(FoodAIDimens.Space24),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
    ) {
        Icon(
            Icons.Outlined.Restaurant,
            contentDescription = null,
            tint = FoodAIColors.Primary,
            modifier = Modifier.size(48.dp),
        )
        Text(title, style = FoodAITypography.titleLarge, textAlign = TextAlign.Center)
        Text(
            subtitle,
            style = FoodAITypography.bodyMedium,
            color = FoodAIColors.TextSecondary,
            textAlign = TextAlign.Center,
        )
        if (actionLabel != null && onAction != null) {
            FoodAIPrimaryButton(label = actionLabel, onClick = onAction, showArrow = false)
        }
    }
}

@Composable
fun FoodAIRecipeCard(
    name: String,
    caloriesLabel: String,
    image: RecipeImageDto?,
    modifier: Modifier = Modifier,
    onClick: () -> Unit = {},
) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space12),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(140.dp)
                .clip(FoodAIShapes.Card)
                .background(FoodAIColors.PrimarySoft),
            contentAlignment = Alignment.Center,
        ) {
            val url = image?.thumbnailUrl ?: image?.url
            if (!url.isNullOrBlank()) {
                AsyncImage(
                    model = url,
                    contentDescription = name,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                )
            } else {
                Icon(
                    Icons.Outlined.Restaurant,
                    contentDescription = null,
                    tint = FoodAIColors.Primary,
                    modifier = Modifier.size(36.dp),
                )
            }
        }
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text(name, style = FoodAITypography.titleMedium, maxLines = 2)
        Text(caloriesLabel, style = FoodAITypography.bodySmall, color = FoodAIColors.TextSecondary)
        Spacer(Modifier.height(FoodAIDimens.Space8))
        FoodAISecondaryButton(label = "Открыть", onClick = onClick)
    }
}

@Composable
fun FoodAIMacroCard(
    protein: String,
    fat: String,
    carbs: String,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
    ) {
        MacroCell("Б", protein, Modifier.weight(1f))
        MacroCell("Ж", fat, Modifier.weight(1f))
        MacroCell("У", carbs, Modifier.weight(1f))
    }
}

@Composable
private fun MacroCell(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.Chip)
            .background(FoodAIColors.PrimarySoft)
            .padding(FoodAIDimens.Space12),
    ) {
        Text(label, style = FoodAITypography.labelMedium, color = FoodAIColors.Primary)
        Text(value, style = FoodAITypography.titleMedium)
    }
}

data class FoodAINavItem(
    val route: String,
    val label: String,
    val icon: ImageVector,
)

/**
 * Bottom navigation. Optional [onFabClick] reserves a center slot for a docked FAB
 * drawn by the parent [androidx.compose.material3.Scaffold] — do not overlay a
 * clipped circle here (touches get eaten by bottomBar bounds).
 */
@Composable
fun FoodAINavigationBar(
    items: List<FoodAINavItem>,
    currentRoute: String?,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
    onFabClick: (() -> Unit)? = null,
) {
    NavigationBar(
        containerColor = FoodAIColors.Surface,
        tonalElevation = 0.dp,
        modifier = modifier
            .fillMaxWidth()
            .border(
                width = 1.dp,
                color = FoodAIColors.Divider,
                shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
            ),
    ) {
        if (onFabClick == null) {
            items.forEach { item ->
                NavBarSlot(item = item, currentRoute = currentRoute, onSelect = onSelect)
            }
        } else {
            // Even split around the center FAB slot (e.g. 2 + FAB + 2 for 4 tabs,
            // or 2 + FAB + 3 for 5 tabs — prefer even counts when possible).
            val leftCount = items.size / 2
            val left = items.take(leftCount)
            val right = items.drop(leftCount)
            left.forEach { item ->
                NavBarSlot(item = item, currentRoute = currentRoute, onSelect = onSelect)
            }
            NavigationBarItem(
                selected = false,
                onClick = onFabClick,
                icon = {
                    // Invisible placeholder; real FAB is Scaffold.floatingActionButton.
                    Spacer(Modifier.size(48.dp))
                },
                label = { Text(" ") },
                colors = NavigationBarItemDefaults.colors(indicatorColor = Color.Transparent),
                enabled = true,
            )
            right.forEach { item ->
                NavBarSlot(item = item, currentRoute = currentRoute, onSelect = onSelect)
            }
        }
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.NavBarSlot(
    item: FoodAINavItem,
    currentRoute: String?,
    onSelect: (String) -> Unit,
) {
    val selected = currentRoute == item.route
    NavigationBarItem(
        selected = selected,
        onClick = { onSelect(item.route) },
        icon = {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(FoodAIDimens.RadiusPill))
                    .background(if (selected) FoodAIColors.NavSelected else Color.Transparent)
                    .padding(horizontal = 12.dp, vertical = 6.dp),
            ) {
                Icon(
                    item.icon,
                    contentDescription = item.label,
                    tint = if (selected) FoodAIColors.Primary else FoodAIColors.TextMuted,
                )
            }
        },
        label = {
            Text(
                item.label,
                color = if (selected) FoodAIColors.Primary else FoodAIColors.TextMuted,
                style = FoodAITypography.labelMedium,
            )
        },
        colors = NavigationBarItemDefaults.colors(indicatorColor = Color.Transparent),
    )
}

@Composable
fun FoodAIFoodTile(
    emoji: String,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .clip(FoodAIShapes.Tile)
            .background(if (selected) FoodAIColors.PrimaryLight else FoodAIColors.Surface)
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = if (selected) FoodAIColors.Primary else FoodAIColors.Divider,
                shape = FoodAIShapes.Tile,
            )
            .clickable(onClick = onClick)
            .padding(vertical = FoodAIDimens.Space12, horizontal = FoodAIDimens.Space4),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(emoji, style = FoodAITypography.headlineSmall)
            Spacer(Modifier.height(4.dp))
            Text(
                label,
                style = FoodAITypography.labelMedium,
                color = FoodAIColors.TextPrimary,
                textAlign = TextAlign.Center,
                maxLines = 1,
            )
        }
        if (selected) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(4.dp)
                    .size(18.dp)
                    .clip(androidx.compose.foundation.shape.CircleShape)
                    .background(FoodAIColors.Primary),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(12.dp),
                )
            }
        }
    }
}
