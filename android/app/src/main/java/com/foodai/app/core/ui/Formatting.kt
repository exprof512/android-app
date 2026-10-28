package com.foodai.app.core.ui

import java.text.NumberFormat
import java.util.Locale

private val RU = Locale("ru")

/** Russian grouping (2 722) instead of the device locale (2,722). */
fun formatKcal(value: Int): String = NumberFormat.getIntegerInstance(RU).format(value)

fun formatMoney(value: Double): String =
    NumberFormat.getNumberInstance(RU).apply {
        maximumFractionDigits = 0
    }.format(value)

fun formatGrams(value: Int): String = "$value г"
