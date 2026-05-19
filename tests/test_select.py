"""Tests for CodexModelSelectEntity.

Covers options building (coordinator models + current model fallback),
deduplication, noop on same option, and async_select_option call flow.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports
from custom_components.codex_proxy.const import DEFAULT_MODEL  # noqa: E402
from custom_components.codex_proxy.select import CodexModelSelectEntity  # noqa: E402

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
    entity._attr_unique_id = "sub-1_model_select"
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

    def test_returns_coordinator_models_exact_list(self) -> None:
        """When the current model is already in the coordinator list, options
        must be *exactly* the coordinator list in the same order — no extras.

        test_returns_coordinator_models uses two ``in`` checks which pass even
        if options contains additional unexpected entries (e.g. from a stale
        prepend path).  Exact list equality verifies the happy path is clean."""
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.4"])
        assert entity.options == ["gpt-5.5", "gpt-5.4"], (
            f"Expected exactly ['gpt-5.5', 'gpt-5.4'], got {entity.options!r}"
        )

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

    def test_fallback_to_default_when_current_is_none_and_coordinator_empty(self) -> None:
        """If current_option returns None (subentry stores explicit None for the
        chat_model key) and the coordinator has no models, options must still
        return [DEFAULT_MODEL] rather than an empty list."""
        entity = _make_entity(DEFAULT_MODEL, [])
        # Force current_option to return None by overriding subentry data
        entity._subentry.data = {"chat_model": None}
        assert entity.options == [DEFAULT_MODEL]


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

    def test_falls_back_to_default_when_value_is_none(self) -> None:
        """Explicit None stored in subentry data (e.g., written by an older
        version) must produce DEFAULT_MODEL, not None, so HA never warns about
        current_option not being in options."""
        entity = _make_entity()
        entity._subentry.data = {"chat_model": None}
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
    async def test_update_subentry_data_passed_as_keyword(self) -> None:
        """async_update_subentry must be called with ``data=`` as a keyword
        argument, not a positional one.

        test_update_subentry_receives_new_model uses an OR fallback:
        ``call_kwargs[1].get("data") or call_kwargs[0][2]`` — it passes whether
        data is keyword or the third positional arg.  If a refactor changes the
        calling convention to positional (dropping the ``data=`` keyword), the
        existing test still passes while HA's config_entries API may reject the
        call.  Pinning ``"data" in call_args.kwargs`` ensures the keyword form is
        always used, matching the pattern established in test_setup_entry.py
        (test_installation_id_update_uses_keyword_data_arg, v0.2.107)."""
        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        await entity.async_select_option("gpt-5.6")
        call_args = entity.hass.config_entries.async_update_subentry.call_args
        assert "data" in call_args.kwargs, (
            f"async_update_subentry must be called with data= as a keyword arg; "
            f"got kwargs={call_args.kwargs!r}, args={call_args.args!r}"
        )

    @pytest.mark.asyncio
    async def test_info_logged_on_model_change(self) -> None:
        """_LOGGER.info is called once when the model is changed, mentioning
        both the old and new model ids."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.6")
        mock_log.info.assert_called_once()
        # Log message should mention both old and new model
        logged = str(mock_log.info.call_args)
        assert "gpt-5.6" in logged
        assert "gpt-5.5" in logged  # old model must also appear

    @pytest.mark.asyncio
    async def test_info_log_includes_subentry_title(self) -> None:
        """The model-change info log must include the subentry title so operators
        with multiple subentries (conversation + ai_task) can identify which
        agent's model was changed.

        Without the title, log lines are identical across subentries:
        'Model changed from gpt-5.5 to gpt-5.6' is ambiguous when both
        conversation and ai_task agents are reconfigured simultaneously.
        Matches the pattern added in v0.2.79 for the update entity."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        # _make_subentry sets title = "Test Agent"
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.6")
        logged = str(mock_log.info.call_args)
        assert "Test Agent" in logged, (
            "Subentry title missing from model-change log — "
            "operators cannot identify which agent's model changed in multi-subentry setups"
        )

    @pytest.mark.asyncio
    async def test_info_log_model_positions_in_format_args(self) -> None:
        """The info log format must pass (title, old_model, new_model) as
        positional format args in that order so the rendered message places
        them correctly.

        test_info_logged_on_model_change uses str(call_args) to check that
        both model ids appear, but that would pass even if old and new model
        args were swapped.  Checking the positional args directly pins the
        order: args[1]=title, args[2]=old_model, args[3]=new_model — matching
        the format string 'Model for subentry … changed from … to …'."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.6")
        call_args = mock_log.info.call_args
        assert call_args.args[1] == "Test Agent", (
            f"Expected subentry title 'Test Agent' at args[1], got {call_args.args[1]!r}"
        )
        assert call_args.args[2] == "gpt-5.5", (
            f"Expected old model 'gpt-5.5' at args[2], got {call_args.args[2]!r}"
        )
        assert call_args.args[3] == "gpt-5.6", (
            f"Expected new model 'gpt-5.6' at args[3], got {call_args.args[3]!r}"
        )

    @pytest.mark.asyncio
    async def test_info_log_format_string_exact(self) -> None:
        """args[0] of the info call must be the exact format string used in
        select.py so a refactor that changes the template wording is caught.

        test_info_log_model_positions_in_format_args pins args[1-3] (title,
        old, new) but never checks args[0] — the format string itself.  If the
        log message were reworded to e.g. 'Switching model …', all positional
        tests still pass while the operator-facing log text changes silently."""
        from unittest.mock import patch

        entity = _make_entity("gpt-5.5", ["gpt-5.5", "gpt-5.6"])
        with patch("custom_components.codex_proxy.select._LOGGER") as mock_log:
            await entity.async_select_option("gpt-5.6")
        fmt = mock_log.info.call_args.args[0]
        assert fmt == "Model for subentry '%s' changed from '%s' to '%s'; reloading entry", (
            f"Expected exact format string "
            f"\"Model for subentry '%s' changed from '%s' to '%s'; reloading entry\", "
            f"got {fmt!r}"
        )

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

    def test_translation_key_in_strings_json(self) -> None:
        """_attr_translation_key must map to an existing key in strings.json entity.select.

        HA renders the raw translation-key string (e.g. 'active_model') instead
        of a human-readable label when this mapping is absent.  A refactor that
        renames the Python attribute without updating strings.json would pass all
        other ClassAttribute tests but silently break the UI; this test catches
        exactly that drift."""
        import json
        import pathlib

        strings_path = (
            pathlib.Path(__file__).parent.parent
            / "custom_components"
            / "codex_proxy"
            / "strings.json"
        )
        select_strings = json.loads(strings_path.read_text()).get("entity", {}).get("select", {})
        key = CodexModelSelectEntity._attr_translation_key
        assert key in select_strings, (
            f"'{key}' missing from strings.json entity.select — "
            "HA will render the raw translation key instead of a human-readable select label"
        )


class TestDeviceInfo:
    """Device info must use build_codex_device_info for full metadata."""

    def _make_full_entity(
        self, model: str = "gpt-5.5", title: str = "My Agent"
    ) -> CodexModelSelectEntity:
        """Build an entity via __init__ so device_info is set by the real constructor."""
        coord = _make_coordinator([])
        entry = _make_entry()
        subentry = _make_subentry(model)
        subentry.title = title

        entity = object.__new__(CodexModelSelectEntity)
        CodexModelSelectEntity.__init__(entity, coord, entry, subentry)
        entity.hass = MagicMock()
        entity.hass.config_entries.async_reload = AsyncMock()
        return entity

    def test_manufacturer_is_set(self) -> None:
        """select entity device_info must include manufacturer (not bare identifiers-only)."""
        entity = self._make_full_entity()
        assert entity._attr_device_info.get("manufacturer") == "OpenAI Codex Token Pool"

    def test_name_matches_subentry_title(self) -> None:
        """Device name must reflect the subentry title so HA shows a readable card."""
        entity = self._make_full_entity(title="Codex Test Agent")
        assert entity._attr_device_info.get("name") == "Codex Test Agent"

    def test_sw_version_is_present(self) -> None:
        """sw_version must be present so the device card shows the integration version."""
        entity = self._make_full_entity()
        assert "sw_version" in entity._attr_device_info

    def test_unique_id_exact_format(self) -> None:
        """unique_id must be '{subentry_id}_model_select' exactly.

        Pinning the full format catches a refactor that changes the suffix or
        separator — a breaking change because HA uses the unique_id as a stable
        entity registry key, so any format change silently creates a duplicate
        entity and orphans the old one.  This test builds via the real __init__
        so a change in the constructor is caught directly."""
        entity = self._make_full_entity()
        # _make_subentry sets subentry_id = "sub-1"
        assert entity._attr_unique_id == "sub-1_model_select"


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
