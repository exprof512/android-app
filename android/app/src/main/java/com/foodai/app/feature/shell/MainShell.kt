package com.foodai.app.feature.shell

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import com.foodai.app.core.ui.theme.FoodAiTokens
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
            profile = state.profile,
            onLogout = { viewModel.logout(onSignedOut) },
            onEditProfile = onEditProfile,
        )
    }
}

@Composable
fun MainShell(
    email: String,
    profile: ProfileResponse?,
    onLogout: () -> Unit,
    onEditProfile: () -> Unit,
) {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val current = backStack?.destination?.route
    val hideBottomBar = current?.startsWith("recipe/") == true

    Scaffold(
        bottomBar = {
            if (!hideBottomBar) {
                NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = current == tab.route,
                            onClick = {
                                navController.navigate(tab.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
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
                RecipeRoute(onBack = { navController.popBackStack() })
            }
        }
    }
}

@Composable
private fun ProfilePane(
    email: String,
    profile: ProfileResponse?,
    onEditProfile: () -> Unit,
    onLogout: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceLg.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
        horizontalAlignment = Alignment.Start,
    ) {
        Text("Profile", style = MaterialTheme.typography.headlineMedium)
        Text(
            text = email,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
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
        OutlinedButton(onClick = onEditProfile) {
            Text("Изменить анкету")
        }
        Button(onClick = onLogout) {
            Text("Выйти")
        }
    }
}

@Composable
private fun PlaceholderPane(title: String, body: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceLg.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(title, style = MaterialTheme.typography.headlineMedium)
        Text(
            text = body,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 8.dp),
        )
    }
}
