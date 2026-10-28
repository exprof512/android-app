package com.foodai.app.core.prices

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

data class ManualPrice(
    val store: String,
    val product: String,
    /** Price per 100 g/ml, or per piece for "pcs". */
    val price: Double,
)

/**
 * On-device price book: preferred stores from onboarding + user-entered prices.
 * Prices are local-first; no store API is required.
 */
@Singleton
class PriceBookStore @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val prefs = context.getSharedPreferences("foodai_price_book", Context.MODE_PRIVATE)

    fun stores(): List<String> =
        prefs.getStringSet(KEY_STORES, emptySet()).orEmpty().sorted()

    fun saveStores(stores: Set<String>) {
        prefs.edit().putStringSet(KEY_STORES, stores).apply()
    }

    fun prices(): List<ManualPrice> =
        prefs.getString(KEY_PRICES, null)
            .orEmpty()
            .lineSequence()
            .mapNotNull { line ->
                val parts = line.split('\t')
                if (parts.size != 3) return@mapNotNull null
                val price = parts[2].toDoubleOrNull() ?: return@mapNotNull null
                ManualPrice(store = parts[0], product = parts[1], price = price)
            }
            .toList()

    fun priceFor(store: String?, product: String): Double? {
        if (store.isNullOrBlank()) return null
        val key = product.trim().lowercase()
        return prices()
            .firstOrNull { it.store == store && it.product.equals(key, ignoreCase = true) }
            ?.price
    }

    fun upsert(store: String, product: String, price: Double) {
        if (store.isBlank() || product.isBlank() || price <= 0) return
        val normalized = product.trim().lowercase()
        val next = prices()
            .filterNot { it.store == store && it.product.equals(normalized, ignoreCase = true) } +
            ManualPrice(store = store, product = normalized, price = price)
        write(next)
    }

    fun remove(store: String, product: String) {
        write(prices().filterNot { it.store == store && it.product.equals(product, ignoreCase = true) })
    }

    private fun write(rows: List<ManualPrice>) {
        val payload = rows.joinToString("\n") { "${it.store}\t${it.product}\t${it.price}" }
        prefs.edit().putString(KEY_PRICES, payload).apply()
    }

    private companion object {
        const val KEY_STORES = "stores"
        const val KEY_PRICES = "prices"
    }
}
