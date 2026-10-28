package com.foodai.app.core.diary

import android.content.Context
import com.foodai.app.core.network.NutritionLogDto
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json

/** Last successfully loaded diary day, so offline users still see their food. */
@Singleton
class DiaryCacheStore @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val prefs = context.getSharedPreferences("foodai_diary_cache", Context.MODE_PRIVATE)
    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    fun save(date: String, logs: List<NutritionLogDto>) {
        runCatching {
            prefs.edit()
                .putString(key(date), json.encodeToString(ListSerializer, logs))
                .apply()
        }
    }

    fun load(date: String): List<NutritionLogDto>? = runCatching {
        prefs.getString(key(date), null)
            ?.let { json.decodeFromString(ListSerializer, it) }
    }.getOrNull()

    private fun key(date: String) = "day_$date"

    private companion object {
        val ListSerializer = kotlinx.serialization.builtins.ListSerializer(
            NutritionLogDto.serializer(),
        )
    }
}
