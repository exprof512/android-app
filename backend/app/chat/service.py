"""ChatEngine: bounded contextual AI chat."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import TextAIQuotaExhausted, TextAIUnavailable
from app.ai.service import TextAIService
from app.chat.errors import ChatMessageEmpty, ConversationNotFound
from app.chat.models import AiConversation, AiMessage
from app.chat.repository import ChatRepository
from app.chat.schemas import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatMessageResponse,
    ConversationCreate,
    ConversationOut,
    SuggestedActionOut,
)
from app.core.errors import OwnershipDenied
from app.core.models import utcnow
from app.entitlements import constants as entitlement_constants
from app.entitlements.service import EntitlementsService
from app.meal_plans.models import MealPlan, MealPlanItem
from app.profiles.models import FoodPreference, FoodRestriction, Goal, UserProfile
from app.recipes.models import Recipe

_UNSAFE_MARKERS = (
    "диагноз",
    "диагностир",
    "лечение",
    "назначь лекар",
    "гарантированно похуде",
    "точно похуде",
    "обязательно сбросишь",
)


class ChatService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: ChatRepository,
        text_ai: TextAIService,
        entitlements: EntitlementsService | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._text_ai = text_ai
        self._entitlements = entitlements

    async def create_or_get(
        self, user_id: UUID, payload: ConversationCreate
    ) -> ConversationOut:
        if payload.context_plan_id is None and payload.context_recipe_id is None:
            existing = await self._repository.get_current(user_id)
            if existing is not None:
                return self._conversation_out(existing)

        conversation = AiConversation(
            user_id=user_id,
            title=payload.title,
            context_plan_id=payload.context_plan_id,
            context_recipe_id=payload.context_recipe_id,
            status="active",
        )
        await self._repository.add_conversation(conversation)
        await self._session.commit()
        refreshed = await self._repository.get(conversation.id)
        assert refreshed is not None
        return self._conversation_out(refreshed)

    async def get(self, user_id: UUID, conversation_id: UUID) -> ConversationOut:
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFound()
        if conversation.user_id != user_id:
            raise OwnershipDenied()
        return self._conversation_out(conversation)

    async def post_message(
        self, user_id: UUID, conversation_id: UUID, payload: ChatMessageCreate
    ) -> ChatMessageResponse:
        content = payload.content.strip()
        if not content:
            raise ChatMessageEmpty()

        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFound()
        if conversation.user_id != user_id:
            raise OwnershipDenied()

        if self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_CHAT_MESSAGE
            )

        user_message = AiMessage(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )
        await self._repository.add_message(user_message)

        warnings: list[str] = []
        if any(marker in content.lower() for marker in _UNSAFE_MARKERS):
            answer = (
                "Я не ставлю диагнозы и не назначаю лечение. "
                "Обратитесь к врачу или диетологу. Могу помочь с планом питания FoodAI "
                "в рамках общих рекомендаций."
            )
            actions: list[dict] = [
                {"type": "none", "label": "Понятно", "payload": None}
            ]
            warnings.append("Запрос направлен в безопасный отказ.")
        else:
            context = await self._build_context(user_id, conversation, content)
            try:
                result = await self._text_ai.chat_answer(
                    context=context, user_id=user_id, conversation_id=conversation.id
                )
                answer = result.answer
                actions = [
                    action.model_dump(mode="json") for action in result.suggested_actions
                ]
                warnings.extend(result.warnings)
            except (TextAIQuotaExhausted, TextAIUnavailable):
                answer = (
                    "Сейчас AI временно недоступен. Попробуйте позже или откройте "
                    "Today / Shopping — там можно заменить блюдо и собрать покупки без чата."
                )
                actions = [
                    {
                        "type": "open_shopping_list",
                        "label": "Открыть список покупок",
                        "payload": None,
                    }
                ]
                warnings.append("Ответ без live AI: провайдер недоступен.")

        assistant = AiMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            suggested_actions=actions,
        )
        await self._repository.add_message(assistant)
        conversation.updated_at = utcnow()
        await self._session.commit()
        await self._session.refresh(user_message)
        await self._session.refresh(assistant)

        return ChatMessageResponse(
            conversation_id=conversation.id,
            user_message=self._message_out(user_message),
            assistant_message=self._message_out(assistant),
            warnings=warnings,
        )

    async def _build_context(
        self, user_id: UUID, conversation: AiConversation, user_content: str
    ) -> dict:
        profile = (
            await self._session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        goal = None
        if profile is not None and profile.active_goal_id is not None:
            goal = await self._session.get(Goal, profile.active_goal_id)

        restrictions = list(
            (
                await self._session.execute(
                    select(FoodRestriction).where(FoodRestriction.user_id == user_id)
                )
            ).scalars()
        )
        preferences = list(
            (
                await self._session.execute(
                    select(FoodPreference).where(FoodPreference.user_id == user_id)
                )
            ).scalars()
        )

        today = date.today()
        plan = None
        if conversation.context_plan_id is not None:
            plan = await self._session.get(MealPlan, conversation.context_plan_id)
        if plan is None:
            plan = (
                await self._session.execute(
                    select(MealPlan)
                    .where(
                        MealPlan.user_id == user_id,
                        MealPlan.start_date <= today,
                        MealPlan.end_date >= today,
                        MealPlan.status == "ready",
                    )
                    .order_by(MealPlan.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        plan_summary: list[dict] = []
        today_balance: dict | None = None
        if plan is not None:
            items = list(
                (
                    await self._session.execute(
                        select(MealPlanItem).where(
                            MealPlanItem.meal_plan_id == plan.id,
                            MealPlanItem.planned_date == today,
                        )
                    )
                ).scalars()
            )
            for item in items:
                recipe = await self._session.get(Recipe, item.recipe_id)
                plan_summary.append(
                    {
                        "meal_type": item.meal_type,
                        "recipe_id": str(item.recipe_id),
                        "name": recipe.name if recipe else "Блюдо",
                        "is_completed": item.is_completed,
                    }
                )
            completed = [i for i in items if i.is_completed]
            consumed = sum(i.calories_kcal for i in completed)
            today_balance = {
                "calories_remaining_kcal": max(plan.calorie_target_kcal - consumed, 0),
                "protein_remaining_g": float(
                    max(
                        float(plan.protein_target_g)
                        - float(sum((i.protein_g for i in completed), 0)),
                        0,
                    )
                ),
            }

        recipe_name = None
        if conversation.context_recipe_id is not None:
            recipe = await self._session.get(Recipe, conversation.context_recipe_id)
            recipe_name = recipe.name if recipe else None

        recent = [
            {"role": msg.role, "content": msg.content[:500]}
            for msg in conversation.messages[-8:]
        ]

        return {
            "locale": "ru-RU",
            "user_message": user_content,
            "active_goal": (
                {
                    "type": goal.goal_type,
                    "calorie_target_kcal": goal.calorie_target_kcal,
                }
                if goal
                else None
            ),
            "today_balance": today_balance,
            "current_plan_summary": plan_summary,
            "focus_recipe_name": recipe_name,
            "restrictions": [row.display_name for row in restrictions][:20],
            "preferences": [
                row.display_name
                for row in preferences
                if row.preference_type == "liked"
            ][:20],
            "recent_messages": recent,
        }

    def _conversation_out(self, conversation: AiConversation) -> ConversationOut:
        return ConversationOut(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            context_plan_id=conversation.context_plan_id,
            context_recipe_id=conversation.context_recipe_id,
            messages=[self._message_out(msg) for msg in conversation.messages],
        )

    @staticmethod
    def _message_out(message: AiMessage) -> ChatMessageOut:
        actions: list[SuggestedActionOut] = []
        for raw in message.suggested_actions or []:
            try:
                actions.append(SuggestedActionOut.model_validate(raw))
            except Exception:
                continue
        return ChatMessageOut(
            id=message.id,
            role=message.role,
            content=message.content,
            suggested_actions=actions,
            created_at=message.created_at,
        )
