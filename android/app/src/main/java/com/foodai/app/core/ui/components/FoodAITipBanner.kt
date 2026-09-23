package com.foodai.app.core.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

/** Soft tip banner controlled by Settings → «Подсказки в приложении». */
@Composable
fun FoodAITipBanner(
    tipId: String,
    text: String,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("foodai_settings", android.content.Context.MODE_PRIVATE)
    }
    val tipsEnabled = prefs.getBoolean("tips_enabled", true)
    var dismissed by remember(tipId) {
        mutableStateOf(prefs.getBoolean("tip_dismissed_$tipId", false))
    }
    AnimatedVisibility(visible = tipsEnabled && !dismissed, modifier = modifier) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(FoodAIShapes.Card)
                .background(FoodAIColors.PrimarySoft)
                .padding(horizontal = FoodAIDimens.Space12, vertical = FoodAIDimens.Space8),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            Icon(
                Icons.Outlined.Lightbulb,
                contentDescription = null,
                tint = FoodAIColors.Primary,
                modifier = Modifier.size(20.dp),
            )
            Text(
                text = text,
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.PrimaryDark,
                modifier = Modifier.weight(1f),
            )
            IconButton(
                onClick = {
                    dismissed = true
                    prefs.edit().putBoolean("tip_dismissed_$tipId", true).apply()
                },
                modifier = Modifier.size(32.dp),
            ) {
                Icon(Icons.Filled.Close, contentDescription = "Скрыть подсказку", tint = FoodAIColors.TextMuted)
            }
        }
    }
}
