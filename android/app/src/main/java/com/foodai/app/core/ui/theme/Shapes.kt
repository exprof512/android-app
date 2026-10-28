package com.foodai.app.core.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

object FoodAIShapes {
    val Chip = RoundedCornerShape(12.dp)
    val Input = RoundedCornerShape(16.dp)
    val Card = RoundedCornerShape(22.dp)
    val CardLarge = RoundedCornerShape(28.dp)
    val Button = RoundedCornerShape(percent = 50)
    val Pill = RoundedCornerShape(percent = 50)
    val Tile = RoundedCornerShape(18.dp)
}

val FoodAIMaterialShapes = Shapes(
    extraSmall = RoundedCornerShape(10.dp),
    small = FoodAIShapes.Chip,
    medium = FoodAIShapes.Tile,
    large = FoodAIShapes.Card,
    extraLarge = FoodAIShapes.CardLarge,
)
