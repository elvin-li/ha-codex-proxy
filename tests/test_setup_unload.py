"""Tests for async_setup_entry, async_unload_entry, and _async_update_listener
in custom_components/codex_proxy/__init__.py.

Runs without a full HA install — all HA modules are mocked via ha_stubs.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy import (  # noqa: E402
    async_unload_entry,
    _async_update_listener,
)
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
    hass.data = {
        DOMAIN: {
            entry_id: {DATA_COORDINATOR: coordinator or MagicMock()},
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


# ---------------------------------------------------------------------------
# _async_update_listener
# ---------------------------------------------------------------------------


class TestAsyncUpdateListener:
    @pytest.mark.asyncio
    async def test_calls_async_reload_with_entry_id(self) -> None:
        entry = _make_entry("entry-reload")
        hass = MagicMock()
        hass.config_entries.async_reload = AsyncMock()

        await _async_update_listener(hass, entry)

        hass.config_entries.async_reload.assert_awaited_once_with("entry-reload")

    @pytest.mark.asyncio
    async def test_reload_called_exactly_once(self) -> None:
        entry = _make_entry("entry-once")
        hass = MagicMock()
        hass.config_entries.async_reload = AsyncMock()

        await _async_update_listener(hass, entry)

        assert hass.config_entries.async_reload.await_count == 1
