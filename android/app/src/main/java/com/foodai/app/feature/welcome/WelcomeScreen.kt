package com.foodai.app.feature.welcome

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.Spa
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.foodai.app.R
import com.foodai.app.core.ui.components.FoodAILogo
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun WelcomeRoute(
    onStart: () -> Unit,
    onLogin: () -> Unit,
) {
    WelcomeScreen(onStart = onStart, onLogin = onLogin)
}

@Composable
fun WelcomeScreen(
    onStart: () -> Unit,
    onLogin: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = FoodAIDimens.ScreenPadding)
            .padding(top = FoodAIDimens.Space24, bottom = FoodAIDimens.Space24)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        FoodAILogo(markSize = 48.dp, textSize = 28.sp)
        Spacer(Modifier.height(FoodAIDimens.Space20))
        Text(
            text = "Твой персональный\nAI-помощник по питанию",
            style = FoodAITypography.headlineMedium,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text(
            text = "Вкусные рецепты. Реальные результаты.\nПросто, удобно, для тебя.",
            style = FoodAITypography.bodyMedium,
            color = FoodAIColors.TextSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(FoodAIDimens.Space24))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            FeatureTile("Персональные\nпланы", Icons.AutoMirrored.Outlined.ShowChart, Modifier.weight(1f))
            FeatureTile("Вкусные\nрецепты", Icons.Outlined.Restaurant, Modifier.weight(1f))
            FeatureTile("Списки\nпокупок", Icons.Outlined.ShoppingCart, Modifier.weight(1f))
            FeatureTile("Здоровые\nпривычки", Icons.Outlined.Spa, Modifier.weight(1f))
        }
        Spacer(Modifier.height(FoodAIDimens.Space24))
        Box(contentAlignment = Alignment.TopEnd) {
            Image(
                painter = painterResource(R.drawable.img_hero_bowl),
                contentDescription = "Здоровое блюдо",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(220.dp)
                    .clip(CircleShape),
            )
            Text(
                text = "Вкусно. Полезно.\nПросто. ♡",
                color = FoodAIColors.PrimaryDark,
                style = FoodAITypography.bodySmall,
                fontWeight = FontWeight.Medium,
                textAlign = TextAlign.End,
                modifier = Modifier.padding(top = 8.dp, end = 4.dp),
            )
        }
        Spacer(Modifier.height(FoodAIDimens.Space32))
        FoodAIPrimaryButton(label = "Начать", onClick = onStart, showArrow = true)
        Spacer(Modifier.height(FoodAIDimens.Space8))
        TextButton(onClick = onLogin) {
            Text(
                text = buildAnnotatedString {
                    append("Уже есть аккаунт? ")
                    withStyle(SpanStyle(color = FoodAIColors.Primary, fontWeight = FontWeight.Bold)) {
                        append("Войти")
                    }
                },
                color = FoodAIColors.TextSecondary,
                style = FoodAITypography.bodyLarge,
            )
        }
    }
}

@Composable
private fun FeatureTile(
    label: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(52.dp)
                .clip(FoodAIShapes.Tile)
                .background(FoodAIColors.PrimarySoft),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = FoodAIColors.Primary, modifier = Modifier.size(26.dp))
        }
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text(
            label,
            style = FoodAITypography.labelMedium,
            color = FoodAIColors.TextSecondary,
            textAlign = TextAlign.Center,
            maxLines = 2,
        )
    }
}
