"""Phase 13 contextual chat tests — MockTextProvider only."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.ai.mock import MockTextProvider
from tests.conftest import API_PREFIX
from tests.test_profile_api import PROFILE_PAYLOAD, auth, register


@pytest.mark.asyncio
async def test_chat_conversation_and_safe_refusal(client: AsyncClient, app):
    tokens = await register(client, "chat@example.com")
    profile = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=PROFILE_PAYLOAD
    )
    assert profile.status_code == 200, profile.text

    app.state.text_ai_provider = MockTextProvider(
        [
            {
                "answer": "Можно заменить курицу на индейку или тофу.",
                "suggested_actions": [
                    {
                        "type": "replace_meal_item",
                        "label": "Заменить блюдо",
                        "payload": None,
                    }
                ],
                "warnings": [],
            }
        ]
    )

    created = await client.post(
        f"{API_PREFIX}/ai/chat/conversations",
        headers=auth(tokens),
        json={"title": "Тест"},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["id"]

    reply = await client.post(
        f"{API_PREFIX}/ai/chat/conversations/{conversation_id}/messages",
        headers=auth(tokens),
        json={"content": "Чем заменить курицу на ужин?"},
    )
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["assistant_message"]["content"]
    assert body["assistant_message"]["suggested_actions"]

    unsafe = await client.post(
        f"{API_PREFIX}/ai/chat/conversations/{conversation_id}/messages",
        headers=auth(tokens),
        json={"content": "Поставь мне диагноз и назначь лечение"},
    )
    assert unsafe.status_code == 200, unsafe.text
    assert "врач" in unsafe.json()["assistant_message"]["content"].lower()
    assert unsafe.json()["warnings"]
