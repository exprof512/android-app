"""AI usage cost aggregation for admins."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import median
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiTextUsage
from app.images.models import AiImageUsage


class AIUsageAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def summary(
        self, *, from_date: date | None = None, to_date: date | None = None
    ) -> dict:
        start, end = self._window(from_date, to_date)
        text_rows = list(
            (
                await self._session.execute(
                    select(AiTextUsage).where(
                        AiTextUsage.created_at >= start,
                        AiTextUsage.created_at < end,
                    )
                )
            ).scalars()
        )
        image_rows = list(
            (
                await self._session.execute(
                    select(AiImageUsage).where(
                        AiImageUsage.created_at >= start,
                        AiImageUsage.created_at < end,
                    )
                )
            ).scalars()
        )

        def _count(rows, status: str) -> int:
            return sum(1 for r in rows if r.status == status)

        text_latency = [r.duration_ms for r in text_rows if r.duration_ms is not None]
        image_latency = [r.duration_ms for r in image_rows if r.duration_ms is not None]

        return {
            "from": start.date().isoformat(),
            "to": (end - timedelta(seconds=1)).date().isoformat(),
            "text": {
                "total_requests": len(text_rows),
                "successful": _count(text_rows, "ok"),
                "failed": _count(text_rows, "failed") + _count(text_rows, "invalid"),
                "cached": _count(text_rows, "cached"),
                "total_input_tokens": sum(r.input_tokens or 0 for r in text_rows),
                "total_output_tokens": sum(r.output_tokens or 0 for r in text_rows),
                "estimated_cost": float(
                    sum((r.estimated_cost or Decimal("0")) for r in text_rows)
                ),
                "avg_latency_ms": self._avg(text_latency),
                "p50_latency_ms": self._percentile(text_latency, 50),
                "p95_latency_ms": self._percentile(text_latency, 95),
            },
            "image": {
                "total_requests": len(image_rows),
                "successful": _count(image_rows, "ok") + _count(image_rows, "ready"),
                "failed": _count(image_rows, "failed"),
                "reused": _count(image_rows, "reused"),
                "estimated_cost": float(
                    sum((r.estimated_cost or Decimal("0")) for r in image_rows)
                ),
                "avg_latency_ms": self._avg(image_latency),
                "p50_latency_ms": self._percentile(image_latency, 50),
                "p95_latency_ms": self._percentile(image_latency, 95),
            },
        }

    async def daily(
        self, *, from_date: date | None = None, to_date: date | None = None
    ) -> list[dict]:
        start, end = self._window(from_date, to_date)
        text_rows = list(
            (
                await self._session.execute(
                    select(AiTextUsage).where(
                        AiTextUsage.created_at >= start,
                        AiTextUsage.created_at < end,
                    )
                )
            ).scalars()
        )
        by_day: dict[str, dict] = {}
        for row in text_rows:
            day = row.created_at.date().isoformat()
            bucket = by_day.setdefault(
                day,
                {
                    "date": day,
                    "text_requests": 0,
                    "text_cost": 0.0,
                    "cached": 0,
                    "failed": 0,
                },
            )
            bucket["text_requests"] += 1
            bucket["text_cost"] += float(row.estimated_cost or 0)
            if row.status == "cached":
                bucket["cached"] += 1
            if row.status in {"failed", "invalid"}:
                bucket["failed"] += 1
        return [by_day[k] for k in sorted(by_day.keys())]

    async def by_operation(
        self, *, from_date: date | None = None, to_date: date | None = None
    ) -> list[dict]:
        start, end = self._window(from_date, to_date)
        text_rows = list(
            (
                await self._session.execute(
                    select(AiTextUsage).where(
                        AiTextUsage.created_at >= start,
                        AiTextUsage.created_at < end,
                    )
                )
            ).scalars()
        )
        by_op: dict[str, dict] = {}
        for row in text_rows:
            key = f"{row.operation}|{row.model}"
            bucket = by_op.setdefault(
                key,
                {
                    "operation": row.operation,
                    "model": row.model,
                    "requests": 0,
                    "estimated_cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            )
            bucket["requests"] += 1
            bucket["estimated_cost"] += float(row.estimated_cost or 0)
            bucket["input_tokens"] += row.input_tokens or 0
            bucket["output_tokens"] += row.output_tokens or 0
        return sorted(by_op.values(), key=lambda x: x["requests"], reverse=True)

    @staticmethod
    def _window(
        from_date: date | None, to_date: date | None
    ) -> tuple[datetime, datetime]:
        end_d = to_date or date.today()
        start_d = from_date or (end_d - timedelta(days=30))
        start = datetime.combine(start_d, datetime.min.time()).replace(tzinfo=None)
        end = datetime.combine(end_d + timedelta(days=1), datetime.min.time()).replace(
            tzinfo=None
        )
        # Use timezone-aware via utcnow pattern — store as aware
        from datetime import UTC

        return start.replace(tzinfo=UTC), end.replace(tzinfo=UTC)

    @staticmethod
    def _avg(values: list[int]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    @staticmethod
    def _percentile(values: list[int], pct: int) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if pct <= 50:
            return float(median(ordered))
        idx = min(len(ordered) - 1, int(len(ordered) * pct / 100))
        return float(ordered[idx])
