"""Tests for CodexModelUpdate entity logic.

Tests run without a full HA install by mocking the entire homeassistant
namespace before importing the module under test.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: inject fake HA modules so codex_proxy can be imported normally.
# Must happen before any codex_proxy import.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports

from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402
from custom_components.codex_proxy.update import CodexModelUpdate  # noqa: E402

# Alias for use in _make_entity
_CoordinatorEntityBase = tests.ha_stubs._CoordinatorEntity


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

    @pytest.mark.asyncio
    async def test_install_logs_on_change(self) -> None:
        """_LOGGER.info is called once when a model upgrade is installed."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.6")
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.6", backup=False)
        mock_log.info.assert_called_once()
        logged = str(mock_log.info.call_args)
        assert "gpt-5.6" in logged

    @pytest.mark.asyncio
    async def test_no_log_on_noop_install(self) -> None:
        """No log when version is already installed."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.5")
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.5", backup=False)
        mock_log.info.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_coordinator_update — live subentry refresh
# ---------------------------------------------------------------------------


class TestTitle:
    def test_title_is_chinese_string(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert entity.title == "Codex 号池模型"

    def test_title_is_not_none(self) -> None:
        entity = _make_entity()
        assert entity.title is not None


class TestClassAttributes:
    def test_has_entity_name_is_true(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_has_entity_name is True

    def test_supported_features_is_set(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_supported_features is not None

    def test_entity_category_is_config(self) -> None:
        """Update entities belong to the CONFIG category (not DIAGNOSTIC)."""
        from custom_components.codex_proxy.update import CodexModelUpdate
        from homeassistant.const import EntityCategory  # type: ignore[attr-defined]

        assert CodexModelUpdate._attr_entity_category is EntityCategory.CONFIG

    def test_translation_key(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_translation_key == "model_update"


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
