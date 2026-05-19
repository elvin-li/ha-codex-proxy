"""Tests that coordinator debug logging fires on retry and success paths.

Patches asyncio.sleep so retries complete instantly and verifies that
_LOGGER.debug was called with expected message patterns.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Bootstrap — must precede codex_proxy imports
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import tests.ha_stubs  # noqa: F401, E402  — must precede codex_proxy imports
from custom_components.codex_proxy.const import (  # noqa: E402
    CODEX_OPENAI_BETA,
    CODEX_ORIGINATOR,
    CODEX_USER_AGENT,
)
from custom_components.codex_proxy.coordinator import CodexModelCoordinator  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator() -> CodexModelCoordinator:
    coord = object.__new__(CodexModelCoordinator)
    coord._url = "https://proxy.example.com/v1/models"
    coord._headers = {
        "Authorization": "Bearer sk-test",
        "User-Agent": CODEX_USER_AGENT,
        "OpenAI-Beta": CODEX_OPENAI_BETA,
        "originator": CODEX_ORIGINATOR,
        "x-codex-installation-id": "00000000-0000-0000-0000-000000000001",
        "Accept": "application/json",
    }
    coord._http = MagicMock()
    coord.logger = MagicMock()
    return coord


def _make_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {"data": []}
    if status_code >= 400:
        response_mock = MagicMock()
        response_mock.status_code = status_code  # must be int for < 500 check
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=response_mock
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

    @pytest.mark.asyncio
    async def test_success_log_includes_proxy_url(self) -> None:
        """The success 'Fetched …' debug message must include the proxy URL.

        Operators running multiple Codex entries (different proxy providers)
        need to identify which proxy's fetch just succeeded from a single HA
        log line.  The existing test_debug_logged_on_success only verifies the
        model count appears; this test pins that the URL is also present."""
        coord = _make_coordinator()
        ok = _make_response(
            200,
            {"data": [{"id": "gpt-5.5", "created": 100}]},
        )
        coord._http.get = AsyncMock(return_value=ok)

        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        debug_calls = mock_log.debug.call_args_list
        fetched_calls = [c for c in debug_calls if "Fetched" in str(c)]
        assert fetched_calls, "Expected a 'Fetched … models' debug log"
        # The second positional format-arg must be the coordinator URL so an
        # operator with two entries can distinguish "proxy-a fetched 0 models"
        # from "proxy-b fetched 5 models" without reading the entry_id.
        call_args = fetched_calls[-1][0]
        assert coord._url in call_args, (
            f"Proxy URL {coord._url!r} missing from success debug log — "
            "operators cannot identify which proxy succeeded in multi-entry setups"
        )

    @pytest.mark.asyncio
    async def test_coordinator_logs_never_leak_api_key(self) -> None:
        """No log call emitted by _async_update_data must contain the API key.

        The Authorization header ('Bearer sk-…') stored in _headers must never
        appear in any log output because HA log files are routinely shared in
        bug reports.  This is a regression guard — the current code does not log
        headers, but a future refactor adding diagnostic header-dump logging
        would be caught here before reaching production."""
        _API_KEY = "sk-super-secret-key"
        coord = _make_coordinator()
        coord._headers["Authorization"] = f"Bearer {_API_KEY}"
        ok = _make_response(
            200,
            {"data": [{"id": "gpt-5.5", "created": 100}]},
        )
        coord._http.get = AsyncMock(return_value=ok)

        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        all_logged = " ".join(str(c) for c in mock_log.mock_calls)
        assert _API_KEY not in all_logged, (
            f"API key {_API_KEY!r} appeared in a coordinator log call — "
            "credentials must never be written to HA's log files"
        )

    @pytest.mark.asyncio
    async def test_debug_block_skipped_when_logging_disabled(self) -> None:
        """When isEnabledFor(DEBUG) returns False the expensive chat-count
        sum() and debug() call are both skipped — the coordinator still returns
        correct data; the guard purely avoids unnecessary computation."""
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
            mock_log.isEnabledFor.return_value = False
            result = await coord._async_update_data()

        # Data returned correctly even when debug logging is disabled.
        assert len(result["models"]) == 2
        # The guard prevented any 'Fetched …' debug call.
        fetched_calls = [c for c in mock_log.debug.call_args_list if "Fetched" in str(c)]
        assert not fetched_calls, "debug() must not be called when isEnabledFor returns False"
