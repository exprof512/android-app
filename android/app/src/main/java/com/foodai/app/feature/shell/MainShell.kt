package com.foodai.app.feature.shell

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
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
import com.foodai.app.core.ui.FoodAiPrimaryButton
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAiTokens
import com.foodai.app.feature.chat.ChatRoute
import com.foodai.app.feature.plan.TodayRoute
import com.foodai.app.feature.plan.WeekRoute
import com.foodai.app.feature.progress.ProgressRoute
import com.foodai.app.feature.recipe.RecipeRoute
import com.foodai.app.feature.shopping.ShoppingRoute
import com.foodai.app.navigation.Routes

private data class TopTab(
    val route: String,
    val label: String,
    val icon: ImageVector,
)

private val tabs = listOf(
    TopTab(Routes.Home, "Home", Icons.Outlined.Home),
    TopTab(Routes.Plan, "Plan", Icons.Outlined.CalendarMonth),
    TopTab(Routes.Shopping, "Shopping", Icons.Outlined.ShoppingCart),
    TopTab(Routes.Progress, "Progress", Icons.AutoMirrored.Outlined.ShowChart),
    TopTab(Routes.Profile, "Profile", Icons.Outlined.Person),
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
    val hideBottomBar = current?.startsWith("recipe/") == true || current?.startsWith("chat/") == true

    Scaffold(
        containerColor = FoodAiTokens.Mist,
        bottomBar = {
            if (!hideBottomBar) {
                NavigationBar(
                    containerColor = FoodAiTokens.NavBar,
                    tonalElevation = 0.dp,
                ) {
                    tabs.forEach { tab ->
                        val selected = current == tab.route
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(tab.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(FoodAiTokens.RadiusPill.dp))
                                        .background(
                                            if (selected) FoodAiTokens.NavSelected else Color.Transparent,
                                        )
                                        .padding(horizontal = 12.dp, vertical = 6.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Icon(
                                        tab.icon,
                                        contentDescription = tab.label,
                                        tint = if (selected) {
                                            FoodAiTokens.Forest
                                        } else {
                                            FoodAiTokens.Muted
                                        },
                                    )
                                }
                            },
                            label = {
                                Text(
                                    tab.label,
                                    color = if (selected) FoodAiTokens.Forest else FoodAiTokens.Muted,
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                indicatorColor = Color.Transparent,
                            ),
                        )
                    }
                }
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
                )
            }
            composable(Routes.Plan) {
                WeekRoute(
                    onOpenRecipe = { recipeId, itemId ->
                        navController.navigate("recipe/$recipeId?itemId=$itemId")
                    },
                )
            }
            composable(Routes.Shopping) {
                ShoppingRoute()
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
                    onLogout = onLogout,
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
                    onAskAi = { recipeId -> navController.navigate("chat/$recipeId") },
                )
            }
            composable(
                route = "chat/{recipeId}",
                arguments = listOf(navArgument("recipeId") { type = NavType.StringType }),
            ) {
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
    onLogout: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceLg.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineMedium)
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(CircleShape)
                    .background(FoodAiTokens.LeafSoft),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Outlined.Person,
                    contentDescription = null,
                    tint = FoodAiTokens.Forest,
                )
            }
            Column {
                Text(email, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Surface(
                    color = if (tier == "premium") FoodAiTokens.Gold.copy(alpha = 0.2f) else FoodAiTokens.Fog,
                    shape = RoundedCornerShape(FoodAiTokens.RadiusPill.dp),
                ) {
                    Text(
                        text = if (tier == "premium") "Premium" else "Free",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = if (tier == "premium") FoodAiTokens.Gold else FoodAiTokens.Forest,
                    )
                }
            }
        }
        if (tier != "premium") {
            Surface(
                color = FoodAiTokens.LeafSoft,
                shape = RoundedCornerShape(FoodAiTokens.RadiusMd.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(FoodAiTokens.SpaceMd.dp)) {
                    Text("Premium", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Больше генераций плана, замен блюд, чата и перегенерация фото рецептов.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Оплата подключится позже — лимиты уже работают на сервере.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        val goal = profile?.goal
        if (goal != null) {
            Text(
                text = "Цель: ${goal.calorieTargetKcal} ккал · " +
                    "Б ${goal.macroTargetsG.protein} / Ж ${goal.macroTargetsG.fat} / " +
                    "У ${goal.macroTargetsG.carbohydrate}",
                style = MaterialTheme.typography.titleMedium,
            )
        }
        profile?.warnings.orEmpty().forEach { warning ->
            Text(warning, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        FoodAiPrimaryButton(label = "Изменить анкету", onClick = onEditProfile)
        FoodAiPrimaryButton(label = "Выйти", onClick = onLogout)
    }
}
