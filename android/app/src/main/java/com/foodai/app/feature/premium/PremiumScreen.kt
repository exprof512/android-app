package com.foodai.app.feature.premium

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.Analytics
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.SmartToy
import androidx.compose.material.icons.outlined.SupportAgent
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.components.FoodAIInfoCard
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.components.FoodAISecondaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PremiumRoute(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Premium") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        PremiumScreen(modifier = Modifier.padding(padding))
    }
}

@Composable
fun PremiumScreen(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
    ) {
        Text("👑  Premium", style = FoodAITypography.headlineMedium)
        Text("Больше возможностей для твоих целей", style = FoodAITypography.titleMedium)
        Text(
            "Персональные планы, больше рецептов и безлимитный AI-помощник.",
            style = FoodAITypography.bodyMedium,
            color = FoodAIColors.TextSecondary,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            Feature("1000+ рецептов", Icons.Outlined.Restaurant, Modifier.weight(1f))
            Feature("Безлимитный AI", Icons.Outlined.SmartToy, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            Feature("Планы на любой случай", Icons.Outlined.CalendarMonth, Modifier.weight(1f))
            Feature("Аналитика", Icons.Outlined.Analytics, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            Feature("Умный шопинг", Icons.Outlined.ShoppingCart, Modifier.weight(1f))
            Feature("Приоритетная поддержка", Icons.Outlined.SupportAgent, Modifier.weight(1f))
        }
        PlanCard(
            title = "Базовый",
            price = "Бесплатно",
            subtitle = "Текущий",
            highlight = false,
            cta = "Текущий план",
            enabled = false,
        )
        PlanCard(
            title = "Premium",
            price = "Цена из конфигурации",
            subtitle = "Популярный",
            highlight = true,
            cta = "Выбрать план",
            enabled = true,
        )
        PlanCard(
            title = "Premium+",
            price = "Цена из конфигурации",
            subtitle = "Годовой",
            highlight = false,
            cta = "Выбрать план",
            enabled = true,
        )
        FoodAIInfoCard(text = "Фактические цены подключаются из backend/конфигурации. Макетные суммы на reference — только design placeholder.")
    }
}

@Composable
private fun Feature(label: String, icon: ImageVector, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.PrimarySoft)
            .padding(FoodAIDimens.Space12),
    ) {
        Icon(icon, null, tint = FoodAIColors.Primary)
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text(label, style = FoodAITypography.titleSmall)
    }
}

@Composable
private fun PlanCard(
    title: String,
    price: String,
    subtitle: String,
    highlight: Boolean,
    cta: String,
    enabled: Boolean,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .then(
                if (highlight) {
                    Modifier.border(2.dp, FoodAIColors.Primary, FoodAIShapes.CardLarge)
                } else {
                    Modifier.border(1.dp, FoodAIColors.Divider, FoodAIShapes.CardLarge)
                },
            )
            .padding(FoodAIDimens.Space16),
    ) {
        Text(subtitle, style = FoodAITypography.labelMedium, color = FoodAIColors.Primary)
        Text(title, style = FoodAITypography.titleLarge)
        Text(price, style = FoodAITypography.headlineSmall)
        Spacer(Modifier.height(FoodAIDimens.Space12))
        if (enabled) {
            FoodAIPrimaryButton(label = cta, onClick = {}, showArrow = false)
        } else {
            FoodAISecondaryButton(label = cta, onClick = {})
        }
    }
}
