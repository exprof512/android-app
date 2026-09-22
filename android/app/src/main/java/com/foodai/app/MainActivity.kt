package com.foodai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import com.foodai.app.core.ui.theme.FoodAiTheme
import com.foodai.app.navigation.FoodAiNavHost
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Keep resize-on-IME behaviour working with Compose (chat input stays visible).
        WindowCompat.setDecorFitsSystemWindows(window, true)
        setContent {
            FoodAiTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    FoodAiNavHost()
                }
            }
        }
    }
}
