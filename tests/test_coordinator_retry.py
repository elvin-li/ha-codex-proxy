"""Tests for CodexModelCoordinator's _async_update_data retry / back-off logic.

We mock httpx at the call-site so we can simulate 5xx, timeout, DNS failure,
and bad JSON without a live proxy. asyncio.sleep is patched to avoid actually
waiting in tests.

Import order: stdlib → httpx → ha_stubs → homeassistant → codex_proxy.
httpx must be imported before ha_stubs (real library); ha_stubs must precede
all homeassistant imports so the stubs are registered first.
"""

# isort: skip_file
from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap HA stubs BEFORE any codex_proxy import
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
import httpx  # real httpx — coordinator uses it directly  # noqa: E402

import tests.ha_stubs  # noqa: F401, E402  — must precede ALL homeassistant imports
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402
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
    """Instantiate a coordinator with mocked HA deps (bypasses __init__)."""
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
    coord._http = MagicMock()  # httpx.AsyncClient mock
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
# Success path
# ---------------------------------------------------------------------------


class TestCoordinatorSuccess:
    @pytest.mark.asyncio
    async def test_returns_models_list_on_success(self) -> None:
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.5", "created": 100, "owned_by": "openai"},
                    {"id": "gpt-5.4", "created": 50, "owned_by": "openai"},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert "models" in result
        assert len(result["models"]) == 2

    @pytest.mark.asyncio
    async def test_return_dict_has_exactly_models_key(self) -> None:
        """_async_update_data must return a dict with exactly one key: 'models'.

        test_returns_models_list_on_success only checks that 'models' is present
        using ``in``; it passes even if extra keys are returned (e.g. a 'metadata'
        key added during a refactor).  The coordinator's data dict is consumed by
        chat_models, latest_chat_model_id, and diagnostics — all of which assume
        only 'models' is present.  Exact set equality here catches accidental
        additions to the return payload."""
        coord = _make_coordinator()
        response = _make_response(
            200, {"data": [{"id": "gpt-5.5", "created": 100, "owned_by": "openai"}]}
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert set(result.keys()) == {"models"}, (
            f"_async_update_data must return exactly {{'models'}}, got keys: {set(result.keys())!r}"
        )

    @pytest.mark.asyncio
    async def test_models_sorted_newest_first(self) -> None:
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.4", "created": 50},
                    {"id": "gpt-5.5", "created": 100},
                    {"id": "gpt-5.3", "created": 10},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        ids = [m["id"] for m in result["models"]]
        assert ids == ["gpt-5.5", "gpt-5.4", "gpt-5.3"]

    @pytest.mark.asyncio
    async def test_deduplication_on_success(self) -> None:
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.5", "created": 100},
                    {"id": "gpt-5.5", "created": 100},  # duplicate
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert len(result["models"]) == 1

    @pytest.mark.asyncio
    async def test_equal_timestamps_sorted_alphabetically(self) -> None:
        """When all proxy-reported models carry the same 'created' timestamp
        (commonly 0 from local gateways), _async_update_data must return them
        in deterministic alphabetical order by model id so that
        latest_chat_model_id is stable across polls even when the proxy
        changes its iteration order."""
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-z-model", "created": 0},
                    {"id": "gpt-a-model", "created": 0},
                    {"id": "gpt-m-model", "created": 0},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        ids = [m["id"] for m in result["models"]]
        assert ids == ["gpt-a-model", "gpt-m-model", "gpt-z-model"]

    @pytest.mark.asyncio
    async def test_non_dict_entries_skipped_without_crash(self) -> None:
        """A proxy returning a mixed list (dicts + bare strings) must not crash
        _async_update_data.  The non-dict entries must be silently ignored;
        valid dict entries must be processed normally."""
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.5", "created": 100},
                    "bare-string-entry",  # would crash .get() without isinstance guard
                    None,  # NoneType — same
                    42,  # int — same
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert len(result["models"]) == 1
        assert result["models"][0]["id"] == "gpt-5.5"


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
        coord._http.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException("timed out"),
                ok,
            ]
        )

        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()):
            result = await coord._async_update_data()

        assert result["models"][0]["id"] == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_raises_update_failed_after_max_retries(self) -> None:
        from custom_components.codex_proxy.const import COORDINATOR_MAX_RETRIES

        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            pytest.raises(UpdateFailed),
        ):
            await coord._async_update_data()

        # Must have attempted exactly COORDINATOR_MAX_RETRIES times (catches off-by-one
        # if the retry range is accidentally changed).
        assert coord._http.get.call_count == COORDINATOR_MAX_RETRIES

    @pytest.mark.asyncio
    async def test_sleep_called_between_retries(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        sleep_mock = AsyncMock()
        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock),
            pytest.raises(UpdateFailed),
        ):
            await coord._async_update_data()

        # Should have slept between retries (not after the final one)
        assert sleep_mock.call_count >= 1

    @pytest.mark.asyncio
    async def test_exhausted_retries_message_contains_url(self) -> None:
        """UpdateFailed raised after all retries are exhausted must include the
        proxy URL so operators with multiple Codex entries can identify the
        failing proxy from a single HA log line.

        Companion to TestCoordinatorNonTransient.test_connection_error_message_contains_url —
        together they ensure the URL invariant holds across both failure paths
        (immediate non-transient vs. exhausted retries)."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            pytest.raises(UpdateFailed) as exc_info,
        ):
            await coord._async_update_data()

        assert coord._url in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exhausted_retries_message_contains_error_type(self) -> None:
        """UpdateFailed raised after all retries must include the exception type
        name so operators can distinguish a timeout-exhausted entry from a
        5xx-exhausted entry without enabling coordinator DEBUG logging.

        The message format is 'Failed to fetch {url} after N attempts
        (last error: ExcType: message)'.  The existing
        test_exhausted_retries_message_contains_url only pins the URL portion;
        a refactor that dropped the ``type(last_err).__name__`` interpolation
        would still pass that test — producing an opaque '(last error: timed out)'
        with no type context.  This test closes the gap, mirroring
        test_retry_log_includes_error_type_for_timeout which covers the same
        invariant for the intermediate retry debug log."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            pytest.raises(UpdateFailed) as exc_info,
        ):
            await coord._async_update_data()

        assert "TimeoutException" in str(exc_info.value), (
            "UpdateFailed message after exhausted retries must include the exception "
            "type name ('TimeoutException') so operators can distinguish timeout "
            "failures from HTTP 5xx failures without enabling DEBUG logging"
        )

    @pytest.mark.asyncio
    async def test_exhausted_retries_message_contains_attempt_count(self) -> None:
        """The UpdateFailed message must include the exact attempt count so an
        operator can immediately see how many retries were made.

        The format is 'Failed to fetch {url} after {COORDINATOR_MAX_RETRIES}
        attempts (last error: …)'.  Existing tests pin the URL and error-type
        portions but neither verifies the count literal.  A refactor that
        accidentally hardcodes a different number (e.g. '1 attempt') or drops
        the count entirely would still pass those tests.

        We check ``str(COORDINATOR_MAX_RETRIES) in message`` so the test
        automatically tracks the constant — if someone changes the constant
        to 5 and forgets to update the error-message format string, this fails."""
        from custom_components.codex_proxy.const import COORDINATOR_MAX_RETRIES

        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            pytest.raises(UpdateFailed) as exc_info,
        ):
            await coord._async_update_data()

        msg = str(exc_info.value)
        assert str(COORDINATOR_MAX_RETRIES) in msg, (
            f"Expected attempt count '{COORDINATOR_MAX_RETRIES}' in UpdateFailed message, "
            f"got: {msg!r} — the message must reference the actual retry count from the const"
        )

    @pytest.mark.asyncio
    async def test_exhausted_retries_message_exact_format(self) -> None:
        """After all retries are exhausted, UpdateFailed must equal exactly:
        'Failed to fetch {url} after 3 attempts (last error: TimeoutException: timed out)'

        The three existing tests each check a different substring (URL, error
        type, attempt count); together they constrain the message but leave the
        surrounding prose unchecked.  For example, 'Could not reach {url} after
        3 attempts [TimeoutException: timed out]' would pass all three substring
        checks but use different wording that breaks log-parsing.  Exact equality
        pins everything in a single assertion."""
        from custom_components.codex_proxy.const import COORDINATOR_MAX_RETRIES

        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()),
            pytest.raises(UpdateFailed) as exc_info,
        ):
            await coord._async_update_data()

        expected = (
            f"Failed to fetch {coord._url} after {COORDINATOR_MAX_RETRIES} attempts "
            f"(last error: TimeoutException: timed out)"
        )
        assert str(exc_info.value) == expected, (
            f"Expected {expected!r}, got {str(exc_info.value)!r}"
        )


# ---------------------------------------------------------------------------
# Non-transient errors (immediate failure)
# ---------------------------------------------------------------------------


class TestCoordinatorNonTransient:
    @pytest.mark.asyncio
    async def test_connection_error_raises_immediately(self) -> None:
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with pytest.raises(UpdateFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_bad_json_raises_immediately(self) -> None:
        import json

        coord = _make_coordinator()
        bad_response = MagicMock()
        bad_response.raise_for_status.return_value = None
        # httpx raises json.JSONDecodeError (subclass of ValueError) on bad JSON
        bad_response.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        coord._http.get = AsyncMock(return_value=bad_response)

        with pytest.raises(UpdateFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_connection_error_does_not_retry(self) -> None:
        """ConnectError is non-transient — should NOT retry."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        sleep_mock = AsyncMock()
        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock),
            pytest.raises(UpdateFailed),
        ):
            await coord._async_update_data()

        # No sleep between retries — it failed immediately
        sleep_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_4xx_raises_immediately_without_retry(self) -> None:
        """HTTP 4xx (e.g. 401 Unauthorized) must NOT be retried."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_response(401))

        sleep_mock = AsyncMock()
        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=sleep_mock),
            pytest.raises(UpdateFailed),
        ):
            await coord._async_update_data()

        sleep_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_403_raises_immediately(self) -> None:
        """HTTP 403 Forbidden must also fail immediately."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(return_value=_make_response(403))

        with pytest.raises(UpdateFailed, match="403"):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_connection_error_message_contains_url(self) -> None:
        """UpdateFailed raised for a non-transient ConnectError must include
        the proxy URL so operators with multiple Codex entries can identify
        the failing proxy from a single HA log line without cross-referencing
        entry IDs."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with pytest.raises(UpdateFailed) as exc_info:
            await coord._async_update_data()

        assert coord._url in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error_message_exact_format(self) -> None:
        """UpdateFailed message for a ConnectError must follow exactly:
        'Failed to fetch {url}: ConnectError: {detail}'.

        test_connection_error_message_contains_url only checks that the URL
        is a substring — 'Proxy error (https://…): conn refused' would still
        pass.  Pinning the exact format ensures log-scraping scripts that
        parse 'Failed to fetch <url>:' from HA logs continue to work after
        any coordinator refactor."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        with pytest.raises(UpdateFailed) as exc_info:
            await coord._async_update_data()

        expected_msg = f"Failed to fetch {coord._url}: ConnectError: connection refused"
        assert str(exc_info.value) == expected_msg, (
            f"Expected {expected_msg!r}, got {str(exc_info.value)!r}"
        )

    @pytest.mark.asyncio
    async def test_5xx_still_retried(self) -> None:
        """HTTP 503 must still be retried (behaviour unchanged)."""
        coord = _make_coordinator()
        ok = _make_response(200, {"data": [{"id": "gpt-5.5", "created": 100}]})
        coord._http.get = AsyncMock(side_effect=[_make_response(503), ok])

        with patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=AsyncMock()):
            result = await coord._async_update_data()

        assert result["models"][0]["id"] == "gpt-5.5"


# ---------------------------------------------------------------------------
# Payload format resilience
# ---------------------------------------------------------------------------


class TestPayloadFormats:
    @pytest.mark.asyncio
    async def test_standard_data_wrapper(self) -> None:
        """{"object":"list","data":[...]} — standard OpenAI format."""
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "object": "list",
                "data": [{"id": "gpt-5.5", "created": 100}],
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()
        assert len(result["models"]) == 1
        assert result["models"][0]["id"] == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_bare_list_payload(self) -> None:
        """Some proxies return a bare JSON array instead of {"data":[...]}."""
        coord = _make_coordinator()
        bare_response = MagicMock()
        bare_response.raise_for_status.return_value = None
        bare_response.json.return_value = [{"id": "gpt-5.5", "created": 100}]
        coord._http.get = AsyncMock(return_value=bare_response)

        result = await coord._async_update_data()
        assert len(result["models"]) == 1
        assert result["models"][0]["id"] == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_empty_data_list(self) -> None:
        """Empty model list returns empty models dict."""
        coord = _make_coordinator()
        response = _make_response(200, {"data": []})
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()
        assert result["models"] == []

    @pytest.mark.asyncio
    async def test_non_list_payload_treated_as_empty(self) -> None:
        """A scalar JSON value (e.g. null) should not crash the coordinator."""
        coord = _make_coordinator()
        bad_response = MagicMock()
        bad_response.raise_for_status.return_value = None
        bad_response.json.return_value = None  # scalar — not a dict or list
        coord._http.get = AsyncMock(return_value=bad_response)

        result = await coord._async_update_data()
        assert result["models"] == []

    @pytest.mark.asyncio
    async def test_non_numeric_created_field_does_not_crash(self) -> None:
        """If a proxy returns a non-numeric 'created' value (e.g. an ISO date
        string), the coordinator must degrade gracefully to created=0 rather
        than raising ValueError and crashing the entire update."""
        coord = _make_coordinator()
        response = _make_response(
            200,
            {"data": [{"id": "gpt-5.5", "created": "2024-01-01"}]},
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert len(result["models"]) == 1
        assert result["models"][0]["id"] == "gpt-5.5"
        assert result["models"][0]["created"] == 0  # fell back to 0

    @pytest.mark.asyncio
    async def test_numeric_string_created_is_parsed(self) -> None:
        """A stringified epoch timestamp must still sort correctly."""
        coord = _make_coordinator()
        response = _make_response(
            200,
            {
                "data": [
                    {"id": "gpt-5.5", "created": "1700000000"},
                    {"id": "gpt-5.4", "created": "1600000000"},
                ]
            },
        )
        coord._http.get = AsyncMock(return_value=response)

        result = await coord._async_update_data()

        assert result["models"][0]["id"] == "gpt-5.5"  # newer first
        assert result["models"][0]["created"] == 1_700_000_000


# ---------------------------------------------------------------------------
# Retry delay safe access
# ---------------------------------------------------------------------------


class TestRetryDelayClamping:
    @pytest.mark.asyncio
    async def test_sleep_called_with_expected_delays(self) -> None:
        """With COORDINATOR_MAX_RETRIES=3 and COORDINATOR_RETRY_DELAYS=(5, 30),
        two sleeps should occur with the exact delay values from the table."""
        coord = _make_coordinator()
        coord._http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        sleep_delays: list = []

        async def capture_sleep(delay: float) -> None:
            sleep_delays.append(delay)

        with (
            patch("custom_components.codex_proxy.coordinator.asyncio.sleep", new=capture_sleep),
            pytest.raises(UpdateFailed),
        ):
            await coord._async_update_data()

        # COORDINATOR_MAX_RETRIES=3 means 2 sleeps (between attempt 0→1 and 1→2)
        from custom_components.codex_proxy.const import COORDINATOR_RETRY_DELAYS

        assert len(sleep_delays) == 2
        assert sleep_delays[0] == COORDINATOR_RETRY_DELAYS[0]
        assert sleep_delays[1] == COORDINATOR_RETRY_DELAYS[1]
