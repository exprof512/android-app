package com.foodai.app.core.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

/** UI states from docs/design/screens/18-ui-states.jpg */

enum class FoodAIToastKind { Success, Info, Warning, Error }

@Composable
fun FoodAIToast(
    message: String,
    kind: FoodAIToastKind,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null,
) {
    val bg = when (kind) {
        FoodAIToastKind.Success -> FoodAIColors.PrimarySoft
        FoodAIToastKind.Info -> Color(0xFFE8F1FF)
        FoodAIToastKind.Warning -> Color(0xFFFFF4E5)
        FoodAIToastKind.Error -> Color(0xFFFEECEC)
    }
    val fg = when (kind) {
        FoodAIToastKind.Success -> FoodAIColors.PrimaryDark
        FoodAIToastKind.Info -> Color(0xFF1D4ED8)
        FoodAIToastKind.Warning -> Color(0xFFB45309)
        FoodAIToastKind.Error -> FoodAIColors.Error
    }
    val icon: ImageVector = when (kind) {
        FoodAIToastKind.Success -> Icons.Filled.Check
        FoodAIToastKind.Info -> Icons.Outlined.Info
        FoodAIToastKind.Warning -> Icons.Outlined.WarningAmber
        FoodAIToastKind.Error -> Icons.Outlined.ErrorOutline
    }
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(bg)
            .padding(FoodAIDimens.Space12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = fg, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(FoodAIDimens.Space8))
        Text(message, style = FoodAITypography.bodyMedium, color = fg, modifier = Modifier.weight(1f))
        if (onDismiss != null) {
            IconButton(onClick = onDismiss, modifier = Modifier.size(28.dp)) {
                Icon(Icons.Filled.Close, contentDescription = "Закрыть", tint = fg)
            }
        }
    }
}

@Composable
fun FoodAIDangerButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    filled: Boolean = false,
) {
    if (filled) {
        androidx.compose.material3.Button(
            onClick = onClick,
            modifier = modifier.fillMaxWidth().height(FoodAIDimens.ButtonHeight),
            shape = FoodAIShapes.Button,
            colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                containerColor = FoodAIColors.Error,
                contentColor = Color.White,
            ),
        ) {
            Text(label, style = FoodAITypography.labelLarge)
        }
    } else {
        androidx.compose.material3.OutlinedButton(
            onClick = onClick,
            modifier = modifier.fillMaxWidth().height(FoodAIDimens.ButtonHeight),
            shape = FoodAIShapes.Button,
            border = BorderStroke(1.5.dp, FoodAIColors.Error),
            colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                contentColor = FoodAIColors.Error,
            ),
        ) {
            Text(label, style = FoodAITypography.labelLarge)
        }
    }
}

@Composable
fun FoodAILoadingButton(
    label: String = "…",
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(FoodAIDimens.ButtonHeight)
            .clip(FoodAIShapes.Button)
            .background(FoodAIColors.Primary),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(
            color = Color.White,
            strokeWidth = 2.dp,
            modifier = Modifier.size(22.dp),
        )
    }
}

@Composable
fun FoodAIStatusDot(
    complete: Boolean,
    loading: Boolean = false,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .size(24.dp)
            .clip(CircleShape)
            .background(if (complete) FoodAIColors.Primary else FoodAIColors.Divider),
        contentAlignment = Alignment.Center,
    ) {
        when {
            complete -> Icon(Icons.Filled.Check, null, tint = Color.White, modifier = Modifier.size(14.dp))
            loading -> CircularProgressIndicator(
                modifier = Modifier.size(14.dp),
                strokeWidth = 2.dp,
                color = FoodAIColors.Primary,
            )
        }
    }
}

@Composable
fun FoodAIMacroBar(
    label: String,
    current: Int,
    target: Int,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = FoodAITypography.labelMedium)
            Text("$current / $target г", style = FoodAITypography.labelMedium, color = FoodAIColors.TextSecondary)
        }
        Spacer(Modifier.height(4.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(FoodAIShapes.Pill)
                .background(FoodAIColors.Divider),
        ) {
            val p = if (target > 0) (current.toFloat() / target).coerceIn(0f, 1f) else 0f
            Box(
                modifier = Modifier
                    .fillMaxWidth(p)
                    .height(6.dp)
                    .clip(FoodAIShapes.Pill)
                    .background(color),
            )
        }
    }
}
