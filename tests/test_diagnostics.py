"""Tests for the diagnostics module.

Exercises async_get_config_entry_diagnostics: API key redaction, coordinator
info shape, and subentry enumeration. Runs without a full HA install.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.diagnostics",
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
    "homeassistant.components.openai_conversation.conversation",
    "homeassistant.components.openai_conversation.ai_task",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.httpx_client",
    "homeassistant.helpers.update_coordinator",
]
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# Real async_redact_data implementation so redaction actually works in tests.
def _real_async_redact_data(data: dict[str, Any], to_redact: set[str]) -> dict[str, Any]:
    result = dict(data)
    for key in to_redact:
        if key in result:
            result[key] = "**REDACTED**"
    return result


sys.modules["homeassistant.components.diagnostics"].async_redact_data = (
    _real_async_redact_data
)

from custom_components.codex_proxy.diagnostics import async_get_config_entry_diagnostics  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "sk-secret-test-key-abcdef"
_BASE_URL = "https://proxy.example.com"
_INSTALLATION_ID = "00000000-0000-0000-0000-000000000001"


def _make_subentry(
    subentry_type: str = "conversation",
    title: str = "Test Agent",
    data: dict[str, Any] | None = None,
) -> MagicMock:
    s = MagicMock()
    s.subentry_type = subentry_type
    s.title = title
    s.data = data or {
        "chat_model": "gpt-5.5",
        "service_tier": None,
    }
    return s


def _make_coordinator(
    last_success: bool = True,
    last_time: datetime | None = None,
    chat_models: list[dict[str, Any]] | None = None,
    latest_id: str | None = "gpt-5.5",
    models_data: list[dict[str, Any]] | None = None,
) -> MagicMock:
    coord = MagicMock()
    coord.last_update_success = last_success
    coord.last_update_success_time = last_time
    coord.chat_models = chat_models or [{"id": "gpt-5.5"}]
    coord.latest_chat_model_id = latest_id
    coord.data = {"models": models_data or [{"id": "gpt-5.5"}]}
    return coord


def _make_hass(coordinator: MagicMock, entry_id: str) -> MagicMock:
    from custom_components.codex_proxy.const import DATA_COORDINATOR, DOMAIN

    hass = MagicMock()
    hass.data = {DOMAIN: {entry_id: {DATA_COORDINATOR: coordinator}}}
    return hass


def _make_entry(
    entry_id: str = "entry-1",
    api_key: str = _API_KEY,
    base_url: str = _BASE_URL,
    subentries: dict[str, Any] | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {
        "api_key": api_key,
        "base_url": base_url,
        "codex_installation_id": _INSTALLATION_ID,
    }
    entry.subentries = subentries or {}
    return entry


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiagnosticsRedaction:
    @pytest.mark.asyncio
    async def test_api_key_is_redacted(self) -> None:
        coord = _make_coordinator()
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["entry_data"]["api_key"] == "**REDACTED**"
        assert _API_KEY not in str(result)

    @pytest.mark.asyncio
    async def test_base_url_not_redacted(self) -> None:
        coord = _make_coordinator()
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["entry_data"]["base_url"] == _BASE_URL


class TestDiagnosticsCoordinatorInfo:
    @pytest.mark.asyncio
    async def test_coordinator_section_present(self) -> None:
        coord = _make_coordinator()
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert "coordinator" in result
        c = result["coordinator"]
        assert "last_update_success" in c
        assert "last_update_success_time" in c
        assert "chat_models_count" in c
        assert "latest_chat_model" in c
        assert "models" in c

    @pytest.mark.asyncio
    async def test_last_update_success_time_isoformat(self) -> None:
        ts = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
        coord = _make_coordinator(last_time=ts)
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["last_update_success_time"] == ts.isoformat()

    @pytest.mark.asyncio
    async def test_last_update_success_time_none(self) -> None:
        coord = _make_coordinator(last_time=None)
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["last_update_success_time"] is None

    @pytest.mark.asyncio
    async def test_chat_models_count(self) -> None:
        models = [{"id": "gpt-5.5"}, {"id": "gpt-5.4"}]
        coord = _make_coordinator(chat_models=models)
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["chat_models_count"] == 2

    @pytest.mark.asyncio
    async def test_latest_chat_model(self) -> None:
        coord = _make_coordinator(latest_id="gpt-5.6")
        entry = _make_entry()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["coordinator"]["latest_chat_model"] == "gpt-5.6"


class TestDiagnosticsSubentries:
    @pytest.mark.asyncio
    async def test_subentries_section_present(self) -> None:
        conv = _make_subentry("conversation", "Codex 号池对话")
        task = _make_subentry("ai_task_data", "Codex 号池 AI Task")
        entry = _make_entry(subentries={"s1": conv, "s2": task})
        coord = _make_coordinator()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert len(result["subentries"]) == 2
        types = {s["subentry_type"] for s in result["subentries"]}
        assert "conversation" in types
        assert "ai_task_data" in types

    @pytest.mark.asyncio
    async def test_empty_subentries(self) -> None:
        entry = _make_entry(subentries={})
        coord = _make_coordinator()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["subentries"] == []

    @pytest.mark.asyncio
    async def test_subentry_data_included(self) -> None:
        sub = _make_subentry(data={"chat_model": "gpt-5.5", "service_tier": None})
        entry = _make_entry(subentries={"s1": sub})
        coord = _make_coordinator()
        hass = _make_hass(coord, entry.entry_id)

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["subentries"][0]["data"]["chat_model"] == "gpt-5.5"
