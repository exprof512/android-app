package com.foodai.app.core.ui.components

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun FoodAIPrimaryButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    showArrow: Boolean = true,
    fullWidth: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .then(if (fullWidth) Modifier.fillMaxWidth() else Modifier)
            .height(FoodAIDimens.ButtonHeight),
        shape = FoodAIShapes.Button,
        colors = ButtonDefaults.buttonColors(
            containerColor = FoodAIColors.Primary,
            contentColor = FoodAIColors.TextOnPrimary,
            disabledContainerColor = FoodAIColors.Primary.copy(alpha = 0.4f),
            disabledContentColor = FoodAIColors.TextOnPrimary,
        ),
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 2.dp,
            pressedElevation = 0.dp,
        ),
        contentPadding = PaddingValues(horizontal = FoodAIDimens.Space24),
    ) {
        Text(label, style = FoodAITypography.labelLarge, color = FoodAIColors.TextOnPrimary)
        if (showArrow) {
            Spacer(Modifier.width(FoodAIDimens.Space8))
            Text("→", style = FoodAITypography.labelLarge, color = FoodAIColors.TextOnPrimary)
        }
    }
}

@Composable
fun FoodAISecondaryButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    TextButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(FoodAIDimens.TouchTarget),
    ) {
        Text(label, style = FoodAITypography.labelLarge, color = FoodAIColors.Primary)
    }
}

@Composable
fun FoodAIOutlinedButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .fillMaxWidth()
            .height(FoodAIDimens.ButtonHeight),
        shape = FoodAIShapes.Button,
        colors = ButtonDefaults.outlinedButtonColors(
            contentColor = FoodAIColors.Primary,
        ),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, FoodAIColors.Primary),
    ) {
        Text(label, style = FoodAITypography.labelLarge)
    }
}

@Composable
fun FoodAIIconButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    androidx.compose.material3.IconButton(
        onClick = onClick,
        modifier = modifier.size(FoodAIDimens.IconButtonSize),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = FoodAIColors.TextPrimary,
        )
    }
}
