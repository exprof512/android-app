package com.foodai.app.feature.ai

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.foodai.app.core.network.AdaptDayDto
import com.foodai.app.core.network.RecommendationCandidateDto
import com.foodai.app.core.network.SubstitutionAlternativeDto
import com.foodai.app.core.network.SubstitutionDto
import com.foodai.app.core.network.VariantDto
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAIOutlinedButton
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

sealed class AiPreviewState {
    data object Idle : AiPreviewState()
    data object Loading : AiPreviewState()
    data class Recommendations(
        val recommendationId: String,
        val candidates: List<RecommendationCandidateDto>,
        val warnings: List<String> = emptyList(),
        val selectedIndex: Int = 0,
        val applying: Boolean = false,
        val title: String = "Что мне съесть?",
    ) : AiPreviewState()

    data class AdaptDay(
        val preview: AdaptDayDto,
        val applying: Boolean = false,
    ) : AiPreviewState()

    data class Variant(
        val preview: VariantDto,
        val applying: Boolean = false,
        val mealPlanItemId: String? = null,
    ) : AiPreviewState()

    data class Substitution(
        val preview: SubstitutionDto,
    ) : AiPreviewState()

    data class Error(val message: String) : AiPreviewState()
    data class Empty(val message: String) : AiPreviewState()
}

@Composable
fun CandidateCard(
    candidate: RecommendationCandidateDto,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    FoodAICard(onClick = onClick) {
        Text(candidate.name, style = FoodAITypography.titleMedium)
        Spacer(Modifier.height(4.dp))
        Text(
            "${candidate.caloriesKcal} ккал · Б ${"%.0f".format(candidate.proteinG)} г" +
                (candidate.estimatedCostAmount?.let { " · ≈ ${"%.0f".format(it)} ${candidate.currency}" } ?: "") +
                " · ${candidate.cookTimeMinutes} мин",
            style = FoodAITypography.bodySmall,
            color = FoodAIColors.TextSecondary,
        )
        candidate.reason?.takeIf { it.isNotBlank() }?.let { reason ->
            Spacer(Modifier.height(6.dp))
            Text(
                "Почему: ${reason.take(120)}${if (reason.length > 120) "…" else ""}",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        if (selected) {
            Spacer(Modifier.height(4.dp))
            Text("Выбрано", style = FoodAITypography.labelMedium, color = FoodAIColors.Primary)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiPreviewSheet(
    state: AiPreviewState,
    onDismiss: () -> Unit,
    onSelectCandidate: (Int) -> Unit = {},
    onConfirmRecommendations: () -> Unit = {},
    onConfirmAdaptDay: () -> Unit = {},
    onConfirmVariant: () -> Unit = {},
    onApplySubstitution: (SubstitutionAlternativeDto) -> Unit = {},
) {
    when (state) {
        AiPreviewState.Idle -> Unit
        is AiPreviewState.Loading -> {
            ModalBottomSheet(
                onDismissRequest = onDismiss,
                sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            ) {
                Column(Modifier.padding(FoodAIDimens.ScreenPadding)) {
                    Text("AI думает…", style = FoodAITypography.titleLarge)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Подбираем варианты. Ничего не меняется, пока вы не подтвердите.",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                    Spacer(Modifier.height(24.dp))
                }
            }
        }
        is AiPreviewState.Error -> {
            AlertDialog(
                onDismissRequest = onDismiss,
                title = { Text("AI недоступен") },
                text = { Text(state.message) },
                confirmButton = {
                    TextButton(onClick = onDismiss) { Text("OK") }
                },
            )
        }
        is AiPreviewState.Empty -> {
            AlertDialog(
                onDismissRequest = onDismiss,
                title = { Text("Нет вариантов") },
                text = { Text(state.message) },
                confirmButton = {
                    TextButton(onClick = onDismiss) { Text("OK") }
                },
            )
        }
        is AiPreviewState.Recommendations -> {
            ModalBottomSheet(
                onDismissRequest = { if (!state.applying) onDismiss() },
                sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            ) {
                Column(
                    Modifier
                        .padding(FoodAIDimens.ScreenPadding)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
                ) {
                    Text(state.title, style = FoodAITypography.titleLarge)
                    Text(
                        "Выберите вариант и подтвердите — запись появится в дневнике.",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                    state.warnings.forEach { Text("⚠ $it", color = FoodAIColors.Warning) }
                    state.candidates.forEachIndexed { index, candidate ->
                        CandidateCard(
                            candidate = candidate,
                            selected = index == state.selectedIndex,
                            onClick = { onSelectCandidate(index) },
                        )
                    }
                    FoodAIPrimaryButton(
                        label = if (state.applying) "Применяем…" else "Подтвердить выбор",
                        onClick = onConfirmRecommendations,
                        enabled = !state.applying && state.candidates.isNotEmpty(),
                        showArrow = false,
                    )
                    FoodAIOutlinedButton(label = "Отмена", onClick = onDismiss)
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
        is AiPreviewState.AdaptDay -> {
            ModalBottomSheet(
                onDismissRequest = { if (!state.applying) onDismiss() },
                sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            ) {
                Column(
                    Modifier
                        .padding(FoodAIDimens.ScreenPadding)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
                ) {
                    Text("Адаптация дня", style = FoodAITypography.titleLarge)
                    state.preview.rationale?.let {
                        Text(it, style = FoodAITypography.bodyMedium)
                    }
                    state.preview.note?.let {
                        Text(it, style = FoodAITypography.bodySmall, color = FoodAIColors.TextSecondary)
                    }
                    state.preview.warnings.forEach {
                        Text("⚠ $it", color = FoodAIColors.Warning)
                    }
                    state.preview.replacements.forEach { slot ->
                        FoodAICard {
                            Text(mealTypeRu(slot.mealType), style = FoodAITypography.labelMedium)
                            slot.candidate?.let { CandidateCard(it) }
                            slot.reason?.let {
                                Text(it, style = FoodAITypography.bodySmall)
                            }
                        }
                    }
                    FoodAIPrimaryButton(
                        label = if (state.applying) "Применяем…" else "Применить замены",
                        onClick = onConfirmAdaptDay,
                        enabled = !state.applying && state.preview.replacements.isNotEmpty(),
                        showArrow = false,
                    )
                    FoodAIOutlinedButton(label = "Отмена", onClick = onDismiss)
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
        is AiPreviewState.Variant -> {
            ModalBottomSheet(
                onDismissRequest = { if (!state.applying) onDismiss() },
                sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            ) {
                Column(
                    Modifier
                        .padding(FoodAIDimens.ScreenPadding)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
                ) {
                    Text("Вариант рецепта", style = FoodAITypography.titleLarge)
                    state.preview.changesSummary?.let {
                        Text(it, style = FoodAITypography.bodyMedium)
                    }
                    state.preview.warnings.forEach {
                        Text("⚠ $it", color = FoodAIColors.Warning)
                    }
                    state.preview.candidate?.let { CandidateCard(it) }
                    FoodAIPrimaryButton(
                        label = if (state.applying) {
                            "Применяем…"
                        } else if (state.mealPlanItemId != null) {
                            "Заменить в плане"
                        } else {
                            "Добавить в дневник"
                        },
                        onClick = onConfirmVariant,
                        enabled = !state.applying && state.preview.candidate != null,
                        showArrow = false,
                    )
                    FoodAIOutlinedButton(label = "Отмена", onClick = onDismiss)
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
        is AiPreviewState.Substitution -> {
            ModalBottomSheet(
                onDismissRequest = onDismiss,
                sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            ) {
                Column(
                    Modifier
                        .padding(FoodAIDimens.ScreenPadding)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
                ) {
                    Text(
                        "Замена: ${state.preview.originalName}",
                        style = FoodAITypography.titleLarge,
                    )
                    state.preview.warnings.forEach {
                        Text("⚠ $it", color = FoodAIColors.Warning)
                    }
                    if (state.preview.alternatives.isEmpty()) {
                        Text("Подходящих альтернатив нет.", style = FoodAITypography.bodyMedium)
                    } else {
                        state.preview.alternatives.forEach { alt ->
                            FoodAICard {
                                Text(
                                    "${alt.name} — ${alt.quantity} ${alt.unit}",
                                    style = FoodAITypography.titleMedium,
                                )
                                alt.reason?.let {
                                    Text(it, style = FoodAITypography.bodySmall)
                                }
                                TextButton(onClick = { onApplySubstitution(alt) }) {
                                    Text("Заменить в рецепте", color = FoodAIColors.Primary)
                                }
                            }
                        }
                    }
                    Text(
                        "Будет создана ваша копия рецепта — остальные планы не изменятся.",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                    FoodAIOutlinedButton(label = "Закрыть", onClick = onDismiss)
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
fun RememberDislikeDialog(
    foodName: String,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Запомнить нелюбовь?") },
        text = {
            Text("Добавить «$foodName» в список нелюбимых продуктов? Это повлияет на будущие рекомендации.")
        },
        confirmButton = {
            TextButton(onClick = onConfirm) { Text("Запомнить") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        },
    )
}

fun mealTypeRu(mealType: String): String = when (mealType) {
    "breakfast" -> "Завтрак"
    "lunch" -> "Обед"
    "dinner" -> "Ужин"
    "snack" -> "Перекус"
    else -> mealType
}
