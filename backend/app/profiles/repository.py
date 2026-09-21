"""Persistence for the profile questionnaire, goals, preferences and pantry."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        statement = select(UserProfile).where(UserProfile.user_id == user_id)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def create_profile(self, user_id: UUID) -> UserProfile:
        profile = UserProfile(user_id=user_id)
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def get_active_goal(self, user_id: UUID) -> Goal | None:
        statement = select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def add_goal(self, goal: Goal) -> Goal:
        self._session.add(goal)
        await self._session.flush()
        return goal

    async def list_preferences(self, user_id: UUID) -> list[FoodPreference]:
        statement = (
            select(FoodPreference)
            .where(FoodPreference.user_id == user_id)
            .order_by(FoodPreference.display_name)
        )
        return list((await self._session.execute(statement)).scalars())

    async def list_restrictions(self, user_id: UUID) -> list[FoodRestriction]:
        statement = (
            select(FoodRestriction)
            .where(FoodRestriction.user_id == user_id)
            .order_by(FoodRestriction.display_name)
        )
        return list((await self._session.execute(statement)).scalars())

    async def list_pantry(self, user_id: UUID) -> list[AvailableProduct]:
        statement = (
            select(AvailableProduct)
            .where(AvailableProduct.user_id == user_id)
            .order_by(AvailableProduct.display_name)
        )
        return list((await self._session.execute(statement)).scalars())

    async def replace_preferences(
        self, user_id: UUID, preferences: list[FoodPreference]
    ) -> None:
        await self._session.execute(
            delete(FoodPreference).where(FoodPreference.user_id == user_id)
        )
        self._session.add_all(preferences)
        await self._session.flush()

    async def replace_restrictions(
        self, user_id: UUID, restrictions: list[FoodRestriction]
    ) -> None:
        await self._session.execute(
            delete(FoodRestriction).where(FoodRestriction.user_id == user_id)
        )
        self._session.add_all(restrictions)
        await self._session.flush()

    async def replace_pantry(
        self, user_id: UUID, products: list[AvailableProduct]
    ) -> None:
        await self._session.execute(
            delete(AvailableProduct).where(AvailableProduct.user_id == user_id)
        )
        self._session.add_all(products)
        await self._session.flush()
