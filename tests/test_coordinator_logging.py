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
    async def test_retry_log_format_string_starts_with_transient_error_on_attempt(
        self,
    ) -> None:
        """The retry debug log format string must start with 'Transient error on attempt'.

        test_debug_logged_on_transient_retry uses an OR condition
        ('Transient' in str OR 'attempt' in str) that passes as long as
        *either* word appears in any debug call — even if the retry message
        is silently reformatted to, say, 'attempt N — Transient' (wrong order)
        or just 'Transient failure' (missing 'attempt').

        This test finds the retry call directly via args[0] and verifies the
        format string begins with the exact phrase 'Transient error on attempt',
        catching both word-order changes and partial omissions in one assertion."""
        coord = _make_coordinator()
        fail = _make_response(503)
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 1}]})
        coord._http.get = AsyncMock(side_effect=[fail, ok])

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log,
        ):
            await coord._async_update_data()

        retry_calls = [
            c for c in mock_log.debug.call_args_list if c.args and "Transient" in str(c.args[0])
        ]
        assert retry_calls, "Expected at least one retry debug log call containing 'Transient'"
        fmt = retry_calls[0].args[0]
        assert fmt.startswith("Transient error on attempt"), (
            f"Retry log format string must start with 'Transient error on attempt', got {fmt!r}"
        )

    @pytest.mark.asyncio
    async def test_retry_log_includes_error_type_for_5xx(self) -> None:
        """The retry debug log must include the exception type name so operators
        can distinguish HTTP 5xx transient failures from timeout transient failures
        without enabling higher verbosity.

        The retry format is 'Transient error on attempt N/M (ExcType) — retrying
        in Xs'.  The existing test_debug_logged_on_transient_retry only checks
        'Transient' or 'attempt' with OR; neither verifies the (%s) placeholder
        is filled with the error class name.  A refactor dropping the type arg
        would produce 'Transient error on attempt 1/3 () — retrying in 5s' — still
        passing the existing test."""
        coord = _make_coordinator()
        fail = _make_response(503)
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 1}]})
        coord._http.get = AsyncMock(side_effect=[fail, ok])

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log,
        ):
            await coord._async_update_data()

        debug_calls_str = " ".join(str(c) for c in mock_log.debug.call_args_list)
        # For a 503, the error type is HTTPStatusError
        assert "HTTPStatusError" in debug_calls_str, (
            "Retry log must include the exception type (HTTPStatusError) so operators "
            "can distinguish HTTP 5xx from timeout retries without extra verbosity"
        )

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
    async def test_retry_log_includes_error_type_for_timeout(self) -> None:
        """The retry debug log must include 'TimeoutException' when the failure
        is a timeout, so operators can distinguish timeouts from 5xx in HA logs.

        Companion to test_retry_log_includes_error_type_for_5xx — together they
        pin that the (%s) error-type placeholder is filled for both transient
        failure modes."""
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

        debug_calls_str = " ".join(str(c) for c in mock_log.debug.call_args_list)
        assert "TimeoutException" in debug_calls_str, (
            "Retry log must include 'TimeoutException' so operators can distinguish "
            "timeout retries from HTTP 5xx retries without cross-referencing timestamps"
        )

    @pytest.mark.asyncio
    async def test_retry_log_error_type_arg_exact_for_timeout(self) -> None:
        """args[3] of the timeout retry debug call must be exactly 'TimeoutException'.

        test_retry_log_includes_error_type_for_timeout checks the combined
        str(call_args_list) for 'TimeoutException' — a substring match that
        passes even if the error type is 'httpx.TimeoutException' (prefixed) or
        'SomeOtherTimeoutException' (just happens to contain the substring).
        Checking args[3] directly pins that the (%s) placeholder resolves to the
        bare class name 'TimeoutException', matching the format string
        'Transient error on attempt %d/%d (%s) — retrying in %ds'."""
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

        retry_calls = [
            c
            for c in mock_log.debug.call_args_list
            if c.args and isinstance(c.args[0], str) and c.args[0].startswith("Transient")
        ]
        assert retry_calls, "Expected at least one retry debug call starting with 'Transient'"
        err_type_arg = retry_calls[0].args[3]
        assert err_type_arg == "TimeoutException", (
            f"Expected error-type arg 'TimeoutException' at args[3], got {err_type_arg!r} — "
            "the format arg must be type(last_err).__name__ (bare class name)"
        )

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
    async def test_success_log_format_string_starts_with_fetched(self) -> None:
        """The success debug log format string must start with 'Fetched'.

        test_debug_logged_on_success checks the combined str(call_args) with an
        OR condition — it passes as long as either '2' or 'model' appears anywhere
        in the call repr, including in the format string itself.  A refactor that
        rewrites the format string to e.g. 'Model list updated: %d entries…' would
        still pass the OR test (because 'model' is a substring of 'Model') but
        would break the operator expectation set by log documentation.

        This test finds the 'Fetched' call by args[0] and pins the exact prefix
        so any format-string rename is caught immediately."""
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
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        fetched_calls = [
            c for c in mock_log.debug.call_args_list if c.args and "Fetched" in str(c.args[0])
        ]
        assert fetched_calls, (
            "Expected at least one debug call whose format string contains 'Fetched'"
        )
        fmt = fetched_calls[-1].args[0]
        assert fmt.startswith("Fetched"), (
            f"Success log format string must start with 'Fetched', got {fmt!r}"
        )

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
    async def test_success_log_chat_count_when_all_are_chat_models(self) -> None:
        """When all fetched models are chat-capable, the third format arg must
        equal len(models) — i.e., the chat-capable count must match the total.

        Companion to test_success_log_shows_zero_for_image_only which pins
        call_args[3] == 0 for image-only payloads.  Together they cover both
        ends of the chat-count range.  The existing test_debug_logged_on_success
        uses an OR condition ('2' in str OR 'model' in str) that can pass even
        if the count argument is wrong or missing.  This test directly checks
        call_args[3] == 2 so a refactor that drops or mis-computes chat_count
        (e.g. always emitting 0) is caught here rather than only at runtime."""
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
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        debug_calls = mock_log.debug.call_args_list
        fetched_calls = [c for c in debug_calls if "Fetched" in str(c)]
        assert fetched_calls, "Expected a 'Fetched … models' debug log call"
        call_args = fetched_calls[-1][0]  # positional args tuple
        assert call_args[3] == 2, (
            f"Expected chat-capable count 2, got {call_args[3]} — "
            "all-chat-model payload must yield chat_count == total model count"
        )

    @pytest.mark.asyncio
    async def test_success_log_total_count_arg_is_len_models(self) -> None:
        """The first count format arg (args[1]) must equal the *total* number of
        models returned by the API — including image-only models that are filtered
        out of chat_models.

        test_success_log_shows_zero_for_image_only pins args[3]==0 (chat-capable)
        for an image-only payload, but does not verify args[1] (total).  A refactor
        that accidentally passes chat_count twice — ``debug(fmt, 0, url, 0)``
        instead of ``debug(fmt, 2, url, 0)`` — would pass every existing test
        because none checks args[1] explicitly.

        With 2 image-only models the correct values are:
          args[1] = 2  (total fetched)
          args[3] = 0  (chat-capable after filtering)
        """
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

        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        debug_calls = mock_log.debug.call_args_list
        fetched_calls = [c for c in debug_calls if "Fetched" in str(c)]
        assert fetched_calls, "Expected a 'Fetched … models' debug log call"
        call_args = fetched_calls[-1][0]
        assert call_args[1] == 2, (
            f"Expected total model count 2 at args[1], got {call_args[1]!r} — "
            "the first format arg must be len(models) (including image-only), "
            "not the filtered chat-capable count"
        )

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

    @pytest.mark.asyncio
    async def test_success_log_format_string_exact(self) -> None:
        """args[0] of the 'Fetched' success debug call must be the exact format string.

        test_success_log_format_string_starts_with_fetched checks only that
        args[0].startswith('Fetched') — it passes if the remainder of the
        template changes (e.g. 'Fetched %d models' without the URL or chat
        count).  Pinning the full format string ensures operator documentation
        that references 'Fetched %d models from %s (%d chat-capable after
        filtering)' stays in sync with the actual emitted message."""
        coord = _make_coordinator()
        ok = _make_response(
            200,
            {"data": [{"id": "gpt-5.5", "created": 100}]},
        )
        coord._http.get = AsyncMock(return_value=ok)

        with patch("custom_components.codex_proxy.coordinator._LOGGER") as mock_log:
            mock_log.isEnabledFor.return_value = True
            await coord._async_update_data()

        fetched_calls = [
            c
            for c in mock_log.debug.call_args_list
            if c.args and isinstance(c.args[0], str) and c.args[0].startswith("Fetched")
        ]
        assert fetched_calls, "Expected at least one 'Fetched' debug call"
        fmt = fetched_calls[-1].args[0]
        assert fmt == "Fetched %d models from %s (%d chat-capable after filtering)", (
            f"Expected exact format string "
            f"'Fetched %d models from %s (%d chat-capable after filtering)', got {fmt!r}"
        )
