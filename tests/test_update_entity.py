"""Tests for CodexModelUpdate entity logic.

Tests run without a full HA install by mocking the entire homeassistant
namespace before importing the module under test.
"""

from __future__ import annotations

import os
import sys
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


def _make_subentry(model: str = DEFAULT_MODEL, title: str = "Test Agent") -> MagicMock:
    sub = MagicMock()
    sub.subentry_id = "sub-1"
    sub.title = title
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
        assert "not yet available" in entity.release_summary

    def test_no_coordinator_data_mentions_refresh_button(self) -> None:
        """When the model list hasn't loaded yet, the summary must include
        an actionable reference to the 'Refresh Models' button so users know
        how to trigger an immediate check.  This pins the UX text added in
        v0.2.58 against regression back to opaque developer-speak."""
        entity = _make_entity("gpt-5.5", None)
        assert "Refresh Models" in entity.release_summary

    def test_up_to_date(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert "latest" in entity.release_summary

    def test_up_to_date_says_already_on_latest_model(self) -> None:
        """Pin the exact 'Already on the latest model' phrasing so a future
        edit that changes the wording is caught immediately rather than
        silently breaking user-visible update card text."""
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert "Already on the latest model" in entity.release_summary

    def test_up_to_date_exact_release_summary(self) -> None:
        """When installed == latest, release_summary must be exactly
        'Already on the latest model from the proxy.'

        test_up_to_date_says_already_on_latest_model uses a substring check —
        it passes even if 'from the proxy.' is dropped or 'latest model' is
        changed to 'latest version'.  Pinning the full sentence catches any
        UX wording change before it reaches users, since the update card shows
        this text verbatim in the Home Assistant device card."""
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        assert entity.release_summary == "Already on the latest model from the proxy.", (
            f"Expected 'Already on the latest model from the proxy.', "
            f"got {entity.release_summary!r}"
        )

    def test_update_available(self) -> None:
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        summary = entity.release_summary
        assert "gpt-5.6" in summary
        assert "gpt-5.5" in summary

    def test_update_available_says_click_install(self) -> None:
        """The update-available summary must include an explicit call-to-action
        so users know the install button will apply the change."""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        assert "Click Install" in entity.release_summary

    def test_update_available_new_model_labeled_as_available(self) -> None:
        """The new (latest) model must be described as 'available' and the old
        (installed) model must be described as 'installed' — not the other way.

        test_update_available uses two ``in`` checks that pass even if the
        models are swapped in the message (both strings still appear).  This test
        verifies their relative positions: 'available: gpt-5.6' must precede
        'installed: gpt-5.5' so the summary reads correctly in the HA update card.

        Expected format: '… available: gpt-5.6 (installed: gpt-5.5). …'"""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        summary = entity.release_summary
        available_pos = summary.find("gpt-5.6")
        installed_pos = summary.find("gpt-5.5")
        assert available_pos < installed_pos, (
            f"New model 'gpt-5.6' (pos {available_pos}) must appear before "
            f"old model 'gpt-5.5' (pos {installed_pos}) in the summary — "
            "the format is '… available: <new> (installed: <old>) …'"
        )

    def test_update_available_exact_release_summary(self) -> None:
        """When a newer model is available, release_summary must be exactly:
        'Proxy has a newer model available: gpt-5.6 (installed: gpt-5.5). Click Install to switch.'

        The other update-available tests each check a single substring ('gpt-5.6
        in summary', 'gpt-5.5 in summary', 'Click Install in summary') and one
        positional check — together they constrain the string but leave gaps.
        For example a message like 'gpt-5.6 available (gpt-5.5 old) Click Install
        would pass all substring checks.  Pinning the full string catches any
        UX wording change in one assertion."""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        expected = (
            "Proxy has a newer model available: gpt-5.6 "
            "(installed: gpt-5.5). Click Install to switch."
        )
        assert entity.release_summary == expected, (
            f"Expected {expected!r}, got {entity.release_summary!r}"
        )


# ---------------------------------------------------------------------------
# release_url
# ---------------------------------------------------------------------------


class TestReleaseUrl:
    def test_none_when_no_latest(self) -> None:
        """release_url is always None — proxy model IDs may not be OpenAI IDs."""
        entity = _make_entity("gpt-5.5", None)
        assert entity.release_url is None

    def test_always_none(self) -> None:
        """release_url returns None even when a newer model is available."""
        entity = _make_entity("gpt-5.5", "gpt-5.6")
        assert entity.release_url is None


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
        # Verify the correct data key is written into the subentry
        _, call_kwargs = entity.hass.config_entries.async_update_subentry.call_args
        new_data = call_kwargs.get("data", {})
        from custom_components.codex_proxy.update import UPSTREAM_CONF_CHAT_MODEL

        assert new_data[UPSTREAM_CONF_CHAT_MODEL] == "gpt-5.6"

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
    async def test_install_log_includes_old_model(self) -> None:
        """The install info log must mention the OLD model ('was …') alongside
        the new model so operators can understand what was replaced.

        The log format is 'Installing model … (was …)'.  The existing test
        test_install_logs_on_change only verifies the NEW model appears; without
        this test a refactor that dropped the third format arg would silently
        remove the 'was' context — matching the gap that was fixed for the
        select entity (test_select.py::test_info_logged_on_model_change already
        checks both old and new)."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.6")
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.6", backup=False)
        logged = str(mock_log.info.call_args)
        # Old installed model must appear so the operator knows what was replaced
        assert "gpt-5.5" in logged, (
            "Old model 'gpt-5.5' missing from install log — "
            "operators cannot identify what was replaced without the 'was …' context"
        )

    @pytest.mark.asyncio
    async def test_install_log_includes_subentry_title(self) -> None:
        """The install info log must mention the subentry title so operators
        with multiple subentries (conversation + ai_task) can identify which
        agent's model was upgraded.

        Without the title, two simultaneous upgrades would produce identical
        log lines 'Installing model gpt-5.6 (was gpt-5.5)' with no way to
        distinguish which agent changed."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.6")
        # _make_subentry() uses title "Test Agent"
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.6", backup=False)
        logged = str(mock_log.info.call_args)
        assert "Test Agent" in logged, (
            "Subentry title missing from install log — "
            "operators cannot identify which agent was upgraded in multi-subentry setups"
        )

    @pytest.mark.asyncio
    async def test_install_log_model_positions_in_format_args(self) -> None:
        """The install info log must pass (target, title, old) as positional
        format args at indices 1, 2, and 3 respectively.

        The existing tests for new model, old model, and title each use
        str(call_args) — they pass even if the args are reordered so the
        rendered message scrambles 'Installing … on … (was …)'.  This test
        pins the exact positions so a refactor that swaps the arg order is
        immediately caught:
          args[1] = target (new model)
          args[2] = subentry title
          args[3] = installed_version (old model)"""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.6")
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.6", backup=False)
        call_args = mock_log.info.call_args
        assert call_args.args[1] == "gpt-5.6", (
            f"Expected new model 'gpt-5.6' at args[1], got {call_args.args[1]!r}"
        )
        assert call_args.args[2] == "Test Agent", (
            f"Expected subentry title 'Test Agent' at args[2], got {call_args.args[2]!r}"
        )
        assert call_args.args[3] == "gpt-5.5", (
            f"Expected old model 'gpt-5.5' at args[3], got {call_args.args[3]!r}"
        )

    @pytest.mark.asyncio
    async def test_install_log_format_string_exact(self) -> None:
        """args[0] of the install info call must be the exact format string.

        test_install_log_model_positions_in_format_args pins args[1-3] (target,
        title, old) but never checks args[0] — the template itself.  If the
        wording changed to e.g. 'Upgrading model …', the positional tests still
        pass while the operator-visible log text changes silently."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", "gpt-5.6")
        with patch("custom_components.codex_proxy.update._LOGGER") as mock_log:
            await entity.async_install(version="gpt-5.6", backup=False)
        fmt = mock_log.info.call_args.args[0]
        assert fmt == "Installing model '%s' on subentry '%s' (was '%s'); reloading entry", (
            f"Expected exact format string "
            f"\"Installing model '%s' on subentry '%s' (was '%s'); reloading entry\", "
            f"got {fmt!r}"
        )

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
    def test_title_includes_subentry_name(self) -> None:
        """title must include the subentry title so updates are distinguishable
        when a user has multiple subentries (conversation + ai_task)."""
        entity = _make_entity("gpt-5.5", "gpt-5.5")
        # _make_subentry default title is "Test Agent"
        assert entity.title == "Proxy model (Test Agent)"

    def test_title_is_not_none(self) -> None:
        entity = _make_entity()
        assert entity.title is not None

    def test_title_changes_with_subentry_title(self) -> None:
        """Different subentry titles produce different update entity titles."""
        entity_a = _make_entity("gpt-5.5", "gpt-5.5")
        entity_a._subentry = _make_subentry("gpt-5.5", title="Agent A")
        entity_b = _make_entity("gpt-5.5", "gpt-5.5")
        entity_b._subentry = _make_subentry("gpt-5.5", title="Agent B")
        assert entity_a.title != entity_b.title
        assert "Agent A" in entity_a.title
        assert "Agent B" in entity_b.title

    def test_title_exact_format_with_different_subentry_titles(self) -> None:
        """title must follow exactly 'Proxy model ({subentry.title})' for each subentry.

        test_title_changes_with_subentry_title uses ``in`` substring checks —
        'Agent A' anywhere in the title passes, including a hypothetical
        'Agent A is configured'.  The existing test_title_format also uses the
        default 'Test Agent' title; this test uses custom titles to confirm the
        format string is parametric (not hardcoded) and both titles are
        formatted identically."""
        entity_a = _make_entity("gpt-5.5", "gpt-5.5")
        entity_a._subentry = _make_subentry("gpt-5.5", title="Agent A")
        entity_b = _make_entity("gpt-5.5", "gpt-5.5")
        entity_b._subentry = _make_subentry("gpt-5.5", title="Agent B")
        assert entity_a.title == "Proxy model (Agent A)", (
            f"Expected 'Proxy model (Agent A)', got {entity_a.title!r}"
        )
        assert entity_b.title == "Proxy model (Agent B)", (
            f"Expected 'Proxy model (Agent B)', got {entity_b.title!r}"
        )


class TestClassAttributes:
    def test_has_entity_name_is_true(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_has_entity_name is True

    def test_supported_features_is_set(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_supported_features is not None

    def test_entity_category_is_config(self) -> None:
        """Update entities belong to the CONFIG category (not DIAGNOSTIC)."""
        from homeassistant.const import EntityCategory  # type: ignore[attr-defined]

        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_entity_category is EntityCategory.CONFIG

    def test_translation_key(self) -> None:
        from custom_components.codex_proxy.update import CodexModelUpdate

        assert CodexModelUpdate._attr_translation_key == "model_update"

    def test_translation_key_in_strings_json(self) -> None:
        """_attr_translation_key must map to an existing key in strings.json entity.update.

        HA renders the raw translation-key string (e.g. 'model_update') instead
        of a human-readable name when this mapping is absent.  A refactor that
        renames the Python attribute without updating strings.json would pass all
        other ClassAttribute tests but silently break the UI; this test catches
        exactly that drift."""
        import json
        import pathlib

        from custom_components.codex_proxy.update import CodexModelUpdate

        strings_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "strings.json"
        )
        update_strings = json.loads(strings_path.read_text()).get("entity", {}).get("update", {})
        key = CodexModelUpdate._attr_translation_key
        assert key in update_strings, (
            f"'{key}' missing from strings.json entity.update — "
            "HA will render the raw translation key instead of a human-readable update entity name"
        )


class TestDeviceInfo:
    """Device info must use build_codex_device_info for full metadata."""

    def _make_full_entity(self, model: str = "gpt-5.5", title: str = "My Agent") -> CodexModelUpdate:
        """Build an entity via __init__ so device_info is set by the real constructor."""
        from custom_components.codex_proxy.update import CodexModelUpdate

        coord = _make_coordinator(model)
        entry = MagicMock()
        entry.entry_id = "entry-1"
        subentry = _make_subentry(model, title)

        entity = object.__new__(CodexModelUpdate)
        CodexModelUpdate.__init__(entity, coord, entry, subentry)
        entity.hass = MagicMock()
        entity.hass.config_entries.async_reload = AsyncMock()
        return entity

    def test_manufacturer_is_set(self) -> None:
        """update entity device_info must include manufacturer (not bare identifiers-only)."""
        entity = self._make_full_entity()
        assert entity._attr_device_info.get("manufacturer") == "OpenAI Codex Token Pool"

    def test_name_matches_subentry_title(self) -> None:
        """Device name must reflect the subentry title so HA shows a readable card."""
        entity = self._make_full_entity(title="Codex Update Test")
        assert entity._attr_device_info.get("name") == "Codex Update Test"

    def test_sw_version_is_present(self) -> None:
        """sw_version must be present so the device card shows the integration version."""
        entity = self._make_full_entity()
        assert "sw_version" in entity._attr_device_info

    def test_unique_id_exact_format(self) -> None:
        """unique_id must be '{subentry_id}_model_update' exactly.

        Pinning the full format catches a refactor that changes the suffix or
        separator — a breaking change because HA uses the unique_id as a stable
        entity registry key, so any format change silently creates a duplicate
        entity and orphans the old one.  This test builds via the real __init__
        so a change in the constructor is caught directly."""
        entity = self._make_full_entity()
        # _make_subentry sets subentry_id = "sub-1"
        assert entity._attr_unique_id == "sub-1_model_update"


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
