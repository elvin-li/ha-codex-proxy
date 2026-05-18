"""Tests for CodexModelUpdate entity logic.

Tests run without a full HA install by mocking the entire homeassistant
namespace before importing the module under test.
"""
from __future__ import annotations

import sys
import os
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: inject fake HA modules so codex_proxy can be imported normally.
# Must happen before any codex_proxy import.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
    "homeassistant.components.openai_conversation.conversation",
    "homeassistant.components.openai_conversation.ai_task",
    "homeassistant.components.update",
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

for _mod_name in _HA_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

# Patch specific attributes needed for imports to succeed
sys.modules[
    "homeassistant.components.openai_conversation.const"
].CONF_CHAT_MODEL = "chat_model"
class _Subscriptable:
    """Base class whose subclasses support `Cls[X]` generic syntax."""
    def __class_getitem__(cls, item: Any) -> type:
        return cls


class _UpdateEntityBase(_Subscriptable):
    pass


class _CoordinatorEntityBase(_Subscriptable):
    def _handle_coordinator_update(self) -> None:
        """Stub — real implementation notifies HA state machine."""


class _DataUpdateCoordinatorBase(_Subscriptable):
    pass


sys.modules["homeassistant.components.update"].UpdateEntity = _UpdateEntityBase
sys.modules["homeassistant.components.update"].UpdateEntityFeature = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = _CoordinatorEntityBase
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = _DataUpdateCoordinatorBase
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
sys.modules["homeassistant.helpers.device_registry"].DeviceEntryType = MagicMock()
sys.modules["homeassistant.const"].EntityCategory = MagicMock()
sys.modules["homeassistant.core"].callback = lambda f: f

# Now safe to import const and update
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402
from custom_components.codex_proxy.update import CodexModelUpdate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subentry(model: str = DEFAULT_MODEL) -> MagicMock:
    sub = MagicMock()
    sub.subentry_id = "sub-1"
    sub.data = {"chat_model": model}
    return sub


def _make_coordinator(latest: str | None) -> MagicMock:
    coord = MagicMock()
    coord.latest_chat_model_id = latest
    return coord


def _make_entity(
    installed: str = DEFAULT_MODEL, latest: str | None = DEFAULT_MODEL
) -> CodexModelUpdate:
    entity = object.__new__(CodexModelUpdate)
    entity._subentry = _make_subentry(installed)
    entity._entry = MagicMock()
    entity._entry.entry_id = "entry-1"
    entity.coordinator = _make_coordinator(latest)
    entity.hass = MagicMock()
    entity.hass.config_entries.async_reload = AsyncMock()
    return entity


# ---------------------------------------------------------------------------
# installed_version / latest_version
# ---------------------------------------------------------------------------


class TestVersionProperties:
    def test_installed_version_from_subentry(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert entity.installed_version == "gpt-5.5"

    def test_installed_version_falls_back_to_default(self) -> None:
        entity = _make_entity()
        entity._subentry = MagicMock()
        entity._subentry.data = {}  # no chat_model key
        assert entity.installed_version == DEFAULT_MODEL

    def test_latest_version_equals_coordinator_latest(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        assert entity.latest_version == "gpt-5.6"

    def test_latest_version_falls_back_to_installed_when_coordinator_empty(
        self,
    ) -> None:
        entity = _make_entity("gpt-5.5", None)
        assert entity.latest_version == entity.installed_version


# ---------------------------------------------------------------------------
# release_summary
# ---------------------------------------------------------------------------


class TestReleaseSummary:
    def test_no_coordinator_data(self) -> None:
        entity = _make_entity("gpt-5.5", None)
        assert "尚未" in entity.release_summary

    def test_up_to_date(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert "最新" in entity.release_summary

    def test_update_available(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        summary = entity.release_summary
        assert "gpt-5.6" in summary
        assert "gpt-5.5" in summary


# ---------------------------------------------------------------------------
# release_url
# ---------------------------------------------------------------------------


class TestReleaseUrl:
    def test_none_when_no_latest(self) -> None:
        entity = _make_entity("gpt-5.5", None)
        assert entity.release_url is None

    def test_url_contains_model_id(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        url = entity.release_url
        assert url is not None
        assert "gpt-5.6" in url


# ---------------------------------------------------------------------------
# async_install
# ---------------------------------------------------------------------------


class TestAsyncInstall:
    @pytest.mark.asyncio
    async def test_install_noop_when_already_current(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        await entity.async_install(version="gpt-5.5", backup=False)
        entity.hass.config_entries.async_update_subentry.assert_not_called()
        entity.hass.config_entries.async_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_updates_subentry_and_reloads(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        await entity.async_install(version="gpt-5.6", backup=False)
        entity.hass.config_entries.async_update_subentry.assert_called_once()
        entity.hass.config_entries.async_reload.assert_awaited_once_with("entry-1")

    @pytest.mark.asyncio
    async def test_install_uses_latest_when_version_is_none(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        await entity.async_install(version=None, backup=False)
        entity.hass.config_entries.async_update_subentry.assert_called_once()
        entity.hass.config_entries.async_reload.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_install_noop_when_no_target_and_no_latest(self) -> None:
        entity = _make_entity("gpt-5.5", None)
        await entity.async_install(version=None, backup=False)
        entity.hass.config_entries.async_update_subentry.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_coordinator_update — live subentry refresh
# ---------------------------------------------------------------------------


class TestHandleCoordinatorUpdate:
    def test_subentry_refreshed_from_entry_subentries(self) -> None:
        """After a coordinator update, _subentry should be re-read from
        entry.subentries so installed_version reflects external changes."""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        # Simulate the live subentry having been updated externally to gpt-5.6
        live_subentry = _make_subentry("gpt-5.6")
        entity._entry.subentries = {entity._subentry.subentry_id: live_subentry}

        entity._handle_coordinator_update()

        assert entity._subentry is live_subentry
        assert entity.installed_version == "gpt-5.6"

    def test_subentry_unchanged_when_not_in_entry(self) -> None:
        """If the subentry_id is not found in entry.subentries (e.g. it was
        deleted), the stale subentry reference is preserved."""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        original_subentry = entity._subentry
        entity._entry.subentries = {}  # empty — subentry not found

        entity._handle_coordinator_update()

        assert entity._subentry is original_subentry
