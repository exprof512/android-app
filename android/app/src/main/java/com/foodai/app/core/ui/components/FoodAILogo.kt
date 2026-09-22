package com.foodai.app.core.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.foodai.app.R
import com.foodai.app.core.ui.theme.FoodAIColors

/**
 * App mark + wordmark. Uses transparent vector mark (not PNG with opaque bg).
 * Do not reuse as a hero food visual.
 */
@Composable
fun FoodAILogo(
    modifier: Modifier = Modifier,
    markSize: Dp = 40.dp,
    textSize: TextUnit = 28.sp,
    showWordmark: Boolean = true,
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.ic_foodai_mark),
            contentDescription = "FoodAI",
            modifier = Modifier.size(markSize),
        )
        if (showWordmark) {
            Text(
                text = buildAnnotatedString {
                    withStyle(
                        SpanStyle(
                            color = FoodAIColors.TextPrimary,
                            fontWeight = FontWeight.Bold,
                            fontSize = textSize,
                        ),
                    ) {
                        append("Food")
                    }
                    withStyle(
                        SpanStyle(
                            color = FoodAIColors.Primary,
                            fontWeight = FontWeight.Bold,
                            fontSize = textSize,
                        ),
                    ) {
                        append("AI")
                    }
                },
            )
        }
    }
}
