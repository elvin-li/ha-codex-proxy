"""Tests for async_setup_entry and async_unload_entry
in custom_components/codex_proxy/__init__.py.

Runs without a full HA install — all HA modules are mocked via ha_stubs.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402
from custom_components.codex_proxy import async_unload_entry  # noqa: E402
from custom_components.codex_proxy.const import (  # noqa: E402
    CONF_INSTALLATION_ID,
    DATA_COORDINATOR,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: str = "entry-1",
    installation_id: str | None = "00000000-0000-0000-0000-000000000001",
) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    data: dict = {
        "api_key": "sk-test",
        "base_url": "https://proxy.example.com",
    }
    if installation_id is not None:
        data[CONF_INSTALLATION_ID] = installation_id
    entry.data = data
    return entry


def _make_hass(entry_id: str = "entry-1", coordinator: object = None) -> MagicMock:
    hass = MagicMock()
    if coordinator is None:
        coordinator = MagicMock()
        # ``async_unload_entry`` awaits ``coordinator.async_shutdown()`` to
        # cancel the periodic refresh listener before popping ``hass.data``.
        # A plain ``MagicMock`` would raise ``TypeError: object MagicMock
        # can't be used in 'await' expression`` here, so install an
        # ``AsyncMock`` for that method.
        coordinator.async_shutdown = AsyncMock()
    hass.data = {
        DOMAIN: {
            entry_id: {DATA_COORDINATOR: coordinator},
        }
    }
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    return hass


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


class TestAsyncUnloadEntry:
    @pytest.mark.asyncio
    async def test_unload_returns_true_on_success(self) -> None:
        entry = _make_entry()
        hass = _make_hass(entry.entry_id)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_unload_pops_entry_from_hass_data(self) -> None:
        entry = _make_entry("entry-pop")
        coord = MagicMock()
        coord.async_shutdown = AsyncMock()  # awaited by async_unload_entry
        hass = _make_hass("entry-pop", coord)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        assert "entry-pop" in hass.data[DOMAIN]

        await async_unload_entry(hass, entry)

        assert "entry-pop" not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_false_does_not_pop_data(self) -> None:
        entry = _make_entry("entry-nopop")
        hass = _make_hass("entry-nopop")
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        await async_unload_entry(hass, entry)

        # Data should still be present since unload was not successful
        assert "entry-nopop" in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_calls_async_unload_platforms(self) -> None:
        from custom_components.codex_proxy import PLATFORMS

        entry = _make_entry()
        hass = _make_hass(entry.entry_id)

        await async_unload_entry(hass, entry)

        hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)

    @pytest.mark.asyncio
    async def test_unload_returns_false_when_platforms_fail(self) -> None:
        """When ``async_unload_platforms`` returns ``False`` (HA couldn't cleanly
        unload one of the platforms), ``async_unload_entry`` must propagate that
        ``False`` so HA knows the entry is still live and doesn't remove it from
        the registry."""
        entry = _make_entry()
        hass = _make_hass(entry.entry_id)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(hass, entry)

        assert result is False

    @pytest.mark.asyncio
    async def test_unload_safe_when_entry_absent_from_hass_data(self) -> None:
        """If the entry was already removed from ``hass.data[DOMAIN]`` before
        ``async_unload_entry`` is called (e.g. a double-unload race), the call
        must not raise ``KeyError`` — the ``pop`` is a no-op and the entry still
        unloads cleanly."""
        entry = _make_entry("entry-gone")
        hass = _make_hass(entry.entry_id)
        # Simulate pre-removed entry data
        hass.data[DOMAIN].pop("entry-gone", None)

        # Should not raise KeyError
        result = await async_unload_entry(hass, entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_unload_shuts_down_coordinator(self) -> None:
        """``async_unload_entry`` must await ``coordinator.async_shutdown()``
        before popping ``hass.data`` so the scheduled refresh listener
        registered by ``DataUpdateCoordinator.__init__`` is cancelled.

        Pre-v0.2.172 the unload path skipped this, so the next periodic tick
        still fired after unload and entered ``_async_update_data`` against a
        coordinator whose entry had been removed — any downstream lookup of
        ``hass.data[DOMAIN][entry.entry_id]`` raised ``KeyError`` and the HA
        log filled with spurious post-unload tracebacks on every reload."""
        entry = _make_entry("entry-shut")
        coord = MagicMock()
        coord.async_shutdown = AsyncMock()
        hass = _make_hass("entry-shut", coord)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        await async_unload_entry(hass, entry)

        coord.async_shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unload_does_not_shut_down_coordinator_on_failure(self) -> None:
        """When ``async_unload_platforms`` returns ``False`` (a platform refused
        to unload), the coordinator must NOT be shut down — the entry is still
        live and HA will retry the unload later.  Shutting the coordinator
        down early would leave the still-loaded platforms pointing at a dead
        coordinator and break their state updates."""
        entry = _make_entry("entry-keepalive")
        coord = MagicMock()
        coord.async_shutdown = AsyncMock()
        hass = _make_hass("entry-keepalive", coord)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        await async_unload_entry(hass, entry)

        coord.async_shutdown.assert_not_awaited()
