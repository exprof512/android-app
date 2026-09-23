package com.foodai.app.core.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun FoodAIHeader(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier,
    trailing: @Composable (() -> Unit)? = null,
) {
    Row(modifier = modifier.fillMaxWidth()) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = FoodAITypography.headlineMedium)
            Spacer(Modifier.height(FoodAIDimens.Space8))
            Text(subtitle, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
        }
        if (trailing != null) {
            trailing()
        }
    }
}

@Composable
fun FoodAIOnboardingTopBar(
    step: Int,
    total: Int,
    onBack: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
    ) {
        if (onBack != null) {
            Box(
                modifier = Modifier
                    .size(FoodAIDimens.IconButtonSize)
                    .clip(CircleShape)
                    .background(FoodAIColors.SurfaceMuted)
                    .clickable(role = Role.Button, onClick = onBack),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Назад",
                    tint = FoodAIColors.TextPrimary,
                )
            }
        } else {
            Spacer(Modifier.size(FoodAIDimens.IconButtonSize))
        }
        FoodAIStepIndicator(
            step = step,
            total = total,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = "$step из $total",
            style = FoodAITypography.labelMedium,
            color = FoodAIColors.TextSecondary,
        )
    }
}

@Composable
fun FoodAIInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    singleLine: Boolean = true,
    placeholder: String? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.fillMaxWidth(),
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        singleLine = singleLine,
        minLines = if (singleLine) 1 else 3,
        shape = FoodAIShapes.Input,
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = FoodAIColors.Primary,
            unfocusedBorderColor = FoodAIColors.Divider,
            focusedContainerColor = FoodAIColors.Surface,
            unfocusedContainerColor = FoodAIColors.SurfaceMuted,
            cursorColor = FoodAIColors.Primary,
            focusedLabelColor = FoodAIColors.Primary,
        ),
    )
}

@Composable
fun FoodAISearchField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.fillMaxWidth(),
        placeholder = { Text(placeholder, color = FoodAIColors.TextMuted) },
        singleLine = true,
        shape = FoodAIShapes.Pill,
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = FoodAIColors.Primary,
            unfocusedBorderColor = Color.Transparent,
            focusedContainerColor = FoodAIColors.SurfaceMuted,
            unfocusedContainerColor = FoodAIColors.SurfaceMuted,
            cursorColor = FoodAIColors.Primary,
        ),
    )
}

@Composable
fun FoodAIStepper(
    label: String,
    value: String,
    unit: String,
    onDecrement: () -> Unit,
    onIncrement: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(label, style = FoodAITypography.titleMedium)
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(FoodAIShapes.Card)
                .background(FoodAIColors.SurfaceMuted)
                .padding(horizontal = FoodAIDimens.Space12, vertical = FoodAIDimens.Space8),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            StepperIconButton(Icons.Filled.Remove, "Меньше", onDecrement)
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    text = value,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = FoodAIColors.TextPrimary,
                )
                Spacer(Modifier.size(6.dp))
                Text(unit, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
            }
            StepperIconButton(Icons.Filled.Add, "Больше", onIncrement)
        }
    }
}

@Composable
private fun StepperIconButton(
    icon: ImageVector,
    description: String,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .size(40.dp)
            .clip(CircleShape)
            .background(FoodAIColors.Divider)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = description, tint = FoodAIColors.TextPrimary)
    }
}

@Composable
fun FoodAISelectableOption(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
) {
    val bg = if (selected) FoodAIColors.PrimarySoft else FoodAIColors.SurfaceMuted
    val border = if (selected) FoodAIColors.Primary else Color.Transparent
    val content = if (selected) FoodAIColors.Primary else FoodAIColors.TextPrimary
    Row(
        modifier = modifier
            .clip(FoodAIShapes.Card)
            .background(bg)
            .border(2.dp, border, FoodAIShapes.Card)
            .clickable(role = Role.RadioButton, onClick = onClick)
            .padding(horizontal = FoodAIDimens.Space16, vertical = FoodAIDimens.Space12),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = content, modifier = Modifier.size(18.dp))
            Spacer(Modifier.size(FoodAIDimens.Space8))
        }
        Text(label, style = FoodAITypography.titleSmall, color = content)
    }
}

@Composable
fun FoodAIChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val bg = if (selected) FoodAIColors.PrimarySoft else FoodAIColors.Surface
    val border = if (selected) FoodAIColors.Primary else FoodAIColors.Divider
    Box(
        modifier = modifier
            .clip(FoodAIShapes.Tile)
            .background(bg)
            .border(if (selected) 2.dp else 1.dp, border, FoodAIShapes.Tile)
            .clickable(onClick = onClick)
            .padding(FoodAIDimens.Space12),
        contentAlignment = Alignment.Center,
    ) {
        if (selected) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(18.dp)
                    .clip(CircleShape)
                    .background(FoodAIColors.Primary),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.Check,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(12.dp),
                )
            }
        }
        Text(label, style = FoodAITypography.titleSmall, color = FoodAIColors.TextPrimary)
    }
}

@Composable
fun FoodAIAvatar(
    initials: String,
    modifier: Modifier = Modifier,
    imagePath: String? = null,
    size: androidx.compose.ui.unit.Dp = 56.dp,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .background(FoodAIColors.PrimaryLight),
        contentAlignment = Alignment.Center,
    ) {
        if (!imagePath.isNullOrBlank()) {
            coil.compose.AsyncImage(
                model = java.io.File(imagePath),
                contentDescription = null,
                contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                modifier = Modifier
                    .size(size)
                    .clip(CircleShape),
            )
        } else {
            Text(
                text = initials.take(2).uppercase(),
                style = if (size >= 72.dp) FoodAITypography.headlineSmall else FoodAITypography.titleMedium,
                color = FoodAIColors.PrimaryDark,
            )
        }
    }
}
