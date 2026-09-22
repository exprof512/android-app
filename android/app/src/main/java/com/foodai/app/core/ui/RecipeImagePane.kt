package com.foodai.app.core.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.SubcomposeAsyncImage
import com.foodai.app.core.network.RecipeImageDto
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun RecipeImagePane(
    image: RecipeImageDto?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    useFull: Boolean = false,
    enforceAspect: Boolean = true,
) {
    val status = image?.status ?: "pending"
    val url = if (useFull) image?.url else (image?.thumbnailUrl ?: image?.url)
    val base = if (enforceAspect) {
        modifier.fillMaxWidth().aspectRatio(4f / 3f)
    } else {
        modifier
    }
    Box(
        modifier = base
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.PrimarySoft),
        contentAlignment = Alignment.Center,
    ) {
        when {
            status == "ready" && !url.isNullOrBlank() -> {
                SubcomposeAsyncImage(
                    model = url,
                    contentDescription = contentDescription,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                    loading = {
                        CircularProgressIndicator(
                            color = FoodAIColors.Primary,
                            strokeWidth = 2.dp,
                        )
                    },
                    error = {
                        Text(
                            "Фото недоступно",
                            modifier = Modifier.padding(12.dp),
                            style = FoodAITypography.bodySmall,
                            color = FoodAIColors.TextSecondary,
                        )
                    },
                )
            }
            status == "failed" -> Text(
                "Фото недоступно",
                modifier = Modifier.padding(12.dp),
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
            else -> Text(
                "Готовим фото блюда…",
                modifier = Modifier.padding(12.dp),
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
    }
}
