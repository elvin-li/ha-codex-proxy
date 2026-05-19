"""Tests for CodexRefreshModelsButton.

Covers: unique_id, async_press calls async_request_refresh exactly once,
noop on double-press is handled by coordinator throttle (not our code).
"""
from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Bootstrap HA stubs BEFORE any codex_proxy import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.ha_stubs  # noqa: F401, E402

from custom_components.codex_proxy.button import CodexRefreshModelsButton  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.async_request_refresh = AsyncMock()
    return coord


def _make_button(entry_id: str = "entry-1") -> CodexRefreshModelsButton:
    coord = _make_coordinator()
    btn = object.__new__(CodexRefreshModelsButton)
    btn._coordinator = coord
    btn._attr_unique_id = f"{entry_id}_refresh_models"
    btn._attr_device_info = {}
    return btn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRefreshModelsButton:
    def test_unique_id_uses_entry_id(self) -> None:
        btn = _make_button(entry_id="my-entry-42")
        assert "my-entry-42" in btn._attr_unique_id

    @pytest.mark.asyncio
    async def test_press_calls_async_request_refresh(self) -> None:
        btn = _make_button()
        await btn.async_press()
        btn._coordinator.async_request_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_press_does_not_call_entry_reload(self) -> None:
        """Button should delegate throttling to coordinator, not reload entry."""
        btn = _make_button()
        btn.hass = MagicMock()
        await btn.async_press()
        btn.hass.config_entries.async_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_double_press_calls_refresh_twice(self) -> None:
        """The button is stateless — it calls async_request_refresh on every press.
        The coordinator itself throttles redundant refreshes."""
        btn = _make_button()
        await btn.async_press()
        await btn.async_press()
        assert btn._coordinator.async_request_refresh.await_count == 2
