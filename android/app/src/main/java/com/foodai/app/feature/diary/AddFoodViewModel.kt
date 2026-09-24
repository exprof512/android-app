package com.foodai.app.feature.diary

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.FoodCalculateRequest
import com.foodai.app.core.network.FoodSearchHitDto
import com.foodai.app.core.network.NutritionApi
import com.foodai.app.core.network.NutritionLogCreateRequest
import com.foodai.app.core.network.PhotoAnalyzeDto
import com.foodai.app.core.network.PhotoConfirmItemDto
import com.foodai.app.core.network.PhotoConfirmRequest
import com.foodai.app.core.network.PhotoItemDto
import com.foodai.app.core.network.RecentFoodDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.time.LocalDate
import java.util.UUID
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

data class PhotoReviewItem(
    val name: String,
    val ingredientId: String?,
    val grams: Double,
    val caloriesKcal: Int?,
    val proteinG: Double?,
    val fatG: Double?,
    val carbohydrateG: Double?,
    val confidence: Double,
    val lowConfidence: Boolean,
    val matched: Boolean,
)

data class AddFoodUiState(
    val tab: String = "quick",
    val loading: Boolean = false,
    val error: String? = null,
    val searchQuery: String = "",
    val searchHits: List<FoodSearchHitDto> = emptyList(),
    val recent: List<RecentFoodDto> = emptyList(),
    val selectedHit: FoodSearchHitDto? = null,
    val grams: String = "100",
    val calcKcal: Int? = null,
    val calcProtein: Double? = null,
    val calcFat: Double? = null,
    val calcCarbs: Double? = null,
    val photoReview: List<PhotoReviewItem> = emptyList(),
    val photoNeedsReview: Boolean = false,
    val photoWarning: String? = null,
    val mealType: String = "snack",
)

@HiltViewModel
class AddFoodViewModel @Inject constructor(
    private val nutritionApi: NutritionApi,
    private val bus: AppStateBus,
    @ApplicationContext private val context: Context,
) : ViewModel() {
    private val _state = MutableStateFlow(AddFoodUiState())
    val state: StateFlow<AddFoodUiState> = _state.asStateFlow()

    fun setTab(tab: String) {
        _state.value = _state.value.copy(tab = tab, error = null)
        if (tab == "recent" && _state.value.recent.isEmpty()) {
            loadRecent()
        }
    }

    fun setMealType(mealType: String) {
        _state.value = _state.value.copy(mealType = mealType)
    }

    fun loadRecent() {
        viewModelScope.launch {
            runCatching { nutritionApi.recentFoods() }
                .onSuccess { _state.value = _state.value.copy(recent = it) }
        }
    }

    fun search(query: String) {
        _state.value = _state.value.copy(searchQuery = query)
        if (query.length < 2) {
            _state.value = _state.value.copy(searchHits = emptyList())
            return
        }
        viewModelScope.launch {
            runCatching { nutritionApi.searchFoods(query) }
                .onSuccess { _state.value = _state.value.copy(searchHits = it, error = null) }
                .onFailure {
                    _state.value = _state.value.copy(
                        error = (it as? ApiException)?.toUiMessage() ?: "Поиск недоступен",
                    )
                }
        }
    }

    fun selectHit(hit: FoodSearchHitDto) {
        _state.value = _state.value.copy(selectedHit = hit, grams = "100")
        recalculate(hit.ingredientId, 100.0)
    }

    fun setGrams(raw: String) {
        val cleaned = raw.filter { it.isDigit() || it == '.' || it == ',' }
        _state.value = _state.value.copy(grams = cleaned)
        val grams = cleaned.replace(',', '.').toDoubleOrNull() ?: return
        val id = _state.value.selectedHit?.ingredientId ?: return
        if (grams > 0) recalculate(id, grams)
    }

    private fun recalculate(ingredientId: String, grams: Double) {
        viewModelScope.launch {
            runCatching {
                nutritionApi.calculateFood(FoodCalculateRequest(ingredientId, grams))
            }.onSuccess { calc ->
                _state.value = _state.value.copy(
                    calcKcal = calc.caloriesKcal,
                    calcProtein = calc.proteinG,
                    calcFat = calc.fatG,
                    calcCarbs = calc.carbohydrateG,
                )
            }
        }
    }

    fun addQuick(
        description: String,
        calories: Int,
        protein: Double,
        fat: Double,
        carbs: Double,
        onDone: () -> Unit,
    ) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val source = if (protein == 0.0 && fat == 0.0 && carbs == 0.0) "quick_add" else "manual"
                nutritionApi.createLog(
                    NutritionLogCreateRequest(
                        loggedOn = LocalDate.now().toString(),
                        mealType = _state.value.mealType,
                        source = source,
                        description = description,
                        caloriesKcal = calories,
                        proteinG = protein,
                        fatG = fat,
                        carbohydrateG = carbs,
                    ),
                )
                bus.emit(DomainEvent.NutritionLogChanged())
                onDone()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(error = error.toUiMessage(), loading = false)
            } finally {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }

    fun addSearchFood(onDone: () -> Unit) {
        val hit = _state.value.selectedHit ?: return
        val grams = _state.value.grams.replace(',', '.').toDoubleOrNull() ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                nutritionApi.createLog(
                    NutritionLogCreateRequest(
                        loggedOn = LocalDate.now().toString(),
                        mealType = _state.value.mealType,
                        source = "search",
                        description = hit.name,
                        ingredientId = hit.ingredientId,
                        quantityG = grams,
                        unit = "g",
                    ),
                )
                bus.emit(DomainEvent.NutritionLogChanged())
                onDone()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(error = error.toUiMessage())
            } finally {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }

    fun addRecent(item: RecentFoodDto, onDone: () -> Unit) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                if (item.ingredientId != null && item.quantityG != null) {
                    nutritionApi.createLog(
                        NutritionLogCreateRequest(
                            loggedOn = LocalDate.now().toString(),
                            mealType = _state.value.mealType,
                            source = "search",
                            description = item.description,
                            ingredientId = item.ingredientId,
                            quantityG = item.quantityG,
                            unit = "g",
                        ),
                    )
                } else {
                    nutritionApi.createLog(
                        NutritionLogCreateRequest(
                            loggedOn = LocalDate.now().toString(),
                            mealType = _state.value.mealType,
                            source = "manual",
                            description = item.description,
                            caloriesKcal = item.caloriesKcal,
                            proteinG = item.proteinG,
                            fatG = item.fatG,
                            carbohydrateG = item.carbohydrateG,
                        ),
                    )
                }
                bus.emit(DomainEvent.NutritionLogChanged())
                onDone()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(error = error.toUiMessage())
            } finally {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }

    fun analyzePhoto(uri: Uri) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, photoReview = emptyList())
            try {
                val raw = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                    ?: error("Не удалось прочитать фото")
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val (bytes, outMime) = downscaleForUpload(raw, mime)
                val body = bytes.toRequestBody(outMime.toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", "meal.jpg", body)
                val result: PhotoAnalyzeDto = nutritionApi.analyzePhoto(part)
                val review = result.items.map { it.toReview() }
                _state.value = _state.value.copy(
                    loading = false,
                    photoReview = review,
                    photoNeedsReview = result.needsManualReview,
                    photoWarning = when {
                        result.needsManualReview -> "Мы не уверены в некоторых продуктах — проверьте перед сохранением."
                        else -> null
                    },
                    tab = "photo_review",
                )
            } catch (error: Exception) {
                val api = error as? ApiException
                val mapped = when {
                    api?.httpStatus == 413 || api?.code == "image_too_large" ->
                        "Фото слишком большое. Попробуйте другое фото или уменьшите размер."
                    api != null -> api.toUiMessage()
                    else -> "Не удалось распознать фото"
                }
                _state.value = _state.value.copy(
                    loading = false,
                    error = mapped,
                )
            }
        }
    }

    /** Keep uploads under nginx/backend limits (~5–8 MB). */
    private fun downscaleForUpload(bytes: ByteArray, mime: String): Pair<ByteArray, String> {
        if (bytes.size <= 900_000) return bytes to (mime.ifBlank { "image/jpeg" })
        return try {
            val bitmap = android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ?: return bytes to mime
            val maxDim = 1600
            val scale = minOf(
                1f,
                maxDim.toFloat() / maxOf(bitmap.width, bitmap.height).toFloat(),
            )
            val w = maxOf(1, (bitmap.width * scale).toInt())
            val h = maxOf(1, (bitmap.height * scale).toInt())
            val scaled = if (scale < 1f) {
                android.graphics.Bitmap.createScaledBitmap(bitmap, w, h, true)
            } else {
                bitmap
            }
            val stream = java.io.ByteArrayOutputStream()
            var quality = 85
            do {
                stream.reset()
                scaled.compress(android.graphics.Bitmap.CompressFormat.JPEG, quality, stream)
                quality -= 10
            } while (stream.size() > 900_000 && quality >= 50)
            if (scaled !== bitmap) scaled.recycle()
            bitmap.recycle()
            stream.toByteArray() to "image/jpeg"
        } catch (_: Exception) {
            bytes to mime
        }
    }

    fun updatePhotoGrams(index: Int, gramsRaw: String) {
        val grams = gramsRaw.replace(',', '.').toDoubleOrNull() ?: return
        val items = _state.value.photoReview.toMutableList()
        if (index !in items.indices) return
        val item = items[index]
        val id = item.ingredientId
        if (id == null) {
            items[index] = item.copy(grams = grams, caloriesKcal = null)
            _state.value = _state.value.copy(photoReview = items)
            return
        }
        viewModelScope.launch {
            runCatching {
                nutritionApi.recalculatePhoto(FoodCalculateRequest(id, grams))
            }.onSuccess { calc ->
                val next = _state.value.photoReview.toMutableList()
                if (index in next.indices) {
                    next[index] = next[index].copy(
                        grams = grams,
                        caloriesKcal = calc.caloriesKcal,
                        proteinG = calc.proteinG,
                        fatG = calc.fatG,
                        carbohydrateG = calc.carbohydrateG,
                    )
                    _state.value = _state.value.copy(photoReview = next)
                }
            }
        }
    }

    fun removePhotoItem(index: Int) {
        val next = _state.value.photoReview.toMutableList()
        if (index in next.indices) {
            next.removeAt(index)
            _state.value = _state.value.copy(photoReview = next)
        }
    }

    fun confirmPhoto(onDone: () -> Unit) {
        val items = _state.value.photoReview.filter { it.ingredientId != null && it.grams > 0 }
        if (items.isEmpty()) {
            _state.value = _state.value.copy(error = "Выберите продукты с известным составом")
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                nutritionApi.confirmPhoto(
                    PhotoConfirmRequest(
                        loggedOn = LocalDate.now().toString(),
                        mealType = _state.value.mealType,
                        items = items.map {
                            PhotoConfirmItemDto(
                                ingredientId = it.ingredientId,
                                description = it.name,
                                quantityG = it.grams,
                                mealType = _state.value.mealType,
                            )
                        },
                    ),
                    idempotencyKey = UUID.randomUUID().toString(),
                )
                bus.emit(DomainEvent.NutritionLogChanged())
                onDone()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(error = error.toUiMessage())
            } finally {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }

    private fun PhotoItemDto.toReview(): PhotoReviewItem =
        PhotoReviewItem(
            name = canonicalName ?: name,
            ingredientId = ingredientId,
            grams = estimatedGrams ?: 100.0,
            caloriesKcal = caloriesKcal,
            proteinG = proteinG,
            fatG = fatG,
            carbohydrateG = carbohydrateG,
            confidence = confidence,
            lowConfidence = lowConfidence,
            matched = matched,
        )
}
