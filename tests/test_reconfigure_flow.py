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

import sys
import os
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
