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
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports

from custom_components.codex_proxy.select import CodexModelSelectEntity  # noqa: E402
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402

# Use the shared CoordinatorEntity base from ha_stubs
from tests.ha_stubs import _CoordinatorEntity as _CoordinatorEntityBase  # noqa: E402


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

    @pytest.mark.asyncio
    async def test_info_logged_on_model_change(self) -> None:
        """_LOGGER.info is called once when the model is changed."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.6")
        mock_log.info.assert_called_once()
        # Log message should mention both old and new model
        logged = str(mock_log.info.call_args)
        assert "gpt-5.6" in logged

    @pytest.mark.asyncio
    async def test_no_log_on_noop(self) -> None:
        """No log should be emitted when the same model is re-selected."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5"])
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.5")
        mock_log.info.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_coordinator_update
# ---------------------------------------------------------------------------


class TestClassAttributes:
    def test_has_entity_name_is_true(self) -> None:
        assert CodexModelSelectEntity._attr_has_entity_name is True

    def test_translation_key(self) -> None:
        assert CodexModelSelectEntity._attr_translation_key == "active_model"

    def test_disabled_by_default(self) -> None:
        """Select entity is opt-in; default enabled = False."""
        assert CodexModelSelectEntity._attr_entity_registry_enabled_default is False

    def test_entity_category_is_config(self) -> None:
        """Select entity belongs to CONFIG category (user configures the model)."""
        from homeassistant.const import EntityCategory  # type: ignore[attr-defined]

        assert CodexModelSelectEntity._attr_entity_category is EntityCategory.CONFIG


class TestHandleCoordinatorUpdate:
    def test_subentry_refreshed_from_entry_on_update(self) -> None:
        """When the coordinator fires an update, _subentry should be re-read
        from _entry.subentries so stale external changes are picked up."""
        entity = _make_entity("gpt-5.5", ["gpt-5.5"])

        updated_sub = _make_subentry("gpt-5.6")
        updated_sub.subentry_id = "sub-1"
        entity._entry.subentries = {"sub-1": updated_sub}

        entity._handle_coordinator_update()

        assert entity._subentry is updated_sub

    def test_subentry_unchanged_when_not_in_entry(self) -> None:
        """If the subentry_id is no longer in entry.subentries (e.g., it was
        deleted), _subentry should not change."""
        entity = _make_entity("gpt-5.5", ["gpt-5.5"])
        original_sub = entity._subentry
        entity._entry.subentries = {}  # subentry removed

        entity._handle_coordinator_update()

        assert entity._subentry is original_sub
