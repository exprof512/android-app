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

/** Russian plural for a day counter: 1 день, 2 дня, 5 дней. */
fun daysWord(value: Int): String {
    val mod10 = value % 10
    val mod100 = value % 100
    return when {
        mod10 == 1 && mod100 != 11 -> "день"
        mod10 in 2..4 && mod100 !in 12..14 -> "дня"
        else -> "дней"
    }
}
