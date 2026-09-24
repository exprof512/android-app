"""Collapse ready meal plans so each calendar day has one owner.

Priority for a date: the plan with more completed items on that date, then
the newer ``updated_at``. Completions on a losing plan are copied onto the
winner's matching meal slot so eaten food is not dropped.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _dates(start: date, end: date) -> list[date]:
    out: list[date] = []
    cursor = start
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=1)
    return out


def _runs(days: list[date]) -> list[tuple[date, date]]:
    if not days:
        return []
    ordered = sorted(days)
    runs: list[tuple[date, date]] = []
    run_start = ordered[0]
    prev = ordered[0]
    for day in ordered[1:]:
        if day == prev + timedelta(days=1):
            prev = day
            continue
        runs.append((run_start, prev))
        run_start = day
        prev = day
    runs.append((run_start, prev))
    return runs


def collapse_ready_overlaps(conn: Connection) -> int:
    """Archive or shrink ready plans until ranges no longer overlap. Returns rows changed."""
    plans = conn.execute(
        text(
            """
            SELECT id, user_id, start_date, end_date, updated_at, created_at
            FROM meal_plans
            WHERE status = 'ready'
            """
        )
    ).mappings().all()
    if not plans:
        return 0
    items = conn.execute(
        text(
            """
            SELECT id, meal_plan_id, planned_date, meal_type, is_completed, status, completed_at
            FROM meal_plan_items
            """
        )
    ).mappings().all()
    by_plan: dict[str, list] = defaultdict(list)
    for item in items:
        by_plan[str(item["meal_plan_id"])].append(item)

    by_user: dict[str, list] = defaultdict(list)
    for plan in plans:
        by_user[str(plan["user_id"])].append(plan)

    changed = 0
    for user_plans in by_user.values():
        if len(user_plans) < 2:
            continue
        all_days: set[date] = set()
        for plan in user_plans:
            all_days.update(_dates(plan["start_date"], plan["end_date"]))
        overlapping = False
        for day in all_days:
            cover = [
                p
                for p in user_plans
                if p["start_date"] <= day <= p["end_date"]
            ]
            if len(cover) > 1:
                overlapping = True
                break
        if not overlapping:
            continue

        def completed_on(plan_id: str, day: date) -> int:
            return sum(
                1
                for item in by_plan.get(plan_id, [])
                if item["planned_date"] == day
                and (item["is_completed"] or item["status"] == "completed")
            )

        winner_for: dict[date, dict] = {}
        for day in sorted(all_days):
            cover = [
                p
                for p in user_plans
                if p["start_date"] <= day <= p["end_date"]
            ]
            if not cover:
                continue
            cover.sort(
                key=lambda p: (
                    completed_on(str(p["id"]), day),
                    p["updated_at"],
                    p["created_at"],
                    str(p["id"]),
                ),
                reverse=True,
            )
            winner_for[day] = cover[0]

        for plan in user_plans:
            span = _dates(plan["start_date"], plan["end_date"])
            won = [day for day in span if winner_for.get(day, {}).get("id") == plan["id"]]
            lost = [day for day in span if day not in won]
            for day in lost:
                winner = winner_for[day]
                _transfer_day(conn, by_plan, loser_id=plan["id"], winner_id=winner["id"], day=day)
            if won == span:
                continue
            runs = _runs(won)
            if not runs:
                conn.execute(
                    text(
                        """
                        UPDATE meal_plans
                        SET status = 'archived', generation_request_hash = NULL
                        WHERE id = :id
                        """
                    ),
                    {"id": plan["id"]},
                )
                changed += 1
                continue
            # Keep the longest run on this row. Extra runs become uncovered only if
            # another ready plan does not already own them — those days were lost,
            # so they are not in `won`.
            longest = max(runs, key=lambda pair: (pair[1] - pair[0]).days)
            conn.execute(
                text(
                    """
                    UPDATE meal_plans
                    SET start_date = :start_date, end_date = :end_date
                    WHERE id = :id
                    """
                ),
                {"id": plan["id"], "start_date": longest[0], "end_date": longest[1]},
            )
            changed += 1
    return changed


def _transfer_day(conn: Connection, by_plan: dict, *, loser_id: UUID, winner_id: UUID, day: date) -> None:
    loser_items = [
        item
        for item in by_plan.get(str(loser_id), [])
        if item["planned_date"] == day
        and (item["is_completed"] or item["status"] == "completed")
    ]
    winner_items = [
        item
        for item in by_plan.get(str(winner_id), [])
        if item["planned_date"] == day
    ]
    for loser in loser_items:
        match = next(
            (item for item in winner_items if item["meal_type"] == loser["meal_type"]),
            None,
        )
        if match is None:
            conn.execute(
                text(
                    """
                    UPDATE nutrition_logs
                    SET meal_plan_item_id = NULL
                    WHERE meal_plan_item_id = :item_id
                    """
                ),
                {"item_id": loser["id"]},
            )
            continue
        conn.execute(
            text(
                """
                UPDATE meal_plan_items
                SET is_completed = TRUE, status = 'completed', completed_at = :completed_at
                WHERE id = :id
                """
            ),
            {"id": match["id"], "completed_at": loser["completed_at"]},
        )
        conn.execute(
            text(
                """
                UPDATE nutrition_logs
                SET meal_plan_item_id = :winner_item
                WHERE meal_plan_item_id = :loser_item
                """
            ),
            {"winner_item": match["id"], "loser_item": loser["id"]},
        )
