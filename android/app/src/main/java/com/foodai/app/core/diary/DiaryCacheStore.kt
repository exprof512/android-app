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

    init {
        // Drop pre-user-scoping keys: they may belong to a previous account.
        val legacy = prefs.all.keys.filter { !it.contains(':') }
        if (legacy.isNotEmpty()) {
            prefs.edit().apply { legacy.forEach { remove(it) } }.apply()
        }
    }

    fun save(userId: String?, date: String, logs: List<NutritionLogDto>) {
        runCatching {
            prefs.edit()
                .putString(key(userId, date), json.encodeToString(ListSerializer, logs))
                .apply()
        }
    }

    fun load(userId: String?, date: String): List<NutritionLogDto>? = runCatching {
        prefs.getString(key(userId, date), null)
            ?.let { json.decodeFromString(ListSerializer, it) }
    }.getOrNull()

    private fun key(userId: String?, date: String) = "${userId ?: "anon"}:day_$date"

    private companion object {
        val ListSerializer = kotlinx.serialization.builtins.ListSerializer(
            NutritionLogDto.serializer(),
        )
    }
}
