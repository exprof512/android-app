"""Food photo analysis — OpenAI Vision identify, backend nutrition."""

from __future__ import annotations

import hashlib
import io
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import TextAIUnavailable
from app.ai.models import AiTextUsage
from app.auth.models import IdempotencyKey
from app.core.errors import ApiError
from app.core.models import as_utc, utcnow
from app.entitlements import constants as entitlement_constants
from app.entitlements.service import EntitlementsService
from app.integrations.openai.vision import (
    MockOpenAIVisionProvider,
    OpenAIVisionProvider,
    VisionAnalysisRequest,
    VisionProvider,
)
from app.nutrition.diary import NutritionDiaryService
from app.nutrition.food_match import match_food_name, nutrition_for_grams
from app.nutrition.models import NutritionLog
from app.recipes.models import Ingredient
from app.recipes.repository import RecipeRepository

logger = logging.getLogger(__name__)

ALLOWED_MIME = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"})


class PhotoItemOut(BaseModel):
    name: str
    estimated_grams: float | None = None
    confidence: float
    matched: bool
    ingredient_id: UUID | None = None
    canonical_name: str | None = None
    calories_kcal: int | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbohydrate_g: float | None = None
    low_confidence: bool = False
    notes: str | None = None


class PhotoAnalyzeOut(BaseModel):
    items: list[PhotoItemOut] = Field(default_factory=list)
    overall_confidence: float = 0.0
    estimated_total_kcal: int | None = None
    warnings: list[str] = Field(default_factory=list)
    model: str | None = None
    needs_manual_review: bool = False


class PhotoConfirmItem(BaseModel):
    ingredient_id: UUID | None = None
    description: str = Field(min_length=1, max_length=255)
    quantity_g: float = Field(gt=0, le=5000)
    meal_type: str = "snack"
    notes: str | None = Field(default=None, max_length=500)


class PhotoConfirmIn(BaseModel):
    logged_on: date
    meal_type: str = "snack"
    items: list[PhotoConfirmItem] = Field(min_length=1, max_length=20)


class PhotoAnalysisService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        vision: VisionProvider,
        entitlements: EntitlementsService | None = None,
        settings: Any = None,
        vision_model: str = "gpt-4.1-mini",
    ) -> None:
        self._session = session
        self._vision = vision
        self._entitlements = entitlements
        self._settings = settings
        self._vision_model = vision_model
        self._diary = NutritionDiaryService(session)

    async def analyze(
        self,
        user_id: UUID,
        *,
        image_bytes: bytes,
        mime_type: str,
    ) -> PhotoAnalyzeOut:
        mime = (mime_type or "image/jpeg").split(";")[0].strip().lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in ALLOWED_MIME:
            raise ApiError(
                status_code=400,
                code="unsupported_image_type",
                message="Поддерживаются JPEG, PNG и WebP.",
            )
        max_bytes = int(
            getattr(self._settings, "openai_vision_max_image_bytes", 5_242_880)
            if self._settings
            else 5_242_880
        )
        if len(image_bytes) > max_bytes:
            raise ApiError(
                status_code=413,
                code="image_too_large",
                message="Фото слишком большое. Сожмите изображение и попробуйте снова.",
            )
        if len(image_bytes) < 64:
            raise ApiError(
                status_code=400,
                code="image_too_small",
                message="Файл изображения повреждён или пуст.",
            )

        if self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_FOOD_PHOTO
            )

        image_bytes = _maybe_downscale(
            image_bytes,
            max_dim=int(
                getattr(self._settings, "openai_vision_max_dimension", 2048)
                if self._settings
                else 2048
            ),
        )

        try:
            raw = await self._vision.analyze_food(
                VisionAnalysisRequest(image_bytes=image_bytes, mime_type=mime, locale="ru")
            )
        except Exception as exc:
            code = getattr(exc, "code", "ai_generation_unavailable")
            await self._record_usage(
                user_id=user_id,
                status="failed",
                error_code=code,
                duration_ms=getattr(exc, "duration_ms", 0) or 0,
            )
            raise TextAIUnavailable(
                code=code if isinstance(code, str) else "ai_generation_unavailable",
                message="Не удалось распознать фото. Попробуйте ещё раз или введите еду вручную.",
            ) from exc

        await self._record_usage(
            user_id=user_id,
            status="ok",
            duration_ms=raw.duration_ms,
            model=raw.model or self._vision_model,
        )

        catalog = await RecipeRepository(self._session).active_catalog()
        items_out: list[PhotoItemOut] = []
        total_kcal = 0
        has_kcal = False
        for item in raw.items:
            matched = match_food_name(
                item.name,
                catalog,
                estimated_grams=item.estimated_grams,
                confidence=item.confidence,
            )
            low = item.confidence < 0.5 or not matched.matched
            entry = PhotoItemOut(
                name=item.name,
                estimated_grams=item.estimated_grams,
                confidence=item.confidence,
                matched=matched.matched,
                ingredient_id=matched.ingredient_id,
                canonical_name=matched.canonical_name if matched.matched else None,
                calories_kcal=matched.calories_kcal,
                protein_g=float(matched.protein_g) if matched.protein_g is not None else None,
                fat_g=float(matched.fat_g) if matched.fat_g is not None else None,
                carbohydrate_g=(
                    float(matched.carbohydrate_g)
                    if matched.carbohydrate_g is not None
                    else None
                ),
                low_confidence=low,
                notes=item.notes,
            )
            items_out.append(entry)
            if matched.calories_kcal is not None:
                total_kcal += matched.calories_kcal
                has_kcal = True

        warnings = list(raw.warnings)
        needs_review = (
            raw.overall_confidence < 0.5
            or not items_out
            or any(i.low_confidence for i in items_out)
        )
        if needs_review:
            warnings.append("low_confidence_review")
        if not items_out:
            warnings.append("no_foods_detected")

        return PhotoAnalyzeOut(
            items=items_out,
            overall_confidence=raw.overall_confidence,
            estimated_total_kcal=total_kcal if has_kcal else None,
            warnings=list(dict.fromkeys(warnings)),
            model=raw.model or self._vision_model,
            needs_manual_review=needs_review,
        )

    async def recalculate_item(
        self, *, ingredient_id: UUID, quantity_g: float
    ) -> PhotoItemOut:
        ingredient = await self._session.get(Ingredient, ingredient_id)
        if ingredient is None or not ingredient.is_active:
            raise ApiError(
                status_code=404,
                code="ingredient_not_found",
                message="Продукт не найден.",
            )
        grams = Decimal(str(quantity_g))
        if grams <= 0 or grams > 5000:
            raise ApiError(
                status_code=422,
                code="invalid_quantity",
                message="Некорректный вес порции.",
            )
        macros = nutrition_for_grams(ingredient, grams)
        return PhotoItemOut(
            name=ingredient.canonical_name,
            estimated_grams=float(grams),
            confidence=1.0,
            matched=True,
            ingredient_id=ingredient.id,
            canonical_name=ingredient.canonical_name,
            calories_kcal=int(macros["calories_kcal"]),
            protein_g=float(macros["protein_g"]),  # type: ignore[arg-type]
            fat_g=float(macros["fat_g"]),  # type: ignore[arg-type]
            carbohydrate_g=float(macros["carbohydrate_g"]),  # type: ignore[arg-type]
            low_confidence=False,
        )

    async def confirm(
        self,
        user_id: UUID,
        *,
        logged_on,
        meal_type: str,
        items: list[PhotoConfirmItem],
        idempotency_key: str | None = None,
    ) -> list:
        if idempotency_key:
            cached = await self._load_idempotent(user_id, idempotency_key)
            if cached is not None:
                return cached

        created = []
        for item in items:
            row = await self._diary.create(
                user_id,
                logged_on=logged_on,
                meal_type=item.meal_type or meal_type,
                source="photo_ai",
                description=item.description,
                ingredient_id=item.ingredient_id,
                quantity_g=Decimal(str(item.quantity_g)),
                unit="g",
                notes=item.notes,
            )
            created.append(row)

        if idempotency_key:
            await self._store_idempotent(
                user_id,
                idempotency_key,
                [str(r.id) for r in created],
            )
        return created

    async def _record_usage(
        self,
        *,
        user_id: UUID,
        status: str,
        duration_ms: int,
        error_code: str | None = None,
        model: str | None = None,
    ) -> None:
        self._session.add(
            AiTextUsage(
                user_id=user_id,
                conversation_id=None,
                operation="food_photo_analysis",
                model=model or self._vision_model,
                input_tokens=None,
                output_tokens=None,
                estimated_cost=None,
                status=status,
                duration_ms=duration_ms,
                error_code=error_code,
                request_fingerprint=None,
                schema_version=getattr(
                    self._settings, "openai_response_schema_version", 2
                )
                if self._settings
                else 2,
            )
        )
        await self._session.flush()

    async def _load_idempotent(
        self, user_id: UUID, key: str
    ) -> list | None:
        row = (
            await self._session.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.user_id == user_id,
                    IdempotencyKey.endpoint == "nutrition_photo_confirm",
                    IdempotencyKey.key == key,
                )
            )
        ).scalar_one_or_none()
        if row is None or as_utc(row.expires_at) <= utcnow():
            return None
        ids = (row.response_body or {}).get("log_ids") or []
        out = []
        for raw in ids:
            log = await self._session.get(NutritionLog, UUID(str(raw)))
            if log is not None:
                out.append(log)
        return out or None

    async def _store_idempotent(
        self, user_id: UUID, key: str, log_ids: list[str]
    ) -> None:
        body = {"log_ids": log_ids}
        digest = hashlib.sha256(
            (",".join(log_ids)).encode("utf-8")
        ).hexdigest()
        self._session.add(
            IdempotencyKey(
                user_id=user_id,
                key=key[:255],
                endpoint="nutrition_photo_confirm",
                request_hash=digest,
                response_status=201,
                response_body=body,
                expires_at=utcnow() + timedelta(hours=24),
            )
        )
        await self._session.flush()


def build_vision_provider(settings: Any) -> VisionProvider:
    if getattr(settings, "app_env", "") == "test":
        return MockOpenAIVisionProvider()
    if settings.openai_api_key.strip():
        return OpenAIVisionProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_vision_model or "gpt-4.1-mini",
            timeout_seconds=settings.openai_vision_timeout_seconds,
        )
    return MockOpenAIVisionProvider()


def _maybe_downscale(image_bytes: bytes, *, max_dim: int) -> bytes:
    try:
        from PIL import Image
    except ImportError:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        return image_bytes
    w, h = img.size
    if max(w, h) <= max_dim:
        return image_bytes
    scale = max_dim / float(max(w, h))
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    img = img.convert("RGB").resize(new_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
