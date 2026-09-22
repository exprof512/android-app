package com.foodai.app.feature.shell

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ExitToApp
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.FitnessCenter
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.LocalFireDepartment
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.TrackChanges
import androidx.compose.material.icons.outlined.WaterDrop
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.components.FoodAIAvatar
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAILinearProgress
import com.foodai.app.core.ui.components.FoodAINavItem
import com.foodai.app.core.ui.components.FoodAINavigationBar
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import com.foodai.app.feature.chat.ChatRoute
import com.foodai.app.feature.plan.TodayRoute
import com.foodai.app.feature.plan.WeekRoute
import com.foodai.app.feature.progress.ProgressRoute
import com.foodai.app.feature.recipe.RecipeRoute
import com.foodai.app.feature.shopping.ShoppingRoute
import com.foodai.app.navigation.Routes

private val mainTabs = listOf(
    FoodAINavItem(Routes.Home, "Сегодня", Icons.Outlined.Home),
    FoodAINavItem(Routes.Plan, "План", Icons.Outlined.CalendarMonth),
    FoodAINavItem(Routes.Progress, "Прогресс", Icons.AutoMirrored.Outlined.ShowChart),
    FoodAINavItem(Routes.Profile, "Профиль", Icons.Outlined.Person),
)

@Composable
fun MainShellRoute(
    onSignedOut: () -> Unit,
    onEditProfile: () -> Unit,
    viewModel: SessionViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading && state.user == null -> LoadingPane("Проверяем сессию…")
        state.error != null && state.user == null -> ErrorPane(
            message = state.error ?: "Ошибка сессии",
            onRetry = viewModel::refresh,
        )
        else -> MainShell(
            email = state.user?.email ?: "—",
            tier = state.user?.tier ?: "free",
            profile = state.profile,
            onLogout = { viewModel.logout(onSignedOut) },
            onEditProfile = onEditProfile,
        )
    }
}

@Composable
fun MainShell(
    email: String,
    tier: String,
    profile: ProfileResponse?,
    onLogout: () -> Unit,
    onEditProfile: () -> Unit,
) {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val current = backStack?.destination?.route
    val hideBottomBar = current?.startsWith("recipe/") == true ||
        current?.startsWith("chat") == true ||
        current == "premium" ||
        current == Routes.Shopping

    Scaffold(
        containerColor = FoodAIColors.Background,
        bottomBar = {
            if (!hideBottomBar) {
                FoodAINavigationBar(
                    items = mainTabs,
                    currentRoute = current,
                    onSelect = { route ->
                        navController.navigate(route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onFabClick = { navController.navigate("chat") },
                )
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.Home,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.Home) {
                TodayRoute(
                    onOpenRecipe = { recipeId, itemId ->
                        navController.navigate("recipe/$recipeId?itemId=$itemId")
                    },
                    onOpenShopping = { navController.navigate(Routes.Shopping) },
                )
            }
            composable(Routes.Plan) {
                WeekRoute(
                    onOpenRecipe = { recipeId, itemId ->
                        navController.navigate("recipe/$recipeId?itemId=$itemId")
                    },
                    onOpenShopping = { navController.navigate(Routes.Shopping) },
                )
            }
            composable(Routes.Shopping) {
                ShoppingRoute(onBack = { navController.popBackStack() })
            }
            composable(Routes.Progress) {
                ProgressRoute()
            }
            composable(Routes.Profile) {
                ProfilePane(
                    email = email,
                    tier = tier,
                    profile = profile,
                    onEditProfile = onEditProfile,
                    onPremium = { navController.navigate("premium") },
                    onLogout = onLogout,
                )
            }
            composable("premium") {
                com.foodai.app.feature.premium.PremiumRoute(
                    onBack = { navController.popBackStack() },
                )
            }
            composable(
                route = "recipe/{recipeId}?itemId={itemId}",
                arguments = listOf(
                    navArgument("recipeId") { type = NavType.StringType },
                    navArgument("itemId") {
                        type = NavType.StringType
                        nullable = true
                        defaultValue = null
                    },
                ),
            ) {
                RecipeRoute(
                    onBack = { navController.popBackStack() },
                    onAskAi = { recipeId, itemId ->
                        val path = if (itemId.isNullOrBlank()) {
                            "chat?recipeId=$recipeId"
                        } else {
                            "chat?recipeId=$recipeId&itemId=$itemId"
                        }
                        navController.navigate(path)
                    },
                )
            }
            composable(
                route = "chat?recipeId={recipeId}&itemId={itemId}",
                arguments = listOf(
                    navArgument("recipeId") {
                        type = NavType.StringType
                        nullable = true
                        defaultValue = null
                    },
                    navArgument("itemId") {
                        type = NavType.StringType
                        nullable = true
                        defaultValue = null
                    },
                ),
            ) {
                ChatRoute(onBack = { navController.popBackStack() })
            }
            composable("chat") {
                ChatRoute(onBack = { navController.popBackStack() })
            }
        }
    }
}

@Composable
private fun ProfilePane(
    email: String,
    tier: String,
    profile: ProfileResponse?,
    onEditProfile: () -> Unit,
    onPremium: () -> Unit,
    onLogout: () -> Unit,
) {
    val name = email.substringBefore("@").replaceFirstChar { it.uppercase() }
    val p = profile?.profile
    val goal = profile?.goal
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text("Профиль", style = FoodAITypography.headlineMedium)
                Text(
                    "Твои цели. Твой прогресс. Твоя лучшая версия.",
                    style = FoodAITypography.bodyMedium,
                    color = FoodAIColors.TextSecondary,
                )
            }
            Row(
                modifier = Modifier
                    .clip(FoodAIShapes.Pill)
                    .background(FoodAIColors.PrimarySoft)
                    .clickable(onClick = onEditProfile)
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Icon(Icons.Outlined.Settings, null, tint = FoodAIColors.Primary, modifier = Modifier.size(18.dp))
                Text("Настройки", color = FoodAIColors.Primary, style = FoodAITypography.labelMedium)
            }
        }

        FoodAICard(onClick = onEditProfile) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                FoodAIAvatar(initials = name.take(2))
                Spacer(Modifier.size(FoodAIDimens.Space12))
                Column(Modifier.weight(1f)) {
                    Text(name, style = FoodAITypography.titleLarge)
                    Text(
                        "Стремлюсь к здоровью, энергии и большим целям",
                        style = FoodAITypography.bodySmall,
                    )
                    if (p != null) {
                        Spacer(Modifier.height(FoodAIDimens.Space8))
                        Text(
                            listOfNotNull(
                                p.ageYears?.let { "$it года" },
                                p.heightCm?.let { "${it.toInt()} см" },
                                p.currentWeightKg?.let { "${it.toInt()} кг" },
                            ).joinToString(" · "),
                            style = FoodAITypography.bodySmall,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                }
                Icon(Icons.Outlined.ChevronRight, null, tint = FoodAIColors.TextMuted)
            }
        }

        if (goal != null) {
            FoodAICard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.TrackChanges, null, tint = FoodAIColors.Primary)
                    Spacer(Modifier.size(FoodAIDimens.Space8))
                    Column(Modifier.weight(1f)) {
                        Text("Моя цель", style = FoodAITypography.titleMedium)
                        Text(
                            "${goal.calorieTargetKcal} ккал/день",
                            style = FoodAITypography.bodySmall,
                        )
                    }
                    Text(
                        "Изменить",
                        color = FoodAIColors.Primary,
                        style = FoodAITypography.labelMedium,
                        modifier = Modifier.clickable(onClick = onEditProfile),
                    )
                }
                Spacer(Modifier.height(FoodAIDimens.Space12))
                FoodAILinearProgress(progress = 0.35f)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text(
                            "${p?.currentWeightKg?.toInt() ?: "—"} кг",
                            style = FoodAITypography.titleMedium,
                        )
                        Text("Текущий вес", style = FoodAITypography.bodySmall)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            "${goal.targetWeightKg?.toInt() ?: "—"} кг",
                            style = FoodAITypography.titleMedium,
                        )
                        Text("Целевой вес", style = FoodAITypography.bodySmall)
                    }
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            MetricMini("Ккал", "${goal?.calorieTargetKcal ?: "—"}", Icons.Outlined.LocalFireDepartment, Modifier.weight(1f))
            MetricMini("Активность", "3–4", Icons.Outlined.FitnessCenter, Modifier.weight(1f))
            MetricMini("Вода", "2.0 л", Icons.Outlined.WaterDrop, Modifier.weight(1f))
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(FoodAIShapes.CardLarge)
                .background(FoodAIColors.PrimarySoft)
                .padding(FoodAIDimens.Space16),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Премиум", style = FoodAITypography.titleMedium, color = FoodAIColors.PrimaryDark)
                    Text(
                        "Больше рецептов, персональные рекомендации и AI-помощник.",
                        style = FoodAITypography.bodySmall,
                    )
                    if (tier != "free") {
                        Text("Активен · $tier", style = FoodAITypography.labelMedium, color = FoodAIColors.Primary)
                    }
                }
                FoodAIPrimaryButton(
                    label = "Управлять",
                    onClick = onPremium,
                    showArrow = false,
                    fullWidth = false,
                    modifier = Modifier.width(140.dp),
                )
            }
        }

        ProfileMenuItem("Мои данные", "Возраст, рост, вес, цели", Icons.Outlined.Person, onEditProfile)
        ProfileMenuItem("Уведомления", "Напоминания, советы, мотивация", Icons.Outlined.Notifications, onEditProfile)
        ProfileMenuItem(
            "Выйти из аккаунта",
            null,
            Icons.AutoMirrored.Outlined.ExitToApp,
            onLogout,
            danger = true,
        )
        Spacer(Modifier.height(FoodAIDimens.Space24))
    }
}

@Composable
private fun MetricMini(
    title: String,
    value: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space12),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(icon, null, tint = FoodAIColors.Primary, modifier = Modifier.size(20.dp))
        Spacer(Modifier.height(4.dp))
        Text(value, style = FoodAITypography.titleSmall)
        Text(title, style = FoodAITypography.labelSmall)
    }
}

@Composable
private fun ProfileMenuItem(
    title: String,
    subtitle: String?,
    icon: ImageVector,
    onClick: () -> Unit,
    danger: Boolean = false,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .clickable(onClick = onClick)
            .padding(FoodAIDimens.Space16),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            icon,
            null,
            tint = if (danger) FoodAIColors.Error else FoodAIColors.TextSecondary,
            modifier = Modifier.size(22.dp),
        )
        Spacer(Modifier.size(FoodAIDimens.Space12))
        Column(Modifier.weight(1f)) {
            Text(
                title,
                style = FoodAITypography.titleMedium,
                color = if (danger) FoodAIColors.Error else FoodAIColors.TextPrimary,
            )
            if (subtitle != null) {
                Text(subtitle, style = FoodAITypography.bodySmall)
            }
        }
        if (!danger) {
            Icon(Icons.Outlined.ChevronRight, null, tint = FoodAIColors.TextMuted)
        }
    }
}
