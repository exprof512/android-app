package com.foodai.app.core.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

object FoodAIShapes {
    val Chip = RoundedCornerShape(FoodAIDimens.Radius12)
    val Input = RoundedCornerShape(FoodAIDimens.Radius16)
    val Card = RoundedCornerShape(FoodAIDimens.Radius20)
    val CardLarge = RoundedCornerShape(FoodAIDimens.Radius24)
    val Button = RoundedCornerShape(FoodAIDimens.Radius24)
    val Pill = RoundedCornerShape(percent = 50)
    val Tile = RoundedCornerShape(FoodAIDimens.Radius16)
}

val FoodAIMaterialShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = FoodAIShapes.Chip,
    medium = FoodAIShapes.Input,
    large = FoodAIShapes.Card,
    extraLarge = FoodAIShapes.CardLarge,
)
