"""Tests for async_setup_entry in codex_proxy/__init__.py.

Focuses on:
- installation_id is generated when absent from entry.data
- installation_id is reused when already present (no async_update_entry call)
- coordinator failure path: entry still loads (returns True)
- hass.data is populated with DATA_COORDINATOR key
- async_forward_entry_setups is called with PLATFORMS
Runs without a full HA install.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx  # noqa: E402, I001
import tests.ha_stubs  # noqa: F401, E402, I001
from custom_components.codex_proxy import async_setup_entry  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_INSTALLATION_ID,
    DATA_COORDINATOR,
    DOMAIN,
)
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: str = "entry-1",
    installation_id: str | None = None,
) -> MagicMock:
    """Return a mock ConfigEntry optionally pre-populated with an installation_id."""
    entry = MagicMock()
    entry.entry_id = entry_id
    data: dict = {
        "api_key": "sk-test-key",
        "base_url": "https://proxy.example.com",
    }
    if installation_id is not None:
        data[CONF_INSTALLATION_ID] = installation_id
    entry.data = data
    entry.async_on_unload = MagicMock()
    return entry


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    return hass


def _patch_coordinator(first_refresh_side_effect=None):
    """Return a context manager that replaces CodexModelCoordinator with a mock."""
    coord_mock = MagicMock()
    refresh = AsyncMock(side_effect=first_refresh_side_effect)
    coord_mock.async_config_entry_first_refresh = refresh
    return patch(
        "custom_components.codex_proxy.CodexModelCoordinator",
        return_value=coord_mock,
    ), coord_mock


# ---------------------------------------------------------------------------
# installation_id handling
# ---------------------------------------------------------------------------


class TestInstallationId:
    @pytest.mark.asyncio
    async def test_generates_installation_id_when_absent(self) -> None:
        """When entry.data has no installation_id, a fresh UUID is generated and
        async_update_entry is called to persist it."""
        entry = _make_entry(installation_id=None)
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = hass.config_entries.async_update_entry.call_args
        new_data = call_kwargs[1].get("data") or call_kwargs[0][1]
        assert CONF_INSTALLATION_ID in new_data
        # Should be a valid UUID string
        import uuid

        uuid.UUID(new_data[CONF_INSTALLATION_ID])  # raises if invalid

    @pytest.mark.asyncio
    async def test_reuses_installation_id_when_present(self) -> None:
        """When entry.data already has an installation_id, it must be reused and
        async_update_entry must NOT be called."""
        iid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        entry = _make_entry(installation_id=iid)
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_update_entry.assert_not_called()


# ---------------------------------------------------------------------------
# Return value and hass.data
# ---------------------------------------------------------------------------


class TestSetupResult:
    @pytest.mark.asyncio
    async def test_returns_true(self) -> None:
        entry = _make_entry(installation_id="iid-ok")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_hass_data_populated(self) -> None:
        entry = _make_entry("entry-data", installation_id="iid-data")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        assert DOMAIN in hass.data
        assert "entry-data" in hass.data[DOMAIN]
        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-data"]

    @pytest.mark.asyncio
    async def test_forward_entry_setups_called(self) -> None:
        from custom_components.codex_proxy import PLATFORMS

        entry = _make_entry(installation_id="iid-fwd")
        hass = _make_hass()
        patcher, _ = _patch_coordinator()

        with patcher:
            await async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(entry, PLATFORMS)


# ---------------------------------------------------------------------------
# Coordinator first-refresh failure — should not prevent entry from loading
# ---------------------------------------------------------------------------


class TestCoordinatorFailurePath:
    @pytest.mark.asyncio
    async def test_returns_true_when_coordinator_raises_update_failed(self) -> None:
        """UpdateFailed on first refresh is non-fatal; entry still loads."""

        entry = _make_entry(installation_id="iid-fail")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("poll failed"))

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_data_still_stored_when_coordinator_refresh_fails(self) -> None:
        """Even on refresh failure the coordinator is stored in hass.data so the
        next poll can succeed without a full reload."""
        entry = _make_entry("entry-fail2", installation_id="iid-fail2")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(first_refresh_side_effect=UpdateFailed("timeout"))

        with patcher:
            await async_setup_entry(hass, entry)

        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-fail2"]

    @pytest.mark.asyncio
    async def test_httpx_http_error_is_non_fatal(self) -> None:
        """httpx.HTTPError during first refresh is caught and treated as
        non-fatal — the except clause in __init__.py covers both UpdateFailed
        and httpx.HTTPError."""
        entry = _make_entry("entry-fail3", installation_id="iid-fail3")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(
            first_refresh_side_effect=httpx.ConnectError("connection refused")
        )

        with patcher:
            result = await async_setup_entry(hass, entry)

        assert result is True
        assert DATA_COORDINATOR in hass.data[DOMAIN]["entry-fail3"]

    @pytest.mark.asyncio
    async def test_warning_logged_when_coordinator_refresh_fails(self) -> None:
        """When the coordinator's first refresh raises UpdateFailed or
        httpx.HTTPError, ``async_setup_entry`` must emit exactly one
        ``_LOGGER.warning`` call carrying the error so operators can diagnose
        transient startup failures from HA logs without enabling full DEBUG."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-warn")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(
            first_refresh_side_effect=UpdateFailed("proxy unreachable")
        )

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        mock_log.warning.assert_called_once()
        logged = str(mock_log.warning.call_args)
        assert "proxy unreachable" in logged or "Initial model refresh failed" in logged

    @pytest.mark.asyncio
    async def test_warning_log_prefix_is_initial_model_refresh_failed(self) -> None:
        """The warning format string must begin with 'Initial model refresh failed'
        so operators can distinguish startup-phase coordinator failures from
        later runtime poll failures in HA logs.

        The existing test_warning_logged_when_coordinator_refresh_fails uses an
        OR condition (error text OR format prefix); without this dedicated test a
        refactor that changes the format string to e.g. 'Coordinator error: %s'
        would still pass because the exception text 'proxy unreachable' appears
        in the call_args repr regardless of the format prefix."""
        from unittest.mock import patch

        entry = _make_entry(installation_id="iid-prefix")
        hass = _make_hass()
        patcher, _ = _patch_coordinator(
            first_refresh_side_effect=UpdateFailed("proxy unreachable")
        )

        with (
            patcher,
            patch("custom_components.codex_proxy._LOGGER") as mock_log,
        ):
            await async_setup_entry(hass, entry)

        logged = str(mock_log.warning.call_args)
        assert "Initial model refresh failed" in logged, (
            "Warning format prefix 'Initial model refresh failed' missing from "
            "startup coordinator failure log — operators cannot distinguish "
            "startup-phase failures without the specific prefix in HA logs"
        )
