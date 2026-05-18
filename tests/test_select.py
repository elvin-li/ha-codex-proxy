"""Tests for CodexModelSelectEntity.

Covers options building (coordinator models + current model fallback),
deduplication, noop on same option, and async_select_option call flow.
"""
from __future__ import annotations

import sys
import os
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
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
    "homeassistant.components.select",
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

sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_CHAT_MODEL = "chat_model"
sys.modules["homeassistant.const"].EntityCategory = MagicMock()
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
sys.modules["homeassistant.helpers.device_registry"].DeviceEntryType = MagicMock()


class _Subscriptable:
    def __class_getitem__(cls, item: Any) -> type:
        return cls


class _SelectEntityBase:
    pass


class _CoordinatorEntityBase(_Subscriptable):
    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator


sys.modules["homeassistant.components.select"].SelectEntity = _SelectEntityBase
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = (
    _CoordinatorEntityBase
)

from custom_components.codex_proxy.select import CodexModelSelectEntity  # noqa: E402
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(chat_models: list[dict[str, Any]]) -> MagicMock:
    coord = MagicMock()
    coord.chat_models = chat_models
    return coord


def _make_subentry(current_model: str = DEFAULT_MODEL) -> MagicMock:
    sub = MagicMock()
    sub.subentry_id = "sub-1"
    sub.title = "Test Agent"
    sub.data = {"chat_model": current_model}
    return sub


def _make_entry(entry_id: str = "entry-1") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_entity(
    current_model: str = DEFAULT_MODEL,
    coord_models: list[str] | None = None,
) -> CodexModelSelectEntity:
    models = [
        {"id": mid, "created": 0, "owned_by": "", "display_name": mid}
        for mid in (coord_models or [])
    ]
    coord = _make_coordinator(models)
    entry = _make_entry()
    subentry = _make_subentry(current_model)

    entity = object.__new__(CodexModelSelectEntity)
    _CoordinatorEntityBase.__init__(entity, coord)
    entity._entry = entry
    entity._subentry = subentry
    entity._attr_unique_id = f"sub-1_model_select"
    entity._attr_device_info = {}
    entity.hass = MagicMock()
    entity.hass.config_entries.async_reload = AsyncMock()
    return entity


# ---------------------------------------------------------------------------
# options property
# ---------------------------------------------------------------------------


class TestOptions:
    def test_returns_coordinator_models(self) -> None:
        entity = _make_entity(DEFAULT_MODEL, ["gpt-5.5", "gpt-5.4"])
        assert "gpt-5.5" in entity.options
        assert "gpt-5.4" in entity.options

    def test_current_model_prepended_if_missing_from_coordinator(self) -> None:
        entity = _make_entity("gpt-5.3", ["gpt-5.5", "gpt-5.4"])
        assert entity.options[0] == "gpt-5.3"

    def test_current_model_not_duplicated(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.4"])
        assert entity.options.count("gpt-5.5") == 1

    def test_fallback_to_default_when_coordinator_empty(self) -> None:
        entity = _make_entity(DEFAULT_MODEL, [])
        assert entity.options == [DEFAULT_MODEL]

    def test_deduplication(self) -> None:
        # Coordinator returns same id twice (shouldn't happen, but be defensive)
        entity = _make_entity(DEFAULT_MODEL, ["gpt-5.5", "gpt-5.5"])
        assert entity.options.count("gpt-5.5") == 1

    def test_order_preserved(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.6", "gpt-5.5", "gpt-5.4"])
        assert entity.options == ["gpt-5.6", "gpt-5.5", "gpt-5.4"]


# ---------------------------------------------------------------------------
# current_option property
# ---------------------------------------------------------------------------


class TestCurrentOption:
    def test_returns_subentry_model(self) -> None:
        entity = _make_entity("gpt-5.6")
        assert entity.current_option == "gpt-5.6"

    def test_falls_back_to_default_when_missing(self) -> None:
        entity = _make_entity()
        entity._subentry.data = {}
        assert entity.current_option == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# async_select_option
# ---------------------------------------------------------------------------


class TestAsyncSelectOption:
    @pytest.mark.asyncio
    async def test_noop_when_same_option_selected(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.5"])
        await entity.async_select_option("gpt-5.5")
        entity.hass.config_entries.async_update_subentry.assert_not_called()
        entity.hass.config_entries.async_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_subentry_on_change(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        await entity.async_select_option("gpt-5.6")
        entity.hass.config_entries.async_update_subentry.assert_called_once()

    @pytest.mark.asyncio
    async def test_reloads_entry_on_change(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        await entity.async_select_option("gpt-5.6")
        entity.hass.config_entries.async_reload.assert_awaited_once_with("entry-1")

    @pytest.mark.asyncio
    async def test_update_subentry_receives_new_model(self) -> None:
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        await entity.async_select_option("gpt-5.6")
        call_kwargs = entity.hass.config_entries.async_update_subentry.call_args
        # Third positional arg or keyword 'data' contains the new subentry data
        new_data = call_kwargs[1].get("data") or call_kwargs[0][2]
        assert new_data["chat_model"] == "gpt-5.6"
