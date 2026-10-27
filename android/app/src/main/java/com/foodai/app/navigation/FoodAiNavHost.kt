package com.foodai.app.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.network.RefreshCoordinator
import com.foodai.app.feature.auth.AuthRoute
import com.foodai.app.feature.boot.BootRoute
import com.foodai.app.feature.onboarding.OnboardingRoute
import com.foodai.app.feature.shell.MainShellRoute
import com.foodai.app.feature.welcome.WelcomeRoute
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent

object Routes {
    const val Welcome = "welcome"
    const val Auth = "auth"
    const val Boot = "boot"
    const val Onboarding = "onboarding"
    const val OnboardingRoute = "onboarding?generatePlan={generatePlan}"
    const val Main = "main"
    const val Home = "home"
    const val Plan = "plan"
    const val Diary = "diary"
    const val Shopping = "shopping"
    const val Progress = "progress"
    const val Profile = "profile"
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AuthRepositoryEntryPoint {
    fun authRepository(): AuthRepository
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface SessionEntryPoint {
    fun refreshCoordinator(): RefreshCoordinator
}

@Composable
fun FoodAiNavHost() {
    val navController = rememberNavController()
    val context = LocalContext.current.applicationContext
    val start = remember {
        val repo = EntryPointAccessors.fromApplication(
            context,
            AuthRepositoryEntryPoint::class.java,
        ).authRepository()
        if (repo.hasSession()) Routes.Boot else Routes.Welcome
    }
    val sessionExpired = remember {
        EntryPointAccessors.fromApplication(
            context,
            SessionEntryPoint::class.java,
        ).refreshCoordinator().sessionExpired
    }

    LaunchedEffect(sessionExpired) {
        sessionExpired.collect {
            if (navController.currentDestination?.route != Routes.Welcome) {
                navController.navigate(Routes.Welcome) {
                    popUpTo(navController.graph.id) { inclusive = true }
                    launchSingleTop = true
                }
            }
        }
    }

    NavHost(navController = navController, startDestination = start) {
        composable(Routes.Welcome) {
            WelcomeRoute(
                onStart = {
                    navController.navigate(Routes.Auth) {
                        popUpTo(Routes.Welcome) { inclusive = true }
                    }
                },
                onLogin = {
                    navController.navigate(Routes.Auth) {
                        popUpTo(Routes.Welcome) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.Auth) {
            AuthRoute(
                onSignedIn = {
                    navController.navigate(Routes.Boot) {
                        popUpTo(Routes.Auth) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.Boot) {
            BootRoute(
                onOnboarding = {
                    navController.navigate("onboarding?generatePlan=true") {
                        popUpTo(Routes.Boot) { inclusive = true }
                    }
                },
                onMain = {
                    navController.navigate(Routes.Main) {
                        popUpTo(Routes.Boot) { inclusive = true }
                    }
                },
                onSignedOut = {
                    navController.navigate(Routes.Welcome) {
                        popUpTo(Routes.Boot) { inclusive = true }
                    }
                },
            )
        }
        composable(
            route = Routes.OnboardingRoute,
            arguments = listOf(
                navArgument("generatePlan") {
                    type = NavType.BoolType
                    defaultValue = true
                },
            ),
        ) { entry ->
            val generatePlan = entry.arguments?.getBoolean("generatePlan") ?: true
            OnboardingRoute(
                generatePlan = generatePlan,
                onFinished = {
                    navController.navigate(Routes.Main) {
                        popUpTo(Routes.OnboardingRoute) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.Main) {
            MainShellRoute(
                onSignedOut = {
                    navController.navigate(Routes.Welcome) {
                        popUpTo(Routes.Main) { inclusive = true }
                    }
                },
                onEditProfile = {
                    navController.navigate("onboarding?generatePlan=false")
                },
            )
        }
    }
}
