"""Tests for CodexConfigFlow.async_step_reconfigure data preservation.

The reconfigure step must pass ``data={**entry.data, ...}`` to
``async_update_reload_and_abort`` so that CONF_INSTALLATION_ID (and any other
future entry fields) are not silently dropped, forcing a UUID regeneration on
the next load.

ha_stubs now provides a real _ConfigFlow base class so that ``class
CodexConfigFlow(ConfigFlow, domain=DOMAIN)`` produces a genuine Python class
rather than a MagicMock, enabling direct unit tests of the flow method.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs BEFORE any codex_proxy import.
# ha_stubs registers _ConfigFlow / _ConfigSubentryFlow so that
# ``class CodexConfigFlow(ConfigFlow, domain=DOMAIN)`` produces a real class.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports
from custom_components.codex_proxy.config_flow import CodexConfigFlow  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_INSTALLATION_ID,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INSTALLATION_ID = "00000000-0000-0000-0000-deadbeef0001"
_OLD_API_KEY = "sk-old-key"
_NEW_API_KEY = "sk-new-key"
_OLD_URL = "https://old-proxy.example.com"
_NEW_URL = "https://new-proxy.example.com"


def _make_entry(
    entry_id: str = "entry-1",
    extra: dict[str, Any] | None = None,
) -> MagicMock:
    """Return a mock ConfigEntry whose data includes CONF_INSTALLATION_ID."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {
        CONF_API_KEY: _OLD_API_KEY,
        CONF_BASE_URL: _OLD_URL,
        CONF_INSTALLATION_ID: _INSTALLATION_ID,
        **(extra or {}),
    }
    return entry


def _make_flow(entry: MagicMock) -> CodexConfigFlow:
    """Build a bare CodexConfigFlow with HA lifecycle methods mocked out."""
    flow = object.__new__(CodexConfigFlow)
    flow.hass = MagicMock()
    flow._get_reconfigure_entry = MagicMock(return_value=entry)
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = MagicMock()
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.add_suggested_values_to_schema = MagicMock(side_effect=lambda schema, _: schema)
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    return flow


_VALID_USER_INPUT = {
    CONF_API_KEY: _NEW_API_KEY,
    CONF_BASE_URL: _NEW_URL,
    "model": "gpt-5.5",
    "toml_config": "",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReconfigureInitialForm:
    @pytest.mark.asyncio
    async def test_initial_form_shows_current_entry_values(self) -> None:
        """Calling async_step_reconfigure(None) should display the form pre-filled
        with the entry's current api_key and base_url (line 312 path)."""
        entry = _make_entry()
        flow = _make_flow(entry)

        result = await flow.async_step_reconfigure(None)

        flow.async_show_form.assert_called_once()
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_initial_form_does_not_call_probe(self) -> None:
        """No network probe should happen when the user hasn't submitted yet."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(),
        ) as mock_probe:
            await flow.async_step_reconfigure(None)

        mock_probe.assert_not_called()


class TestReconfigureValidationErrors:
    @pytest.mark.asyncio
    async def test_invalid_url_scheme_reshows_form(self) -> None:
        """A non-http/https URL triggers a validation error and reshows the
        reconfigure form (line 326 path) without calling the probe."""
        entry = _make_entry()
        flow = _make_flow(entry)
        bad_input = {
            CONF_API_KEY: "sk-key",
            CONF_BASE_URL: "ftp://invalid-scheme.example.com",
            "model": "gpt-5.5",
            "toml_config": "",
        }

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(),
        ) as mock_probe:
            result = await flow.async_step_reconfigure(bad_input)

        flow.async_update_reload_and_abort.assert_not_called()
        flow.async_show_form.assert_called_once()
        mock_probe.assert_not_called()
        assert result["type"] == "form"

    @pytest.mark.asyncio
    async def test_bad_toml_reshows_form(self) -> None:
        """Malformed TOML triggers a validation error and reshows the form."""
        entry = _make_entry()
        flow = _make_flow(entry)
        bad_input = {
            CONF_API_KEY: "sk-key",
            CONF_BASE_URL: "",
            "model": "gpt-5.5",
            "toml_config": "this is [ not valid toml !!",
        }

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(),
        ) as mock_probe:
            result = await flow.async_step_reconfigure(bad_input)

        flow.async_update_reload_and_abort.assert_not_called()
        mock_probe.assert_not_called()
        assert result["type"] == "form"


class TestAsyncGetSupportedSubentryTypes:
    def test_conversation_type_registered(self) -> None:
        """async_get_supported_subentry_types must register the conversation type."""
        from custom_components.codex_proxy.config_flow import (
            ConversationSubentryFlowHandler,
        )

        entry = MagicMock()
        types = CodexConfigFlow.async_get_supported_subentry_types(entry)
        assert "conversation" in types
        assert types["conversation"] is ConversationSubentryFlowHandler

    def test_ai_task_type_registered(self) -> None:
        """async_get_supported_subentry_types must register the ai_task_data type."""
        from custom_components.codex_proxy.config_flow import AITaskSubentryFlowHandler

        entry = MagicMock()
        types = CodexConfigFlow.async_get_supported_subentry_types(entry)
        assert "ai_task_data" in types
        assert types["ai_task_data"] is AITaskSubentryFlowHandler

    def test_exactly_two_subentry_types(self) -> None:
        """Exactly two subentry types should be registered."""
        entry = MagicMock()
        types = CodexConfigFlow.async_get_supported_subentry_types(entry)
        assert len(types) == 2


class TestReconfigurePreservesInstallationId:
    @pytest.mark.asyncio
    async def test_installation_id_preserved_on_success(self) -> None:
        """CONF_INSTALLATION_ID must survive a successful reconfigure."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        call_kwargs = flow.async_update_reload_and_abort.call_args
        passed_data: dict[str, Any] = call_kwargs[1]["data"]
        assert CONF_INSTALLATION_ID in passed_data, (
            "CONF_INSTALLATION_ID was dropped by reconfigure — "
            "async_setup_entry would regenerate a new UUID on next load."
        )
        assert passed_data[CONF_INSTALLATION_ID] == _INSTALLATION_ID

    @pytest.mark.asyncio
    async def test_new_api_key_reflected_in_data(self) -> None:
        """The updated API key must appear in the data passed to HA."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        passed_data = flow.async_update_reload_and_abort.call_args[1]["data"]
        assert passed_data[CONF_API_KEY] == _NEW_API_KEY

    @pytest.mark.asyncio
    async def test_new_base_url_reflected_in_data(self) -> None:
        """The updated base URL must appear in the data passed to HA."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        passed_data = flow.async_update_reload_and_abort.call_args[1]["data"]
        assert passed_data[CONF_BASE_URL] == _NEW_URL

    @pytest.mark.asyncio
    async def test_extra_entry_fields_preserved(self) -> None:
        """Any additional entry.data fields must be preserved verbatim."""
        entry = _make_entry(extra={"custom_vendor_field": "keep-me"})
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        passed_data = flow.async_update_reload_and_abort.call_args[1]["data"]
        assert passed_data.get("custom_vendor_field") == "keep-me"

    @pytest.mark.asyncio
    async def test_probe_error_skips_update(self) -> None:
        """If the probe returns an error, async_update_reload_and_abort is NOT called."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={"base": "cannot_connect"}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        flow.async_update_reload_and_abort.assert_not_called()

    @pytest.mark.asyncio
    async def test_probe_called_with_new_credentials(self) -> None:
        """_probe_proxy must receive the NEW api_key and base_url, not the old ones.

        A regression where the old entry data was used for probing would pass
        the probe with stale-but-still-valid credentials, store the new (possibly
        invalid) ones, and then fail at runtime.  This test verifies the probe
        arguments use the user-supplied values from the reconfigure form."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ) as mock_probe:
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        mock_probe.assert_awaited_once()
        probe_args = mock_probe.call_args[0]  # positional args
        assert probe_args[1] == _NEW_API_KEY, (
            f"probe received old api_key — expected {_NEW_API_KEY!r}, got {probe_args[1]!r}"
        )
        assert probe_args[2] == _NEW_URL, (
            f"probe received old base_url — expected {_NEW_URL!r}, got {probe_args[2]!r}"
        )

    @pytest.mark.asyncio
    async def test_unique_id_set_to_new_base_url(self) -> None:
        """async_set_unique_id must be called with the new base_url so HA can
        detect and prevent duplicate entries pointing at the same proxy.

        Without this call, two config entries configured for the same proxy URL
        would coexist silently — both polling the same /v1/models endpoint and
        creating duplicate entities in every subentry."""
        entry = _make_entry()
        flow = _make_flow(entry)

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(_VALID_USER_INPUT)

        flow.async_set_unique_id.assert_awaited_once_with(_NEW_URL)

    @pytest.mark.asyncio
    async def test_api_key_whitespace_stripped_in_reconfigure(self) -> None:
        """A padded api_key submitted via reconfigure must be stripped before
        being stored — same guarantee as the main flow (v0.2.46 fix)."""
        entry = _make_entry()
        flow = _make_flow(entry)
        padded_input = {**_VALID_USER_INPUT, CONF_API_KEY: "  sk-reconfigured  "}

        with patch(
            "custom_components.codex_proxy.config_flow._probe_proxy",
            new=AsyncMock(return_value={}),
        ):
            await flow.async_step_reconfigure(padded_input)

        passed_data = flow.async_update_reload_and_abort.call_args[1]["data"]
        assert passed_data[CONF_API_KEY] == "sk-reconfigured"
