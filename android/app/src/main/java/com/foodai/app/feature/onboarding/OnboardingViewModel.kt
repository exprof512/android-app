package com.foodai.app.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.TargetPreviewResponse
import com.foodai.app.core.network.isComplete
import com.foodai.app.core.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingUiState(
    val draft: OnboardingDraft = OnboardingDraft(),
    val step: OnboardingStep = OnboardingStep.Goal,
    val preview: TargetPreviewResponse? = null,
    val isSubmitting: Boolean = false,
    val generatePlan: Boolean = true,
    val hydrating: Boolean = true,
    val error: String? = null,
    val finished: Boolean = false,
    /** Shown after profile edit when important fields changed (no auto-generate). */
    val askRebuildPlan: Boolean = false,
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val draftStore: OnboardingDraftStore,
    private val profileRepository: ProfileRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(OnboardingUiState())
    val state: StateFlow<OnboardingUiState> = _state.asStateFlow()
    private var baselineFingerprint: String? = null

    init {
        hydrate()
    }

    private fun hydrate() {
        viewModelScope.launch {
            val userId = authRepository.currentUser()?.id
            val local = draftStore.load(userId)
            val profile = runCatching { profileRepository.getProfile() }.getOrNull()
            val draft = when {
                authRepository.pendingOnboarding() ->
                    if (local.hasMeaningfulInput()) local else OnboardingDraft()
                profile != null && profile.isComplete() -> profile.toOnboardingDraft(stepIndex = 0)
                local.hasMeaningfulInput() -> local
                profile != null -> profile.toOnboardingDraft(local.stepIndex.coerceIn(0, OnboardingStep.TOTAL - 2))
                else -> local
            }
            baselineFingerprint = importantFingerprint(draft)
            val step = OnboardingStep.formSteps
                .getOrElse(draft.stepIndex.coerceIn(0, OnboardingStep.TOTAL - 2)) { OnboardingStep.Goal }
            draftStore.save(userId, draft)
            _state.value = OnboardingUiState(
                draft = draft,
                step = step,
                hydrating = false,
            )
            if (step == OnboardingStep.Meals || step == OnboardingStep.Pantry) {
                refreshPreview()
            }
        }
    }

    fun setGeneratePlan(value: Boolean) {
        _state.update { it.copy(generatePlan = value) }
    }

    fun updateDraft(transform: (OnboardingDraft) -> OnboardingDraft) {
        _state.update { current ->
            val next = transform(current.draft).copy(stepIndex = current.step.index)
            draftStore.save(authRepository.currentUser()?.id, next)
            current.copy(draft = next, error = null)
        }
    }

    fun next() {
        val current = _state.value
        val error = current.draft.validateStep(current.step)
        if (error != null) {
            _state.update { it.copy(error = error) }
            return
        }
        val idx = OnboardingStep.formSteps.indexOf(current.step)
        if (idx < OnboardingStep.formSteps.lastIndex) {
            val nextStep = OnboardingStep.formSteps[idx + 1]
            persistStep(nextStep)
            if (nextStep == OnboardingStep.Meals || nextStep == OnboardingStep.Pantry) {
                refreshPreview()
            }
        } else {
            submit()
        }
    }

    fun back() {
        val current = _state.value
        if (current.isSubmitting) return
        val idx = OnboardingStep.formSteps.indexOf(current.step)
        if (idx > 0) {
            persistStep(OnboardingStep.formSteps[idx - 1])
        }
    }

    fun refreshPreview() {
        val previewBody = _state.value.draft.toPreviewRequestOrNull() ?: return
        viewModelScope.launch {
            try {
                val preview = profileRepository.previewTarget(previewBody)
                _state.update { it.copy(preview = preview, error = null) }
            } catch (error: ApiException) {
                _state.update {
                    it.copy(preview = null, error = friendlyApiMessage(error))
                }
            }
        }
    }

    fun confirmRebuildPlan() {
        viewModelScope.launch {
            _state.update {
                it.copy(askRebuildPlan = false, isSubmitting = true, step = OnboardingStep.Loading)
            }
            try {
                profileRepository.regeneratePlan(days = 7)
                finishSuccessfully()
            } catch (error: ApiException) {
                _state.update {
                    it.copy(
                        isSubmitting = false,
                        step = OnboardingStep.Pantry,
                        error = friendlyApiMessage(error),
                        finished = true,
                    )
                }
            } catch (error: Exception) {
                _state.update {
                    it.copy(
                        isSubmitting = false,
                        finished = true,
                        error = error.message,
                    )
                }
            }
        }
    }

    fun skipRebuildPlan() {
        _state.update { it.copy(askRebuildPlan = false, finished = true) }
    }

    private fun submit() {
        viewModelScope.launch {
            val shouldGenerate = _state.value.generatePlan
            val importantChanged = importantFingerprint(_state.value.draft) != baselineFingerprint
            _state.update {
                it.copy(step = OnboardingStep.Loading, isSubmitting = true, error = null)
            }
            try {
                val userId = authRepository.currentUser()?.id
                val body = _state.value.draft.toUpdateRequest()
                profileRepository.updateProfile(body)
                if (shouldGenerate) {
                    profileRepository.generateFirstPlan(days = 7, force = true)
                    finishSuccessfully()
                } else if (importantChanged) {
                    // Edit path: ask before regenerate — never auto-generate.
                    val snapshot = runCatching { profileRepository.getProfile() }
                        .getOrNull()
                        ?.toOnboardingDraft()
                    if (snapshot != null) {
                        draftStore.save(userId, snapshot)
                    } else {
                        draftStore.clear(userId)
                    }
                    authRepository.setPendingOnboarding(false)
                    _state.update {
                        it.copy(
                            isSubmitting = false,
                            step = OnboardingStep.Pantry,
                            askRebuildPlan = true,
                        )
                    }
                } else {
                    finishSuccessfully()
                }
            } catch (error: ApiException) {
                _state.update {
                    it.copy(
                        isSubmitting = false,
                        step = OnboardingStep.Pantry,
                        error = friendlyApiMessage(error),
                    )
                }
            } catch (error: Exception) {
                _state.update {
                    it.copy(
                        isSubmitting = false,
                        step = OnboardingStep.Pantry,
                        error = error.message ?: "Не удалось сохранить профиль",
                    )
                }
            }
        }
    }

    private suspend fun finishSuccessfully() {
        val userId = authRepository.currentUser()?.id
        val snapshot = runCatching { profileRepository.getProfile() }
            .getOrNull()
            ?.toOnboardingDraft()
        if (snapshot != null) {
            draftStore.save(userId, snapshot)
        } else {
            draftStore.clear(userId)
        }
        authRepository.setPendingOnboarding(false)
        _state.update { it.copy(isSubmitting = false, finished = true, askRebuildPlan = false) }
    }

    private fun importantFingerprint(draft: OnboardingDraft): String =
        listOf(
            draft.goalType,
            draft.targetWeightKg,
            draft.desiredWeeklyChangeKg,
            draft.sex,
            draft.ageYears,
            draft.heightCm,
            draft.currentWeightKg,
            draft.activityLevel,
            draft.mealsPerDay,
            draft.dailyCalorieMode,
            draft.dailyCalorieValue,
            draft.excludedFoods,
            draft.allergies,
            draft.groceryBudgetWeekly,
            draft.maxCookTimeMinutes,
            draft.householdSize,
        ).joinToString("|")

    private fun friendlyApiMessage(error: ApiException): String {
        val fromDetails = error.details.firstNotNullOfOrNull { detail ->
            humanizeNutritionError(detail.field, detail.reason)
        }
        return fromDetails ?: error.toUiMessage()
    }

    private fun persistStep(step: OnboardingStep) {
        _state.update { current ->
            val draft = current.draft.copy(stepIndex = step.index)
            draftStore.save(authRepository.currentUser()?.id, draft)
            current.copy(step = step, draft = draft, error = null)
        }
    }
}
