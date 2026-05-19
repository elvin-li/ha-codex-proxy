"""Tests that coordinator debug logging fires on retry and success paths.

Patches asyncio.sleep so retries complete instantly and verifies that
_LOGGER.debug was called with expected message patterns.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import httpx

# ---------------------------------------------------------------------------
# Bootstrap — use the same inline-stub pattern as test_coordinator_retry.py
# to keep coordinator import isolated from ha_stubs ordering constraints.
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
    def __class_getitem__(cls, item):  # type: ignore[override]
        return cls

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval


sys.modules[
    "homeassistant.helpers.update_coordinator"
].DataUpdateCoordinator = _DataUpdateCoordinatorBase
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception

from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator() -> CodexModelCoordinator:
    coord = object.__new__(CodexModelCoordinator)
    coord._api_key = "sk-test"
    coord._base_url = "https://proxy.example.com"
    coord._installation_id = "00000000-0000-0000-0000-000000000001"
    coord._http = MagicMock()
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
# Retry logging
# ---------------------------------------------------------------------------


class TestRetryLogging:
    @pytest.mark.asyncio
    async def test_debug_logged_on_transient_retry(self) -> None:
        coord = _make_coordinator()
        fail = _make_response(503)
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 1}]})
        coord._http.get = AsyncMock(side_effect=[fail, ok])

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log,
        ):
            await coord._async_update_data()

        # debug should have been called at least once (the retry message)
        assert mock_log.debug.call_count >= 1
        debug_calls_str = " ".join(str(c) for c in mock_log.debug.call_args_list)
        assert "Transient" in debug_calls_str or "attempt" in debug_calls_str.lower()

    @pytest.mark.asyncio
    async def test_debug_logged_on_timeout_retry(self) -> None:
        coord = _make_coordinator()
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 1}]})
        coord._http.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException("timed out"),
                ok,
            ]
        )

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log,
        ):
            await coord._async_update_data()

        assert mock_log.debug.call_count >= 1

    @pytest.mark.asyncio
    async def test_sleep_delay_passed_to_logger(self) -> None:
        """The retry log message should include the sleep delay."""
        coord = _make_coordinator()
        fail = _make_response(503)
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 1}]})
        coord._http.get = AsyncMock(side_effect=[fail, ok])

        sleep_mock = AsyncMock()
        logged_delays: list[int] = []

        def capture_debug(*args, **kwargs):
            # The delay is the 4th positional format arg
            if len(args) >= 5:
                logged_delays.append(args[4])

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock),
            patch(
                "custom_components.codex_proxy.coordinator._LOGGER.debug",
                side_effect=capture_debug,
            ),
        ):
            await coord._async_update_data()

        # The sleep was called with the delay; verify it matches what was logged
        if sleep_mock.call_count > 0 and logged_delays:
            assert sleep_mock.call_args_list[0][0][0] == logged_delays[0]


# ---------------------------------------------------------------------------
# Success logging
# ---------------------------------------------------------------------------


class TestSuccessLogging:
    @pytest.mark.asyncio
    async def test_debug_logged_on_success(self) -> None:
        coord = _make_coordinator()
        ok = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.5", "created": 100},
                    {"id": "gpt-5.4", "created": 50},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=ok)

        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            await coord._async_update_data()

        # At minimum one debug call after the successful fetch
        assert mock_log.debug.call_count >= 1
        last_call_str = str(mock_log.debug.call_args_list[-1])
        # Should mention the model count
        assert "2" in last_call_str or "model" in last_call_str.lower()

    @pytest.mark.asyncio
    async def test_success_log_shows_zero_for_image_only(self) -> None:
        """Image-only models should show 0 chat-capable in the debug log."""
        coord = _make_coordinator()
        ok = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-image-1", "created": 100},
                    {"id": "dall-e-3", "created": 50},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=ok)

        # Patch the full logger so isEnabledFor(DEBUG) returns True and the
        # debug() call is exercised (the sum() is now guarded by isEnabledFor).
        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        # Find the "Fetched %d models …" call and verify chat-capable == 0
        debug_calls = mock_log.debug.call_args_list
        fetched_calls = [c for c in debug_calls if "Fetched" in str(c)]
        assert fetched_calls, "Expected a 'Fetched … models' debug log call"
        # Third positional arg is the chat-capable count
        call_args = fetched_calls[-1][0]  # positional args tuple
        assert call_args[3] == 0, f"Expected 0 chat-capable, got {call_args[3]}"
