"""Tests for CodexModelCoordinator's _async_update_data retry / back-off logic.

We mock httpx at the call-site so we can simulate 5xx, timeout, DNS failure,
and bad JSON without a live proxy. asyncio.sleep is patched to avoid actually
waiting in tests.
"""
from __future__ import annotations

import asyncio
import sys
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.openai_conversation",
    "homeassistant.components.openai_conversation.const",
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
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

class _DataUpdateCoordinatorBase:
    """Minimal stand-in for DataUpdateCoordinator that supports generic syntax."""

    def __class_getitem__(cls, item):  # type: ignore[override]
        return cls

    def __init__(self, hass, logger, name, update_interval):  # type: ignore[override]
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval


sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = (
    _DataUpdateCoordinatorBase
)
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception


import httpx  # real httpx — coordinator uses it directly  # noqa: E402

from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator() -> CodexModelCoordinator:
    """Instantiate a coordinator with mocked HA deps."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        "api_key": "sk-test",
        "base_url": "https://proxy.example.com",
    }

    coord = object.__new__(CodexModelCoordinator)
    coord._api_key = "sk-test"
    coord._base_url = "https://proxy.example.com"
    coord._installation_id = "00000000-0000-0000-0000-000000000001"
    coord._http = MagicMock()  # httpx.AsyncClient mock
    coord.logger = MagicMock()
    return coord


def _make_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {"data": []}
    if status_code >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=MagicMock()
        )
    else:
        r.raise_for_status.return_value = None
    return r


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestCoordinatorSuccess:
    @pytest.mark.asyncio
    async def test_returns_models_list_on_success(self) -> None:
        coord = _make_coordinator()
        response = _make_response(200, {
            "data": [
                {"id": "gpt-5.5", "created": 100, "owned_by": "openai"},
                {"id": "gpt-5.4", "created": 50, "owned_by": "openai"},
            ]
        })
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert "models" in result
        assert len(result["models"]) == 2

    @pytest.mark.asyncio
    async def test_models_sorted_newest_first(self) -> None:
        coord = _make_coordinator()
        response = _make_response(200, {
            "data": [
                {"id": "gpt-5.4", "created": 50},
                {"id": "gpt-5.5", "created": 100},
                {"id": "gpt-5.3", "created": 10},
            ]
        })
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        ids = [m["id"] for m in result["models"]]
        assert ids == ["gpt-5.5", "gpt-5.4", "gpt-5.3"]

    @pytest.mark.asyncio
    async def test_deduplication_on_success(self) -> None:
        coord = _make_coordinator()
        response = _make_response(200, {
            "data": [
                {"id": "gpt-5.5", "created": 100},
                {"id": "gpt-5.5", "created": 100},  # duplicate
            ]
        })
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert len(result["models"]) == 1


# ---------------------------------------------------------------------------
# Retry / back-off (transient errors)
# ---------------------------------------------------------------------------


class TestCoordinatorRetry:
    @pytest.mark.asyncio
    async def test_retries_on_5xx_and_succeeds(self) -> None:
        coord = _make_coordinator()
        fail = _make_response(503)
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 100}]})
        coord._http.get = AsyncMock(side_effect=[fail, ok])

        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()):
            result = await coord._async_update_data()

        assert result["models"][0]["id"] == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_retries_on_timeout_and_succeeds(self) -> None:
        coord = _make_coordinator()
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 100}]})
        coord._http.get = AsyncMock(side_effect=[
            httpx.TimeoutException("timed out"),
            ok,
        ])

        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()):
            result = await coord._async_update_data()

        assert result["models"][0]["id"] == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_raises_update_failed_after_max_retries(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(Exception):  # UpdateFailed (mocked as Exception)
                await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_sleep_called_between_retries(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )

        sleep_mock = AsyncMock()
        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock):
            with pytest.raises(Exception):
                await coord._async_update_data()

        # Should have slept between retries (not after the final one)
        assert sleep_mock.call_count >= 1


# ---------------------------------------------------------------------------
# Non-transient errors (immediate failure)
# ---------------------------------------------------------------------------


class TestCoordinatorNonTransient:
    @pytest.mark.asyncio
    async def test_connection_error_raises_immediately(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with pytest.raises(Exception):  # UpdateFailed
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_bad_json_raises_immediately(self) -> None:
        coord = _make_coordinator()
        bad_response = MagicMock()
        bad_response.raise_for_status.return_value = None
        bad_response.json.side_effect = ValueError("bad json")
        coord._http.get = AsyncMock(return_value=bad_response)

        with pytest.raises(Exception):  # UpdateFailed
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_connection_error_does_not_retry(self) -> None:
        """ConnectError is non-transient — should NOT retry."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )

        sleep_mock = AsyncMock()
        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock):
            with pytest.raises(Exception):
                await coord._async_update_data()

        # No sleep between retries — it failed immediately
        sleep_mock.assert_not_called()
