"""Shared fixtures for codex_proxy tests."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

DOMAIN = "codex_proxy"
MOCK_API_KEY = "sk-test-key-1234"
MOCK_BASE_URL = "https://proxy.example.com"
MOCK_MODEL = "gpt-5.5"
MOCK_INSTALLATION_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Minimal stand-ins for HA types so tests run without a full HA install.
# When running inside pytest-homeassistant-custom-component these are replaced
# by the real HA fixtures.
# ---------------------------------------------------------------------------


class _FakeSubentry:
    def __init__(
        self,
        subentry_id: str,
        subentry_type: str,
        title: str,
        data: dict[str, Any],
    ) -> None:
        self.subentry_id = subentry_id
        self.subentry_type = subentry_type
        self.title = title
        self.data = data


class _FakeEntry:
    def __init__(
        self,
        entry_id: str,
        data: dict[str, Any],
        subentries: dict[str, _FakeSubentry] | None = None,
        title: str = "Codex 号池 (proxy.example.com)",
    ) -> None:
        self.entry_id = entry_id
        self.data = data
        self.subentries: dict[str, _FakeSubentry] = subentries or {}
        self.title = title


@pytest.fixture
def mock_entry() -> _FakeEntry:
    """Config entry with one conversation and one ai_task subentry."""
    conv = _FakeSubentry(
        subentry_id="sub-conv-1",
        subentry_type="conversation",
        title="Codex 号池对话",
        data={
            "chat_model": MOCK_MODEL,
            "reasoning_effort": "xhigh",
            "store_responses": False,
            "prompt": "",
            "service_tier": None,
            "llm_hass_api": [],
        },
    )
    task = _FakeSubentry(
        subentry_id="sub-task-1",
        subentry_type="ai_task_data",
        title="Codex 号池 AI Task",
        data={
            "chat_model": MOCK_MODEL,
            "reasoning_effort": "xhigh",
            "store_responses": False,
            "prompt": "",
            "service_tier": None,
            "llm_hass_api": [],
        },
    )
    return _FakeEntry(
        entry_id="entry-test-1",
        data={
            "api_key": MOCK_API_KEY,
            "base_url": MOCK_BASE_URL,
            "codex_installation_id": MOCK_INSTALLATION_ID,
        },
        subentries={"sub-conv-1": conv, "sub-task-1": task},
    )


@pytest.fixture
def mock_coordinator(mock_entry: _FakeEntry) -> MagicMock:
    """Fake coordinator with one chat model returned."""
    coord = MagicMock()
    coord.data = {
        "models": [
            {
                "id": "gpt-5.5",
                "created": 1_700_000_000,
                "owned_by": "openai",
                "display_name": "GPT-5.5",
            }
        ]
    }
    coord.chat_models = coord.data["models"]
    coord.latest_chat_model_id = "gpt-5.5"
    coord.last_update_success = True
    coord.last_update_success_time = None
    return coord
